#!/usr/bin/env python3
"""Relay Gazebo ROS clock and inject one bounded backward jump after mapping is active."""
import argparse
import json
from pathlib import Path
import time

import rclpy
from rclpy.clock import Clock as RosClock, ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import (DurabilityPolicy, QoSProfile, ReliabilityPolicy,
                       qos_profile_sensor_data)
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import PointCloud2
from uav_interfaces.msg import LocalizationStatus


def to_ns(stamp):
    return stamp.sec * 1_000_000_000 + stamp.nanosec


def from_ns(stamp_ns):
    stamp = Clock().clock
    stamp.sec, stamp.nanosec = divmod(stamp_ns, 1_000_000_000)
    return stamp


class ClockRegressionRelay(Node):
    def __init__(self, args):
        super().__init__('clock_regression_relay')
        self.args = args
        status_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                                durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.publisher = self.create_publisher(Clock, '/clock', qos_profile_sensor_data)
        self.create_subscription(Clock, '/fault/input/clock', self.on_source_clock,
                                 qos_profile_sensor_data)
        self.create_subscription(LocalizationStatus, '/localization/status', self.on_status,
                                 status_qos)
        self.create_subscription(PointCloud2, '/grid_map/occupancy', self.on_map, 10)
        self.timer = self.create_timer(0.1, self.on_timer,
                                       clock=RosClock(clock_type=ClockType.STEADY_TIME))
        self.started = time.monotonic()
        self.tracking = False
        self.occupied_points = 0
        self.last_source_ns = None
        self.injected = False
        self.report = {
            'scope': 'One synthetic ROS /clock backward jump after live VINS tracking and nonempty EGO map',
            'source_topic': '/fault/input/clock',
            'output_topic': '/clock',
            'regression_seconds': args.regression_seconds,
            'source_clock_count': 0,
            'clock_regression_injected': False,
            'tracking_observed_before_injection': False,
            'occupied_points_observed_before_injection': 0,
        }

    def on_status(self, msg):
        self.tracking = msg.valid and msg.state == LocalizationStatus.TRACKING

    def on_map(self, msg):
        self.occupied_points = msg.width * msg.height

    def on_source_clock(self, msg):
        source_ns = to_ns(msg.clock)
        self.report['source_clock_count'] += 1
        if self.injected:
            if self.report.get('source_stamp_after_regression_ns') is None:
                self.report['source_stamp_after_regression_ns'] = source_ns
            self.publisher.publish(msg)
            self.last_source_ns = source_ns
            return

        if self.tracking and self.occupied_points > 0 and self.last_source_ns is not None:
            regression_ns = round(self.args.regression_seconds * 1_000_000_000)
            regressed_ns = max(0, min(source_ns, self.last_source_ns) - regression_ns)
            injected = Clock()
            injected.clock = from_ns(regressed_ns)
            self.publisher.publish(injected)
            self.injected = True
            self.report.update({
                'clock_regression_injected': True,
                'tracking_observed_before_injection': self.tracking,
                'occupied_points_observed_before_injection': self.occupied_points,
                'trigger_wall_elapsed_s': round(time.monotonic() - self.started, 3),
                'source_stamp_before_regression_ns': source_ns,
                'regressed_stamp_ns': regressed_ns,
                'regression_magnitude_ns': min(source_ns, self.last_source_ns) - regressed_ns,
            })
        else:
            self.publisher.publish(msg)
        self.last_source_ns = source_ns

    def on_timer(self):
        if time.monotonic() - self.started >= self.args.max_wall_s:
            rclpy.shutdown()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-wall-s', type=float, default=90.0)
    parser.add_argument('--regression-seconds', type=float, default=1.0)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    if args.max_wall_s <= 0 or args.regression_seconds <= 0:
        parser.error('max wall duration and regression amount must be positive')
    rclpy.init()
    node = ClockRegressionRelay(args)
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        node.report['interrupted'] = True
    finally:
        node.report['wall_seconds'] = round(time.monotonic() - node.started, 3)
        node.report['tracking_observed_before_injection'] |= node.tracking
        node.report['final_occupied_points'] = node.occupied_points
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(node.report, indent=2) + '\n')
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    print(json.dumps(node.report, indent=2))
    if not node.report['clock_regression_injected']:
        raise SystemExit('Clock regression was not injected after tracking and occupied map were observed')


if __name__ == '__main__':
    main()
