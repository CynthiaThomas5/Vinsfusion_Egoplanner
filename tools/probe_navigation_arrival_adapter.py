#!/usr/bin/env python3
"""Verify ROS action success from fresh, matching-epoch odometry samples."""

import json
import math
import threading
import time
import uuid
from pathlib import Path

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rosgraph_msgs.msg import Clock
from uav_interfaces.action import NavigateToPose
from uav_interfaces.msg import LocalizationStatus, NavigationCommand, TrajectoryCancel
from uav_navigation.node import NavigationNode


def wait_for(predicate, description, timeout_s=5.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise RuntimeError(f'timed out waiting for {description}')


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--project-root', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()

    rclpy.init()
    root = rclpy.parameter.Parameter(
        'project_root', rclpy.parameter.Parameter.Type.STRING, args.project_root)
    use_sim_time = rclpy.parameter.Parameter(
        'use_sim_time', rclpy.parameter.Parameter.Type.BOOL, True)
    navigation = NavigationNode(parameter_overrides=[root, use_sim_time])
    peer = Node('navigation_arrival_adapter_probe')
    epoch = uuid.uuid4().hex
    status_qos = QoSProfile(
        depth=1,
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.TRANSIENT_LOCAL,
    )
    status_pub = peer.create_publisher(
        LocalizationStatus, '/localization/status', status_qos)
    odom_pub = peer.create_publisher(Odometry, '/localization/optimized_imu_odom', 10)
    clock_pub = peer.create_publisher(Clock, '/clock', 10)
    commands = []
    cancels = []
    peer.create_subscription(NavigationCommand, '/navigation/ego_goal',
                             commands.append, 10)
    peer.create_subscription(TrajectoryCancel, '/navigation/trajectory_cancel',
                             cancels.append, 10)
    action_client = ActionClient(peer, NavigateToPose,
                                 '/navigation/navigate_to_pose')
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(navigation)
    executor.add_node(peer)
    spin_thread = threading.Thread(target=executor.spin, daemon=True)

    target = (1.0, -0.2, 0.8)
    target_yaw = 0.6
    clock_ns = 0

    def publish_state(position=(0.0, 0.0, 0.0), yaw=0.0):
        nonlocal clock_ns
        clock_ns += 50_000_000
        status = LocalizationStatus()
        status.epoch = epoch
        status.state = LocalizationStatus.TRACKING
        status.valid = True
        status.reason = 'tracking'
        status_pub.publish(status)

        odom = Odometry()
        odom.header.frame_id = f'odom_{epoch}'
        odom.header.stamp.sec = clock_ns // 1_000_000_000
        odom.header.stamp.nanosec = clock_ns % 1_000_000_000
        odom.pose.pose.position.x = position[0]
        odom.pose.pose.position.y = position[1]
        odom.pose.pose.position.z = position[2]
        odom.pose.pose.orientation.z = math.sin(yaw / 2.0)
        odom.pose.pose.orientation.w = math.cos(yaw / 2.0)
        odom_pub.publish(odom)

        clock = Clock()
        clock.clock.sec = clock_ns // 1_000_000_000
        clock.clock.nanosec = clock_ns % 1_000_000_000
        clock_pub.publish(clock)

    try:
        spin_thread.start()
        wait_for(lambda: action_client.wait_for_server(timeout_sec=0.0),
                 'navigation action server')
        wait_for(lambda: navigation._ego_goal_pub.get_subscription_count() == 1,
                 'EGO goal observer')
        wait_for(lambda: navigation._trajectory_cancel_pub.get_subscription_count() == 1,
                 'trajectory cancellation observer')

        for _ in range(20):
            publish_state()
            time.sleep(0.03)
        wait_for(lambda: navigation.core.localization_ready,
                 'valid TRACKING localization')

        request = NavigateToPose.Goal()
        request.target = PoseStamped()
        request.target.header.frame_id = f'odom_{epoch}'
        request.target.pose.position.x = target[0]
        request.target.pose.position.y = target[1]
        request.target.pose.position.z = target[2]
        request.target.pose.orientation.z = math.sin(target_yaw / 2.0)
        request.target.pose.orientation.w = math.cos(target_yaw / 2.0)
        request.position_tolerance_m = 0.1
        request.yaw_tolerance_rad = 0.1
        request.dwell_s = 0.25
        request.timeout_s = 6.0

        goal_future = action_client.send_goal_async(request)
        goal_deadline = time.monotonic() + 5.0
        while not goal_future.done() and time.monotonic() < goal_deadline:
            publish_state()
            time.sleep(0.05)
        if not goal_future.done():
            raise RuntimeError('timed out waiting for action goal response')
        goal_handle = goal_future.result()
        if not goal_handle.accepted:
            raise RuntimeError('valid current-epoch goal was rejected')
        result_future = goal_handle.get_result_async()
        wait_for(lambda: len(commands) == 1, 'matching EGO goal command')
        goal_id = uuid.UUID(bytes=bytes(goal_handle.goal_id.uuid)).hex
        command = commands[0]
        if command.goal_id != goal_id or command.epoch != epoch:
            raise RuntimeError('EGO goal command lost the action goal ID or epoch')

        # Position is correct, but yaw remains outside tolerance; this must not succeed.
        wrong_yaw_deadline = time.monotonic() + 0.4
        while time.monotonic() < wrong_yaw_deadline:
            publish_state(target, 0.0)
            time.sleep(0.05)
            if result_future.done():
                raise RuntimeError('goal succeeded while yaw was outside tolerance')

        # Holding the full target pose should complete the configured dwell.
        arrival_deadline = time.monotonic() + 3.0
        while not result_future.done() and time.monotonic() < arrival_deadline:
            publish_state(target, target_yaw)
            time.sleep(0.05)
        if not result_future.done():
            raise RuntimeError('goal did not succeed after holding position and yaw')
        response = result_future.result()
        if response.status != GoalStatus.STATUS_SUCCEEDED:
            raise RuntimeError(f'expected SUCCEEDED, got action status {response.status}')
        if not response.result.success or response.result.reason != 'position_yaw_tolerance_held':
            raise RuntimeError(f'unexpected action result: {response.result}')
        if cancels:
            raise RuntimeError('successful arrival unexpectedly canceled the trajectory')
        if not navigation.wait_for_action_callbacks(timeout_sec=1.0):
            raise RuntimeError('arrival action callback remained active after its result')

        report = {
            'scope': 'Synthetic ROS action adapter test; injected current-epoch odometry, no vehicle controller or PX4',
            'result': 'PASS_ACTION_ARRIVAL_SUCCESS',
            'epoch': epoch,
            'goal_id': goal_id,
            'target_position_odom_m': list(target),
            'target_yaw_rad': target_yaw,
            'position_tolerance_m': request.position_tolerance_m,
            'yaw_tolerance_rad': request.yaw_tolerance_rad,
            'dwell_s': request.dwell_s,
            'yaw_outside_tolerance_blocked_success': True,
            'action_status': 'SUCCEEDED',
            'action_result': {
                'success': bool(response.result.success),
                'reason': response.result.reason,
            },
            'matching_ego_goal_command': True,
            'trajectory_cancel_count': len(cancels),
            'qualification': 'Adapter integration only; does not prove trajectory tracking, closed-loop arrival, obstacle clearance, PX4, or flight acceptance.',
        }
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + '\n')
        print('PASS_ACTION_ARRIVAL_SUCCESS')
    finally:
        executor.shutdown()
        if spin_thread.is_alive():
            spin_thread.join(timeout=2.0)
        action_client.destroy()
        peer.destroy_node()
        navigation.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
