#!/usr/bin/env python3
"""Wait for fresh VINS/depth/map readiness without publishing commands."""
import argparse
import json
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
from uav_interfaces.msg import DepthHealth, LocalizationStatus, MapStatus


class Readiness(Node):
    def __init__(self):
        super().__init__('n04_readiness_probe',
                         parameter_overrides=[rclpy.parameter.Parameter('use_sim_time', value=True)])
        durable = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                             durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.depth = None
        self.localization = None
        self.mapping = None
        self.create_subscription(DepthHealth, '/mapping/depth_health',
                                 self.on_depth, durable)
        self.create_subscription(LocalizationStatus, '/localization/status',
                                 self.on_localization, durable)
        self.create_subscription(MapStatus, '/mapping/status', self.on_mapping, durable)

    def on_depth(self, msg):
        self.depth = {'valid': bool(msg.valid), 'state': int(msg.state), 'reason': msg.reason,
                      'frame_id': msg.header.frame_id}

    def on_localization(self, msg):
        self.localization = {'epoch': msg.epoch, 'valid': bool(msg.valid),
                             'state': int(msg.state), 'reason': msg.reason,
                             'frame_id': msg.header.frame_id}

    def on_mapping(self, msg):
        self.mapping = {'epoch': msg.epoch, 'map_id': msg.map_id,
                        'input_ready': bool(msg.input_ready),
                        'reset_acknowledged': bool(msg.reset_acknowledged),
                        'reason': msg.reason}

    def snapshot(self):
        return {'depth_health': self.depth, 'localization': self.localization,
                'map_status': self.mapping}

    def ready(self, expected_epoch):
        return bool(
            self.depth and self.depth['valid']
            and self.depth['state'] == DepthHealth.STATE_READY
            and self.localization and self.localization['valid']
            and self.localization['epoch'] == expected_epoch
            and self.mapping and self.mapping['epoch'] == expected_epoch
            and self.mapping['input_ready'] and self.mapping['reset_acknowledged']
            and self.mapping['map_id'].startswith(expected_epoch+'-')
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-epoch', required=True)
    parser.add_argument('--timeout-s', type=float, default=90.0)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if args.timeout_s <= 0:
        raise ValueError('--timeout-s must be positive')
    rclpy.init()
    node = Readiness()
    deadline = time.monotonic()+args.timeout_s
    try:
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
            if node.ready(args.expected_epoch):
                report = {'schema': 'n04-pre-motion-readiness/v1', 'ready': True,
                          'expected_epoch': args.expected_epoch,
                          'sample': node.snapshot(), 'wall_elapsed_s': args.timeout_s-(deadline-time.monotonic())}
                with open(args.output, 'w') as stream:
                    json.dump(report, stream, indent=2)
                    stream.write('\n')
                print(json.dumps(report, indent=2))
                return
        report = {'schema': 'n04-pre-motion-readiness/v1', 'ready': False,
                  'expected_epoch': args.expected_epoch, 'sample': node.snapshot(),
                  'failure': 'fresh_tracking_depth_ready_and_map_ready_not_observed'}
        with open(args.output, 'w') as stream:
            json.dump(report, stream, indent=2)
            stream.write('\n')
        raise SystemExit('N04 stack did not become ready; inspect the retained status sample')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
