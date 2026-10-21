#!/usr/bin/env python3
"""Run one service-gated debug-truth EGO goal, then land through the PX4 bridge."""

import argparse
from collections import Counter
import json
import math
from pathlib import Path
import time

import rclpy
from nav_msgs.msg import Odometry
from px4_msgs.msg import (OffboardControlMode, TrajectorySetpoint,
                          VehicleCommand, VehicleLocalPosition,
                          VehicleOdometry, VehicleStatus)
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import PointCloud2
from uav_interfaces.action import NavigateToPose
from uav_interfaces.msg import LocalizationStatus, PositionCommand, Px4BridgeStatus
from uav_interfaces.srv import EnableOffboard


class EgoFlightProbe(Node):
    def __init__(self):
        super().__init__('px4_debug_ego_flight_probe')
        sensor_qos = QoSProfile(depth=20, reliability=ReliabilityPolicy.BEST_EFFORT)
        reliable_qos = QoSProfile(depth=20, reliability=ReliabilityPolicy.RELIABLE)
        status_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE)
        self.localization = None
        self.odometry = None
        self.bridge = None
        self.map_point_counts = []
        self.position_commands = []
        self.bridge_phases = []
        self.counts = Counter()
        self.create_subscription(LocalizationStatus, '/debug_truth/localization_status',
                                 self._on_localization, status_qos)
        self.create_subscription(Odometry, '/debug_truth/optimized_imu_odom',
                                 self._on_odometry, sensor_qos)
        self.create_subscription(Px4BridgeStatus, '/uav_px4_bridge/status',
                                 self._on_bridge, status_qos)
        self.create_subscription(PointCloud2, '/grid_map/occupancy',
                                 self._on_map, sensor_qos)
        self.create_subscription(PositionCommand, '/position_cmd',
                                 self._on_position_command, reliable_qos)
        self.create_subscription(VehicleOdometry, '/fmu/in/vehicle_visual_odometry',
                                 lambda _: self._count('visual_odometry_input'), sensor_qos)
        self.create_subscription(OffboardControlMode, '/fmu/in/offboard_control_mode',
                                 lambda _: self._count('control_mode'), sensor_qos)
        self.create_subscription(TrajectorySetpoint, '/fmu/in/trajectory_setpoint',
                                 lambda _: self._count('trajectory_setpoint'), sensor_qos)
        self.create_subscription(VehicleCommand, '/fmu/in/vehicle_command',
                                 lambda _: self._count('vehicle_command'), sensor_qos)
        self.create_subscription(VehicleStatus, '/fmu/out/vehicle_status_v1',
                                 self._on_vehicle_status, sensor_qos)
        self.create_subscription(VehicleLocalPosition, '/fmu/out/vehicle_local_position_v1',
                                 lambda _: self._count('local_position'), sensor_qos)
        self.enable_client = self.create_client(
            EnableOffboard, '/uav_px4_bridge/enable_offboard')
        self.action_client = ActionClient(self, NavigateToPose,
                                          '/navigation/navigate_to_pose')
        self.vehicle_status = None
        self.latest_position_command = None

    def _count(self, key):
        self.counts[key] += 1

    def _on_localization(self, msg):
        self.localization = msg
        self._count('localization_status')

    def _on_odometry(self, msg):
        self.odometry = msg
        self._count('debug_truth_odometry')

    def _on_bridge(self, msg):
        self.bridge = msg
        phase = (msg.phase, msg.reason, bool(msg.armed), bool(msg.landed))
        if not self.bridge_phases or self.bridge_phases[-1] != phase:
            self.bridge_phases.append(phase)

    def _on_map(self, msg):
        points = int(msg.width) * int(msg.height)
        self.map_point_counts.append(points)
        self._count('occupancy_cloud')

    def _on_position_command(self, msg):
        self.latest_position_command = msg
        self.position_commands.append({
            'goal_id': msg.goal_id, 'epoch': msg.epoch,
            'trajectory_id': int(msg.trajectory_id),
            'flag': int(msg.trajectory_flag),
            'position_enu': [float(msg.position.x), float(msg.position.y),
                             float(msg.position.z)],
            'yaw_enu': float(msg.yaw),
        })
        self._count('position_command')

    def _on_vehicle_status(self, msg):
        self.vehicle_status = {
            'arming_state': int(msg.arming_state), 'nav_state': int(msg.nav_state),
            'pre_flight_checks_pass': bool(msg.pre_flight_checks_pass),
            'failsafe': bool(msg.failsafe),
        }
        self._count('px4_status')

    def publisher_counts(self):
        topics = ('/fmu/in/vehicle_visual_odometry',
                  '/fmu/in/offboard_control_mode',
                  '/fmu/in/trajectory_setpoint',
                  '/fmu/in/vehicle_command', '/position_cmd',
                  '/navigation/ego_goal', '/navigation/trajectory_cancel')
        return {topic: len(self.get_publishers_info_by_topic(topic)) for topic in topics}


def spin_until(node, predicate, timeout_s):
    deadline = time.monotonic() + timeout_s
    while rclpy.ok() and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.05)
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-root', default='.')
    parser.add_argument('--goal-config', default='config/components/navigation/debug_truth_smoke_goal.json')
    parser.add_argument('--output', required=True)
    parser.add_argument('--precondition-timeout-s', type=float, default=25.0)
    parser.add_argument('--flight-timeout-s', type=float, default=45.0)
    parser.add_argument('--landing-timeout-s', type=float, default=25.0)
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    goal_config = json.loads((root / args.goal_config).read_text())
    result = {'profile': 'debug_truth', 'result': 'FAIL', 'service_calls': [],
              'action_goal_sent': False, 'action_success': False}

    rclpy.init()
    node = EgoFlightProbe()
    try:
        if not node.action_client.wait_for_server(timeout_sec=8.0):
            raise TimeoutError('navigation_action_server_unavailable')
        ready = spin_until(node, lambda: (
            node.localization is not None
            and node.localization.valid
            and node.localization.state == LocalizationStatus.TRACKING
            and node.odometry is not None
            and node.bridge is not None
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
            raise TimeoutError('truth_bridge_map_preconditions_not_ready')
        if node.odometry.header.frame_id != f'odom_{node.localization.epoch}':
            raise RuntimeError('debug_truth_epoch_frame_mismatch')

        enabled = call_enable(node, True)
        result['service_calls'].append({'enable': True, **enabled})
        if not enabled['accepted']:
            raise RuntimeError('offboard_enable_rejected:' + enabled['reason'])
        active = spin_until(node, lambda: (
            node.bridge is not None and node.bridge.phase == 'ACTIVE'
            and node.bridge.armed and not node.bridge.landed
        ), args.flight_timeout_s)
        result['takeoff_active_observed'] = active
        if not active:
            raise TimeoutError('bridge_did_not_reach_active_after_takeoff')

        pose = node.odometry.pose.pose
        goal = NavigateToPose.Goal()
        goal.target.header.frame_id = f'odom_{node.localization.epoch}'
        goal.target.header.stamp = node.get_clock().now().to_msg()
        goal.target.pose.position.x = float(pose.position.x) + float(goal_config['target_offset_enu_m'][0])
        goal.target.pose.position.y = float(pose.position.y) + float(goal_config['target_offset_enu_m'][1])
        goal.target.pose.position.z = float(pose.position.z) + float(goal_config['target_offset_enu_m'][2])
        yaw = math.atan2(2.0 * (pose.orientation.w * pose.orientation.z
                                + pose.orientation.x * pose.orientation.y),
                         1.0 - 2.0 * (pose.orientation.y ** 2
                                       + pose.orientation.z ** 2))
        goal.target.pose.orientation.z = math.sin(yaw / 2.0)
        goal.target.pose.orientation.w = math.cos(yaw / 2.0)
        goal.position_tolerance_m = float(goal_config['position_tolerance_m'])
        goal.yaw_tolerance_rad = float(goal_config['yaw_tolerance_rad'])
        goal.dwell_s = float(goal_config['dwell_s'])
        goal.timeout_s = float(goal_config['timeout_s'])
        result['goal'] = {
            'frame': goal.target.header.frame_id,
            'target_enu': [goal.target.pose.position.x, goal.target.pose.position.y,
                           goal.target.pose.position.z],
            'yaw_enu': yaw,
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
        if node.bridge is not None and node.bridge.armed and node.bridge.phase not in (
                'LANDING', 'LANDED', 'LOCKED'):
            try:
                disabled = call_enable(node, False)
                result['service_calls'].append({'enable': False, **disabled})
                result['landed_and_disarmed'] = spin_until(node, lambda: (
                    node.bridge is not None and node.bridge.phase == 'LANDED'
                    and node.bridge.landed and not node.bridge.armed
                ), args.landing_timeout_s)
            except Exception as land_exc:
                result['landing_error'] = str(land_exc)
    finally:
        result['counts'] = dict(node.counts)
        result['map_point_count_max'] = max(node.map_point_counts, default=0)
        result['position_command_flag_counts'] = {
            str(flag): count for flag, count in Counter(
                item['flag'] for item in node.position_commands).items()}
        result['bridge_phases'] = node.bridge_phases
        result['latest_bridge_status'] = ({
            'phase': node.bridge.phase, 'reason': node.bridge.reason,
            'armed': bool(node.bridge.armed), 'landed': bool(node.bridge.landed),
            'ready': bool(node.bridge.ready),
        } if node.bridge is not None else None)
        result['latest_vehicle_status'] = node.vehicle_status
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
