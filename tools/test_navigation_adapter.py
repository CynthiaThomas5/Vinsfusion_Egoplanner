#!/usr/bin/env python3
"""Exercise the ROS action adapter with synthetic localization and EGO peers."""

import threading
import time
import uuid

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


def wait_future(future, description, timeout_s=5.0):
    wait_for(future.done, description, timeout_s)
    return future.result()


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--project-root', required=True)
    args = parser.parse_args()

    rclpy.init()
    root_parameter = rclpy.parameter.Parameter(
        'project_root', rclpy.parameter.Parameter.Type.STRING, args.project_root)
    simulated_time_parameter = rclpy.parameter.Parameter(
        'use_sim_time', rclpy.parameter.Parameter.Type.BOOL, True)
    navigation = NavigationNode(
        parameter_overrides=[root_parameter, simulated_time_parameter])
    peer = Node('navigation_adapter_probe')
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(navigation)
    executor.add_node(peer)

    epoch = uuid.uuid4().hex
    goals = []
    cancels = []
    status_qos = QoSProfile(
        depth=1,
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.TRANSIENT_LOCAL,
    )
    status_pub = peer.create_publisher(
        LocalizationStatus, '/localization/status', status_qos)
    odom_pub = peer.create_publisher(Odometry, '/localization/optimized_imu_odom', 10)
    clock_pub = peer.create_publisher(Clock, '/clock', 10)
    peer.create_subscription(
        NavigationCommand, '/navigation/ego_goal', goals.append, 10)
    peer.create_subscription(
        TrajectoryCancel, '/navigation/trajectory_cancel', cancels.append, 10)
    action_client = ActionClient(peer, NavigateToPose, '/navigation/navigate_to_pose')

    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()
    try:
        wait_for(lambda: action_client.wait_for_server(timeout_sec=0.0),
                 'navigation action server')
        wait_for(lambda: navigation._ego_goal_pub.get_subscription_count() == 1,
                 'fake EGO goal subscriber')
        wait_for(lambda: navigation._trajectory_cancel_pub.get_subscription_count() == 1,
                 'fake EGO cancellation subscriber')

        status = LocalizationStatus()
        status.epoch = epoch
        status.state = LocalizationStatus.TRACKING
        status.valid = True
        status.reason = 'tracking'
        odom = Odometry()
        odom.header.frame_id = f'odom_{epoch}'
        odom.pose.pose.orientation.w = 1.0
        clock = Clock()
        for tick in range(10):
            status_pub.publish(status)
            odom_pub.publish(odom)
            clock.clock.sec = tick
            clock_pub.publish(clock)
            time.sleep(0.02)
        wait_for(lambda: navigation.core.localization_ready
                 and navigation._latest_pose_epoch == epoch,
                 'initial navigation state before blocked-log check')

        warning_entered = threading.Event()
        release_warning = threading.Event()
        original_get_logger = navigation.get_logger
        original_logger = original_get_logger()

        class BlockingWarningLogger:
            def warning(self, message):
                if message.startswith('optimized odometry callback resumed after '):
                    warning_entered.set()
                    release_warning.wait(timeout=3.0)
                else:
                    original_logger.warning(message)

            def __getattr__(self, name):
                return getattr(original_logger, name)

        navigation.get_logger = lambda: BlockingWarningLogger()
        with navigation._lock:
            navigation._latest_pose_received = (
                time.monotonic() - navigation.max_odometry_age_s - 1.0)
        odometry_thread = threading.Thread(
            target=navigation._on_odometry, args=(odom,), daemon=True)
        odometry_thread.start()
        try:
            wait_for(warning_entered.is_set, 'stale-odometry warning entry')
            if not navigation._lock.acquire(timeout=0.5):
                raise RuntimeError('stale-odometry warning held the navigation state lock')
            navigation._lock.release()
        finally:
            release_warning.set()
            odometry_thread.join(timeout=2.0)
            navigation.get_logger = original_get_logger
        if odometry_thread.is_alive():
            raise RuntimeError('stale-odometry callback did not finish after releasing its logger')

        def make_goal(x, frame_epoch=None):
            request = NavigateToPose.Goal()
            request.target = PoseStamped()
            request.target.header.frame_id = f'odom_{frame_epoch or epoch}'
            request.target.pose.position.x = x
            request.target.pose.orientation.w = 1.0
            request.position_tolerance_m = 0.1
            request.yaw_tolerance_rad = 0.1
            request.dwell_s = 0.0
            request.timeout_s = 5.0
            return request

        info_entered = threading.Event()
        release_info = threading.Event()

        class BlockingAcceptedGoalLogger:
            def info(self, message):
                if message.startswith('accepted goal '):
                    info_entered.set()
                    release_info.wait(timeout=3.0)
                else:
                    original_logger.info(message)

            def __getattr__(self, name):
                return getattr(original_logger, name)

        navigation.get_logger = lambda: BlockingAcceptedGoalLogger()
        first_goal_future = action_client.send_goal_async(make_goal(5.0))
        try:
            wait_for(info_entered.is_set, 'accepted-goal info entry')
            if not navigation._lock.acquire(timeout=0.5):
                raise RuntimeError('accepted-goal info held the navigation state lock')
            navigation._lock.release()
        finally:
            release_info.set()
            navigation.get_logger = original_get_logger
        first_handle = wait_future(first_goal_future, 'first goal response')
        if not first_handle.accepted:
            raise RuntimeError('valid TRACKING goal was rejected')
        first_result_future = first_handle.get_result_async()
        wait_for(lambda: len(goals) >= 1, 'first EGO goal command')
        expected_id = uuid.UUID(bytes=bytes(first_handle.goal_id.uuid)).hex
        if goals[-1].goal_id != expected_id or goals[-1].epoch != epoch:
            raise RuntimeError('EGO command did not preserve the action goal UUID and epoch')

        wait_future(first_handle.cancel_goal_async(), 'cancel acknowledgement')
        canceled = wait_future(first_result_future, 'canceled action result')
        if canceled.status != GoalStatus.STATUS_CANCELED:
            raise RuntimeError(f'expected canceled result, got status {canceled.status}')
        wait_for(lambda: len(cancels) >= 1, 'EGO trajectory cancellation')
        if cancels[-1].goal_id != expected_id or cancels[-1].epoch != epoch:
            raise RuntimeError('explicit cancellation lost its goal UUID or epoch')

        stale_epoch = epoch
        epoch = uuid.uuid4().hex
        status.epoch = epoch
        odom.header.frame_id = f'odom_{epoch}'
        for tick in range(10, 13):
            status_pub.publish(status)
            odom_pub.publish(odom)
            clock.clock.sec = tick
            clock_pub.publish(clock)
            time.sleep(0.02)
        wait_for(lambda: navigation.core.epoch == epoch
                 and navigation._latest_pose_epoch == epoch,
                 'new localization epoch')
        stale_handle = wait_future(
            action_client.send_goal_async(make_goal(5.5, stale_epoch)),
            'stale-epoch goal response')
        if stale_handle.accepted:
            raise RuntimeError('goal in the previous VINS epoch was accepted')

        second_handle = wait_future(
            action_client.send_goal_async(make_goal(6.0)), 'second goal response')
        if not second_handle.accepted:
            raise RuntimeError('second valid TRACKING goal was rejected')
        second_result_future = second_handle.get_result_async()
        wait_for(lambda: len(goals) >= 2, 'second EGO goal command')
        clock.clock.sec = 11
        clock.clock.nanosec = 999_999_999
        clock_pub.publish(clock)
        aborted = wait_future(second_result_future, 'clock-regression abort')
        if aborted.status != GoalStatus.STATUS_ABORTED:
            raise RuntimeError(f'expected aborted result after clock rollback, got {aborted.status}')
        if aborted.result.reason != 'clock_regression':
            raise RuntimeError(f'unexpected rollback reason: {aborted.result.reason}')
        wait_for(lambda: len(cancels) >= 2, 'rollback trajectory cancellation')
        if cancels[-1].goal_id != goals[-1].goal_id or cancels[-1].epoch != epoch:
            raise RuntimeError('clock rollback cancellation did not target the active epoch goal')

        epoch = uuid.uuid4().hex
        status.epoch = epoch
        odom.header.frame_id = f'odom_{epoch}'
        for tick in range(12, 15):
            status_pub.publish(status)
            odom_pub.publish(odom)
            clock.clock.sec = tick
            clock_pub.publish(clock)
            time.sleep(0.02)
        wait_for(lambda: navigation.core.epoch == epoch
                 and navigation.core.localization_ready,
                 'recovered epoch before shutdown test')

        stale_handle = wait_future(
            action_client.send_goal_async(make_goal(6.5)),
            'frozen-clock stale-status goal response')
        if not stale_handle.accepted:
            raise RuntimeError('fresh TRACKING goal was rejected before stale-status test')
        stale_result_future = stale_handle.get_result_async()
        wait_for(lambda: len(goals) >= 3, 'frozen-clock EGO goal command')
        keep_pose_stop = threading.Event()

        def keep_pose_fresh():
            while not keep_pose_stop.wait(0.05):
                odom_pub.publish(odom)

        pose_thread = threading.Thread(target=keep_pose_fresh, daemon=True)
        pose_thread.start()
        stale_result = wait_future(
            stale_result_future, 'wall-time stale-status abort while ROS clock is frozen',
            timeout_s=2.0)
        keep_pose_stop.set()
        pose_thread.join(timeout=1.0)
        if (stale_result.status != GoalStatus.STATUS_ABORTED
                or stale_result.result.reason != 'localization_status_stale'):
            raise RuntimeError(
                'frozen ROS clock did not trigger the wall-time localization stale guard')
        wait_for(lambda: len(cancels) >= 3, 'stale-status trajectory cancellation')
        if cancels[-1].goal_id != goals[-1].goal_id or cancels[-1].epoch != epoch:
            raise RuntimeError('stale-status cancellation did not target the active goal and epoch')

        for tick in range(15, 21):
            status_pub.publish(status)
            odom_pub.publish(odom)
            clock.clock.sec = tick
            clock_pub.publish(clock)
            time.sleep(0.02)
        wait_for(lambda: navigation.core.localization_ready
                 and navigation._latest_pose_epoch == epoch,
                 'fresh localization recovery after stale-status test')

        shutdown_handle = wait_future(
            action_client.send_goal_async(make_goal(7.0)),
            'shutdown-path goal response')
        if not shutdown_handle.accepted:
            raise RuntimeError('valid shutdown-path goal was rejected')
        shutdown_result_future = shutdown_handle.get_result_async()
        wait_for(lambda: len(goals) >= 4, 'shutdown-path EGO goal command')
        navigation.request_shutdown()
        shutdown_result = wait_future(
            shutdown_result_future, 'graceful navigation shutdown result')
        if (shutdown_result.status != GoalStatus.STATUS_ABORTED
                or shutdown_result.result.reason != 'navigation_node_shutdown'):
            raise RuntimeError('shutdown did not abort the active action with its shutdown reason')
        wait_for(lambda: len(cancels) >= 4, 'shutdown trajectory cancellation')
        if cancels[-1].goal_id != goals[-1].goal_id or cancels[-1].epoch != epoch:
            raise RuntimeError('shutdown cancellation did not target the active goal and epoch')
        if not navigation.wait_for_action_callbacks(timeout_sec=1.0):
            raise RuntimeError('shutdown action callback did not finish before executor teardown')

        print('PASS: blocked odometry warning and accepted-goal info release the state lock; action routing, cancel, stale-epoch rejection, clock-regression abort, frozen-clock stale guard, and shutdown abort')
    finally:
        executor.shutdown()
        spin_thread.join(timeout=2.0)
        action_client.destroy()
        peer.destroy_node()
        navigation.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
