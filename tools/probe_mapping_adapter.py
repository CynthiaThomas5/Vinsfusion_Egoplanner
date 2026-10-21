#!/usr/bin/env python3
"""Synthetic ROS smoke probe for the mapping input gate and EGO plan_env."""
import argparse
import json
from pathlib import Path
import struct
import time
import uuid

import rclpy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import (DurabilityPolicy, QoSProfile, ReliabilityPolicy,
                       qos_profile_sensor_data)
from sensor_msgs.msg import Image, PointCloud2
from uav_interfaces.msg import DepthHealth, LocalizationStatus


class MappingProbe(Node):
    def __init__(self):
        super().__init__('mapping_input_probe')
        self.epoch = uuid.uuid4().hex
        status_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                                durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.localization_pub = self.create_publisher(LocalizationStatus, '/localization/status', status_qos)
        self.odometry_pub = self.create_publisher(Odometry, '/localization/optimized_imu_odom', qos_profile_sensor_data)
        self.depth_pub = self.create_publisher(Image, '/sensors/d435i/depth', qos_profile_sensor_data)
        self.depth_sub = self.create_subscription(Image, '/drone_0_depth_image', self.on_depth, qos_profile_sensor_data)
        self.health_sub = self.create_subscription(DepthHealth, '/mapping/depth_health', self.on_health, 10)
        self.map_sub = self.create_subscription(PointCloud2, '/grid_map/occupancy', self.on_map, 10)
        self.pose_sub = self.create_subscription(PoseStamped, '/drone_0_camera_pose', self.on_pose, qos_profile_sensor_data)
        self.depth_health_ready = False
        self.depth_outputs = 0
        self.pose_outputs = 0
        self.last_pose_frame = ''
        self.depth_stamps = set()
        self.pose_stamps = set()
        self.map_messages = 0
        self.max_occupied_points = 0
        self.map_points = []

    def on_health(self, msg):
        self.depth_health_ready = msg.valid and msg.state == DepthHealth.STATE_READY

    def on_depth(self, msg):
        self.depth_outputs += 1
        self.depth_stamps.add((msg.header.stamp.sec, msg.header.stamp.nanosec))

    def on_pose(self, msg):
        self.pose_outputs += 1
        self.last_pose_frame = msg.header.frame_id
        self.pose_stamps.add((msg.header.stamp.sec, msg.header.stamp.nanosec))

    def on_map(self, msg):
        self.map_messages += 1
        point_count = msg.width * msg.height
        self.map_points.append(point_count)
        self.max_occupied_points = max(self.max_occupied_points, point_count)

    def publish_localization_status(self, valid=True):
        msg = LocalizationStatus()
        msg.header.frame_id = f'odom_{self.epoch}'
        msg.epoch = self.epoch
        msg.state = LocalizationStatus.TRACKING if valid else LocalizationStatus.LOST
        msg.valid = valid
        msg.reason = 'synthetic_mapping_probe' if valid else 'synthetic_gate_close'
        msg.body_frame = f'd435i_imu_{self.epoch}'
        msg.covariance_valid = False
        self.localization_pub.publish(msg)

    def publish_odom(self, stamp_ns):
        msg = Odometry()
        msg.header.stamp.sec, msg.header.stamp.nanosec = divmod(stamp_ns, 1_000_000_000)
        msg.header.frame_id = f'odom_{self.epoch}'
        msg.child_frame_id = f'd435i_imu_{self.epoch}'
        msg.pose.pose.orientation.w = 1.0
        self.odometry_pub.publish(msg)

    def publish_depth(self, stamp_ns):
        width, height = 640, 480
        pixels = bytearray(width * height * 4)
        # Sparse finite returns exercise partial depth holes; the remaining
        # zero pixels must stay unknown and must not be raycast as free space.
        for row in range(8, 40, 8):
            for col in range(8, 40, 8):
                struct.pack_into('<f', pixels, (row * width + col) * 4, 2.0)
        msg = Image()
        msg.header.stamp.sec, msg.header.stamp.nanosec = divmod(stamp_ns, 1_000_000_000)
        msg.header.frame_id = 'depth_optical_frame'
        msg.height, msg.width = height, width
        msg.encoding = '32FC1'
        msg.is_bigendian = 0
        msg.step = width * 4
        msg.data = pixels
        self.depth_pub.publish(msg)


def spin(node, duration_s):
    until = time.monotonic() + duration_s
    while rclpy.ok() and time.monotonic() < until:
        rclpy.spin_once(node, timeout_sec=0.01)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    rclpy.init()
    node = MappingProbe()
    start = time.monotonic()
    try:
        deadline = start + 15.0
        stamp = 20_000_000_000
        frame = 0
        invalidated = False
        empty_map_after_invalidation = False
        outputs_at_invalidation = None
        while time.monotonic() < deadline:
            if not invalidated:
                node.publish_localization_status()
            else:
                node.publish_localization_status(valid=False)
            before = stamp + frame * 100_000_000
            node.publish_odom(before - 20_000_000)
            node.publish_depth(before)
            node.publish_odom(before + 20_000_000)
            frame += 1
            spin(node, 0.1)
            paired_stamps = node.depth_stamps & node.pose_stamps
            if (not invalidated and len(paired_stamps) >= 3
                    and node.max_occupied_points > 0):
                invalidated = True
                node.publish_localization_status(valid=False)
                spin(node, 0.2)
                outputs_at_invalidation = (node.depth_outputs, node.pose_outputs)
            if (invalidated and node.map_points
                    and node.map_points[-1] == 0
                    and any(points > 0 for points in node.map_points)):
                empty_map_after_invalidation = True
                break
        spin(node, 0.4)
        paired_stamps = node.depth_stamps & node.pose_stamps
        result = {
            'epoch': node.epoch,
            'elapsed_wall_s': round(time.monotonic() - start, 3),
            'depth_health_ready_observed': node.depth_health_ready,
            'depth_outputs': node.depth_outputs,
            'pose_outputs': node.pose_outputs,
            'paired_output_stamp_count': len(paired_stamps),
            'paired_output_stamps': sorted(paired_stamps),
            'last_pose_frame': node.last_pose_frame,
            'map_messages': node.map_messages,
            'map_point_counts': node.map_points,
            'max_occupied_points': node.max_occupied_points,
            'gate_invalidated_after_mapping': invalidated,
            'outputs_at_invalidation': outputs_at_invalidation,
            'outputs_after_invalidation': [node.depth_outputs, node.pose_outputs],
            'empty_map_after_invalidation': empty_map_after_invalidation,
            'qualification': 'synthetic ROS integration smoke only; no physical geometry, planner response, or PX4 qualification'
        }
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))
        if (len(paired_stamps) < 3 or node.max_occupied_points <= 0 or not invalidated
                or not empty_map_after_invalidation
                or outputs_at_invalidation != (node.depth_outputs, node.pose_outputs)):
            raise SystemExit('Mapping adapter/plan_env smoke did not pair inputs or clear the map after gate closure')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
