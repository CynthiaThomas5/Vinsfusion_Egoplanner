#!/usr/bin/env python3
"""Run one service-gated VIO EGO goal, then land through the PX4 bridge."""

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import time

from atomic_record import write_json_atomic
from flight_profile import legs, navigation_duration_requirement, navigation_elapsed_sim_s
from n10_motion_cancel import StopWindowTracker, cancel_trigger

import rclpy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from px4_msgs.msg import (OffboardControlMode, TrajectorySetpoint,
                          VehicleCommand, VehicleLocalPosition,
                          VehicleOdometry, VehicleStatus, TimesyncStatus)
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import Image, PointCloud2
from std_msgs.msg import String
from uav_interfaces.action import NavigateToPose
from uav_interfaces.msg import DepthHealth, LocalizationStatus, PositionCommand, Px4BridgeStatus
from uav_interfaces.srv import EnableOffboard


class EgoFlightProbe(Node):
    def __init__(self):
        super().__init__('px4_debug_ego_flight_probe')
        self.started_wall = time.monotonic()
        sensor_qos = QoSProfile(depth=20, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.sensor_qos = sensor_qos
        reliable_qos = QoSProfile(depth=20, reliability=ReliabilityPolicy.RELIABLE)
        status_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE)
        self.localization = None
        self.odometry = None
        self.bridge = None
        self.latest_bridge_detail = None
        self.bridge_detail_history = []
        self.timesync_history = []
        self.latest_timesync = None
        self.map_point_counts = []
        self.position_commands = []
        self.speed_observation_epoch = None
        self.speed_observation_active = False
        self.speed_observation_samples = []
        self.speed_observation_sample_counts = {}
        self.speed_observation_last_samples = {}
        self.speed_observation_maxima_m_s = {}
        self.px4_setpoint_observations = []
        self.bridge_phases = []
        self.counts = Counter()
        self.create_subscription(LocalizationStatus, '/localization/status',
                                 self._on_localization, status_qos)
        self.create_subscription(Odometry, '/localization/optimized_imu_odom',
                                 self._on_odometry, sensor_qos)
        self.create_subscription(Px4BridgeStatus, '/uav_px4_bridge/status',
                                 self._on_bridge, status_qos)
        self.create_subscription(String, '/uav_px4_bridge/status/detail',
                                 self._on_bridge_detail, reliable_qos)
        self.create_subscription(TimesyncStatus, '/fmu/out/timesync_status',
                                 self._on_timesync_status, sensor_qos)
        self.create_subscription(PointCloud2, '/grid_map/occupancy',
                                 self._on_map, sensor_qos)
        self.create_subscription(PositionCommand, '/position_cmd',
                                 self._on_position_command, reliable_qos)
        self.create_subscription(VehicleOdometry, '/fmu/in/vehicle_visual_odometry',
                                 lambda _: self._count('visual_odometry_input'), sensor_qos)
        self.create_subscription(OffboardControlMode, '/fmu/in/offboard_control_mode',
                                 lambda _: self._count('control_mode'), sensor_qos)
        self.create_subscription(TrajectorySetpoint, '/fmu/in/trajectory_setpoint',
                                 self._on_px4_trajectory_setpoint, sensor_qos)
        self.create_subscription(VehicleCommand, '/fmu/in/vehicle_command',
                                 lambda _: self._count('vehicle_command'), sensor_qos)
        self.create_subscription(VehicleStatus, '/fmu/out/vehicle_status_v1',
                                 self._on_vehicle_status, sensor_qos)
        self.create_subscription(VehicleLocalPosition, '/fmu/out/vehicle_local_position_v1',
                                 self._on_local_position, sensor_qos)
        self.enable_client = self.create_client(
            EnableOffboard, '/uav_px4_bridge/enable_offboard')
        self.action_client = ActionClient(self, NavigateToPose,
                                          '/navigation/navigate_to_pose')
        self.vehicle_status = None
        self.vehicle_status_history = []
        self.latest_position_command = None
        self.streams = {}
        self.localization_quality_history = []
        self.vins_quality_history = []
        self.vins_telemetry_topic = None
        self.vins_telemetry_subscription = None
        self.local_position_history = []
        for topic, key, qos in (
            ('/sensors/d435i/depth', 'raw_depth', sensor_qos),
            ('/drone_0_depth_image', 'ego_depth', sensor_qos),
            ('/drone_0_camera_pose', 'ego_camera_pose', sensor_qos),
            ('/mapping/depth_health', 'depth_health', status_qos),
        ):
            if key in ('raw_depth', 'ego_depth'):
                continue  # Native depth gates remain active; avoid duplicate image deserialization.
            msg_type = DepthHealth if key == 'depth_health' else (PoseStamped if key == 'ego_camera_pose' else Image)
            self.create_subscription(msg_type, topic, lambda msg, k=key: self._record_stream(k, msg), qos)

    def _count(self, key):
        self.counts[key] += 1

    def _record_stream(self, key, msg):
        now = time.monotonic()
        header = getattr(msg, 'header', None)
        stamp = (int(header.stamp.sec) * 1_000_000_000 + int(header.stamp.nanosec)) if header else None
        row = self.streams.setdefault(key, {
            'count': 0, 'first_wall_elapsed_s': now - self.started_wall,
            'last_wall_elapsed_s': None, 'first_stamp_ns': stamp, 'last_stamp_ns': None,
            'max_receipt_gap_s': 0.0, 'max_stamp_gap_s': 0.0, 'large_gaps': [],
        })
        previous_wall = row['last_wall_elapsed_s']
        previous_stamp = row['last_stamp_ns']
        wall_elapsed = now - self.started_wall
        if previous_wall is not None:
            gap = wall_elapsed - previous_wall
            row['max_receipt_gap_s'] = max(row['max_receipt_gap_s'], gap)
            stamp_gap = ((stamp - previous_stamp) / 1e9
                         if stamp is not None and previous_stamp is not None else None)
            if stamp_gap is not None:
                row['max_stamp_gap_s'] = max(row['max_stamp_gap_s'], stamp_gap)
            if gap >= 0.2 and len(row['large_gaps']) < 100:
                row['large_gaps'].append({
                    'wall_elapsed_s': wall_elapsed, 'receipt_gap_s': gap,
                    'stamp_gap_s': stamp_gap, 'stamp_ns': stamp,
                })
        row['count'] += 1
        row['last_wall_elapsed_s'] = wall_elapsed
        row['last_stamp_ns'] = stamp
        if key == 'depth_health':
            row['last_status'] = {'valid': bool(msg.valid), 'state': int(msg.state), 'reason': msg.reason}
        elif key == 'localization_status':
            row['last_status'] = {'valid': bool(msg.valid), 'state': int(msg.state), 'reason': msg.reason}

    def _on_localization(self, msg):
        self._record_stream('localization_status', msg)
        self.localization_quality_history.append({
            'wall_elapsed_s': time.monotonic() - self.started_wall,
            'stamp_ns': int(msg.header.stamp.sec) * 1_000_000_000 + int(msg.header.stamp.nanosec),
            'source_stamp_ns': int(msg.source_stamp.sec) * 1_000_000_000 + int(msg.source_stamp.nanosec),
            'epoch': msg.epoch, 'state': int(msg.state), 'valid': bool(msg.valid),
            'reason': msg.reason, 'normalized_cost': float(msg.normalized_cost),
            'good_pairs': int(msg.good_pairs),
            'accepted_optimized': int(msg.accepted_optimized),
            'accepted_propagated': int(msg.accepted_propagated),
        })
        if msg.epoch and self.vins_telemetry_subscription is None:
            self.vins_telemetry_topic = f'/vins_raw/s_{msg.epoch}/estimator_telemetry'
            self.vins_telemetry_subscription = self.create_subscription(
                String, self.vins_telemetry_topic, self._on_vins_telemetry,
                self.sensor_qos)
        self.localization = msg
        self._count('localization_status')

    def _on_vins_telemetry(self, msg):
        try:
            metrics = json.loads(msg.data)
        except (TypeError, ValueError):
            self._count('malformed_vins_telemetry')
            return
        residuals = float(metrics.get('residual_components', 0) or 0)
        cost = float(metrics.get('final_cost', 0) or 0)
        normalized = math.sqrt(2.0 * cost / residuals) if residuals > 0 else None
        self.vins_quality_history.append({
            **metrics,  # Retain source diagnostics, biases and residual groups verbatim.
            'wall_elapsed_s': time.monotonic() - self.started_wall,
            'stamp_ns': int(metrics.get('stamp_ns', 0)),
            'initialized': bool(metrics.get('initialized', False)),
            'solve_current': bool(metrics.get('solve_current', False)),
            'solver_usable': bool(metrics.get('solver_usable', False)),
            'state_finite': bool(metrics.get('state_finite', False)),
            'input_features': int(metrics.get('input_features', 0)),
            'stereo_features': int(metrics.get('stereo_features', 0)),
            'continued_tracks': int(metrics.get('continued_tracks', 0)),
            'long_tracks': int(metrics.get('long_tracks', 0)),
            'residual_components': int(residuals),
            'final_cost': cost,
            'normalized_cost': normalized,
            'solve_seconds': float(metrics.get('solve_seconds', 0) or 0),
            'iterations': int(metrics.get('iterations', 0)),
            'visual_observations': int(metrics.get('visual_observations', 0)),
        })

    def _on_local_position(self, msg):
        now = time.monotonic()
        sample = {
            'wall_elapsed_s': now - self.started_wall,
            'sim_time_ns': getattr(self, 'sim_clock_ns', None),
            'timestamp_us': int(msg.timestamp),
            'timestamp_sample_us': int(msg.timestamp_sample),
            'x': float(msg.x), 'y': float(msg.y), 'z': float(msg.z),
            'vx': float(msg.vx), 'vy': float(msg.vy), 'vz': float(msg.vz),
            'heading': float(msg.heading),
            'xy_valid': bool(msg.xy_valid), 'z_valid': bool(msg.z_valid),
        }
        self.local_position_history.append(sample)
        if self.speed_observation_active:
            if msg.xy_valid and msg.z_valid:
                self._observe_speed(
                    'px4_vehicle_local_position',
                    (msg.vx, msg.vy, msg.vz), int(msg.timestamp_sample))
            else:
                self._observe_speed(
                    'px4_vehicle_local_position', (float('nan'),) * 3,
                    int(msg.timestamp_sample))
        self._count('local_position')

    def _on_odometry(self, msg):
        self._record_stream('optimized_odometry', msg)
        self.odometry = msg
        self._count('vins_optimized_odometry')

    def _on_bridge(self, msg):
        self.bridge = msg
        phase = (msg.phase, msg.reason, bool(msg.armed), bool(msg.landed))
        if not self.bridge_phases or self.bridge_phases[-1] != phase:
            self.bridge_phases.append(phase)

    def _on_bridge_detail(self, msg):
        try:
            detail = json.loads(msg.data)
        except (TypeError, ValueError):
            return
        self.latest_bridge_detail = detail
        freshness = detail.get('px4_telemetry_freshness', {})
        failed_sources = []
        for name, sample in freshness.items():
            source_age = sample.get('source_age_sim_s')
            receipt_age = sample.get('receipt_age_wall_s')
            if (source_age is None or receipt_age is None
                    or source_age < -sample.get('max_source_future_sim_s', 0.0)
                    or source_age > sample.get('max_source_age_sim_s', float('inf'))
                    or receipt_age > sample.get('max_receipt_age_wall_s', float('inf'))):
                failed_sources.append(name)
        phase, reason = detail.get('phase', ''), detail.get('reason', '')
        now = time.monotonic()
        self.bridge_detail_history.append({
            'sequence': len(self.bridge_detail_history) + 1,
            'wall_elapsed_s': now - self.started_wall,
            'phase': phase,
            'reason': reason,
            'freshness_failed_sources': failed_sources,
            'timesync_sample_count': len(self.timesync_history),
            'latest_timesync': self.latest_timesync,
            'detail': detail,
        })

    def _on_timesync_status(self, msg):
        now = time.monotonic()
        sample = {
            'sequence': len(self.timesync_history) + 1,
            'wall_elapsed_s': now - self.started_wall,
            'timestamp': int(msg.timestamp),
            'source_protocol': int(msg.source_protocol),
            'remote_timestamp': int(msg.remote_timestamp),
            'observed_offset': int(msg.observed_offset),
            'estimated_offset': int(msg.estimated_offset),
            'round_trip_time': int(msg.round_trip_time),
        }
        self.timesync_history.append(sample)
        self.latest_timesync = sample

    def _on_map(self, msg):
        self._record_stream('occupancy_cloud', msg)
        points = int(msg.width) * int(msg.height)
        self.map_point_counts.append(points)
        self._count('occupancy_cloud')

    def _on_position_command(self, msg):
        self.latest_position_command = msg
        self.position_commands.append({
            'goal_id': msg.goal_id, 'epoch': msg.epoch,
            'source_stamp_ns': int(msg.header.stamp.sec)*1000000000+int(msg.header.stamp.nanosec),
            'velocity_enu_m_s': [float(msg.velocity.x), float(msg.velocity.y), float(msg.velocity.z)],
            'acceleration_enu_m_s2': [float(msg.acceleration.x), float(msg.acceleration.y), float(msg.acceleration.z)],
            'trajectory_id': int(msg.trajectory_id),
            'flag': int(msg.trajectory_flag),
            'wall_elapsed_s': time.monotonic() - self.started_wall,
            'position_enu': [float(msg.position.x), float(msg.position.y),
                             float(msg.position.z)],
            'yaw_enu': float(msg.yaw),
        })
        if (self.speed_observation_active and msg.epoch == self.speed_observation_epoch
                and msg.trajectory_flag in (
                    PositionCommand.TRAJECTORY_STATUS_READY,
                    PositionCommand.TRAJECTORY_STATUS_COMPLETED)):
            stamp_ns = (int(msg.header.stamp.sec) * 1_000_000_000
                        + int(msg.header.stamp.nanosec))
            self._observe_speed(
                'ego_position_command_reference',
                (msg.velocity.x, msg.velocity.y, msg.velocity.z), stamp_ns)
        self._count('position_command')

    def _observe_speed(self, source, velocity, timestamp):
        values = ()
        try:
            values = tuple(float(value) for value in velocity)
            magnitude = math.sqrt(sum(value * value for value in values))
            if (len(values) == 3 and all(math.isfinite(value) for value in values)
                    and math.isfinite(magnitude)):
                self.speed_observation_maxima_m_s[source] = max(
                    magnitude, self.speed_observation_maxima_m_s.get(source, 0.0))
        except (TypeError, ValueError, OverflowError):
            magnitude = None
        valid_values = (len(values) == 3
                        and all(math.isfinite(value) for value in values))
        row = {
            'source': source,
            'velocity_m_s': list(values) if valid_values else None,
            'vector_speed_m_s': (magnitude if valid_values and magnitude is not None
                                 and math.isfinite(magnitude) else None),
            'timestamp': timestamp,
            'sim_time_ns': getattr(self, 'sim_clock_ns', None),
            'wall_elapsed_s': time.monotonic() - self.started_wall,
            'sample_valid': valid_values and magnitude is not None and math.isfinite(magnitude),
        }
        self.speed_observation_sample_counts[source] = (
            self.speed_observation_sample_counts.get(source, 0) + 1)
        if self.speed_observation_sample_counts[source] == 1:
            self.speed_observation_samples.append(row)
        self.speed_observation_last_samples[source] = row

    def _on_px4_trajectory_setpoint(self, msg):
        self.px4_setpoint_observations.append({
            'timestamp_us': int(msg.timestamp),
            'wall_elapsed_s': time.monotonic() - self.started_wall,
            'position_ned': [float(v) for v in msg.position],
            'yaw_ned_rad': float(msg.yaw),
            'yawspeed_ned_rad_s': float(msg.yawspeed),
        })
        self._count('trajectory_setpoint')

    def _on_vehicle_status(self, msg):
        self.vehicle_status = {
            'arming_state': int(msg.arming_state), 'nav_state': int(msg.nav_state),
            'pre_flight_checks_pass': bool(msg.pre_flight_checks_pass),
            'failsafe': bool(msg.failsafe),
            'timestamp': int(msg.timestamp),
        }
        self.vehicle_status_history.append({
            **self.vehicle_status,
            'sequence': len(self.vehicle_status_history) + 1,
            'wall_elapsed_s': time.monotonic() - self.started_wall,
        })
        self._count('px4_status')

    def publisher_counts(self):
        topics = ('/fmu/in/vehicle_visual_odometry',
                  '/fmu/in/offboard_control_mode',
                  '/fmu/in/trajectory_setpoint',
                  '/fmu/in/vehicle_command', '/position_cmd',
                  '/navigation/ego_goal', '/navigation/trajectory_cancel')
        return {topic: len(self.get_publishers_info_by_topic(topic)) for topic in topics}


def localization_tracking_current_epoch(node, epoch):
    if not node.localization_quality_history:
        return False
    status = node.localization_quality_history[-1]
    return (status['epoch'] == epoch and status['valid']
            and status['state'] == LocalizationStatus.TRACKING)


def localization_epoch_current(node, epoch):
    """Require the same VINS session identity; health state stays observational."""
    return node.localization is not None and node.localization.epoch == epoch


def spin_until(node, predicate, timeout_s, abort_predicate=None):
    deadline = time.monotonic() + timeout_s
    while rclpy.ok() and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.05)
        if abort_predicate is not None and abort_predicate():
            return False
        if predicate():
            return True
    return bool(predicate())


def call_enable(node, enable, timeout_s=4.0):
    if not node.enable_client.wait_for_service(timeout_sec=timeout_s):
        raise TimeoutError('enable_offboard_service_unavailable')
    request = EnableOffboard.Request()
    request.enable = enable
    future = node.enable_client.call_async(request)
    if not spin_until(node, future.done, timeout_s):
        raise TimeoutError('enable_offboard_service_timeout')
    response = future.result()
    if response is None:
        raise RuntimeError('enable_offboard_service_empty_response')
    return {'accepted': bool(response.accepted), 'reason': response.reason}


def expected_fault_abort_matches(action_result, expected_reason):
    """Match one explicitly expected native fault-abort reason."""
    return bool(
        expected_reason
        and isinstance(action_result, dict)
        and action_result.get('outcome') == 'aborted'
        and expected_reason in str(action_result.get('reason') or '')
    )


def run_n10_cancel_diagnostic(node, handle, action_future, goal_id, epoch,
                              speed_window_m_s, timeout_s):
    """Cancel one official EGO goal at a measured PX4 speed and observe its stop."""
    lower, upper = map(float, speed_window_m_s)
    if not (math.isfinite(lower) and math.isfinite(upper) and 0.0 < lower < upper):
        raise ValueError('cancel_speed_window_must_be_finite_positive_increasing')
    deadline = time.monotonic() + float(timeout_s)
    trigger = None
    trigger_local_index = None
    while rclpy.ok() and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.01)
        if action_future.done():
            raise RuntimeError('navigation_goal_finished_before_cancel_speed_window')
        if (node.bridge is None or node.bridge.phase != 'ACTIVE' or not node.bridge.armed
                or node.bridge.landed):
            raise RuntimeError('bridge_left_active_before_cancel_speed_window')
        if not localization_epoch_current(node, epoch):
            raise RuntimeError('localization_epoch_changed_before_cancel_speed_window')
        command = node.position_commands[-1] if node.position_commands else None
        local_index = len(node.local_position_history) - 1
        local = node.local_position_history[local_index] if local_index >= 0 else None
        trigger = cancel_trigger(
            command, local, goal_id=goal_id, epoch=epoch,
            ready_flag=PositionCommand.TRAJECTORY_STATUS_READY,
            speed_window_m_s=(lower, upper))
        if trigger is not None:
            trigger_local_index = local_index
            trigger['request_wall_elapsed_s'] = time.monotonic() - node.started_wall
            trigger['command_wall_elapsed_s'] = command['wall_elapsed_s']
            trigger['px4_local_wall_elapsed_s'] = local['wall_elapsed_s']
            trigger['cancel_trigger_speed_window_m_s'] = [lower, upper]
            break
        trigger = None
    if trigger is None:
        raise TimeoutError('px4_speed_window_not_observed_before_goal_end')

    node.n10_cancel_diagnostic = trigger
    old_trajectory_id = int(trigger['ego_reference_trajectory_id'])
    cancel_start_wall = time.monotonic()
    cancel_future = handle.cancel_goal_async()
    if not spin_until(node, cancel_future.done, 3.0):
        raise TimeoutError('caller_cancel_acknowledgement_timeout')
    cancel_response = cancel_future.result()
    trigger['cancel_acknowledged'] = bool(cancel_response.goals_canceling)
    trigger['cancel_ack_wall_delay_s'] = time.monotonic() - cancel_start_wall
    if not trigger['cancel_acknowledged']:
        raise RuntimeError('caller_cancel_not_accepted')
    node.n10_cancel_diagnostic = trigger
    if not spin_until(node, action_future.done, 5.0):
        raise TimeoutError('canceled_navigation_action_result_timeout')
    wrapped = action_future.result()
    nav_result = wrapped.result
    trigger['action_result'] = {
        'status': int(wrapped.status), 'success': bool(nav_result.success),
        'outcome': nav_result.outcome, 'reason': nav_result.reason,
    }
    trigger['action_result_wall_elapsed_s'] = time.monotonic() - node.started_wall
    node.n10_cancel_diagnostic = trigger
    if not (int(wrapped.status) == 5 and nav_result.outcome == 'canceled'
            and nav_result.reason == 'caller_cancel' and not nav_result.success):
        raise RuntimeError('navigation_action_did_not_report_caller_cancel')

    tracker = StopWindowTracker(trigger_sim_ns=int(trigger['request_sim_ns']))
    next_local_index = int(trigger_local_index)
    stop_window = None
    replacement = None
    stop_deadline = time.monotonic() + max(45.0, min(float(timeout_s), 90.0))
    while rclpy.ok() and time.monotonic() < stop_deadline:
        rclpy.spin_once(node, timeout_sec=0.01)
        if (node.bridge is None or node.bridge.phase != 'ACTIVE' or not node.bridge.armed
                or node.bridge.landed):
            raise RuntimeError('bridge_left_active_during_cancel_stop')
        if not localization_epoch_current(node, epoch):
            raise RuntimeError('localization_epoch_changed_during_cancel_stop')
        replacement_rows = [row for row in node.position_commands
                            if row['goal_id'] == goal_id and row['epoch'] == epoch
                            and row['source_stamp_ns'] >= int(trigger['request_sim_ns'])
                            and row['trajectory_id'] != old_trajectory_id]
        if replacement is None and replacement_rows:
            replacement = replacement_rows[0]
        for row in node.local_position_history[next_local_index:]:
            stop_window = tracker.observe(row)
            if stop_window is not None:
                break
        next_local_index = len(node.local_position_history)
        if stop_window is not None and replacement is not None:
            break

    if replacement is None:
        raise TimeoutError('replacement_ego_trajectory_not_observed_after_cancel')
    if stop_window is None:
        raise TimeoutError('px4_stop_band_not_held_for_one_simulation_second')
    trigger['old_trajectory_id'] = old_trajectory_id
    trigger['replacement_trajectory'] = {
        'trajectory_id': int(replacement['trajectory_id']),
        'first_source_stamp_ns': int(replacement['source_stamp_ns']),
        'first_velocity_enu_m_s': replacement['velocity_enu_m_s'],
        'first_acceleration_enu_m_s2': replacement['acceleration_enu_m_s2'],
        'first_wall_elapsed_s': replacement['wall_elapsed_s'],
        'distinct_from_canceled_trajectory': (
            int(replacement['trajectory_id']) != old_trajectory_id),
    }
    node.n10_cancel_diagnostic = trigger
    trigger['stop_band'] = stop_window
    node.n10_cancel_diagnostic = trigger
    trigger['stop_distance_definition'] = (
        'Gazebo truth horizontal path length from request_sim_ns to stop_band.start_sim_ns; '
        'computed offline with no truth input to control')
    return trigger


def telemetry_sources_fresh(detail):
    sources = detail.get('px4_telemetry_freshness', {})
    required = ('vehicle_status', 'local_position', 'attitude',
                'estimator_flags', 'land_detected')
    for name in required:
        sample = sources.get(name)
        if not isinstance(sample, dict):
            return False
        age = sample.get('source_age_sim_s')
        receipt_age = sample.get('receipt_age_wall_s')
        if (age is None or receipt_age is None
                or not math.isfinite(float(age))
                or not math.isfinite(float(receipt_age))
                or float(age) < -float(sample['max_source_future_sim_s'])
                or float(age) > float(sample['max_source_age_sim_s'])
                or float(receipt_age) > float(sample['max_receipt_age_wall_s'])):
            return False
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-root', default='.')
    parser.add_argument('--goal-config', default='config/components/navigation/room_crossing_goal.json')
    parser.add_argument('--output', required=True)
    parser.add_argument('--precondition-timeout-s', type=float, default=30.0)
    parser.add_argument('--flight-timeout-s', type=float, default=90.0)
    parser.add_argument('--landing-timeout-s', type=float, default=45.0)
    parser.add_argument('--cancel-speed-window', nargs=2, type=float,
                        metavar=('MIN_M_S', 'MAX_M_S'),
                        help='N10 diagnostic: cancel the single official EGO goal at measured PX4 horizontal speed')
    parser.add_argument('--expected-fault-abort-reason',
                        help='N10 fault calibration only: accept this native action-abort reason and wait for bridge-owned landing without disabling Offboard')
    args = parser.parse_args()
    if args.expected_fault_abort_reason and args.cancel_speed_window is not None:
        parser.error('fault-terminal and caller-cancel diagnostic modes are mutually exclusive')
    root = Path(args.project_root).resolve()
    goal_config = json.loads((root / args.goal_config).read_text())
    profile_config = dict(goal_config)
    result = {'profile': 'vio_closed_loop', 'result': 'FAIL', 'service_calls': [],
              'action_goal_sent': False, 'action_success': False}
    result['localization_quality_policy'] = 'quality_and_freshness_thresholds_removed; raw metrics observational'

    official_ego = json.loads((root/'config/components/navigation/task_supervisor.json').read_text()).get('collision_policy') == 'official_ego'
    result['collision_policy'] = 'official_ego' if official_ego else 'known_free'
    mission_legs = legs(goal_config)
    minimum_navigation_sim_s = navigation_duration_requirement(goal_config)
    navigation_start_ns = None
    if args.cancel_speed_window is not None:
        if not official_ego or len(mission_legs) != 1:
            raise ValueError('n10_cancel_diagnostic_requires_one_official_ego_goal')
        lower, upper = map(float, args.cancel_speed_window)
        if not (math.isfinite(lower) and math.isfinite(upper) and 0.0 < lower < upper):
            raise ValueError('cancel_speed_window_must_be_finite_positive_increasing')
        result['run_classification'] = 'diagnostic_caller_cancel_stop; not formal qualification'
        result['cancel_trigger_speed_window_m_s'] = [lower, upper]
        result['formal_qualification'] = False
    if args.expected_fault_abort_reason:
        result['run_classification'] = 'diagnostic fault-terminal calibration; not formal qualification'
        result['expected_fault_abort_reason'] = args.expected_fault_abort_reason
        result['formal_qualification'] = False
    result['goal_config'] = args.goal_config
    result['legs'] = []
    result['runtime_speed_guard'] = {
        'enabled': False,
        'reason': 'user_removed_extra_speed_caps',
    }
    result['runtime_speed_observation'] = {
        'sources': ['ego_position_command_reference', 'px4_vehicle_local_position'],
        'mode': 'observation_only',
        'truth_used_for_control': False,
    }
    rclpy.init()
    node = EgoFlightProbe()
    node.sim_clock_ns = None
    node.sim_clock_regressions = 0
    node.sim_clock_history = []
    node.sim_clock_recorded_ns = None

    def on_clock(message):
        stamp = int(message.clock.sec) * 1_000_000_000 + int(message.clock.nanosec)
        previous = node.sim_clock_ns
        if previous is not None and stamp < previous:
            node.sim_clock_regressions += 1
        node.sim_clock_ns = stamp
        if (node.sim_clock_recorded_ns is None or stamp < node.sim_clock_recorded_ns
                or stamp - node.sim_clock_recorded_ns >= 1_000_000_000):
            node.sim_clock_history.append({
                'wall_elapsed_s': time.monotonic() - node.started_wall,
                'sim_time_ns': stamp,
            })
            node.sim_clock_recorded_ns = stamp

    node.create_subscription(Clock, '/clock', on_clock, node.sensor_qos)
    try:
        gate = Path(args.output).parent/'preflight.json'
        (gate.parent/'flight-probe-ready').touch()
        if not spin_until(node, gate.exists, 100.0):
            raise TimeoutError('preflight_report_missing')
        if not json.loads(gate.read_text())['passed']:
            raise RuntimeError('preflight_failed')
        if not node.action_client.wait_for_server(timeout_sec=8.0):
            raise TimeoutError('navigation_action_server_unavailable')
        ready = spin_until(node, lambda: (
            node.localization is not None
            and bool(node.localization.epoch)
            and node.odometry is not None
            and node.bridge is not None
            and (node.bridge.ready or node.bridge.reason == 'px4_preflight_failed')
            and node.bridge.phase == 'DISABLED'
            and node.bridge.landed and not node.bridge.armed
            and node.bridge.local_position_valid
            and node.bridge.ev_position_fused and node.bridge.ev_yaw_fused
            and not node.bridge.gnss_aiding_active
            and (official_ego or (bool(node.map_point_counts)
                 and max(node.map_point_counts) >= int(goal_config['minimum_occupancy_points'])))
        ), args.precondition_timeout_s)
        result['preconditions_ready'] = ready
        result['localization_epoch'] = node.localization.epoch if node.localization else ''
        result['map_max_point_count_before_enable'] = max(node.map_point_counts, default=0)
        if not ready:
            raise TimeoutError('vio_bridge_map_preconditions_not_ready')
        if node.odometry.header.frame_id != f'odom_{node.localization.epoch}':
            raise RuntimeError('vio_epoch_frame_mismatch')
        if not spin_until(node, lambda: node.sim_clock_ns is not None, 10.0):
            raise TimeoutError('simulation_clock_unavailable_before_enable')

        result['project_local_age_gates_enabled'] = False
        result['project_local_stability_window_s'] = 0.0
        result['localization_tracking_at_enable'] = localization_tracking_current_epoch(
            node, result['localization_epoch'])
        result['localization_epoch_current_at_enable'] = localization_epoch_current(
            node, result['localization_epoch'])
        result['localization_status_at_enable'] = (
            {'valid': bool(node.localization.valid), 'state': int(node.localization.state),
             'reason': node.localization.reason} if node.localization else None)
        result['px4_telemetry_detail_at_enable'] = node.latest_bridge_detail
        result['px4_telemetry_age_observation_samples_at_enable'] = len(
            node.bridge_detail_history)
        if not result['localization_epoch_current_at_enable']:
            raise RuntimeError('localization_epoch_unavailable_at_enable')

        if official_ego:
            velocity = node.odometry.twist.twist.linear
            speed = math.sqrt(velocity.x**2 + velocity.y**2 + velocity.z**2)
            result['takeoff_speed_at_enable_m_s_observed'] = (
                speed if math.isfinite(speed) else None)
            result['takeoff_speed_control_effect'] = 'observation_only'
        enabled = call_enable(node, True)
        result['service_calls'].append({'enable': True, **enabled})
        if not enabled['accepted']:
            raise RuntimeError('offboard_enable_rejected:' + enabled['reason'])
        active = spin_until(node, lambda: (
            node.bridge is not None and node.bridge.phase == 'ACTIVE'
            and node.bridge.armed and not node.bridge.landed
            and localization_epoch_current(node, result['localization_epoch'])
        ), args.flight_timeout_s, abort_predicate=lambda: not localization_epoch_current(
            node, result['localization_epoch']))
        result['takeoff_active_observed'] = active
        if not active and not localization_epoch_current(node, result['localization_epoch']):
            raise RuntimeError('localization_epoch_changed_during_takeoff')
        if not active:
            raise TimeoutError('bridge_did_not_reach_active_after_takeoff')

        for subscription in list(node.subscriptions):
            if subscription.topic_name == '/grid_map/occupancy':
                node.destroy_subscription(subscription)
        result['diagnostic_scope'] = 'No project-local VINS health-state, quality, or age admission/abort gates; VINS epoch, clock, mapping identity, native EGO behavior, and PX4 control checks remain active.'

        pose = node.odometry.pose.pose
        initial_position = [float(pose.position.x), float(pose.position.y), float(pose.position.z)]
        yaw = math.atan2(2.0 * (pose.orientation.w * pose.orientation.z
                                + pose.orientation.x * pose.orientation.y),
                         1.0 - 2.0 * (pose.orientation.y ** 2 + pose.orientation.z ** 2))
        result['airborne_origin_enu'] = initial_position
        for leg_index, goal_config in enumerate(mission_legs):
            result['active_leg_index'] = leg_index
            result['action_success'] = False
            result.pop('goal_completed_source_ns', None)
            if not localization_epoch_current(node, result['localization_epoch']):
                raise RuntimeError('localization_epoch_changed_before_next_leg')
            goal = NavigateToPose.Goal()
            goal.target.header.frame_id = f'odom_{node.localization.epoch}'
            goal.target.header.stamp = node.odometry.header.stamp
            goal.target.pose.position.x = initial_position[0] + float(goal_config['target_offset_enu_m'][0])
            goal.target.pose.position.y = initial_position[1] + float(goal_config['target_offset_enu_m'][1])
            goal.target.pose.position.z = initial_position[2] + float(goal_config['target_offset_enu_m'][2])
            target_yaw = yaw + float(goal_config.get('yaw_offset_rad', 0.0))
            goal.target.pose.orientation.z = math.sin(target_yaw / 2.0)
            goal.target.pose.orientation.w = math.cos(target_yaw / 2.0)
            goal.position_tolerance_m = float(goal_config['position_tolerance_m'])
            goal.yaw_tolerance_rad = float(goal_config['yaw_tolerance_rad'])
            goal.dwell_s = float(goal_config['dwell_s'])
            goal.timeout_s = float(goal_config['timeout_s'])
            result['goal'] = {
                'frame': goal.target.header.frame_id,
                'target_enu': [goal.target.pose.position.x, goal.target.pose.position.y,
                               goal.target.pose.position.z],
                'yaw_enu': target_yaw,
                'yaw_offset_rad': float(goal_config.get('yaw_offset_rad', 0.0)),
                'position_tolerance_m': goal.position_tolerance_m,
                'yaw_tolerance_rad': goal.yaw_tolerance_rad,
                'timeout_s': goal.timeout_s,
            }
            result['goal']['source_ns'] = node.odometry.header.stamp.sec * 10**9 + node.odometry.header.stamp.nanosec
            result['goal_start_sim_ns'] = node.sim_clock_ns
            if navigation_start_ns is None:
                navigation_start_ns = node.sim_clock_ns
            node.speed_observation_epoch = result['localization_epoch']
            node.speed_observation_active = True
            send_future = node.action_client.send_goal_async(goal)
            if not spin_until(node, send_future.done, 5.0):
                raise TimeoutError('navigation_goal_response_timeout')
            handle = send_future.result()
            if handle is None or not handle.accepted:
                raise RuntimeError('navigation_goal_rejected')
            result['action_goal_sent'] = True
            result['goal_sent_wall_elapsed_s'] = time.monotonic() - node.started_wall
            result['goal_id'] = bytes(handle.goal_id.uuid).hex()
            action_future = handle.get_result_async()
            goal_wall_watchdog = float(profile_config.get(
                'goal_wall_watchdog_s', goal.timeout_s * 10.0 + 4.0))
            if not math.isfinite(goal_wall_watchdog) or goal_wall_watchdog <= 0.0:
                raise ValueError('goal_wall_watchdog_s_must_be_finite_positive')
            if args.cancel_speed_window is not None:
                cancel_record = run_n10_cancel_diagnostic(
                    node, handle, action_future, result['goal_id'],
                    result['localization_epoch'], args.cancel_speed_window,
                    min(goal_wall_watchdog, goal.timeout_s + 30.0))
                result['cancel_stop'] = cancel_record
                result['action_result'] = cancel_record['action_result']
                result['action_success'] = False
                result['action_canceled'] = True
                result['cancel_diagnostic_completed'] = True
                result['legs'].append({
                    'goal': result['goal'], 'goal_id': result['goal_id'],
                    'action_result': result['action_result'],
                    'action_success': False, 'action_canceled': True,
                    'cancel_stop': cancel_record,
                    'goal_sent_wall_elapsed_s': result['goal_sent_wall_elapsed_s'],
                })
                break
            goal_start_wall = time.monotonic()
            goal_start_sim_ns = node.sim_clock_ns
            finished = spin_until(
                node, action_future.done, goal_wall_watchdog)
            goal_end_wall = time.monotonic()
            goal_end_sim_ns = node.sim_clock_ns
            goal_elapsed_sim_s = (
                (goal_end_sim_ns - goal_start_sim_ns) / 1e9
                if goal_start_sim_ns is not None and goal_end_sim_ns is not None
                else None)
            result['goal_timing'] = {
                'timeout_sim_s': goal.timeout_s,
                'wall_watchdog_s': goal_wall_watchdog,
                'wall_elapsed_s': goal_end_wall - goal_start_wall,
                'sim_elapsed_s': goal_elapsed_sim_s,
                'realtime_factor_sim_over_wall': (
                    goal_elapsed_sim_s / (goal_end_wall - goal_start_wall)
                    if goal_elapsed_sim_s is not None and goal_end_wall > goal_start_wall
                    else None),
                'clock_regressions': node.sim_clock_regressions,
            }
            if not finished:
                try:
                    cancel_future = handle.cancel_goal_async()
                    cancel_acknowledged = spin_until(node, cancel_future.done, 2.0)
                    cancel_response = cancel_future.result() if cancel_acknowledged else None
                    result['watchdog_cancel'] = {
                        'request_sent': True,
                        'response_received': cancel_acknowledged,
                        'accepted': bool(cancel_response.goals_canceling)
                        if cancel_response is not None else False,
                    }
                except Exception as cancel_exc:
                    result['watchdog_cancel'] = {
                        'request_sent': True, 'response_received': False,
                        'accepted': False, 'error': str(cancel_exc),
                    }
                raise TimeoutError('navigation_goal_result_timeout')
            wrapped = action_future.result()
            nav_result = wrapped.result
            result['action_result'] = {
                'status': int(wrapped.status), 'success': bool(nav_result.success),
                'outcome': nav_result.outcome, 'reason': nav_result.reason,
                'final_position': [float(nav_result.final_pose.pose.position.x),
                                   float(nav_result.final_pose.pose.position.y),
                                   float(nav_result.final_pose.pose.position.z)],
            }
            result['action_success'] = bool(nav_result.success and nav_result.outcome == 'succeeded')
            if not result['action_success']:
                if expected_fault_abort_matches(
                        result['action_result'], args.expected_fault_abort_reason):
                    result['expected_fault_abort_observed'] = True
                    fault_state_seen = spin_until(node, lambda: (
                        node.bridge is not None
                        and node.bridge.phase in ('LANDING', 'LANDED')
                    ), min(5.0, args.landing_timeout_s))
                    result['bridge_fault_landing_started'] = fault_state_seen
                    if not fault_state_seen:
                        raise RuntimeError('native_fault_abort_without_bridge_landing')
                    landed = spin_until(node, lambda: (
                        node.bridge is not None and node.bridge.phase == 'LANDED'
                        and node.bridge.landed and not node.bridge.armed
                    ), args.landing_timeout_s)
                    result['landed_and_disarmed'] = landed
                    result['bridge_reason_at_terminal'] = (
                        node.bridge.reason if node.bridge is not None else '')
                    if not landed:
                        raise TimeoutError('native_fault_landing_terminal_timeout')
                    result['result'] = 'EXPECTED_FAULT_TERMINAL'
                    result['legs'].append({
                        'goal': result['goal'], 'goal_id': result['goal_id'],
                        'action_result': result['action_result'],
                        'action_success': False,
                        'expected_fault_abort_observed': True,
                        'bridge_fault_landing_started': True,
                        'landed_and_disarmed': True,
                        'goal_sent_wall_elapsed_s': result['goal_sent_wall_elapsed_s'],
                    })
                    break
                raise RuntimeError('navigation_action_not_successful:' + nav_result.reason)

            matching = [item for item in node.position_commands
                        if item['goal_id'] == result['goal_id']
                        and item['epoch'] == result['localization_epoch']
                        and item['flag'] == PositionCommand.TRAJECTORY_STATUS_READY]
            result['matching_ready_trajectory_samples'] = len(matching)
            if not matching:
                raise RuntimeError('no_matching_ego_ready_position_command_observed')
            result['goal_completed_source_ns'] = node.odometry.header.stamp.sec * 10**9 + node.odometry.header.stamp.nanosec
            result['legs'].append({k: result[k] for k in ('goal', 'goal_id', 'action_result', 'action_success', 'goal_sent_wall_elapsed_s', 'goal_start_sim_ns', 'goal_completed_source_ns', 'matching_ready_trajectory_samples')})
            if minimum_navigation_sim_s > 0:
                elapsed = navigation_elapsed_sim_s(navigation_start_ns, node.sim_clock_ns)
                result['continuous_navigation'] = {
                    'required_sim_s': minimum_navigation_sim_s,
                    'start_source_ns': navigation_start_ns,
                    'end_source_ns': node.sim_clock_ns,
                    'observed_sim_s': elapsed,
                    'completed_goal_count': len(result['legs']),
                    'same_airborne_session': True,
                }
                if elapsed >= minimum_navigation_sim_s:
                    break

        if minimum_navigation_sim_s > 0 and (
                result.get('continuous_navigation', {}).get('observed_sim_s', 0)
                < minimum_navigation_sim_s):
            raise RuntimeError('bounded_mission_exhausted_before_required_navigation_duration')


        hold_sim_s = (0.0 if (args.cancel_speed_window is not None
                              or result.get('expected_fault_abort_observed') is True) else
                      float(profile_config.get('diagnostic_post_goal_hold_sim_s', 0.0)))
        if args.cancel_speed_window is not None:
            result['post_goal_hold_skipped'] = 'caller-cancel stop measurement ends with a 1s measured PX4 stop band'
        elif result.get('expected_fault_abort_observed') is True:
            result['post_goal_hold_skipped'] = 'native fault landing owns terminal; no post-abort operator command'
        if not math.isfinite(hold_sim_s) or hold_sim_s < 0.0:
            raise ValueError('diagnostic_post_goal_hold_sim_s_must_be_finite_nonnegative')
        if hold_sim_s > 0.0:
            hold_wall_timeout_s = float(profile_config.get(
                'diagnostic_post_goal_hold_wall_timeout_s', hold_sim_s * 10.0 + 30.0))
            clock_stall_wall_s = float(profile_config.get('sim_clock_stall_wall_s', 15.0))
            if (not math.isfinite(hold_wall_timeout_s) or hold_wall_timeout_s <= 0.0
                    or not math.isfinite(clock_stall_wall_s) or clock_stall_wall_s <= 0.0):
                raise ValueError('invalid_post_goal_hold_watchdog_configuration')
            if node.sim_clock_ns is None:
                raise RuntimeError('simulation_clock_missing_before_post_goal_hold')
            hold_start_wall = time.monotonic()
            hold_start_sim_ns = node.sim_clock_ns
            last_clock_ns = node.sim_clock_ns
            last_clock_progress_wall = hold_start_wall
            start_pose = node.odometry.pose.pose
            hold_start_odom = [float(start_pose.position.x), float(start_pose.position.y),
                               float(start_pose.position.z)]
            hold_abort = None
            while rclpy.ok():
                now = time.monotonic()
                current_clock_ns = node.sim_clock_ns
                if current_clock_ns is not None and current_clock_ns > last_clock_ns:
                    last_clock_ns = current_clock_ns
                    last_clock_progress_wall = now
                if current_clock_ns is not None and current_clock_ns < last_clock_ns:
                    hold_abort = 'simulation_clock_regressed_during_hold'
                    break
                if node.sim_clock_regressions:
                    hold_abort = 'simulation_clock_regressed_during_hold'
                    break
                if current_clock_ns is None or (now - last_clock_progress_wall) > clock_stall_wall_s:
                    hold_abort = 'simulation_clock_stalled_during_hold'
                    break
                if node.bridge is None or node.bridge.phase != 'ACTIVE' or not node.bridge.armed:
                    hold_abort = 'bridge_left_active_armed_state_during_hold'
                    break
                if not localization_epoch_current(node, result['localization_epoch']):
                    hold_abort = 'localization_epoch_changed_during_hold'
                    break
                if (current_clock_ns - hold_start_sim_ns) >= hold_sim_s * 1e9:
                    break
                if now - hold_start_wall >= hold_wall_timeout_s:
                    hold_abort = 'post_goal_hold_wall_watchdog_expired'
                    break
                rclpy.spin_once(node, timeout_sec=0.05)
            hold_end_wall = time.monotonic()
            hold_end_sim_ns = node.sim_clock_ns
            hold_end_pose = node.odometry.pose.pose if node.odometry is not None else None
            hold_end_odom = ([float(hold_end_pose.position.x), float(hold_end_pose.position.y),
                              float(hold_end_pose.position.z)] if hold_end_pose is not None else None)
            hold_elapsed_sim_s = (
                (hold_end_sim_ns - hold_start_sim_ns) / 1e9
                if hold_end_sim_ns is not None else None)
            result['post_goal_hold'] = {
                'requested_sim_s': hold_sim_s,
                'observed_sim_s': hold_elapsed_sim_s,
                'wall_elapsed_s': hold_end_wall - hold_start_wall,
                'wall_watchdog_s': hold_wall_timeout_s,
                'clock_stall_watchdog_s': clock_stall_wall_s,
                'realtime_factor_sim_over_wall': (
                    hold_elapsed_sim_s / (hold_end_wall - hold_start_wall)
                    if hold_elapsed_sim_s is not None and hold_end_wall > hold_start_wall
                    else None),
                'start_odometry_position_enu_m': hold_start_odom,
                'end_odometry_position_enu_m': hold_end_odom,
                'completed': (hold_abort is None and hold_elapsed_sim_s is not None
                              and hold_elapsed_sim_s >= hold_sim_s),
                'abort_reason': hold_abort,
                'bridge_status_at_end': ({
                    'phase': node.bridge.phase, 'armed': bool(node.bridge.armed),
                    'landed': bool(node.bridge.landed), 'reason': node.bridge.reason,
                } if node.bridge is not None else None),
            }
            if hold_abort is not None or not result['post_goal_hold']['completed']:
                raise RuntimeError(hold_abort or 'post_goal_hold_incomplete')

        node.speed_observation_active = False
        if result.get('expected_fault_abort_observed') is True:
            # Preserve the bridge-owned native fault landing. Do not race it
            # with the runner's normal operator-disable closeout.
            result['operator_disable_sent_after_fault'] = False
        else:
            disabled = call_enable(node, False)
            result['service_calls'].append({'enable': False, **disabled})
            if not disabled['accepted']:
                raise RuntimeError('offboard_disable_rejected:' + disabled['reason'])
            landed = spin_until(node, lambda: (
                node.bridge is not None and node.bridge.phase == 'LANDED'
                and node.bridge.landed and not node.bridge.armed
            ), args.landing_timeout_s)
            result['landed_and_disarmed'] = landed
            if not landed:
                raise TimeoutError('landed_disarmed_not_observed_after_goal')
            result['result'] = 'PASS'
    except Exception as exc:
        result['failure'] = str(exc)
        node.speed_observation_active = False
        preserve_native_fault_path = (
            bool(args.expected_fault_abort_reason)
            and result.get('expected_fault_abort_observed') is True
            and not result.get('landed_and_disarmed'))
        result['operator_disable_suppressed_for_native_fault'] = preserve_native_fault_path
        if (not preserve_native_fault_path and node.bridge is not None
                and node.bridge.phase not in ('DISABLED', 'LANDED', 'LOCKED')):
            try:
                disabled = call_enable(node, False)
                result['service_calls'].append({'enable': False, **disabled})
                if node.bridge.armed or node.bridge.phase in ('TAKEOFF', 'ACTIVE', 'LANDING'):
                    result['landed_and_disarmed'] = spin_until(node, lambda: (
                        node.bridge is not None and node.bridge.phase == 'LANDED'
                        and node.bridge.landed and not node.bridge.armed
                    ), args.landing_timeout_s)
                else:
                    result['disabled_before_arm'] = spin_until(node, lambda: (
                        node.bridge is not None and node.bridge.phase in ('DISABLED', 'LOCKED')
                        and not node.bridge.armed
                    ), 3.0)
            except Exception as land_exc:
                result['landing_error'] = str(land_exc)
    finally:
        if args.cancel_speed_window is not None and 'cancel_stop' not in result:
            result['cancel_stop'] = getattr(node, 'n10_cancel_diagnostic', None)
        result['counts'] = dict(node.counts)
        result['stream_diagnostics'] = node.streams
        result['localization_quality_history'] = node.localization_quality_history
        result['vins_quality_history'] = node.vins_quality_history
        result['vins_telemetry_topic'] = node.vins_telemetry_topic
        result['local_position_history'] = node.local_position_history
        result['map_point_count_max'] = max(node.map_point_counts, default=0)
        result['position_command_history'] = node.position_commands
        result['speed_observation_samples'] = node.speed_observation_samples
        result['speed_observation_sample_counts'] = node.speed_observation_sample_counts
        result['speed_observation_last_samples'] = node.speed_observation_last_samples
        result['speed_observation_maxima_m_s'] = node.speed_observation_maxima_m_s
        result['px4_trajectory_setpoint_observations'] = node.px4_setpoint_observations
        result['position_command_flag_counts'] = {
            str(flag): count for flag, count in Counter(
                item['flag'] for item in node.position_commands).items()}
        result['bridge_phases'] = node.bridge_phases
        result['latest_bridge_detail'] = node.latest_bridge_detail
        result['bridge_detail_history'] = node.bridge_detail_history
        result['timesync_history'] = node.timesync_history
        result['simulation_clock_history'] = node.sim_clock_history
        result['simulation_clock_regressions'] = node.sim_clock_regressions
        result['latest_bridge_status'] = ({
            'phase': node.bridge.phase, 'reason': node.bridge.reason,
            'armed': bool(node.bridge.armed), 'landed': bool(node.bridge.landed),
            'ready': bool(node.bridge.ready),
        } if node.bridge is not None else None)
        result['latest_vehicle_status'] = node.vehicle_status
        result['vehicle_status_history'] = node.vehicle_status_history
        result['latest_localization_status'] = ({
            'epoch': node.localization.epoch, 'state': int(node.localization.state),
            'valid': bool(node.localization.valid), 'reason': node.localization.reason,
            'accepted_optimized': int(node.localization.accepted_optimized),
            'accepted_propagated': int(node.localization.accepted_propagated),
        } if node.localization is not None else None)
        result['publisher_counts'] = node.publisher_counts()
        goal_id = result.get('goal_id', '')
        result['matching_ready_trajectory_samples'] = sum(
            item['goal_id'] == goal_id
            and item['epoch'] == result.get('localization_epoch')
            and item['flag'] == PositionCommand.TRAJECTORY_STATUS_READY
            for item in node.position_commands)
        write_json_atomic(Path(args.output), result, indent=2, sort_keys=True)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    print(json.dumps(result, indent=2, sort_keys=True))
    if (result['result'] != 'PASS'
            and not (result['result'] == 'EXPECTED_FAULT_TERMINAL'
                     and result.get('landed_and_disarmed') is True)):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
