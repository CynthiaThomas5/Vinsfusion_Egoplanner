"""Ground full-load conversion in the sole bridge; no PX4 publisher or enable service."""
import json
import time

from nav_msgs.msg import Odometry
from rclpy.qos import qos_profile_sensor_data, QoSProfile, ReliabilityPolicy, DurabilityPolicy
from std_msgs.msg import String
from uav_interfaces.msg import LocalizationStatus, PositionCommand
from uav_sim.geometry import load_rig
from .rigid_body import mount_rotation_translation
from .trajectory import position_command_to_ned
from .vision_odometry import odometry_to_px4_values


class HardwareComputePath:
    def __init__(self, node, config, profile, frames, rig_path):
        if profile.get('ground_truth_online_allowed') is not False:
            raise ValueError('Compute-only requires VINS without truth')
        rig = load_rig(rig_path)
        mount = rig['airframe_mount']
        # shortcut: unqualified board geometry is used only for discarded calculations;
        # real EV/control keep their independent measured-mount gate.
        self.matrix = mount.get('T_airframe_imu') or mount['bench_observation']['approximate_transform']['T_fc_imu_candidate']
        _, self.lever = mount_rotation_translation(self.matrix)
        self.node, self.config, self.profile, self.frames = node, config, profile, frames
        self.epoch = None
        self.fault = ''
        self.health = None
        self.counts = {'odometry':0, 'ev_computed':0, 'commands':0, 'commands_computed':0}
        self.reason = 'waiting_for_localization'
        self.ages = []
        self.last_stamp = None
        self.last_receive = None
        self.max_gap = 0.
        self.detail = node.create_publisher(String, '/hardware/bridge_compute', 10)
        qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                         durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.subscriptions = [
            node.create_subscription(Odometry, '/localization/optimized_imu_odom', self.on_odometry, qos_profile_sensor_data),
            node.create_subscription(LocalizationStatus, '/localization/status', self.on_health, qos),
            node.create_subscription(PositionCommand, '/position_cmd', self.on_command, 10)]
        self.timer = node.create_timer(1., self.tick)
        node.get_logger().info('hardware compute-only ready; PX4 outputs disabled')

    def on_health(self, msg):
        if self.epoch is not None and msg.epoch != self.epoch:
            self.fault = 'localization_epoch_changed'
        self.health = msg
        self.health_received = time.monotonic()
        if self.epoch is None and msg.valid: self.epoch = msg.epoch

    def valid(self):
        return (not self.fault and self.health is not None and self.health.valid
                and time.monotonic()-self.health_received <= self.config['health_receipt_budget_s'])

    def on_odometry(self, msg):
        self.counts['odometry'] += 1
        now = time.monotonic()
        if self.last_receive is not None: self.max_gap = max(self.max_gap, now-self.last_receive)
        self.last_receive = now
        stamp = msg.header.stamp.sec*10**9+msg.header.stamp.nanosec
        age = (time.time_ns()-stamp)/1e9
        self.ages.append(age)
        try:
            if self.last_stamp is not None and stamp < self.last_stamp:
                self.fault = 'odometry_time_regression'
            self.last_stamp = stamp
            if not self.valid(): raise ValueError(self.fault or 'localization_invalid_or_stale')
            if age < -self.config['max_future_s'] or (self.config.get('enforce_source_age', True) and age > self.config['source_age_budget_s']):
                raise ValueError('odometry_source_age')
            odometry_to_px4_values(msg, self.profile, self.frames, time.time_ns()//1000,
                self.config['position_variance_m2'], self.config['orientation_variance_rad2'],
                self.config['velocity_variance_m2_s2'], self.config['source_quality'],
                expected_epoch=self.epoch, timestamp_sample_us=stamp//1000, T_body_imu=self.matrix)
            self.counts['ev_computed'] += 1
            self.reason = 'computed_outputs_disabled'
        except ValueError as exc:
            self.reason = str(exc)

    def on_command(self, msg):
        self.counts['commands'] += 1
        if not self.valid(): return
        stamp = msg.header.stamp.sec+msg.header.stamp.nanosec/1e9
        if not -self.config['max_future_s'] <= time.time()-stamp <= self.config['command_source_age_budget_s']:
            return
        try:
            value = position_command_to_ned(msg, self.profile, self.frames,
                expected_epoch=self.epoch, sensor_leverarm_body_frd=self.lever)
            if value is not None: self.counts['commands_computed'] += 1
        except ValueError as exc:
            self.reason = str(exc)

    def tick(self):
        ages, self.ages = sorted(self.ages), []
        percentile = lambda p: ages[min(len(ages)-1, int((len(ages)-1)*p))] if ages else None
        msg = String()
        msg.data = json.dumps({'mode':'compute_only', 'px4_publishers_created':False,
            'epoch':self.epoch, 'valid':self.valid(), 'reason':self.fault or self.reason,
            'counts':self.counts, 'source_age_p95_s':percentile(.95),
            'source_age_p99_s':percentile(.99), 'source_age_max_s':max(ages) if ages else None,
            'max_odometry_gap_s':self.max_gap})
        self.detail.publish(msg)
