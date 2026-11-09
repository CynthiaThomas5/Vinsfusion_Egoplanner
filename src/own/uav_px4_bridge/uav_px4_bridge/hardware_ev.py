"""Hardware EV-only path hosted by the existing, sole PX4 bridge node."""
import json
import time

from nav_msgs.msg import Odometry
from rclpy.serialization import deserialize_message
from px4_msgs.msg import (TimesyncStatus, VehicleOdometry, VehicleAttitude,
                          VehicleLocalPosition, EstimatorStatusFlags)
from rclpy.clock import Clock, ClockType
from rclpy.qos import (qos_profile_sensor_data, QoSProfile, ReliabilityPolicy,
                       DurabilityPolicy)
from std_msgs.msg import String
from uav_interfaces.msg import LocalizationStatus
from uav_sim.geometry import load_rig

from .rigid_body import mount_rotation_translation
from .ev_reference import EVNEDReference
from .time_mapping import SystemClockMapper, TimeMappingError, retain_hardware_sync
from .vision_odometry import odometry_to_px4_values


class HardwareEVPath:
    def __init__(self, node, config, profile, frames, rig_path, mode):
        if mode != 'ev_only':
            raise ValueError('Hardware control requires completed HW08 installation/control qualification')
        if (profile.get('name') != 'vio_closed_loop'
                or profile.get('ground_truth_online_allowed') is not False):
            raise ValueError('Hardware EV requires the isolated VINS profile')
        required = {'vehicle_odometry_topic': '/fmu/in/vehicle_visual_odometry',
                    'timesync_status_topic': '/fmu/out/timesync_status',
                    'optimized_odometry_topic': '/localization/optimized_imu_odom',
                    'localization_status_topic': '/localization/status'}
        if any(config.get(key) != value for key, value in required.items()):
            raise ValueError('Hardware EV requires canonical localization/EV topics')
        if node.get_parameter('use_sim_time').value:
            raise ValueError('Hardware bridge requires use_sim_time=False')
        if not rig_path or node.get_parameter('mount_model_sdf').value:
            raise ValueError('Hardware EV requires rig_config without a simulation SDF')
        rig = load_rig(rig_path)
        if rig['source_kind'] != 'hardware_json':
            raise ValueError('Hardware EV requires a hardware JSON rig')
        self.mount = rig['airframe_mount']
        self.matrix = self.mount.get('T_airframe_imu')
        if self.mount.get('status') == 'MEASURED':
            mount_rotation_translation(self.matrix)
        elif node.get_parameter('allow_approximate_bench_ev').value:
            self.matrix = self.mount['bench_observation']['approximate_transform']['T_fc_imu_candidate']
            mount_rotation_translation(self.matrix)
            node.get_logger().warning('USER-AUTHORIZED BENCH EV: approximate flexible-board mount; not flight qualified')
        else:
            self.matrix = None
        self.node, self.config, self.profile, self.frames = node, config, profile, frames
        self.ev_topic = config.get('ev_odometry_topic', config['optimized_odometry_topic'])
        if self.ev_topic not in ('/localization/imu_odom', '/localization/optimized_imu_odom'):
            raise ValueError('Hardware EV requires canonical localization odometry')
        self.reference_mode=config.get('ev_reference_mode','local_frd')
        if self.reference_mode not in ('local_frd','px4_local_ned'):raise ValueError('Unknown EV reference mode')
        self.ned_reference=EVNEDReference() if self.reference_mode=='px4_local_ned' else None
        self.reference_attempt_ns={}
        self.last_ev_attempt_mono = None
        self.mapper = SystemClockMapper(config['source_age_budget_s'],
                                        config['max_future_s'], config['max_clock_step_s'], config.get('enforce_source_age', True))
        self.timesync = self.health = None
        self.sync_receipt = self.health_receipt = None
        self.epoch = None
        self.last_stamp = None
        self.last_receipt = self.last_source = None
        self.fault = ''
        self.reason = 'airframe_mount_unmeasured' if self.matrix is None else 'waiting_for_localization'
        self.count = 0
        self.last_ages = None
        self.ev_pub = node.create_publisher(VehicleOdometry, config['vehicle_odometry_topic'],
                                            qos_profile_sensor_data)
        self.detail_pub = node.create_publisher(String, config['status_topic'], 10)
        self.subscriptions = [
            node.create_subscription(TimesyncStatus, config['timesync_status_topic'],
                                     self.on_timesync, qos_profile_sensor_data),
            node.create_subscription(Odometry, self.ev_topic,
                                     self.on_serialized_odometry if self.ev_topic == '/localization/imu_odom' else self.on_odometry,
                                     qos_profile_sensor_data, raw=self.ev_topic == '/localization/imu_odom'),
            node.create_subscription(LocalizationStatus, config['localization_status_topic'],
                                     self.on_health, QoSProfile(depth=1,
                                         reliability=ReliabilityPolicy.RELIABLE,
                                         durability=DurabilityPolicy.TRANSIENT_LOCAL))]
        if self.ned_reference is not None:
            for kind,typ,topic in [('attitude',VehicleAttitude,'/fmu/out/vehicle_attitude'),
                    ('local',VehicleLocalPosition,'/fmu/out/vehicle_local_position_v1'),
                    ('flags',EstimatorStatusFlags,'/fmu/out/estimator_status_flags')]:
                self.subscriptions.append(node.create_subscription(typ,topic,
                    lambda data,k=kind,t=typ:self.on_reference(k,data,t),qos_profile_sensor_data,raw=True))
        self.clock = Clock(clock_type=ClockType.STEADY_TIME)
        self.timer = node.create_timer(.05, self.tick, clock=self.clock)

    def on_reference(self, kind, data, typ):
        now=time.monotonic_ns()
        if self.ned_reference.alignment is None and now-self.reference_attempt_ns.get(kind,0)>=50000000:
            self.reference_attempt_ns[kind]=now
            self.ned_reference.update(kind,deserialize_message(data,typ),now)

    def on_timesync(self, msg):
        self.latest_timesync = msg
        self.timesync, self.sync_receipt = retain_hardware_sync(
            self.timesync, self.sync_receipt, msg, time.monotonic_ns(), time.time_ns(), self.config)

    def on_health(self, msg):
        if self.epoch is not None and msg.epoch != self.epoch:
            self.fault = 'localization_epoch_changed'
        self.health, self.health_receipt = msg, time.monotonic_ns()

    def on_serialized_odometry(self, data):
        rate = self.config.get('ev_rate_hz', 0)
        if rate and self.last_ev_attempt_mono is not None and (time.monotonic_ns()-self.last_ev_attempt_mono)/1e9 < 1./rate:
            return
        self.on_odometry(deserialize_message(data, Odometry))

    def on_odometry(self, msg):
        mono, system = time.monotonic_ns(), time.time_ns()
        rate = self.config.get('ev_rate_hz', 0)
        if rate and self.last_ev_attempt_mono is not None and (mono-self.last_ev_attempt_mono)/1e9 < 1./rate:
            return
        self.last_ev_attempt_mono = mono
        stamp = msg.header.stamp.sec*1_000_000_000+msg.header.stamp.nanosec
        self.last_receipt, self.last_source = mono, stamp
        try:
            if self.fault:
                raise ValueError(self.fault)
            if self.matrix is None:
                raise ValueError('airframe_mount_unmeasured')
            if (self.health is None or not self.health.valid
                    or (mono-self.health_receipt)/1e9 > self.config['health_receipt_budget_s']):
                raise ValueError('localization_invalid_or_stale')
            if self.epoch is None:
                self.epoch = self.health.epoch
            if self.last_stamp is not None and stamp <= self.last_stamp:
                if stamp < self.last_stamp:
                    self.fault = 'odometry_time_regression'
                raise ValueError('odometry_stamp_not_increasing')
            mapped = self.mapper.to_px4(stamp, system, mono, self.timesync,
                self.sync_receipt, self.config['timesync_max_age_s'], self.config['timesync_max_rtt_us'])
            values = odometry_to_px4_values(msg, self.profile, self.frames,
                mapped.now_us, self.config['position_variance_m2'],
                self.config['orientation_variance_rad2'], self.config['velocity_variance_m2_s2'],
                self.config['source_quality'], expected_epoch=self.epoch,
                timestamp_sample_us=mapped.sample_us, T_body_imu=self.matrix)
            if self.ned_reference is not None:
                values=self.ned_reference.apply(values,system,mono)
            output = VehicleOdometry()
            output.timestamp, output.timestamp_sample = values.timestamp, values.timestamp_sample
            # VINS is gravity-aligned with arbitrary initial yaw, not True North.
            output.pose_frame = (VehicleOdometry.POSE_FRAME_NED if self.ned_reference is not None
                                 else VehicleOdometry.POSE_FRAME_FRD)
            output.velocity_frame = VehicleOdometry.VELOCITY_FRAME_BODY_FRD
            for field, value in (('position', values.position_ned),
                    ('q', values.quaternion_ned_frd_wxyz), ('velocity', values.velocity_body_frd),
                    ('angular_velocity', values.angular_velocity_body_frd),
                    ('position_variance', values.position_variance),
                    ('orientation_variance', values.orientation_variance),
                    ('velocity_variance', values.velocity_variance)):
                setattr(output, field, list(value))
            output.quality = values.quality
            send_system, send_mono = time.time_ns(), time.monotonic_ns()
            self.mapper.observe(send_system, send_mono)
            output.timestamp = send_system//1000
            self.ev_pub.publish(output)
            self.last_stamp, self.reason = stamp, 'ev_only'
            self.last_ages = {'source_age_s': mapped.sample_age_wall_s,
                             'health_receipt_age_s': (mono-self.health_receipt)/1e9,
                             'odometry_receipt_age_at_send_s': (send_mono-mono)/1e9}
            self.count += 1
        except (ValueError, TimeMappingError) as exc:
            self.reason = str(exc)

    def tick(self):
        system, mono = time.time_ns(), time.monotonic_ns()
        try:
            self.mapper.observe(system, mono)
        except TimeMappingError as exc:
            self.fault = str(exc)
        if self.health is not None and (not self.health.valid or
                (mono-self.health_receipt)/1e9 > self.config['health_receipt_budget_s']):
            self.reason = 'localization_invalid_or_stale'
        elif self.last_receipt is not None and (mono-self.last_receipt)/1e9 > self.config['health_receipt_budget_s']:
            self.reason = 'odometry_receipt_stale'
        msg = String()
        msg.data = json.dumps({'mode': 'ev_only', 'ev_source_topic': self.ev_topic, 'reason': self.fault or self.reason,
                               'published': self.count, 'epoch': self.epoch,
                               'latest_rtt_us': getattr(getattr(self, 'latest_timesync', None), 'round_trip_time', None),
                               'accepted_sync_receipt_age_s': None if self.sync_receipt is None else (mono-self.sync_receipt)/1e9,
                               'last_publish_ages': self.last_ages,
                               'odometry_receipt_age_s': (None if self.last_receipt is None
                                   else (mono-self.last_receipt)/1e9),
                               'odometry_source_age_s': (None if self.last_source is None
                                   else (system-self.last_source)/1e9),
                               'approximate_bench_ev': bool(self.node.get_parameter('allow_approximate_bench_ev').value),
                               'control_publishers_created': False,
                               'ev_reference_mode':self.reference_mode,
                               'ev_reference':self.ned_reference.alignment if self.ned_reference is not None else None})
        self.detail_pub.publish(msg)
