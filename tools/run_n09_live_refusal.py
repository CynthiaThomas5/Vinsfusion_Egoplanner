#!/usr/bin/env python3
"""Verify a live out-of-map waypoint aborts before EGO/PX4 actuation."""
import json
from pathlib import Path
import sys
import time
import uuid

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import (DurabilityPolicy, QoSProfile, ReliabilityPolicy,
                       qos_profile_sensor_data)
from action_msgs.msg import GoalStatus
from nav_msgs.msg import Odometry
from uav_interfaces.action import NavigateToPose
from uav_interfaces.msg import LocalizationStatus, MapStatus, NavigationCommand, Px4BridgeStatus


class RefusalProbe(Node):
    def __init__(self):
        super().__init__('n09_live_refusal_probe')
        status_qos = QoSProfile(depth=10,
                                reliability=ReliabilityPolicy.RELIABLE,
                                durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.localization = None
        self.odom = None
        self.map_status = None
        self.bridge = None
        self.receipts = {}
        self.forwarded = []
        self.create_subscription(LocalizationStatus, '/localization/status',
                                 lambda msg: self._receive('localization', msg), status_qos)
        self.create_subscription(Odometry, '/localization/optimized_imu_odom',
                                 lambda msg: self._receive('odom', msg),
                                 qos_profile_sensor_data)
        self.create_subscription(MapStatus, '/mapping/status',
                                 lambda msg: self._receive('map', msg), status_qos)
        self.create_subscription(Px4BridgeStatus, '/uav_px4_bridge/status',
                                 lambda msg: self._receive('bridge', msg), 10)
        self.create_subscription(NavigationCommand, '/navigation/ego_goal',
                                 lambda msg: self.forwarded.append({
                                     'goal_id': msg.goal_id, 'epoch': msg.epoch,
                                     'map_id': msg.map_id}), 10)
        self.client = ActionClient(self, NavigateToPose,
                                   '/navigation/navigate_to_pose')

    def _receive(self, key, message):
        setattr(self, {'localization': 'localization', 'odom': 'odom',
                       'map': 'map_status', 'bridge': 'bridge'}[key], message)
        self.receipts[key] = time.monotonic()

    def pump_until(self, predicate, timeout_s, message):
        deadline = time.monotonic() + timeout_s
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.05)
            if predicate():
                return
        raise TimeoutError(message)


def stamp_ns(stamp):
    return int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)


def run(output):
    output = Path(output).resolve()
    result = {'schema': 'n09-live-refusal/v1', 'passed': False,
              'expected_reason': 'map_query_outside_map',
              'control_was_never_enabled_by_probe': True}
    rclpy.init()
    node = RefusalProbe()
    try:
        node.pump_until(lambda: (
            node.localization is not None and node.localization.valid
            and node.localization.state == LocalizationStatus.TRACKING
            and node.odom is not None and node.map_status is not None
            and node.bridge is not None), 20.0,
            'timed_out_waiting_for_live_localization_map_bridge_state')
        localization = node.localization
        odometry = node.odom
        map_status = node.map_status
        bridge = node.bridge
        epoch = localization.epoch
        if (not epoch or odometry.header.frame_id != f'odom_{epoch}'
                or map_status.epoch != epoch or not map_status.map_id
                or not map_status.input_ready or not map_status.reset_acknowledged):
            raise RuntimeError('live_refusal_probe_identity_or_map_not_ready')
        receipt_ages = {key: time.monotonic() - node.receipts[key]
                        for key in ('localization', 'odom', 'map', 'bridge')}
        result['receipt_ages_before_s'] = receipt_ages
        if max(receipt_ages.values()) > 0.5:
            raise RuntimeError('live_refusal_probe_inputs_stale')
        if bridge.phase not in ('DISABLED', 'LANDED') or bridge.armed or not bridge.landed:
            raise RuntimeError('live_refusal_probe_requires_disarmed_landed_bridge')
        result.update({'epoch': epoch, 'map_id': map_status.map_id,
                       'bridge_phase_before': bridge.phase,
                       'bridge_armed_before': bool(bridge.armed),
                       'bridge_landed_before': bool(bridge.landed)})
        if not node.client.wait_for_server(timeout_sec=8.0):
            raise TimeoutError('navigation_action_server_unavailable')
        goal = NavigateToPose.Goal()
        goal.target.header.frame_id = f'odom_{epoch}'
        goal.target.header.stamp = odometry.header.stamp
        goal.target.pose.position.x = float(odometry.pose.pose.position.x) + 50.0
        goal.target.pose.position.y = float(odometry.pose.pose.position.y)
        goal.target.pose.position.z = float(odometry.pose.pose.position.z) + 0.5
        goal.target.pose.orientation.x = odometry.pose.pose.orientation.x
        goal.target.pose.orientation.y = odometry.pose.pose.orientation.y
        goal.target.pose.orientation.z = odometry.pose.pose.orientation.z
        goal.target.pose.orientation.w = odometry.pose.pose.orientation.w
        goal.position_tolerance_m = 0.05
        goal.yaw_tolerance_rad = 0.1
        goal.dwell_s = 1.0
        goal.timeout_s = 10.0
        result['target_odom'] = [goal.target.pose.position.x,
                                 goal.target.pose.position.y,
                                 goal.target.pose.position.z]
        response = node.client.send_goal_async(goal)
        node.pump_until(response.done, 6.0, 'out_of_map_goal_response_timeout')
        handle = response.result()
        result['goal_request_accepted_for_service_check'] = bool(handle and handle.accepted)
        if handle is None or not handle.accepted:
            raise RuntimeError('out_of_map_goal_rejected_before_query; live map refusal unobserved')
        result['goal_id'] = uuid.UUID(bytes=bytes(handle.goal_id.uuid)).hex
        future = handle.get_result_async()
        node.pump_until(future.done, 8.0, 'out_of_map_action_result_timeout')
        wrapped = future.result()
        result['action_status'] = int(wrapped.status)
        result['outcome'] = wrapped.result.outcome
        result['reason'] = wrapped.result.reason
        result['success'] = bool(wrapped.result.success)
        hold_until = time.monotonic() + 0.3
        while time.monotonic() < hold_until:
            rclpy.spin_once(node, timeout_sec=0.05)
        bridge_after = node.bridge
        result['matching_ego_commands'] = [item for item in node.forwarded
                                           if item['goal_id'] == result['goal_id']]
        result['epoch_unchanged'] = (
            node.localization.epoch == epoch and node.map_status.epoch == epoch
            and node.map_status.map_id == map_status.map_id)
        result['bridge_after'] = {
            'phase': bridge_after.phase, 'armed': bool(bridge_after.armed),
            'landed': bool(bridge_after.landed),
            'control_enabled': bool(bridge_after.control_enabled),
        }
        result['passed'] = bool(
            wrapped.status == GoalStatus.STATUS_ABORTED
            and wrapped.result.outcome == 'rejected'
            and wrapped.result.reason == 'map_query_outside_map'
            and not wrapped.result.success
            and not result['matching_ego_commands']
            and result['epoch_unchanged']
            and bridge_after.phase == result['bridge_phase_before']
            and not bridge_after.armed and bridge_after.landed
            and not bridge_after.control_enabled)
    except Exception as exc:
        result['failure'] = f'{type(exc).__name__}: {exc}'
    finally:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + '\n')
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: run_n09_live_refusal.py REPORT.json')
    if not run(sys.argv[1])['passed']:
        raise SystemExit(1)
