#!/usr/bin/env python3
"""Run one service-gated VIO EGO goal, then land through the PX4 bridge."""

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import time

import rclpy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from px4_msgs.msg import (OffboardControlMode, TrajectorySetpoint,
                          VehicleCommand, VehicleLocalPosition,
                          VehicleOdometry, VehicleStatus, TimesyncStatus)
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
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
        self.local_position_history.append({
            'wall_elapsed_s': now - self.started_wall,
            'timestamp_us': int(msg.timestamp),
            'timestamp_sample_us': int(msg.timestamp_sample),
            'x': float(msg.x), 'y': float(msg.y), 'z': float(msg.z),
            'vx': float(msg.vx), 'vy': float(msg.vy), 'vz': float(msg.vz),
            'heading': float(msg.heading),
            'xy_valid': bool(msg.xy_valid), 'z_valid': bool(msg.z_valid),
        })
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
            'trajectory_id': int(msg.trajectory_id),
            'flag': int(msg.trajectory_flag),
            'wall_elapsed_s': time.monotonic() - self.started_wall,
            'position_enu': [float(msg.position.x), float(msg.position.y),
                             float(msg.position.z)],
            'yaw_enu': float(msg.yaw),
        })
        self._count('position_command')

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


def localization_tracking_fresh(node, epoch, max_status_age_s=0.2):
    if not node.localization_quality_history:
        return False
    status = node.localization_quality_history[-1]
    status_wall = node.started_wall + status['wall_elapsed_s']
    return (status['epoch'] == epoch and status['valid']
            and status['state'] == LocalizationStatus.TRACKING
            and time.monotonic() - status_wall <= max_status_age_s)


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
    parser.add_argument('--px4-fresh-stability-s', type=float, default=5.0)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    goal_config = json.loads((root / args.goal_config).read_text())
    result = {'profile': 'vio_closed_loop', 'result': 'FAIL', 'service_calls': [],
              'action_goal_sent': False, 'action_success': False}

    rclpy.init()
    node = EgoFlightProbe()
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
            and node.localization.valid
            and node.localization.state == LocalizationStatus.TRACKING
            and node.odometry is not None
            and node.bridge is not None
            and (node.bridge.ready or node.bridge.reason == 'px4_preflight_failed')
            and node.bridge.phase == 'DISABLED'
            and node.bridge.landed and not node.bridge.armed
            and node.bridge.local_position_valid
            and node.bridge.ev_position_fused and node.bridge.ev_yaw_fused
            and not node.bridge.gnss_aiding_active
            and bool(node.map_point_counts)
            and max(node.map_point_counts) >= int(goal_config['minimum_occupancy_points'])
        ), args.precondition_timeout_s)
        result['preconditions_ready'] = ready
        result['localization_epoch'] = node.localization.epoch if node.localization else ''
        result['map_max_point_count_before_enable'] = max(node.map_point_counts, default=0)
        if not ready:
            raise TimeoutError('vio_bridge_map_preconditions_not_ready')
        if node.odometry.header.frame_id != f'odom_{node.localization.epoch}':
            raise RuntimeError('vio_epoch_frame_mismatch')

        stability_start = None
        stable_deadline = time.monotonic() + args.precondition_timeout_s
        while rclpy.ok() and time.monotonic() < stable_deadline:
            rclpy.spin_once(node, timeout_sec=0.05)
            now = time.monotonic()
            if (telemetry_sources_fresh(node.latest_bridge_detail or {})
                    and localization_tracking_fresh(node, result['localization_epoch'])):
                if stability_start is None:
                    stability_start = now
                if now - stability_start >= args.px4_fresh_stability_s:
                    break
            else:
                stability_start = None
        result['px4_telemetry_stability_required_s'] = args.px4_fresh_stability_s
        result['localization_tracking_stability_passed'] = (
            stability_start is not None
            and time.monotonic() - stability_start >= args.px4_fresh_stability_s
            and localization_tracking_fresh(node, result['localization_epoch']))
        result['px4_telemetry_stability_passed'] = (
            stability_start is not None
            and time.monotonic() - stability_start >= args.px4_fresh_stability_s
            and telemetry_sources_fresh(node.latest_bridge_detail or {}))
        result['px4_telemetry_detail_at_enable'] = node.latest_bridge_detail
        result['px4_telemetry_fresh_samples_at_enable'] = sum(
            not sample['freshness_failed_sources']
            and telemetry_sources_fresh(sample['detail'])
            for sample in node.bridge_detail_history
            if stability_start is not None
            and sample['wall_elapsed_s'] >= stability_start - node.started_wall)
        if not result['px4_telemetry_stability_passed'] or not result['localization_tracking_stability_passed']:
            raise TimeoutError('localization_or_px4_freshness_not_stable_before_enable')

        enabled = call_enable(node, True)
        result['service_calls'].append({'enable': True, **enabled})
        if not enabled['accepted']:
            raise RuntimeError('offboard_enable_rejected:' + enabled['reason'])
        active = spin_until(node, lambda: (
            node.bridge is not None and node.bridge.phase == 'ACTIVE'
            and node.bridge.armed and not node.bridge.landed
            and localization_tracking_fresh(node, result['localization_epoch'])
        ), args.flight_timeout_s, abort_predicate=lambda: not localization_tracking_fresh(
            node, result['localization_epoch']))
        result['takeoff_active_observed'] = active
        if not active and not localization_tracking_fresh(node, result['localization_epoch']):
            raise RuntimeError('localization_lost_during_takeoff')
        if not active:
            raise TimeoutError('bridge_did_not_reach_active_after_takeoff')

        for subscription in list(node.subscriptions):
            if subscription.topic_name == '/grid_map/occupancy':
                node.destroy_subscription(subscription)
        result['diagnostic_scope'] = 'No duplicate raw/ego image readers; occupancy reader stopped after takeoff. Native localization/mapping/navigation gates unchanged.'

        pose = node.odometry.pose.pose
        goal = NavigateToPose.Goal()
        goal.target.header.frame_id = f'odom_{node.localization.epoch}'
        goal.target.header.stamp = node.odometry.header.stamp
        goal.target.pose.position.x = float(pose.position.x) + float(goal_config['target_offset_enu_m'][0])
        goal.target.pose.position.y = float(pose.position.y) + float(goal_config['target_offset_enu_m'][1])
        goal.target.pose.position.z = float(pose.position.z) + float(goal_config['target_offset_enu_m'][2])
        yaw = math.atan2(2.0 * (pose.orientation.w * pose.orientation.z
                                + pose.orientation.x * pose.orientation.y),
                         1.0 - 2.0 * (pose.orientation.y ** 2
                                       + pose.orientation.z ** 2))
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
        goal_timeout = goal.timeout_s + 4.0
        finished = spin_until(node, action_future.done, goal_timeout)
        if not finished:
            try:
                cancel_future = handle.cancel_goal_async()
                spin_until(node, cancel_future.done, 2.0)
            except Exception:
                pass
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
            raise RuntimeError('navigation_action_not_successful:' + nav_result.reason)

        matching = [item for item in node.position_commands
                    if item['goal_id'] == result['goal_id']
                    and item['epoch'] == result['localization_epoch']
                    and item['flag'] == PositionCommand.TRAJECTORY_STATUS_READY]
        result['matching_ready_trajectory_samples'] = len(matching)
        if not matching:
            raise RuntimeError('no_matching_ego_ready_position_command_observed')
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
        if node.bridge is not None and node.bridge.phase not in ('DISABLED', 'LANDED', 'LOCKED'):
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
        result['counts'] = dict(node.counts)
        result['stream_diagnostics'] = node.streams
        result['localization_quality_history'] = node.localization_quality_history
        result['vins_quality_history'] = node.vins_quality_history
        result['vins_telemetry_topic'] = node.vins_telemetry_topic
        result['local_position_history'] = node.local_position_history
        result['map_point_count_max'] = max(node.map_point_counts, default=0)
        result['position_command_history'] = node.position_commands
        result['px4_trajectory_setpoint_observations'] = node.px4_setpoint_observations
        result['position_command_flag_counts'] = {
            str(flag): count for flag, count in Counter(
                item['flag'] for item in node.position_commands).items()}
        result['bridge_phases'] = node.bridge_phases
        result['latest_bridge_detail'] = node.latest_bridge_detail
        result['bridge_detail_history'] = node.bridge_detail_history
        result['timesync_history'] = node.timesync_history
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
        Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n',
                                     encoding='utf-8')
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    print(json.dumps(result, indent=2, sort_keys=True))
    if result['result'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
