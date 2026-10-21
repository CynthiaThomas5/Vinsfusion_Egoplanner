#!/usr/bin/env python3
"""Exercise trajectory metadata, yaw sampling, and goal-scoped cancellation."""

import os
import signal
import subprocess
import time
import uuid

import rclpy
from geometry_msgs.msg import Point
from rclpy.clock import Clock, ClockType
from rclpy.node import Node
from rclpy.parameter import Parameter
from rosgraph_msgs.msg import Clock as ClockMessage
from traj_utils.msg import Bspline
from uav_interfaces.msg import PositionCommand, TrajectoryCancel


def stamp_ns(stamp):
    return int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)


def wait_for(node, predicate, description, timeout_s=5.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.02)
        if predicate():
            return
    raise RuntimeError(f'timed out waiting for {description}')


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--traj-server', required=True)
    args = parser.parse_args()

    rclpy.init()
    node = Node('trajectory_server_probe', parameter_overrides=[
        Parameter('use_sim_time', value=True)])
    commands = []
    clock_sample = {'ns': 1_000_000_000}
    bspline_pub = node.create_publisher(Bspline, '/planning/bspline', 10)
    cancel_pub = node.create_publisher(TrajectoryCancel, '/navigation/trajectory_cancel', 10)
    node.create_subscription(PositionCommand, '/position_cmd', commands.append, 50)
    clock_pub = node.create_publisher(ClockMessage, '/clock', 10)

    def publish_clock():
        clock_sample['ns'] += 20_000_000
        clock_message = ClockMessage()
        clock_message.clock.sec, clock_message.clock.nanosec = divmod(
            clock_sample['ns'], 1_000_000_000)
        clock_pub.publish(clock_message)

    clock_timer = node.create_timer(
        0.02, publish_clock, clock=Clock(clock_type=ClockType.STEADY_TIME))
    server_command = [args.traj_server, '--ros-args', '-p', 'use_sim_time:=true']
    process = subprocess.Popen(server_command, env=os.environ.copy())
    goal_id = uuid.uuid4().hex
    epoch = uuid.uuid4().hex
    try:
        wait_for(node, lambda: bspline_pub.get_subscription_count() == 1,
                 'traj_server B-spline subscriber')
        spline = Bspline()
        spline.order = 3
        spline.traj_id = 71
        spline.goal_id = goal_id
        spline.epoch = epoch
        spline.start_time = node.get_clock().now().to_msg()
        spline.knots = [0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0]
        for x in (0.0, 1.0, 2.0, 3.0):
            point = Point()
            point.x = x
            spline.pos_pts.append(point)
        spline.yaw_pts = [0.0, 0.1, 0.5, 1.2]
        spline.yaw_dt = 1.0
        bspline_pub.publish(spline)

        wait_for(node, lambda: any(c.trajectory_flag == PositionCommand.TRAJECTORY_STATUS_READY
                                   and c.goal_id == goal_id for c in commands),
                 'epoch-bound trajectory command')
        ready = next(c for c in reversed(commands)
                     if c.trajectory_flag == PositionCommand.TRAJECTORY_STATUS_READY
                     and c.goal_id == goal_id)
        if ready.header.frame_id != f'odom_{epoch}' or ready.epoch != epoch:
            raise RuntimeError('trajectory command did not retain the B-spline epoch frame')
        if abs(stamp_ns(ready.header.stamp) - clock_sample['ns']) > 100_000_000:
            raise RuntimeError('READY command header stamp is not on the simulated ROS clock')
        wait_for(node, lambda: any(c.goal_id == goal_id and c.yaw > 0.7
                                   for c in commands),
                 'requested terminal yaw')

        stale = TrajectoryCancel()
        stale.goal_id = uuid.uuid4().hex
        stale.epoch = epoch
        stale.mode = TrajectoryCancel.MODE_ABORT
        stale.reason = 'stale_probe'
        cancel_pub.publish(stale)
        before_stale_check = len(commands)
        wait_for(node, lambda: any(c.goal_id == goal_id and
                                   c.trajectory_flag == PositionCommand.TRAJECTORY_STATUS_READY
                                   for c in commands[before_stale_check:]),
                 'active trajectory after stale cancellation')

        matching = TrajectoryCancel()
        matching.goal_id = goal_id
        matching.epoch = epoch
        matching.mode = TrajectoryCancel.MODE_ABORT
        matching.reason = 'test_cancel'
        cancel_pub.publish(matching)
        wait_for(node, lambda: any(c.goal_id == goal_id and c.epoch == epoch and
                                   c.trajectory_flag == PositionCommand.TRAJECTORY_STATUS_ABORT
                                   for c in commands),
                 'matching trajectory abort command')
        abort_index = max(i for i, c in enumerate(commands)
                          if c.goal_id == goal_id and
                          c.trajectory_flag == PositionCommand.TRAJECTORY_STATUS_ABORT)
        time.sleep(0.15)
        rclpy.spin_once(node, timeout_sec=0.0)
        if any(c.goal_id == goal_id and
               c.trajectory_flag == PositionCommand.TRAJECTORY_STATUS_READY
               for c in commands[abort_index + 1:]):
            raise RuntimeError('traj_server resumed publishing the canceled trajectory')
        if commands[abort_index].header.frame_id != f'odom_{epoch}':
            raise RuntimeError('abort command lost its trajectory coordinate frame')
        if abs(stamp_ns(commands[abort_index].header.stamp) - clock_sample['ns']) > 100_000_000:
            raise RuntimeError('ABORT command header stamp is not on the simulated ROS clock')

        target_samples = [c.yaw for c in commands
                          if c.goal_id == goal_id and
                          c.trajectory_flag == PositionCommand.TRAJECTORY_STATUS_READY]
        if max(target_samples) < 0.7:
            raise RuntimeError(f'provided yaw spline was not sampled: max yaw={max(target_samples)}')
        print('PASS: trajectory frame, yaw spline, stale-cancel rejection, and matched abort')
    finally:
        process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=3.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3.0)
        exit_code = process.returncode
        clock_timer.cancel()
        node.destroy_node()
        rclpy.shutdown()
        if exit_code != 0:
            raise RuntimeError(f'traj_server exited with status {exit_code}')


if __name__ == '__main__':
    main()
