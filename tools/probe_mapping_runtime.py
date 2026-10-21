#!/usr/bin/env python3
"""Read-only observer for live D435i/VINS-to-EGO mapping integration."""
import argparse
from collections import deque
import json
import math
from pathlib import Path
import signal
import struct
import threading
import time

import rclpy
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup, ReentrantCallbackGroup
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from rclpy.executors import MultiThreadedExecutor
from rclpy.signals import SignalHandlerOptions
from rclpy.node import Node
from rclpy.qos import (DurabilityPolicy, QoSProfile, ReliabilityPolicy,
                       qos_profile_sensor_data)
from sensor_msgs.msg import Image, PointCloud2, PointField
from rosgraph_msgs.msg import Clock
from uav_interfaces.msg import DepthHealth, LocalizationStatus, MapStatus


def stamp_ns(stamp):
    return stamp.sec * 1_000_000_000 + stamp.nanosec


class MappingRuntimeProbe(Node):
    def __init__(self):
        super().__init__('mapping_runtime_probe')
        status_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                                durability=DurabilityPolicy.TRANSIENT_LOCAL)
        output_qos = QoSProfile(depth=100, reliability=ReliabilityPolicy.RELIABLE)
        clock_qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.input_callback_group = ReentrantCallbackGroup()
        self.map_callback_group = MutuallyExclusiveCallbackGroup()
        self.started = time.monotonic()
        self.started_wall_epoch_s = time.time()
        self.depth_input_count = 0
        self.depth_input_samples = []
        self.depth_output_stamps = set()
        self.pose_output_stamps = set()
        self.ego_depth_samples = []
        self.ego_pose_samples = []
        self.last_clock_stamp_ns = None
        self.optimized_odom_count = 0
        self.optimized_samples = []
        self.depth_health_history = []
        self.localization_history = []
        self.map_status_samples = []
        self.map_point_counts = []
        self.map_samples = []
        self.recent_map_messages = deque(maxlen=128)
        self.map_frame_ids = set()
        self.max_occupied_points = 0
        self.max_map_snapshot = None
        self.max_map_message = None
        self.last_health = None
        self.last_localization = None
        self.last_map_points = None

        self.create_subscription(Image, '/sensors/d435i/depth', self.on_depth, qos_profile_sensor_data,
                                 callback_group=self.input_callback_group)
        self.create_subscription(DepthHealth, '/mapping/depth_health', self.on_health, status_qos,
                                 callback_group=self.input_callback_group)
        self.create_subscription(LocalizationStatus, '/localization/status', self.on_localization, status_qos,
                                 callback_group=self.input_callback_group)
        self.create_subscription(MapStatus, '/mapping/status', self.on_map_status, status_qos,
                                 callback_group=self.input_callback_group)
        self.create_subscription(Odometry, '/localization/optimized_imu_odom', self.on_optimized,
                                 qos_profile_sensor_data, callback_group=self.input_callback_group)
        self.create_subscription(Image, '/drone_0_depth_image', self.on_ego_depth, output_qos,
                                 callback_group=self.input_callback_group)
        self.create_subscription(PoseStamped, '/drone_0_camera_pose', self.on_ego_pose, output_qos,
                                 callback_group=self.input_callback_group)
        self.create_subscription(PointCloud2, '/grid_map/occupancy', self.on_map, 10,
                                 callback_group=self.map_callback_group)
        self.create_subscription(Clock, '/clock', self.on_clock, clock_qos,
                                 callback_group=self.input_callback_group)

    def on_depth(self, msg):
        self.depth_input_count += 1
        if len(self.depth_input_samples) < 100_000:
            now = time.monotonic()
            self.depth_input_samples.append({
                'stamp_ns': stamp_ns(msg.header.stamp),
                'wall_elapsed_s': round(now - self.started, 6),
                'wall_epoch_s': round(time.time(), 6),
                'clock_stamp_ns_at_receipt': self.last_clock_stamp_ns,
            })

    def on_health(self, msg):
        current = (msg.state, msg.valid, msg.reason)
        if current != self.last_health:
            self.depth_health_history.append({
                'wall_elapsed_s': round(time.monotonic() - self.started, 3),
                'wall_epoch_s': round(time.time(), 6),
                'state': msg.state, 'valid': msg.valid, 'reason': msg.reason,
                'source_stamp_ns': stamp_ns(msg.header.stamp),
            })
            self.last_health = current

    def on_localization(self, msg):
        current = (msg.epoch, msg.state, msg.valid, msg.reason)
        if current != self.last_localization:
            self.localization_history.append({
                'wall_elapsed_s': round(time.monotonic() - self.started, 3),
                'wall_epoch_s': round(time.time(), 6),
                'epoch': msg.epoch, 'state': msg.state, 'valid': msg.valid,
                'reason': msg.reason, 'frame_id': msg.header.frame_id,
            })
            self.last_localization = current

    def on_map_status(self, msg):
        if len(self.map_status_samples) < 100_000:
            self.map_status_samples.append({
                'header_stamp_ns': stamp_ns(msg.header.stamp),
                'header_frame_id': msg.header.frame_id,
                'wall_elapsed_s': round(time.monotonic() - self.started, 6),
                'wall_epoch_s': round(time.time(), 6),
                'clock_stamp_ns_at_receipt': self.last_clock_stamp_ns,
                'epoch': msg.epoch,
                'map_id': msg.map_id,
                'reset_acknowledged': bool(msg.reset_acknowledged),
                'input_ready': bool(msg.input_ready),
                'reason': msg.reason,
                'last_depth_source_stamp_ns': stamp_ns(msg.last_depth_source_stamp),
                'last_occupancy_stamp_ns': stamp_ns(msg.last_occupancy_stamp),
                'occupancy_cloud_received': bool(msg.occupancy_cloud_received),
                'occupied_point_count': int(msg.occupied_point_count),
                'forwarded_depth_count': int(msg.forwarded_depth_count),
                'calibration_sha256': msg.calibration_sha256,
                'input_config_sha256': msg.input_config_sha256,
                'keyframe_count': int(msg.keyframe_count),
                'keyframe_dropped_count': int(msg.keyframe_dropped_count),
                'keyframe_max_rgbd_stamp_delta_s': msg.keyframe_max_rgbd_stamp_delta_s,
            })

    def on_optimized(self, msg):
        self.optimized_odom_count += 1
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        now = time.monotonic()
        self.optimized_samples.append({
            'stamp_ns': stamp_ns(msg.header.stamp),
            'wall_elapsed_s': round(now - self.started, 6),
            'wall_epoch_s': round(time.time(), 6),
            'position': [p.x, p.y, p.z],
            'quaternion': [q.x, q.y, q.z, q.w],
        })

    def on_ego_depth(self, msg):
        stamp = stamp_ns(msg.header.stamp)
        self.depth_output_stamps.add(stamp)
        self.ego_depth_samples.append({
            'stamp_ns': stamp,
            'wall_elapsed_s': round(time.monotonic() - self.started, 6),
            'wall_epoch_s': round(time.time(), 6),
            'clock_stamp_ns_at_receipt': self.last_clock_stamp_ns,
        })

    def on_clock(self, msg):
        self.last_clock_stamp_ns = stamp_ns(msg.clock)

    def on_ego_pose(self, msg):
        stamp = stamp_ns(msg.header.stamp)
        self.pose_output_stamps.add(stamp)
        position = msg.pose.position
        self.ego_pose_samples.append({
            'stamp_ns': stamp,
            'frame_id': msg.header.frame_id,
            'position': [position.x, position.y, position.z],
            'wall_elapsed_s': round(time.monotonic() - self.started, 6),
            'wall_epoch_s': round(time.time(), 6),
            'clock_stamp_ns_at_receipt': self.last_clock_stamp_ns,
        })

    @staticmethod
    def interval_summary(values):
        if not values:
            return {'count': 0, 'p50': None, 'p95': None, 'max': None}
        ordered = sorted(values)

        def percentile(fraction):
            index = max(0, math.ceil(fraction * len(ordered)) - 1)
            return round(ordered[index], 6)

        return {
            'count': len(values),
            'p50': percentile(0.50),
            'p95': percentile(0.95),
            'max': round(max(values), 6),
        }

    def on_map(self, msg):
        points = msg.width * msg.height
        self.recent_map_messages.append(msg)
        now = time.monotonic()
        if len(self.map_samples) < 100_000:
            self.map_samples.append({
                'stamp_ns': stamp_ns(msg.header.stamp),
                'wall_elapsed_s': round(now - self.started, 6),
                'wall_epoch_s': round(time.time(), 6),
                'clock_stamp_ns_at_receipt': self.last_clock_stamp_ns,
                'points': points,
                'frame_id': msg.header.frame_id,
            })
        self.map_frame_ids.add(msg.header.frame_id)
        if points > self.max_occupied_points:
            self.max_map_message = msg
        self.max_occupied_points = max(self.max_occupied_points, points)
        if points != self.last_map_points:
            self.map_point_counts.append({
                'wall_elapsed_s': round(time.monotonic() - self.started, 3),
                'wall_epoch_s': round(time.time(), 6),
                'points': points, 'frame_id': msg.header.frame_id,
            })
            self.last_map_points = points

    def materialize_max_map_snapshot(self):
        msg = self.max_map_message
        if msg is None:
            return None
        return self.materialize_map_message(msg)

    def materialize_map_message(self, msg):
        field_offsets = {field.name: field for field in msg.fields}
        xyz_fields = [field_offsets.get(name) for name in ('x', 'y', 'z')]
        if any(field is None or field.datatype != PointField.FLOAT32 for field in xyz_fields):
            return None
        endian = '>' if msg.is_bigendian else '<'
        xyz = []
        for row in range(msg.height):
            for col in range(msg.width):
                base = row * msg.row_step + col * msg.point_step
                value = [struct.unpack_from(endian + 'f', msg.data, base + field.offset)[0]
                         for field in xyz_fields]
                if all(math.isfinite(v) for v in value):
                    xyz.append(value)
        self.max_map_snapshot = {
            'stamp_ns': stamp_ns(msg.header.stamp),
            'frame_id': msg.header.frame_id,
            'width': msg.width,
            'height': msg.height,
            'points': xyz,
        }
        return self.max_map_snapshot

    def materialize_status_matched_snapshot(self):
        for status in reversed(self.map_status_samples):
            if not (status['input_ready'] and status['reset_acknowledged']
                    and status['occupancy_cloud_received'] and status['last_occupancy_stamp_ns']):
                continue
            for msg in reversed(self.recent_map_messages):
                if (stamp_ns(msg.header.stamp) == status['last_occupancy_stamp_ns']
                        and msg.header.frame_id == status['header_frame_id']
                        and msg.width * msg.height == status['occupied_point_count']):
                    snapshot = self.materialize_map_message(msg)
                    if snapshot is not None:
                        snapshot['map_status'] = status
                        return snapshot
        return None

    def report(self):
        paired = self.depth_output_stamps & self.pose_output_stamps
        paired_stamps = sorted(paired)
        paired_intervals_s = [
            (later - earlier) / 1_000_000_000
            for earlier, later in zip(paired_stamps, paired_stamps[1:])
        ]
        pose_receipt_intervals_s = [
            later['wall_elapsed_s'] - earlier['wall_elapsed_s']
            for earlier, later in zip(self.ego_pose_samples, self.ego_pose_samples[1:])
        ]
        pose_source_age_at_receipt_s = [
            (sample['clock_stamp_ns_at_receipt'] - sample['stamp_ns']) / 1_000_000_000
            for sample in self.ego_pose_samples
            if sample['clock_stamp_ns_at_receipt'] is not None
        ]
        positions = [sample['position'] for sample in self.ego_pose_samples]

        def interval_percentile(fraction):
            if not paired_intervals_s:
                return None
            ordered = sorted(paired_intervals_s)
            index = max(0, math.ceil(fraction * len(ordered)) - 1)
            return round(ordered[index], 6)

        return {
            'scope': 'Live Gazebo D435i sensor rig, VINS localization adapter, depth gate, and EGO plan_env; read-only observation, no PX4 or control nodes',
            'wall_seconds': round(time.monotonic() - self.started, 3),
            'wall_start_epoch_s': round(self.started_wall_epoch_s, 6),
            'depth_input_count': self.depth_input_count,
            'depth_input_samples': self.depth_input_samples,
            'depth_health_history': self.depth_health_history,
            'localization_history': self.localization_history,
            'map_status_samples': self.map_status_samples,
            'optimized_odom_count': self.optimized_odom_count,
            'ego_depth_output_count': len(self.depth_output_stamps),
            'ego_pose_output_count': len(self.pose_output_stamps),
            'ego_depth_received_message_count': len(self.ego_depth_samples),
            'ego_pose_received_message_count': len(self.ego_pose_samples),
            'paired_output_stamp_count': len(paired),
            'paired_output_stamp_ns': paired_stamps,
            'paired_source_interval_s': {
                'count': len(paired_intervals_s),
                'p50': interval_percentile(0.50),
                'p95': interval_percentile(0.95),
                'max': round(max(paired_intervals_s), 6) if paired_intervals_s else None,
            },
            'ego_pose_wall_receipt_interval_s': self.interval_summary(pose_receipt_intervals_s),
            'ego_pose_source_age_at_receipt_s': self.interval_summary(pose_source_age_at_receipt_s),
            'ego_depth_samples': self.ego_depth_samples,
            'ego_camera_pose_position_range': {
                'frame_ids': sorted({sample['frame_id'] for sample in self.ego_pose_samples}),
                'sample_count': len(positions),
                'min_xyz': [min(p[axis] for p in positions) for axis in range(3)] if positions else None,
                'max_xyz': [max(p[axis] for p in positions) for axis in range(3)] if positions else None,
            },
            'ego_camera_pose_samples': self.ego_pose_samples,
            'map_point_counts': self.map_point_counts,
            'map_samples': self.map_samples,
            'max_occupied_points': self.max_occupied_points,
            'map_frame_ids': sorted(self.map_frame_ids),
            'qualification': 'development integration only; map geometry, obstacle clearance, planner response, PX4, and formal acceptance are not evaluated',
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=float, default=45.0)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--odometry-output', type=Path)
    parser.add_argument('--map-output', type=Path)
    parser.add_argument('--require-map-status-pair', action='store_true')
    args = parser.parse_args()
    if args.seconds <= 0:
        raise ValueError('--seconds must be positive')
    for path in (args.output, args.odometry_output, args.map_output):
        if path is not None and path.exists():
            raise FileExistsError(path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    signal.signal(signal.SIGINT, signal.default_int_handler)
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = MappingRuntimeProbe()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    spin_thread = threading.Thread(target=executor.spin, name='mapping_runtime_probe_executor')
    spin_thread.start()
    report = None
    optimized_samples = []
    max_map_snapshot = None
    status_matched_snapshot = None
    interrupted = False
    try:
        spin_thread.join(timeout=args.seconds)
        if spin_thread.is_alive():
            executor.shutdown(timeout_sec=5.0)
            spin_thread.join(timeout=5.0)
        if spin_thread.is_alive():
            raise RuntimeError('mapping probe executor did not stop after the observation window')
        report = node.report()
        optimized_samples = node.optimized_samples
        status_matched_snapshot = node.materialize_status_matched_snapshot()
        max_map_snapshot = node.materialize_max_map_snapshot()
    except KeyboardInterrupt:
        interrupted = True
    finally:
        executor.shutdown(timeout_sec=5.0)
        spin_thread.join(timeout=5.0)
        if report is None:
            report = node.report()
            optimized_samples = node.optimized_samples
            status_matched_snapshot = node.materialize_status_matched_snapshot()
            max_map_snapshot = node.materialize_max_map_snapshot()
        report['map_status_cloud_pair'] = {
            'matched': status_matched_snapshot is not None,
            'snapshot_stamp_ns': (status_matched_snapshot['stamp_ns']
                                  if status_matched_snapshot is not None else None),
            'snapshot_frame_id': (status_matched_snapshot['frame_id']
                                  if status_matched_snapshot is not None else None),
            'map_id': (status_matched_snapshot['map_status']['map_id']
                       if status_matched_snapshot is not None else None),
            'map_status_sample_count': len(report['map_status_samples']),
        }
        report['interrupted'] = interrupted
        report['executor_stopped_before_node_destroy'] = not spin_thread.is_alive()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    if args.odometry_output is not None:
        args.odometry_output.parent.mkdir(parents=True, exist_ok=True)
        args.odometry_output.write_text(json.dumps({'optimized': optimized_samples}, indent=2) + '\n')
    selected_snapshot = status_matched_snapshot or max_map_snapshot
    if args.map_output is not None and selected_snapshot is not None:
        args.map_output.parent.mkdir(parents=True, exist_ok=True)
        args.map_output.write_text(json.dumps(selected_snapshot, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    paired = report['paired_output_stamp_count']
    tracking = any(row['valid'] and row['state'] == LocalizationStatus.TRACKING
                   for row in report['localization_history'])
    ready = any(row['valid'] and row['state'] == DepthHealth.STATE_READY
                for row in report['depth_health_history'])
    if not tracking or not ready or paired == 0 or report['max_occupied_points'] == 0:
        raise SystemExit('Live mapping probe did not observe valid localization, ready depth, paired inputs, and occupied map output')
    if args.require_map_status_pair and status_matched_snapshot is None:
        raise SystemExit('Live mapping probe did not observe an exact MapStatus/occupancy cloud match')


if __name__ == '__main__':
    main()
