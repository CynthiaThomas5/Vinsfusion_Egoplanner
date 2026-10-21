#!/usr/bin/env python3
"""Read-only bounded probe for one localization adapter replay."""
import argparse
import json
import math
from pathlib import Path
import time

import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.node import Node
from nav_msgs.msg import Odometry
from rclpy.qos import qos_profile_sensor_data
from uav_interfaces.msg import LocalizationStatus


def ns(stamp):
    return stamp.sec*1_000_000_000+stamp.nanosec


class Probe(Node):
    def __init__(self, seconds):
        super().__init__('localization_replay_probe')
        self.started = time.monotonic()
        self.seconds = seconds
        self.report = {
            'scope': 'Read-only adapter observation over real VINS bag replay; no truth topics subscribed',
            'subscriptions': ['/localization/status', '/localization/optimized_imu_odom', '/localization/imu_odom'],
            'status_history': [], 'topics': {}, 'contract_errors': [],
        }
        self.last_status = None
        self.create_subscription(LocalizationStatus, '/localization/status', self.on_status, 10)
        for name, topic in [('optimized', '/localization/optimized_imu_odom'),
                            ('propagated', '/localization/imu_odom')]:
            self.report['topics'][name] = {'topic': topic, 'count': 0, 'frames': [],
                                           'first_stamp_ns': None, 'last_stamp_ns': None,
                                           'strictly_increasing': True, 'all_finite': True}
            self.create_subscription(Odometry, topic, lambda msg, key=name: self.on_odom(key, msg), qos_profile_sensor_data)
        self.timer = self.create_timer(0.1, self.on_timer, clock=Clock(clock_type=ClockType.STEADY_TIME))

    def on_status(self, msg):
        row = {'epoch': msg.epoch, 'state': msg.state, 'valid': msg.valid,
               'reason': msg.reason, 'source_stamp_ns': ns(msg.source_stamp),
               'clock_stamp_ns': ns(msg.header.stamp),
               'wall_elapsed_s': time.monotonic()-self.started,
               'good_pairs': msg.good_pairs, 'normalized_cost': msg.normalized_cost,
               'covariance_valid': msg.covariance_valid,
               'accepted_optimized': msg.accepted_optimized,
               'accepted_propagated': msg.accepted_propagated}
        if row != self.last_status:
            self.report['status_history'].append(row)
            self.last_status = row

    def on_odom(self, name, msg):
        row = self.report['topics'][name]
        stamp = ns(msg.header.stamp)
        if row['first_stamp_ns'] is None:
            row['first_stamp_ns'] = stamp
            row['first_frame'] = msg.header.frame_id
            row['first_child_frame'] = msg.child_frame_id
        if row['last_stamp_ns'] is not None and stamp <= row['last_stamp_ns']:
            row['strictly_increasing'] = False
        row['last_stamp_ns'] = stamp
        row['count'] += 1
        row['frames'] = sorted(set(row['frames'] + [msg.header.frame_id]))
        values = [msg.pose.pose.position.x, msg.pose.pose.position.y, msg.pose.pose.position.z,
                  msg.pose.pose.orientation.x, msg.pose.pose.orientation.y,
                  msg.pose.pose.orientation.z, msg.pose.pose.orientation.w,
                  msg.twist.twist.linear.x, msg.twist.twist.linear.y, msg.twist.twist.linear.z,
                  msg.twist.twist.angular.x, msg.twist.twist.angular.y, msg.twist.twist.angular.z]
        row['all_finite'] &= all(math.isfinite(value) for value in values)

    def on_timer(self):
        if time.monotonic()-self.started >= self.seconds:
            self.report['wall_seconds'] = time.monotonic()-self.started
            rclpy.shutdown()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=float, default=75.0)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.seconds <= 0:
        raise ValueError('--seconds must be positive')
    rclpy.init()
    node = Probe(args.seconds)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.report['interrupted'] = True
    finally:
        if rclpy.ok():
            rclpy.shutdown()
        node.destroy_node()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(node.report, indent=2)+'\n')
    print(json.dumps(node.report, indent=2))


if __name__ == '__main__':
    main()
