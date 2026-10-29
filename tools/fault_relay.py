#!/usr/bin/env python3
"""Replay-only sensor fault relay; it never publishes truth or control data."""
import argparse
import json
from pathlib import Path
import sys
import time

import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image, Imu


def should_drop_source(stamp_ns, origin_ns, start_s, duration_s):
    """Schedule a drop against message time so bag playback speed cannot shift it."""
    elapsed_ns = stamp_ns - origin_ns
    start_ns = round(start_s * 1_000_000_000)
    end_ns = start_ns + round(duration_s * 1_000_000_000)
    return start_ns <= elapsed_ns < end_ns


def should_drop_after_goal_source(stamp_ns, goal_stamp_ns, start_after_s, duration_s):
    """Schedule an isolated input interruption against the active goal stamp."""
    start_ns = goal_stamp_ns + round(start_after_s * 1_000_000_000)
    end_ns = start_ns + round(duration_s * 1_000_000_000)
    return start_ns <= stamp_ns < end_ns


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
        self.last_checkpoint_wall = 0.0
        self.report = {
            'scope': 'Explicit sensor-fault relay with source-stamp scheduled drop window',
            'kind': args.kind,
            'interrupted': False,
            'drop_after_source_s': args.drop_after_source_s,
            'drop_after_goal_s': args.after_goal_s,
            'drop_for_source_s': args.drop_for_source_s,
            'topics': {},
        }
        self.source_origin_ns = None
        self.goal_source_ns = None
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
        self.goal_subscription = None
        if args.after_goal_s is not None:
            from uav_interfaces.msg import NavigationCommand
            self.goal_subscription = self.create_subscription(
                NavigationCommand, '/navigation/ego_goal', self.on_goal, 10)
        self.timer = self.create_timer(0.05, self.on_timer, clock=Clock(clock_type=ClockType.STEADY_TIME))

    def on_goal(self, msg):
        stamp = msg.target.header.stamp.sec * 1_000_000_000 + msg.target.header.stamp.nanosec
        if not msg.goal_id or not msg.epoch or stamp <= 0:
            self.report['invalid_goal_trigger_observations'] = (
                self.report.get('invalid_goal_trigger_observations', 0) + 1)
            return
        if self.goal_source_ns is not None:
            return
        self.goal_source_ns = stamp
        start_ns = stamp + round(self.args.after_goal_s * 1_000_000_000)
        self.report['goal_trigger'] = {
            'goal_id': msg.goal_id,
            'epoch': msg.epoch,
            'map_id': msg.map_id,
            'goal_source_stamp_ns': stamp,
            'drop_window_start_ns': start_ns,
            'drop_window_end_ns': start_ns + round(
                self.args.drop_for_source_s * 1_000_000_000),
        }

    def on_message(self, name, msg):
        stats = self.report['topics'][name]
        stamp = msg.header.stamp.sec*1_000_000_000+msg.header.stamp.nanosec
        if self.source_origin_ns is None:
            self.source_origin_ns = stamp
        stats['received'] += 1
        if stats['first_stamp_ns'] is None:
            stats['first_stamp_ns'] = stamp
        stats['last_stamp_ns'] = stamp
        if self.args.after_goal_s is not None:
            if self.goal_source_ns is None:
                dropped = False
            else:
                dropped = should_drop_after_goal_source(
                    stamp, self.goal_source_ns, self.args.after_goal_s,
                    self.args.drop_for_source_s)
            start_ns = (self.goal_source_ns + round(self.args.after_goal_s * 1e9)
                        if self.goal_source_ns is not None else None)
            end_ns = (start_ns + round(self.args.drop_for_source_s * 1e9)
                      if start_ns is not None else None)
            after_window = end_ns is not None and stamp >= end_ns
        else:
            dropped = should_drop_source(
                stamp, self.source_origin_ns,
                self.args.drop_after_source_s, self.args.drop_for_source_s)
            after_window = stamp-self.source_origin_ns >= round(
                (self.args.drop_after_source_s+self.args.drop_for_source_s)*1_000_000_000)
        if dropped:
            stats['dropped'] += 1
            if stats['drop_first_stamp_ns'] is None:
                stats['drop_first_stamp_ns'] = stamp
            stats['drop_last_stamp_ns'] = stamp
            return
        self.output_publishers[name].publish(msg)
        bucket = 'forwarded_after' if after_window else 'forwarded_before'
        stats[bucket] += 1
        if after_window:
            if stats['forwarded_after_first_stamp_ns'] is None:
                stats['forwarded_after_first_stamp_ns'] = stamp
            stats['forwarded_after_last_stamp_ns'] = stamp

    def on_timer(self):
        elapsed = time.monotonic() - self.started
        if elapsed >= self.args.duration_wall_s:
            self.report['duration_wall_expired'] = True
            self.finalize()
            rclpy.shutdown()
            return
        if elapsed - self.last_checkpoint_wall >= 0.5:
            self.write_report(finalized=False)
            self.last_checkpoint_wall = elapsed

    def update_summary(self, finalized):
        self.report['wall_seconds'] = time.monotonic()-self.started
        self.report['finalized'] = bool(finalized)
        self.report['status'] = 'finalized' if finalized else 'running'
        if self.source_origin_ns is not None:
            self.report['source_origin_ns'] = self.source_origin_ns
        if self.args.after_goal_s is not None:
            self.report['goal_trigger_seen'] = self.goal_source_ns is not None
        elif self.source_origin_ns is not None:
            self.report['drop_window_start_ns'] = self.source_origin_ns + round(
                self.args.drop_after_source_s*1_000_000_000)
            self.report['drop_window_end_ns'] = self.source_origin_ns + round(
                (self.args.drop_after_source_s+self.args.drop_for_source_s)*1_000_000_000)
        self.report['window_observed'] = all(
            row['forwarded_before'] > 0 and row['dropped'] > 0 and row['forwarded_after'] > 0
            for row in self.report['topics'].values())
        self.report['fault_drop_observed'] = any(
            row['dropped'] > 0 for row in self.report['topics'].values())
        self.report['recovery_forward_observed'] = all(
            row['forwarded_after'] > 0 for row in self.report['topics'].values())

    def write_report(self, finalized):
        self.update_summary(finalized)
        self.args.report.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.args.report.with_name(self.args.report.name + '.tmp')
        temporary.write_text(json.dumps(self.report, indent=2)+'\n')
        temporary.replace(self.args.report)

    def finalize(self):
        self.write_report(finalized=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kind', choices=sorted(TOPICS), required=True)
    parser.add_argument('--drop-after-source-s', type=float)
    parser.add_argument('--after-goal-s', type=float)
    parser.add_argument('--drop-for-source-s', type=float, required=True)
    parser.add_argument('--duration-wall-s', type=float, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if ((args.drop_after_source_s is None) == (args.after_goal_s is None)
            or (args.drop_after_source_s is not None and args.drop_after_source_s < 0)
            or (args.after_goal_s is not None and (args.after_goal_s < 0 or args.kind != 'depth'))
            or args.drop_for_source_s <= 0 or args.duration_wall_s <= 0):
        parser.error('choose one non-negative source/goal start, a positive drop duration, and a positive wall duration')
    rclpy.init()
    node = FaultRelay(args)
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        node.report['interrupted'] = True
    finally:
        if rclpy.ok():
            rclpy.shutdown()
        if not node.report.get('duration_wall_expired'):
            node.report['interrupted'] = True
        if isinstance(sys.exc_info()[1], KeyboardInterrupt):
            node.report['interrupted'] = True
        node.finalize()
        node.destroy_node()
    print(json.dumps(node.report, indent=2))


if __name__ == '__main__':
    main()
