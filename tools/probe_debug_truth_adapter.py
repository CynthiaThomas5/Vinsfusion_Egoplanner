#!/usr/bin/env python3
"""Check the live debug-truth adapter's epoch, frame, and sample contract."""
import json
import re
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from nav_msgs.msg import Odometry
from uav_interfaces.msg import LocalizationStatus


class Probe(Node):
    def __init__(self):
        super().__init__('debug_truth_adapter_probe')
        self.epoch = None
        self.frames = None
        self.first_stamp = None
        self.last_stamp = None
        self.odometry_count = 0
        self.tracking = False
        self.failure = ''
        self.control_topics = [
            '/fmu/in/offboard_control_mode',
            '/fmu/in/trajectory_setpoint',
            '/fmu/in/vehicle_command',
            '/fmu/in/vehicle_visual_odometry',
        ]
        qos = QoSProfile(depth=20, reliability=ReliabilityPolicy.RELIABLE)
        self.create_subscription(Odometry, '/debug_truth/optimized_imu_odom',
                                 self.on_odometry, qos)
        self.create_subscription(LocalizationStatus, '/debug_truth/localization_status',
                                 self.on_status, qos)

    def check_epoch(self, epoch):
        if not re.fullmatch(r'[0-9a-f]{32}', epoch or ''):
            self.failure = 'invalid_epoch'
        elif self.epoch is None:
            self.epoch = epoch
        elif self.epoch != epoch:
            self.failure = 'epoch_changed_during_run'

    def on_odometry(self, msg):
        self.check_epoch(msg.header.frame_id.removeprefix('odom_'))
        expected_frames = (f'odom_{self.epoch}', f'd435i_imu_{self.epoch}')
        frames = (msg.header.frame_id, msg.child_frame_id)
        if frames != expected_frames:
            self.failure = 'odometry_frame_contract_mismatch'
        stamp = msg.header.stamp.sec * 1_000_000_000 + msg.header.stamp.nanosec
        if stamp <= 0 or (self.last_stamp is not None and stamp <= self.last_stamp):
            self.failure = 'odometry_stamp_not_increasing'
        if self.first_stamp is None:
            self.first_stamp = stamp
        self.last_stamp = stamp
        self.frames = frames
        self.odometry_count += 1

    def on_status(self, msg):
        self.check_epoch(msg.epoch)
        if self.epoch and (msg.header.frame_id != f'odom_{self.epoch}'
                           or msg.body_frame != f'd435i_imu_{self.epoch}'):
            self.failure = 'status_frame_contract_mismatch'
        if msg.state == LocalizationStatus.LOCKED:
            self.failure = 'adapter_locked:' + msg.reason
        if msg.state == LocalizationStatus.TRACKING and msg.valid:
            self.tracking = True


def main():
    timeout_s = float(sys.argv[1]) if len(sys.argv) > 1 else 12.0
    rclpy.init()
    node = Probe()
    deadline = time.monotonic() + timeout_s
    try:
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.1)
            if node.failure:
                raise RuntimeError(node.failure)
            if node.tracking and node.odometry_count >= 10:
                publisher_counts = {
                    topic: len(node.get_publishers_info_by_topic(topic))
                    for topic in node.control_topics
                }
                if any(publisher_counts.values()):
                    raise RuntimeError('unexpected_px4_input_publisher:' +
                                       json.dumps(publisher_counts, sort_keys=True))
                print(json.dumps({
                    'result': 'PASS',
                    'epoch': node.epoch,
                    'state': 'TRACKING',
                    'odometry_samples': node.odometry_count,
                    'header_frame': node.frames[0],
                    'child_frame': node.frames[1],
                    'first_stamp_ns': node.first_stamp,
                    'last_stamp_ns': node.last_stamp,
                    'px4_input_publisher_counts': publisher_counts,
                }, sort_keys=True))
                return 0
        raise TimeoutError('did not receive 10 odometry samples and valid TRACKING status')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
