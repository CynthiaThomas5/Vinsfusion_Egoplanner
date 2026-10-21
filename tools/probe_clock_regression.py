#!/usr/bin/env python3
"""Read-only verification of localization lock and map clearing after ROS clock rollback."""
import argparse
import json
from pathlib import Path
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import (DurabilityPolicy, QoSProfile, ReliabilityPolicy,
                       qos_profile_sensor_data)
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import Image, PointCloud2
from uav_interfaces.msg import DepthHealth, LocalizationStatus


def stamp_ns(stamp):
    return stamp.sec * 1_000_000_000 + stamp.nanosec


class ClockRegressionProbe(Node):
    def __init__(self):
        super().__init__('clock_regression_probe')
        self.started = time.monotonic()
        self.last_clock_ns = None
        self.clock_backsteps = []
        self.last_localization = None
        self.localization_history = []
        self.depth_health_history = []
        self.depth_outputs = 0
        self.pose_outputs = 0
        self.optimized_odom_outputs = 0
        self.propagated_odom_outputs = 0
        self.map_point_counts = []
        self.lock_wall_elapsed_s = None
        self.output_counts_at_lock = None
        self.settled_output_counts = None
        self.settled_after_wall_elapsed_s = None
        self.empty_map_after_lock = False

        status_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                                durability=DurabilityPolicy.TRANSIENT_LOCAL)
        output_qos = QoSProfile(depth=100, reliability=ReliabilityPolicy.RELIABLE)
        self.create_subscription(Clock, '/clock', self.on_clock, qos_profile_sensor_data)
        self.create_subscription(LocalizationStatus, '/localization/status', self.on_localization,
                                 status_qos)
        self.create_subscription(DepthHealth, '/mapping/depth_health', self.on_depth_health,
                                 status_qos)
        self.create_subscription(Odometry, '/localization/optimized_imu_odom',
                                 self.on_optimized, qos_profile_sensor_data)
        self.create_subscription(Odometry, '/localization/imu_odom',
                                 self.on_propagated, qos_profile_sensor_data)
        self.create_subscription(Image, '/drone_0_depth_image', self.on_depth, output_qos)
        self.create_subscription(PoseStamped, '/drone_0_camera_pose', self.on_pose, output_qos)
        self.create_subscription(PointCloud2, '/grid_map/occupancy', self.on_map, 10)

    def elapsed(self):
        return round(time.monotonic() - self.started, 3)

    def output_counts(self):
        return {
            'ego_depth': self.depth_outputs,
            'ego_pose': self.pose_outputs,
            'optimized_odometry': self.optimized_odom_outputs,
            'propagated_odometry': self.propagated_odom_outputs,
        }

    def on_clock(self, msg):
        current = stamp_ns(msg.clock)
        if self.last_clock_ns is not None and current < self.last_clock_ns:
            self.clock_backsteps.append({
                'wall_elapsed_s': self.elapsed(),
                'previous_stamp_ns': self.last_clock_ns,
                'current_stamp_ns': current,
                'backstep_ns': self.last_clock_ns - current,
            })
        self.last_clock_ns = current

    def on_localization(self, msg):
        current = (msg.epoch, msg.state, msg.valid, msg.reason)
        if current != self.last_localization:
            self.localization_history.append({
                'wall_elapsed_s': self.elapsed(),
                'epoch': msg.epoch,
                'state': msg.state,
                'valid': msg.valid,
                'reason': msg.reason,
                'accepted_optimized': msg.accepted_optimized,
                'accepted_propagated': msg.accepted_propagated,
            })
            self.last_localization = current
        if msg.reason == 'clock_regression' and self.lock_wall_elapsed_s is None:
            self.lock_wall_elapsed_s = self.elapsed()
            self.output_counts_at_lock = self.output_counts()

    def on_depth_health(self, msg):
        current = (msg.state, msg.valid, msg.reason)
        if not self.depth_health_history or self.depth_health_history[-1]['state_tuple'] != current:
            self.depth_health_history.append({
                'wall_elapsed_s': self.elapsed(),
                'state': msg.state,
                'valid': msg.valid,
                'reason': msg.reason,
                'state_tuple': current,
            })

    def on_optimized(self, _msg):
        self.optimized_odom_outputs += 1

    def on_propagated(self, _msg):
        self.propagated_odom_outputs += 1

    def on_depth(self, _msg):
        self.depth_outputs += 1

    def on_pose(self, _msg):
        self.pose_outputs += 1

    def on_map(self, msg):
        points = msg.width * msg.height
        self.map_point_counts.append({'wall_elapsed_s': self.elapsed(), 'points': points})
        if self.lock_wall_elapsed_s is not None and points == 0:
            self.empty_map_after_lock = True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-wall-s', type=float, default=75.0)
    parser.add_argument('--settle-after-lock-s', type=float, default=1.0)
    parser.add_argument('--observe-after-settle-s', type=float, default=3.0)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if min(args.max_wall_s, args.settle_after_lock_s, args.observe_after_settle_s) <= 0:
        parser.error('wall durations must be positive')
    rclpy.init()
    node = ClockRegressionProbe()
    try:
        deadline = node.started + args.max_wall_s
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.05)
            if node.lock_wall_elapsed_s is not None:
                lock_elapsed = node.lock_wall_elapsed_s
                if (node.settled_output_counts is None
                        and node.elapsed() >= lock_elapsed + args.settle_after_lock_s):
                    node.settled_output_counts = node.output_counts()
                    node.settled_after_wall_elapsed_s = node.elapsed()
                if (node.settled_after_wall_elapsed_s is not None
                        and node.elapsed() >= node.settled_after_wall_elapsed_s + args.observe_after_settle_s):
                    break
    finally:
        result = {
            'scope': 'Read-only observation of live Gazebo D435i, VINS, localization, depth health, mapping adapter, and EGO plan_env during one synthetic ROS clock rollback',
            'wall_seconds': node.elapsed(),
            'clock_backsteps': node.clock_backsteps,
            'localization_history': node.localization_history,
            'depth_health_history': [
                {k: v for k, v in row.items() if k != 'state_tuple'}
                for row in node.depth_health_history
            ],
            'map_point_counts': node.map_point_counts,
            'localization_tracking_observed': any(row['valid'] for row in node.localization_history),
            'occupied_map_observed_before_lock': any(
                row['points'] > 0 and (node.lock_wall_elapsed_s is None or row['wall_elapsed_s'] < node.lock_wall_elapsed_s)
                for row in node.map_point_counts
            ),
            'clock_regression_lock_observed': any(
                row['reason'] == 'clock_regression'
                and row['state'] in (LocalizationStatus.LOST, LocalizationStatus.LOCKED)
                for row in node.localization_history
            ),
            'empty_map_after_lock': node.empty_map_after_lock,
            'lock_wall_elapsed_s': node.lock_wall_elapsed_s,
            'output_counts_at_lock': node.output_counts_at_lock,
            'output_counts_at_settle': node.settled_output_counts,
            'localization_outputs_observed_before_lock': (
                node.output_counts_at_lock is not None
                and node.output_counts_at_lock['optimized_odometry'] > 0
                and node.output_counts_at_lock['propagated_odometry'] > 0
            ),
            'final_output_counts': node.output_counts(),
            'outputs_stable_after_settle': (
                node.settled_output_counts is not None
                and node.settled_output_counts == node.output_counts()
            ),
            'qualification': 'single synthetic clock-regression run; not repeated fault-injection acceptance or flight qualification',
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    if (not result['localization_tracking_observed']
            or not result['occupied_map_observed_before_lock']
            or not node.clock_backsteps
            or not result['clock_regression_lock_observed']
            or not result['localization_outputs_observed_before_lock']
            or not result['empty_map_after_lock']
            or not result['outputs_stable_after_settle']):
        raise SystemExit('Clock regression did not lock localization, clear the map, and stop outputs')


if __name__ == '__main__':
    main()
