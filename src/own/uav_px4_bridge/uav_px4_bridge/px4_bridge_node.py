"""ROS 2 PX4 bridge, restricted to the guarded debug_truth SITL profile."""

import json
import math
from pathlib import Path
import time

import rclpy
from ament_index_python.packages import get_package_share_directory
from nav_msgs.msg import Odometry
from px4_msgs.msg import (EstimatorStatusFlags, OffboardControlMode,
                          TimesyncStatus, TrajectorySetpoint, VehicleAttitude,
                          VehicleCommand, VehicleCommandAck, VehicleLandDetected,
                          VehicleLocalPosition, VehicleOdometry,
                          VehicleStatus)
from rclpy.clock import Clock, ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import (QoSProfile, ReliabilityPolicy, DurabilityPolicy,
                       HistoryPolicy)
from rosgraph_msgs.msg import Clock as ClockMessage
from std_msgs.msg import String
from uav_interfaces.msg import LocalizationStatus, PositionCommand, Px4BridgeStatus
from uav_interfaces.srv import EnableOffboard
from uav_sim.geometry import px4_sensor_mount

from .control_state import (OffboardSupervisor, readiness_failure,
                            receipt_limits_fresh)
from .time_mapping import (RosClockMapper, TimeMappingError,
                           fallback_agent_timestamp_us,
                           px4_clock_age_sim_s,
                           px4_ros_source_gap_sim_s,
                           px4_timesync_age_sim_s)
from .trajectory import (angle_difference, compute_rig_frame_alignment,
                         enu_to_ned, position_command_to_ned,
                         px4_sensor_position_ned, rotate_ned_yaw,
                         validate_px4_runtime_profile, yaw_enu_to_ned)
from .vision_odometry import odometry_to_px4_values


def _read_json(path):
    with Path(path).open(encoding='utf-8') as stream:
        return json.load(stream)


def _receipt_age(receipt_ns, now_ns):
    return math.inf if receipt_ns is None else max(0.0, (now_ns - receipt_ns) / 1e9)


def _quaternion_yaw_xyzw(q):
    x, y, z, w = (float(value) for value in q)
    if not all(math.isfinite(value) for value in (x, y, z, w)):
        raise ValueError('source quaternion must be finite')
    norm = math.sqrt(x*x + y*y + z*z + w*w)
    if norm < 1e-9:
        raise ValueError('source quaternion must be nonzero')
    x, y, z, w = x/norm, y/norm, z/norm, w/norm
    return math.atan2(2.0 * (w*z + x*y), 1.0 - 2.0 * (y*y + z*z))


class Px4BridgeNode(Node):
    """Single owner of the PX4 control input topics in this project."""

    def __init__(self):
        super().__init__('uav_px4_bridge')
        self.declare_parameter('profile_path', '')
        self.declare_parameter('bridge_config_path', '')
        self.declare_parameter('frame_contract_path', '')
        self.declare_parameter('mount_model_sdf', '')
        profile_path = self.get_parameter('profile_path').value
        config_path = self.get_parameter('bridge_config_path').value
        frame_path = self.get_parameter('frame_contract_path').value
        if not profile_path or not config_path or not frame_path:
            raise ValueError('profile_path, bridge_config_path and frame_contract_path are required')
        self.profile = _read_json(profile_path)
        profile_config = _read_json(config_path)
        self.frame_contract = _read_json(frame_path)
        profile_name = self.profile.get('name')
        if profile_config.get('profile') != profile_name:
            raise ValueError('PX4 bridge config does not match the selected profile')
        validate_px4_runtime_profile(self.profile, self.frame_contract)
        if profile_name == 'debug_truth':
            self.config = profile_config
            self.clock_topic = self.config['debug_truth_clock_topic']
            self.odometry_topic = self.config['debug_truth_odometry_topic']
            self.localization_topic = self.config['debug_truth_status_topic']
            variance_prefix = 'debug_truth_'
        else:
            forbidden_keys = [key for key in profile_config if 'debug_truth' in key]
            if forbidden_keys:
                raise ValueError('VIO bridge config contains debug_truth inputs')
            if profile_config.get('shared_control_config') != 'debug_truth.json':
                raise ValueError('VIO bridge must use the shared control configuration')
            shared_path = Path(config_path).resolve().parent / 'debug_truth.json'
            shared_config = _read_json(shared_path)
            if shared_config.get('profile') != 'debug_truth':
                raise ValueError('VIO shared control configuration is invalid')
            shared_config = {
                key: value for key, value in shared_config.items()
                if not key.startswith('debug_truth_')
                and key not in ('profile', 'qualification')
            }
            self.config = dict(shared_config)
            self.config.update({key: value for key, value in profile_config.items()
                                if key != 'shared_control_config'})
            self.clock_topic = self.config['clock_topic']
            self.odometry_topic = self.config['optimized_odometry_topic']
            self.localization_topic = self.config['localization_status_topic']
            if (self.clock_topic != '/clock'
                    or self.localization_topic != '/localization/status'
                    or self.odometry_topic != '/localization/optimized_imu_odom'):
                raise ValueError('VIO bridge inputs must use the canonical localization topics')
            variance_prefix = ''
        if self.config.get('px4_clock_domain') != 'gazebo_lockstep':
            raise ValueError('PX4 bridge requires the configured Gazebo lockstep clock domain')
        self.uxrce_dds_time_sync_enabled = self.config.get(
            'uxrce_dds_time_sync_enabled')
        if type(self.uxrce_dds_time_sync_enabled) is not bool:
            raise ValueError('uxrce_dds_time_sync_enabled must be boolean')
        if (not self.uxrce_dds_time_sync_enabled
                and self.config['px4_ros_clock_offset_us'] != 0):
            raise ValueError('direct Gazebo lockstep timestamps require zero PX4/ROS offset')
        self.odometry_variances = (
            self.config[variance_prefix + 'position_variance_m2'],
            self.config[variance_prefix + 'orientation_variance_rad2'],
            self.config[variance_prefix + 'velocity_variance_m2_s2'],
        )

        model_path = self.get_parameter('mount_model_sdf').value
        if not model_path:
            model_path = str(Path(get_package_share_directory('uav_sim')) /
                             'models/x500_d435i/model.sdf')
        self.sensor_mount = px4_sensor_mount(model_path)
        self.sensor_leverarm_frd = tuple(self.sensor_mount['translation_frd_m'])
        self.clock_mapper = RosClockMapper(
            self.config['clock_mapping_min_samples'],
            self.config['clock_mapping_max_samples'],
            self.config['clock_mapping_max_clock_age_wall_s'],
            self.config['clock_mapping_max_source_age_wall_s'],
            self.config['clock_mapping_max_future_wall_s'],
            self.config['clock_mapping_min_sim_rate'],
            self.config['clock_mapping_max_sim_rate'],
            lockstep=True)
        self.supervisor = OffboardSupervisor(
            self.profile, self.frame_contract,
            self.config['prestream_wall_s'], self.config['takeoff_altitude_m'],
            self.config['takeoff_position_tolerance_m'],
            self.config['takeoff_velocity_tolerance_m_s'],
            self.config['takeoff_dwell_wall_s'],
            self.config['command_retry_wall_s'], self.config['command_retry_limit'])

        self.localization = None
        self.localization_receipt_ns = None
        self.odom = None
        self.odom_receipt_ns = None
        self.odom_mapped_receipt_ns = None
        self.odom_time_error = 'clock_mapping_not_converged'
        self.epoch = ''
        self.epoch_fault = ''
        self.bridge_fault = ''
        self.latest_clock_ns = 0
        self.clock_receipt_ns = None
        self.clock_progress_ns = None
        self.clock_progress_receipt_ns = None
        self.timesync = None
        self.timesync_receipt_ns = None
        self.px4_source_offsets_us = {
            'vehicle_status': None,
            'local_position': None,
            'attitude': None,
            'estimator_flags': None,
            'land_detected': None,
        }
        self.vehicle_status = None
        self.vehicle_status_receipt_ns = None
        self.local_position = None
        self.local_position_receipt_ns = None
        self.attitude = None
        self.attitude_receipt_ns = None
        self.estimator_flags = None
        self.estimator_flags_receipt_ns = None
        self.land_detected = None
        self.land_detected_receipt_ns = None
        self.ack = None
        self.ack_receipt_ns = None
        self.alignment = None
        self.alignment_pair = None
        self.alignment_drift_m = -1.0
        self.alignment_yaw_error_rad = -1.0
        self.alignment_fault = ''
        self.position_command = None
        self.position_command_receipt_ns = None
        self.trajectory_fault = ''
        self.px4_timestamp_error = ''
        self.trajectory_completed = False
        self.cached_trajectory_body = None
        self.last_trajectory_goal_id = ''
        self.last_command = 0
        self.last_command_result = 255
        self.pending_command = ''
        self.last_reported_reason = ''
        self.last_status_publish_ns = 0

        sensor_qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT,
                                history=HistoryPolicy.KEEP_LAST)
        reliable_qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE,
                                  history=HistoryPolicy.KEEP_LAST)
        transient_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                                    durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.odom_pub = self.create_publisher(
            VehicleOdometry, self.config['vehicle_odometry_topic'], sensor_qos)
        self.mode_pub = self.create_publisher(
            OffboardControlMode, self.config['offboard_control_mode_topic'], sensor_qos)
        self.setpoint_pub = self.create_publisher(
            TrajectorySetpoint, self.config['trajectory_setpoint_topic'], sensor_qos)
        self.command_pub = self.create_publisher(
            VehicleCommand, self.config['vehicle_command_topic'], reliable_qos)
        self.status_pub = self.create_publisher(
            Px4BridgeStatus, self.config['status_topic'], reliable_qos)
        self.detail_pub = self.create_publisher(String,
                                                self.config['status_topic'] + '/detail',
                                                reliable_qos)

        self.create_subscription(
            ClockMessage, self.clock_topic, self._on_clock, sensor_qos)
        self.create_subscription(
            Odometry, self.odometry_topic, self._on_odometry, sensor_qos)
        self.create_subscription(
            LocalizationStatus, self.localization_topic, self._on_localization,
            transient_qos)
        self.create_subscription(PositionCommand, self.config['position_command_topic'],
                                 self._on_position_command, reliable_qos)
        if self.uxrce_dds_time_sync_enabled:
            self.create_subscription(TimesyncStatus, self.config['timesync_status_topic'],
                                     self._on_timesync, sensor_qos)
        self.create_subscription(VehicleStatus, self.config['vehicle_status_topic'],
                                 self._on_vehicle_status, sensor_qos)
        self.create_subscription(VehicleLocalPosition, self.config['vehicle_local_position_topic'],
                                 self._on_local_position, sensor_qos)
        self.create_subscription(VehicleAttitude, self.config['vehicle_attitude_topic'],
                                 self._on_attitude, sensor_qos)
        self.create_subscription(EstimatorStatusFlags, self.config['estimator_status_flags_topic'],
                                 self._on_estimator_flags, sensor_qos)
        self.create_subscription(VehicleLandDetected, self.config['vehicle_land_detected_topic'],
                                 self._on_land_detected, sensor_qos)
        self.create_subscription(VehicleCommandAck, self.config['vehicle_command_ack_topic'],
                                 self._on_command_ack, sensor_qos)
        self.create_service(EnableOffboard, self.config['enable_service'], self._on_enable)

        period = 1.0 / float(self.config['control_rate_hz'])
        self.steady_clock = Clock(clock_type=ClockType.STEADY_TIME)
        self.create_timer(period, self._on_control_tick, clock=self.steady_clock)
        self.get_logger().info(
            'PX4 bridge initialized in %s; control stays disabled until explicit service enable'
            % profile_name)

    def _now_ns(self):
        return time.monotonic_ns()

    def _on_clock(self, msg):
        now = self._now_ns()
        ros_ns = msg.clock.sec * 1_000_000_000 + msg.clock.nanosec
        self.clock_receipt_ns = now
        if ros_ns <= 0:
            return
        try:
            self.clock_mapper.add_clock(ros_ns, now)
        except TimeMappingError as exc:
            self.bridge_fault = str(exc)
        if ros_ns > self.latest_clock_ns:
            self.clock_progress_ns = ros_ns
            self.clock_progress_receipt_ns = now
        self.latest_clock_ns = ros_ns

    def _on_localization(self, msg):
        now = self._now_ns()
        if self.epoch and msg.epoch != self.epoch:
            self.epoch_fault = 'localization_epoch_changed'
            self.bridge_fault = self.epoch_fault
            self.alignment = None
            self.alignment_pair = None
            self.position_command = None
            self.cached_trajectory_body = None
        elif not self.epoch:
            self.epoch = msg.epoch
        self.localization = msg
        self.localization_receipt_ns = now
        if msg.state != LocalizationStatus.TRACKING or not msg.valid:
            if self.supervisor.phase not in (OffboardSupervisor.DISABLED,
                                             OffboardSupervisor.LANDED,
                                             OffboardSupervisor.LOCKED):
                self.trajectory_fault = msg.reason or 'localization_not_tracking'

    def _on_odometry(self, msg):
        now_mono = self._now_ns()
        self.odom = msg
        self.odom_receipt_ns = now_mono
        match = msg.header.frame_id.removeprefix('odom_')
        if not self.epoch:
            self.epoch = match
        elif match != self.epoch:
            self.epoch_fault = 'localization_epoch_changed'
            self.bridge_fault = self.epoch_fault
            self.alignment = None
            self.alignment_pair = None
            self.position_command = None
            self.cached_trajectory_body = None
            return
        try:
            mapped = self._map_source_time(msg.header.stamp, now_mono)
            values = odometry_to_px4_values(
                msg, self.profile, self.frame_contract,
                mapped.now_us, *self.odometry_variances,
                self.config['source_quality'], expected_epoch=self.epoch,
                timestamp_sample_us=mapped.sample_us)
            output = VehicleOdometry()
            output.timestamp = values.timestamp
            output.timestamp_sample = values.timestamp_sample
            output.pose_frame = VehicleOdometry.POSE_FRAME_NED
            output.position = list(values.position_ned)
            output.q = list(values.quaternion_ned_frd_wxyz)
            output.velocity_frame = VehicleOdometry.VELOCITY_FRAME_BODY_FRD
            output.velocity = list(values.velocity_body_frd)
            output.angular_velocity = list(values.angular_velocity_body_frd)
            output.position_variance = list(values.position_variance)
            output.orientation_variance = list(values.orientation_variance)
            output.velocity_variance = list(values.velocity_variance)
            output.reset_counter = 0
            output.quality = values.quality
            self.odom_pub.publish(output)
            self.odom_mapped_receipt_ns = now_mono
            self.odom_time_error = ''
        except (ValueError, TimeMappingError) as exc:
            self.odom_time_error = str(exc)
            if self.clock_mapper.locked:
                self.bridge_fault = self.clock_mapper.reason

    def _map_source_time(self, stamp, receipt_mono_ns):
        if self.uxrce_dds_time_sync_enabled:
            if self.timesync is None or self.timesync_receipt_ns is None:
                raise TimeMappingError('px4_timesync_stale')
            estimated_offset_us = self.timesync.estimated_offset
            round_trip_time_us = self.timesync.round_trip_time
            timesync_receipt_ns = self.timesync_receipt_ns
            timesync_age_s = self._timesync_age_sim_s()
        else:
            estimated_offset_us = 0
            round_trip_time_us = 0
            timesync_receipt_ns = receipt_mono_ns
            timesync_age_s = 0.0
        return self.clock_mapper.to_px4(
            stamp.sec * 1_000_000_000 + stamp.nanosec,
            receipt_mono_ns, time.time_ns(), estimated_offset_us,
            round_trip_time_us, timesync_receipt_ns,
            self.config['timesync_max_age_sim_s'],
            self.config['timesync_max_rtt_us'],
            self.config['clock_mapping_max_fit_residual_wall_s'],
            timesync_age_s=timesync_age_s,
            px4_ros_clock_offset_us=self.config['px4_ros_clock_offset_us'],
            max_timesync_future_s=self.config['timesync_max_future_sim_s'],
            timestamp_sync_enabled=self.uxrce_dds_time_sync_enabled)

    def _on_timesync(self, msg):
        self.timesync = msg
        self.timesync_receipt_ns = self._now_ns()

    def _timesync_age_sim_s(self):
        if (not self.uxrce_dds_time_sync_enabled or self.timesync is None
                or self.latest_clock_ns <= 0):
            return None
        # PX4's DDS serializer shifts TimesyncStatus.timestamp into the Agent
        # clock. Adding estimated_offset recovers PX4 HRT, which Gazebo's
        # lockstep clock callback sets from the same /clock sample.
        return px4_timesync_age_sim_s(
            self.latest_clock_ns, self.timesync.timestamp,
            self.timesync.estimated_offset)

    def _timesync_fresh(self):
        if not self.uxrce_dds_time_sync_enabled:
            return False
        age_s = self._timesync_age_sim_s()
        return (age_s is not None
                and age_s >= -self.config['timesync_max_future_sim_s']
                and age_s <= self.config['timesync_max_age_sim_s']
                and self.timesync.round_trip_time <= self.config['timesync_max_rtt_us'])

    def _on_vehicle_status(self, msg):
        self.vehicle_status = msg
        self.vehicle_status_receipt_ns = self._now_ns()
        self._capture_px4_source_offset('vehicle_status')

    def _on_local_position(self, msg):
        self.local_position = msg
        self.local_position_receipt_ns = self._now_ns()
        self._capture_px4_source_offset('local_position')

    def _on_attitude(self, msg):
        self.attitude = msg
        self.attitude_receipt_ns = self._now_ns()
        self._capture_px4_source_offset('attitude')

    def _on_estimator_flags(self, msg):
        self.estimator_flags = msg
        self.estimator_flags_receipt_ns = self._now_ns()
        self._capture_px4_source_offset('estimator_flags')

    def _on_land_detected(self, msg):
        self.land_detected = msg
        self.land_detected_receipt_ns = self._now_ns()
        self._capture_px4_source_offset('land_detected')

    def _capture_px4_source_offset(self, source):
        self.px4_source_offsets_us[source] = (
            int(self.timesync.estimated_offset)
            if self.uxrce_dds_time_sync_enabled and self.timesync is not None else
            (0 if not self.uxrce_dds_time_sync_enabled else None))

    def _on_command_ack(self, msg):
        self.ack = msg
        self.ack_receipt_ns = self._now_ns()
        self.last_command_result = int(msg.result)

    def _on_position_command(self, msg):
        now = self._now_ns()
        if self.epoch and msg.epoch != self.epoch:
            self.trajectory_fault = 'trajectory_epoch_mismatch'
            return
        if self.last_trajectory_goal_id and msg.goal_id != self.last_trajectory_goal_id:
            self.cached_trajectory_body = None
            self.trajectory_completed = False
        if msg.goal_id:
            self.last_trajectory_goal_id = msg.goal_id
        self.position_command = msg
        self.position_command_receipt_ns = now
        if msg.trajectory_flag == PositionCommand.TRAJECTORY_STATUS_READY:
            self.trajectory_completed = False
        elif msg.trajectory_flag == PositionCommand.TRAJECTORY_STATUS_COMPLETED:
            self.trajectory_completed = self.cached_trajectory_body is not None
            if not self.trajectory_completed:
                self.trajectory_fault = 'completed_trajectory_without_final_setpoint'
        elif msg.trajectory_flag == PositionCommand.TRAJECTORY_STATUS_EMPTY:
            self.trajectory_completed = False
        else:
            self.trajectory_fault = 'trajectory_' + str(msg.trajectory_flag)

    def _fresh(self, receipt_ns, limit_s, now_ns):
        return _receipt_age(receipt_ns, now_ns) <= float(limit_s)

    def _local_state_fresh(self, now_ns):
        messages = (
            ('vehicle_status', self.vehicle_status, self.vehicle_status_receipt_ns,
             self.config['px4_status_max_receipt_age_wall_s']),
            ('local_position', self.local_position, self.local_position_receipt_ns,
             self.config['px4_max_receipt_age_wall_s']),
            ('attitude', self.attitude, self.attitude_receipt_ns,
             self.config['px4_max_receipt_age_wall_s']),
            ('estimator_flags', self.estimator_flags, self.estimator_flags_receipt_ns,
             self.config['px4_estimator_flags_max_receipt_age_wall_s']),
            ('land_detected', self.land_detected, self.land_detected_receipt_ns,
             self.config['px4_land_detected_max_receipt_age_wall_s']),
        )
        if not receipt_limits_fresh(now_ns, tuple(
                (receipt_ns, max_age_s)
                for _, _, receipt_ns, max_age_s in messages)):
            return False
        if self.latest_clock_ns <= 0:
            return False
        if (self.uxrce_dds_time_sync_enabled
                and (self.timesync is None or self.timesync_receipt_ns is None
                     or not self._timesync_fresh())):
            return False
        max_age_s = self.config['px4_source_timestamp_max_age_sim_s']
        max_future_s = self.config['px4_source_timestamp_max_future_sim_s']
        for source, message, _, _ in messages:
            if message is None:
                return False
            age_s = self._px4_source_age_sim_s(source, message, now_ns)
            if age_s is None:
                return False
            if age_s < -max_future_s or age_s > max_age_s:
                return False
        return True

    def _px4_source_age_sim_s(self, source, message, now_ns):
        offset_us = self.px4_source_offsets_us.get(source)
        if message is None or offset_us is None:
            return None
        try:
            current_ros_ns = self.clock_mapper.ros_time_at_monotonic(
                now_ns, self.config['clock_mapping_max_fit_residual_wall_s'])
            return px4_clock_age_sim_s(
                current_ros_ns, message.timestamp, offset_us)
        except TimeMappingError:
            return None

    def _px4_telemetry_freshness_detail(self, now_ns):
        sources = (
            ('vehicle_status', self.vehicle_status, self.vehicle_status_receipt_ns,
             self.config['px4_status_max_receipt_age_wall_s']),
            ('local_position', self.local_position, self.local_position_receipt_ns,
             self.config['px4_max_receipt_age_wall_s']),
            ('attitude', self.attitude, self.attitude_receipt_ns,
             self.config['px4_max_receipt_age_wall_s']),
            ('estimator_flags', self.estimator_flags, self.estimator_flags_receipt_ns,
             self.config['px4_estimator_flags_max_receipt_age_wall_s']),
            ('land_detected', self.land_detected, self.land_detected_receipt_ns,
             self.config['px4_land_detected_max_receipt_age_wall_s']),
        )
        return {
            name: {
                'source_age_sim_s': self._px4_source_age_sim_s(name, message, now_ns),
                'source_stamp_us': (int(message.timestamp) if message is not None else None),
                'source_timestamp_offset_us': self.px4_source_offsets_us[name],
                'receipt_age_wall_s': _receipt_age(receipt_ns, now_ns),
                'max_source_age_sim_s': self.config['px4_source_timestamp_max_age_sim_s'],
                'max_source_future_sim_s': self.config['px4_source_timestamp_max_future_sim_s'],
                'max_receipt_age_wall_s': max_wall_age_s,
            }
            for name, message, receipt_ns, max_wall_age_s in sources
        }

    def _source_position_enu(self, odometry=None):
        odometry = self.odom if odometry is None else odometry
        p = odometry.pose.pose.position
        return float(p.x), float(p.y), float(p.z)

    def _source_yaw_enu(self, odometry=None):
        odometry = self.odom if odometry is None else odometry
        q = odometry.pose.pose.orientation
        return _quaternion_yaw_xyzw((q.x, q.y, q.z, q.w))

    def _capture_alignment_pair(self, now_ns):
        if (self.odom is None or self.local_position is None
                or self.attitude is None
                or self.latest_clock_ns <= 0
                or not self._fresh(self.odom_receipt_ns,
                                   self.config['odometry_max_receipt_age_wall_s'], now_ns)
                or not self._local_state_fresh(now_ns)):
            return False
        gap_s = self._alignment_pair_gap_sim_s()
        if (gap_s is None
                or gap_s > self.config['alignment_pair_max_source_gap_sim_s']):
            return False
        # Keep the last source-time-matched pair when only one input has
        # advanced; freshness below still expires it using the original
        # receipt times and each stream's existing limits.
        self.alignment_pair = {
            'odometry': self.odom,
            'odometry_receipt_ns': self.odom_receipt_ns,
            'local_position': self.local_position,
            'local_position_receipt_ns': self.local_position_receipt_ns,
            'attitude': self.attitude,
            'attitude_receipt_ns': self.attitude_receipt_ns,
            'estimator_flags': self.estimator_flags,
            'gap_sim_s': gap_s,
        }
        return True

    def _alignment_pair_fresh(self, now_ns):
        self._capture_alignment_pair(now_ns)
        pair = self.alignment_pair
        if pair is None or not self._local_state_fresh(now_ns):
            return False
        return (
            self._fresh(pair['odometry_receipt_ns'],
                        self.config['odometry_max_receipt_age_wall_s'], now_ns)
            and self._fresh(pair['local_position_receipt_ns'],
                            self.config['px4_max_receipt_age_wall_s'], now_ns)
            and self._fresh(pair['attitude_receipt_ns'],
                            self.config['px4_max_receipt_age_wall_s'], now_ns))

    def _alignment_pair_gap_sim_s(self):
        offset_us = self.px4_source_offsets_us['local_position']
        if (self.odom is None or self.local_position is None
                or offset_us is None):
            return None
        stamp = self.odom.header.stamp
        source_ns = int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)
        try:
            return px4_ros_source_gap_sim_s(
                source_ns, self.local_position.timestamp,
                offset_us,
                self.config['px4_ros_clock_offset_us'])
        except TimeMappingError:
            return None

    def _update_alignment(self, now_ns):
        if (self.alignment_fault or self.alignment is not None or self.odom is None
                or self.local_position is None or self.attitude is None
                or self.estimator_flags is None or self.localization is None):
            return
        if not self._alignment_pair_fresh(now_ns):
            return
        pair = self.alignment_pair
        flags = pair['estimator_flags']
        if not (flags.cs_ev_pos and flags.cs_ev_hgt and flags.cs_ev_yaw):
            return
        local = pair['local_position']
        if not (local.xy_valid and local.z_valid and local.heading_good_for_control):
            return
        try:
            self.alignment = compute_rig_frame_alignment(
                self._source_position_enu(pair['odometry']),
                self._source_yaw_enu(pair['odometry']),
                (local.x, local.y, local.z), tuple(pair['attitude'].q),
                local.heading, self.sensor_leverarm_frd)
            self.alignment_drift_m = 0.0
        except (TypeError, ValueError) as exc:
            self.alignment_fault = 'alignment_pair_invalid:' + str(exc)

    def _alignment_health(self, now_ns):
        # EKF initialization can move its local origin while still grounded.
        # Freeze the flight transform at enable, before prestream starts.
        if (not self.alignment_fault
                and self.supervisor.phase == self.supervisor.DISABLED
                and self.vehicle_status is not None
                and self.vehicle_status.arming_state != VehicleStatus.ARMING_STATE_ARMED
                and self.land_detected is not None and self.land_detected.landed):
            self.alignment = None
        self._update_alignment(now_ns)
        if self.alignment is None or self.alignment_pair is None:
            return False
        if not self._alignment_pair_fresh(now_ns):
            return False
        pair = self.alignment_pair
        local = pair['local_position']
        attitude = pair['attitude']
        try:
            source_ned = rotate_ned_yaw(
                enu_to_ned(self._source_position_enu(pair['odometry'])),
                self.alignment.yaw_offset_ned)
            aligned_source_sensor = tuple(
                a + b for a, b in zip(source_ned, self.alignment.origin_offset_ned))
            px4_sensor = px4_sensor_position_ned(
                (local.x, local.y, local.z), tuple(attitude.q),
                self.sensor_leverarm_frd)
            self.alignment_drift_m = math.sqrt(sum(
                (a-b)**2 for a, b in zip(aligned_source_sensor, px4_sensor)))
            yaw_error = abs(angle_difference(
                yaw_enu_to_ned(self._source_yaw_enu(pair['odometry']))
                + self.alignment.yaw_offset_ned,
                local.heading))
        except (TypeError, ValueError):
            return False
        self.alignment_yaw_error_rad = yaw_error
        if (self.alignment_drift_m > self.config['alignment_max_drift_m']
                or yaw_error > self.config['alignment_max_yaw_error_rad']):
            self.alignment_fault = 'px4_frame_alignment_drift'
            return False
        return True

    def _trajectory_is_ready(self, now_ns):
        if self.trajectory_fault:
            return False
        if self.trajectory_completed:
            return self.cached_trajectory_body is not None
        return (self.position_command is not None
                and self.position_command.trajectory_flag == PositionCommand.TRAJECTORY_STATUS_READY
                and self._fresh(self.position_command_receipt_ns,
                                self.config['command_max_receipt_age_wall_s'], now_ns))

    def _snapshot(self, now_ns):
        alignment_valid = self._alignment_health(now_ns)
        loc_fresh = (self.localization is not None
                     and self._fresh(self.localization_receipt_ns,
                                     self.config['localization_max_receipt_age_wall_s'], now_ns)
                     and self.localization.valid
                     and self.localization.state == LocalizationStatus.TRACKING
                     and not self.epoch_fault)
        odom_fresh = (self.odom is not None and self.odom_mapped_receipt_ns is not None
                      and self._fresh(self.odom_mapped_receipt_ns,
                                      self.config['odometry_max_receipt_age_wall_s'], now_ns))
        clock_fresh = (self.latest_clock_ns > 0
                       and self.clock_mapper.reason != 'ros_clock_regression'
                       and self._fresh(self.clock_progress_receipt_ns,
                                       self.config['clock_stall_wall_s'], now_ns))
        clock_domain_valid = (not self.uxrce_dds_time_sync_enabled
                              or (self.timesync is not None and self._timesync_fresh()))
        px4_fresh = self._local_state_fresh(now_ns)
        local = self.local_position
        flags = self.estimator_flags
        status = self.vehicle_status
        land = self.land_detected
        local_valid = (px4_fresh and local is not None and local.xy_valid and local.z_valid
                       and local.heading_good_for_control
                       and all(math.isfinite(float(v)) for v in
                               (local.x, local.y, local.z, local.vx, local.vy, local.vz,
                                local.heading)))
        ev_pos = (px4_fresh and flags is not None
                  and bool(flags.cs_ev_pos and flags.cs_ev_hgt))
        ev_yaw = px4_fresh and flags is not None and bool(flags.cs_ev_yaw)
        gnss_position = flags is not None and bool(flags.cs_gnss_pos or flags.cs_aux_gpos)
        gnss_velocity = flags is not None and bool(flags.cs_gnss_vel)
        gnss_height = flags is not None and bool(flags.cs_gps_hgt)
        gnss_yaw = flags is not None and bool(flags.cs_gnss_yaw)
        armed = (status is not None and
                 status.arming_state == VehicleStatus.ARMING_STATE_ARMED)
        offboard = (status is not None and
                    status.nav_state == VehicleStatus.NAVIGATION_STATE_OFFBOARD)
        return {
            'localization_tracking': loc_fresh and not self.bridge_fault,
            'odometry_fresh': odom_fresh,
            'clock_fresh': clock_fresh,
            'px4_time_domain_valid': clock_domain_valid,
            'px4_telemetry_fresh': px4_fresh,
            'local_position_valid': local_valid,
            'ev_position_fused': ev_pos,
            'ev_yaw_fused': ev_yaw,
            'alignment_valid': alignment_valid,
            'preflight_passed': (status is not None and bool(status.pre_flight_checks_pass)),
            'gnss_position_aiding': gnss_position,
            'gnss_velocity_aiding': gnss_velocity,
            'gnss_height_aiding': gnss_height,
            'gnss_yaw_aiding': gnss_yaw,
            'landed': (land is not None and bool(land.landed)),
            'armed': bool(armed),
            'nav_offboard': bool(offboard),
            'position_ned': ((local.x, local.y, local.z) if local is not None else ()),
            'velocity_ned': ((local.vx, local.vy, local.vz) if local is not None else ()),
            'heading_ned': (local.heading if local is not None else math.nan),
            'trajectory_ready': self._trajectory_is_ready(now_ns),
            'trajectory_fault': bool(self.trajectory_fault),
            'trajectory_reason': self.trajectory_fault,
        }

    def _px4_now_us(self, now_ns):
        if (self.uxrce_dds_time_sync_enabled
                and (self.timesync is None or self.timesync_receipt_ns is None)):
            self.px4_timestamp_error = 'px4_timesync_stale'
            return 0
        if not self.uxrce_dds_time_sync_enabled:
            try:
                timestamp = self.clock_mapper.current_lockstep_px4_time_us(now_ns)
                self.px4_timestamp_error = ''
                return timestamp
            except TimeMappingError as exc:
                self.px4_timestamp_error = str(exc)
                return 0
        receipt_system_ns = time.time_ns()
        if self.latest_clock_ns > 0:
            try:
                estimated_offset_us = (
                    self.timesync.estimated_offset
                    if self.uxrce_dds_time_sync_enabled else 0)
                round_trip_time_us = (
                    self.timesync.round_trip_time
                    if self.uxrce_dds_time_sync_enabled else 0)
                timesync_receipt_ns = (
                    self.timesync_receipt_ns
                    if self.uxrce_dds_time_sync_enabled else now_ns)
                mapped = self.clock_mapper.to_px4(
                    self.latest_clock_ns, now_ns, receipt_system_ns,
                    estimated_offset_us, round_trip_time_us,
                    timesync_receipt_ns, self.config['timesync_max_age_sim_s'],
                    self.config['timesync_max_rtt_us'],
                    self.config['clock_mapping_max_fit_residual_wall_s'],
                    timesync_age_s=self._timesync_age_sim_s(),
                    px4_ros_clock_offset_us=self.config['px4_ros_clock_offset_us'],
                    max_timesync_future_s=self.config['timesync_max_future_sim_s'],
                    timestamp_sync_enabled=self.uxrce_dds_time_sync_enabled)
                self.px4_timestamp_error = ''
                return mapped.now_us
            except TimeMappingError as exc:
                self.px4_timestamp_error = str(exc)
        if not self.uxrce_dds_time_sync_enabled:
            if self.latest_clock_ns <= 0 and not self.px4_timestamp_error:
                self.px4_timestamp_error = 'clock_mapping_not_converged'
            return 0
        # TimesyncStatus.timestamp is the time of that sample, not current
        # Agent time. Reusing it can make Offboard timestamps stale when the
        # lockstep clock mapper briefly rejects a /clock sample.
        return fallback_agent_timestamp_us(
            receipt_system_ns, self._timesync_fresh())

    def _publish_command(self, name, now_ns):
        timestamp = self._px4_now_us(now_ns)
        if timestamp <= 0:
            return False
        message = VehicleCommand()
        message.timestamp = timestamp
        message.target_system = int(self.config['system_id'])
        message.target_component = int(self.config['component_id'])
        message.source_system = int(self.config['system_id'])
        message.source_component = int(self.config['component_id'])
        message.from_external = True
        if name == 'offboard':
            message.command = VehicleCommand.VEHICLE_CMD_DO_SET_MODE
            message.param1 = 1.0
            message.param2 = 6.0
        elif name == 'arm':
            message.command = VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM
            message.param1 = 1.0
        elif name == 'land':
            message.command = VehicleCommand.VEHICLE_CMD_NAV_LAND
        else:
            return False
        self.command_pub.publish(message)
        self.last_command = int(message.command)
        self.last_command_result = 255
        return True

    def _position_for_output(self, output, snapshot, now_ns):
        if output.setpoint_kind == 'trajectory':
            if self.trajectory_completed and self.cached_trajectory_body is not None:
                return self.cached_trajectory_body
            command = self.position_command
            if command is None or self.alignment is None:
                raise ValueError('trajectory_or_alignment_missing')
            setpoint = position_command_to_ned(
                command, self.profile, self.frame_contract, expected_epoch=self.epoch,
                origin_offset_ned=self.alignment.origin_offset_ned,
                yaw_offset_ned=self.alignment.yaw_offset_ned,
                sensor_leverarm_body_frd=self.sensor_leverarm_frd)
            self.cached_trajectory_body = (setpoint.position, setpoint.yaw)
            return self.cached_trajectory_body
        if output.setpoint_kind == 'takeoff':
            return self.supervisor.takeoff_target, self.supervisor.takeoff_yaw
        if (self.supervisor.phase == OffboardSupervisor.ACTIVE
                and self.trajectory_completed and self.cached_trajectory_body is not None):
            return self.cached_trajectory_body
        if len(snapshot['position_ned']) != 3 or not math.isfinite(snapshot['heading_ned']):
            raise ValueError('px4_hold_pose_invalid')
        return tuple(snapshot['position_ned']), float(snapshot['heading_ned'])

    def _publish_control(self, output, snapshot, now_ns):
        if not output.publish_offboard:
            return
        timestamp = self._px4_now_us(now_ns)
        if timestamp <= 0:
            self.trajectory_fault = 'px4_timestamp_unavailable'
            return
        try:
            position, yaw = self._position_for_output(output, snapshot, now_ns)
        except ValueError as exc:
            self.trajectory_fault = str(exc)
            return
        mode = OffboardControlMode()
        mode.timestamp = timestamp
        mode.position = True
        mode.velocity = False
        mode.acceleration = False
        mode.attitude = False
        mode.body_rate = False
        mode.thrust_and_torque = False
        mode.direct_actuator = False
        self.mode_pub.publish(mode)
        setpoint = TrajectorySetpoint()
        setpoint.timestamp = timestamp
        setpoint.position = list(position)
        setpoint.velocity = [math.nan, math.nan, math.nan]
        setpoint.acceleration = [math.nan, math.nan, math.nan]
        setpoint.jerk = [math.nan, math.nan, math.nan]
        setpoint.yaw = float(yaw)
        setpoint.yawspeed = math.nan
        self.setpoint_pub.publish(setpoint)
        if output.command:
            self._publish_command(output.command, now_ns)

    def _on_enable(self, request, response):
        now = self._now_ns()
        snapshot = self._snapshot(now)
        if request.enable:
            if self.bridge_fault or self.alignment_fault:
                response.accepted = False
                response.reason = self.bridge_fault or self.alignment_fault
                return response
            accepted, reason = self.supervisor.enable(snapshot, now / 1e9)
            if accepted:
                # Initial EV fusion can precede EKF yaw convergence. Capture the
                # flight transform from the fresh, landed/disarmed enable pair;
                # keep it fixed throughout prestream, takeoff and navigation.
                self.alignment = None
                self._update_alignment(now)
                if not self._alignment_health(now):
                    self.supervisor.disable(snapshot)
                    accepted = False
                    reason = self.alignment_fault or 'alignment_not_ready_at_enable'
            response.accepted = accepted
            response.reason = reason
        else:
            output = self.supervisor.disable(snapshot)
            response.accepted = True
            response.reason = output.reason
            if output.command:
                self.pending_command = output.command
        return response

    def _publish_status(self, snapshot, now_ns):
        failure = readiness_failure(snapshot, self.profile, self.frame_contract)
        status = Px4BridgeStatus()
        status.header.stamp = self.get_clock().now().to_msg()
        status.epoch = self.epoch
        status.phase = self.supervisor.phase
        status.reason = (self.bridge_fault or self.alignment_fault or self.trajectory_fault
                         or failure or self.supervisor.reason)
        status.ready = not bool(failure or self.bridge_fault or self.alignment_fault)
        status.control_enabled = self.supervisor.phase not in (
            OffboardSupervisor.DISABLED, OffboardSupervisor.LANDED,
            OffboardSupervisor.LOCKED)
        status.armed = bool(snapshot['armed'])
        status.landed = bool(snapshot['landed'])
        status.local_position_valid = bool(snapshot['local_position_valid'])
        status.ev_position_fused = bool(snapshot['ev_position_fused'])
        status.ev_yaw_fused = bool(snapshot['ev_yaw_fused'])
        status.gnss_aiding_active = any(snapshot[name] for name in (
            'gnss_position_aiding', 'gnss_velocity_aiding',
            'gnss_height_aiding', 'gnss_yaw_aiding'))
        if self.alignment is None:
            status.frame_offset_ned = [0.0, 0.0, 0.0]
            status.frame_yaw_offset_ned = 0.0
        else:
            status.frame_offset_ned = list(self.alignment.origin_offset_ned)
            status.frame_yaw_offset_ned = self.alignment.yaw_offset_ned
        status.alignment_drift_m = self.alignment_drift_m
        status.last_command = self.last_command
        status.last_command_result = self.last_command_result
        self.status_pub.publish(status)
        detail = String()
        detail.data = json.dumps({
            'phase': status.phase, 'reason': status.reason,
            'uxrce_dds_time_sync_enabled': self.uxrce_dds_time_sync_enabled,
            'px4_time_domain_valid': snapshot['px4_time_domain_valid'],
            'px4_timestamp_error': self.px4_timestamp_error,
            'odometry_time_error': self.odom_time_error,
            'timesync_age_sim_s': self._timesync_age_sim_s(),
            'px4_telemetry_freshness': self._px4_telemetry_freshness_detail(now_ns),
            'alignment_pair_gap_sim_s': self._alignment_pair_gap_sim_s(),
            'alignment_pair_validated_gap_sim_s': (
                self.alignment_pair['gap_sim_s']
                if self.alignment_pair is not None else None),
            'alignment_pair_validated_age_wall_s': (
                _receipt_age(self.alignment_pair['odometry_receipt_ns'], now_ns)
                if self.alignment_pair is not None else None),
            'model_sha256': self.sensor_mount['model_sha256'],
            'sensor_leverarm_frd_m': self.sensor_leverarm_frd,
            'alignment_drift_m': self.alignment_drift_m,
            'alignment_yaw_error_rad': self.alignment_yaw_error_rad,
            'wall_age_s': _receipt_age(self.odom_mapped_receipt_ns, now_ns),
        }, sort_keys=True)
        self.detail_pub.publish(detail)

    def _on_control_tick(self):
        now = self._now_ns()
        snapshot = self._snapshot(now)
        # A latched fault must not block observing completion of the landing.
        if ((self.bridge_fault or self.alignment_fault)
                and self.supervisor.phase != OffboardSupervisor.LANDING):
            output = self.supervisor.disable(snapshot)
            if self.supervisor.phase == OffboardSupervisor.DISABLED:
                self.supervisor.reason = self.bridge_fault or self.alignment_fault
        else:
            output = self.supervisor.step(snapshot, now / 1e9)
        if self.pending_command:
            self._publish_command(self.pending_command, now)
            self.pending_command = ''
        if output.command == 'land':
            self._publish_command('land', now)
        self._publish_control(output, snapshot, now)
        if self.supervisor.reason != self.last_reported_reason:
            self.last_reported_reason = self.supervisor.reason
            self.get_logger().info('bridge phase=%s reason=%s' % (
                self.supervisor.phase, self.supervisor.reason))
        if now - self.last_status_publish_ns >= int(
                self.config['status_period_wall_s'] * 1e9):
            self._publish_status(snapshot, now)
            self.last_status_publish_ns = now


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = Px4BridgeNode()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except RuntimeError:
        if rclpy.ok():
            raise
    finally:
        if node is not None:
            if node.supervisor.phase not in (OffboardSupervisor.DISABLED,
                                             OffboardSupervisor.LANDED,
                                             OffboardSupervisor.LOCKED):
                node.supervisor.disable({})
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
