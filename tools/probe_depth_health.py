#!/usr/bin/env python3
"""Record only state/reason transitions from the depth health monitor."""
import argparse
import json
from pathlib import Path
import time

import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from uav_interfaces.msg import DepthHealth


class Probe(Node):
    def __init__(self, report, duration):
        super().__init__('depth_health_probe')
        self.report = {'duration_wall_s': duration, 'transitions': [], 'samples': 0}
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE,
                         durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.subscription = self.create_subscription(DepthHealth, '/mapping/depth_health', self.on_status, qos)
        self.report_path = report
        self.started = time.monotonic()
        self.timer = self.create_timer(0.05, self.on_timer, clock=Clock(clock_type=ClockType.STEADY_TIME))

    def on_status(self, msg):
        self.report['samples'] += 1
        state = {DepthHealth.STATE_WAITING: 'WAITING', DepthHealth.STATE_READY: 'READY',
                 DepthHealth.STATE_STALE: 'STALE', DepthHealth.STATE_INVALID: 'INVALID',
                 DepthHealth.STATE_LOCKED: 'LOCKED'}.get(msg.state, str(msg.state))
        value = {'state': state, 'valid': msg.valid, 'reason': msg.reason,
                 'source_stamp_ns': msg.source_stamp.sec*1_000_000_000+msg.source_stamp.nanosec,
                 'received_count': msg.received_count, 'wall_s': time.monotonic()-self.started}
        if not self.report['transitions'] or any(
                self.report['transitions'][-1][key] != value[key] for key in ['state', 'valid', 'reason']):
            self.report['transitions'].append(value)

    def on_timer(self):
        if time.monotonic()-self.started >= self.report['duration_wall_s']:
            rclpy.shutdown()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--duration-wall-s', type=float, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    rclpy.init()
    node = Probe(args.report, args.duration_wall_s)
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(node.report, indent=2)+'\n')
    print(json.dumps(node.report, indent=2))


if __name__ == '__main__':
    main()
