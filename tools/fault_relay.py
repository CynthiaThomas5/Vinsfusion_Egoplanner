#!/usr/bin/env python3
"""Replay-only sensor fault relay; it never publishes truth or control data."""
import argparse
import json
from pathlib import Path
import time

import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, Imu


def should_drop_source(stamp_ns, origin_ns, start_s, duration_s):
    """Schedule a drop against message time so bag playback speed cannot shift it."""
    elapsed_ns = stamp_ns - origin_ns
    start_ns = round(start_s * 1_000_000_000)
    end_ns = start_ns + round(duration_s * 1_000_000_000)
    return start_ns <= elapsed_ns < end_ns


TOPICS = {
    'stereo': [
        ('infra1', Image, '/fault/input/infra1/image_rect', '/sensors/d435i/infra1/image_rect'),
        ('infra2', Image, '/fault/input/infra2/image_rect', '/sensors/d435i/infra2/image_rect'),
    ],
    'imu': [('imu', Imu, '/fault/input/imu', '/sensors/d435i/imu')],
    'depth': [('depth', Image, '/fault/input/depth', '/sensors/d435i/depth')],
}


class FaultRelay(Node):
    def __init__(self, args):
        super().__init__('sensor_fault_relay')
        self.args = args
        self.started = time.monotonic()
        self.report = {
            'scope': 'Replay-only relay with a source-stamp scheduled drop window',
            'kind': args.kind,
            'drop_after_source_s': args.drop_after_source_s,
            'drop_for_source_s': args.drop_for_source_s,
            'topics': {},
        }
        self.source_origin_ns = None
        self.output_publishers = {}
        self.input_subscriptions = []
        for name, msg_type, source, output in TOPICS[args.kind]:
            self.report['topics'][name] = {
                'input_topic': source, 'output_topic': output,
                'received': 0, 'forwarded_before': 0, 'dropped': 0,
                'forwarded_after': 0, 'first_stamp_ns': None, 'last_stamp_ns': None,
                'drop_first_stamp_ns': None, 'drop_last_stamp_ns': None,
                'forwarded_after_first_stamp_ns': None, 'forwarded_after_last_stamp_ns': None,
            }
            self.output_publishers[name] = self.create_publisher(msg_type, output, qos_profile_sensor_data)
            self.input_subscriptions.append(self.create_subscription(
                msg_type, source, lambda msg, key=name: self.on_message(key, msg), qos_profile_sensor_data))
        self.timer = self.create_timer(0.05, self.on_timer, clock=Clock(clock_type=ClockType.STEADY_TIME))

    def on_message(self, name, msg):
        stats = self.report['topics'][name]
        stamp = msg.header.stamp.sec*1_000_000_000+msg.header.stamp.nanosec
        if self.source_origin_ns is None:
            self.source_origin_ns = stamp
        stats['received'] += 1
        if stats['first_stamp_ns'] is None:
            stats['first_stamp_ns'] = stamp
        stats['last_stamp_ns'] = stamp
        if should_drop_source(stamp, self.source_origin_ns,
                              self.args.drop_after_source_s, self.args.drop_for_source_s):
            stats['dropped'] += 1
            if stats['drop_first_stamp_ns'] is None:
                stats['drop_first_stamp_ns'] = stamp
            stats['drop_last_stamp_ns'] = stamp
            return
        self.output_publishers[name].publish(msg)
        after_window = stamp-self.source_origin_ns >= round(
            (self.args.drop_after_source_s+self.args.drop_for_source_s)*1_000_000_000)
        bucket = 'forwarded_after' if after_window else 'forwarded_before'
        stats[bucket] += 1
        if after_window:
            if stats['forwarded_after_first_stamp_ns'] is None:
                stats['forwarded_after_first_stamp_ns'] = stamp
            stats['forwarded_after_last_stamp_ns'] = stamp

    def on_timer(self):
        if time.monotonic()-self.started >= self.args.duration_wall_s:
            self.report['wall_seconds'] = time.monotonic()-self.started
            if self.source_origin_ns is not None:
                self.report['source_origin_ns'] = self.source_origin_ns
                self.report['drop_window_start_ns'] = self.source_origin_ns + round(
                    self.args.drop_after_source_s*1_000_000_000)
                self.report['drop_window_end_ns'] = self.source_origin_ns + round(
                    (self.args.drop_after_source_s+self.args.drop_for_source_s)*1_000_000_000)
            self.report['window_observed'] = all(
                row['forwarded_before'] > 0 and row['dropped'] > 0 and row['forwarded_after'] > 0
                for row in self.report['topics'].values())
            rclpy.shutdown()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kind', choices=sorted(TOPICS), required=True)
    parser.add_argument('--drop-after-source-s', type=float, required=True)
    parser.add_argument('--drop-for-source-s', type=float, required=True)
    parser.add_argument('--duration-wall-s', type=float, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.drop_after_source_s < 0 or args.drop_for_source_s <= 0 or args.duration_wall_s <= 0:
        parser.error('source drop window and relay wall duration must be positive')
    rclpy.init()
    node = FaultRelay(args)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.report['interrupted'] = True
    finally:
        if rclpy.ok():
            rclpy.shutdown()
        node.destroy_node()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(node.report, indent=2)+'\n')
    print(json.dumps(node.report, indent=2))


if __name__ == '__main__':
    main()
