#!/usr/bin/env python3
"""Save exact depth/pose/fusion inputs used by the N04 raw map snapshots."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import signal
import struct
import time

import numpy as np
import rclpy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import (DurabilityPolicy, QoSProfile, ReliabilityPolicy,
                       qos_profile_sensor_data)
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import CameraInfo, Image
from std_msgs.msg import String
from uav_interfaces.msg import DepthHealth, LocalizationStatus, MapStatus


def stamp_ns(stamp):
    return int(stamp.sec)*1_000_000_000+int(stamp.nanosec)


def pose_record(msg):
    p, q = msg.pose.position, msg.pose.orientation
    values = [p.x, p.y, p.z, q.x, q.y, q.z, q.w]
    if not all(math.isfinite(v) for v in values):
        raise ValueError('non-finite camera pose')
    return {'stamp_ns': stamp_ns(msg.header.stamp), 'frame_id': msg.header.frame_id,
            'position': values[:3], 'quaternion': values[3:]}


def status_record(msg):
    return {
        'header_stamp_ns': stamp_ns(msg.header.stamp),
        'header_frame_id': msg.header.frame_id,
        'epoch': msg.epoch, 'map_id': msg.map_id,
        'reset_acknowledged': bool(msg.reset_acknowledged),
        'input_ready': bool(msg.input_ready), 'reason': msg.reason,
        'last_depth_source_stamp_ns': stamp_ns(msg.last_depth_source_stamp),
        'last_occupancy_stamp_ns': stamp_ns(msg.last_occupancy_stamp),
        'occupancy_cloud_received': bool(msg.occupancy_cloud_received),
        'forwarded_depth_count': int(msg.forwarded_depth_count),
        'last_depth_forward_monotonic_ns': int(msg.last_depth_forward_monotonic_ns),
        'depth_callback_count': int(msg.depth_callback_count),
        'pending_depth_count': int(msg.pending_depth_count),
        'pending_depth_high_water_count': int(msg.pending_depth_high_water_count),
        'dropped_depth_count': int(msg.dropped_depth_count),
        'calibration_sha256': msg.calibration_sha256,
        'input_config_sha256': msg.input_config_sha256,
    }


class InputRecorder(Node):
    def __init__(self, depth_topic, pose_topic, seconds, stride, margin):
        super().__init__('n04_mapping_input_recorder',
                         parameter_overrides=[rclpy.parameter.Parameter('use_sim_time', value=True)])
        self.started = time.monotonic()
        self.seconds = seconds
        self.stride = stride
        self.margin = margin
        self.depth_frames = []
        self.depth_arrays = []
        self.raw_depth_headers = []
        self.camera_poses = []
        self.odometry = []
        self.fusion_trace = []
        self.map_status = []
        self.depth_health = []
        self.localization = []
        self.camera_info = []
        self.clock = []
        self.errors = []
        self.last_depth_stamp = None
        reliable = QoSProfile(depth=1000, reliability=ReliabilityPolicy.RELIABLE)
        trace_qos = QoSProfile(depth=1000, reliability=ReliabilityPolicy.BEST_EFFORT)
        durable = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                             durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(Image, '/sensors/d435i/depth', self.on_raw_depth,
                                 qos_profile_sensor_data)
        self.create_subscription(Image, depth_topic, self.on_depth, reliable)
        self.create_subscription(PoseStamped, pose_topic, self.on_camera_pose, reliable)
        self.create_subscription(Odometry, '/localization/optimized_imu_odom',
                                 self.on_odometry, reliable)
        self.create_subscription(String, '/mapping/depth_fusion_trace',
                                 self.on_fusion_trace, trace_qos)
        self.create_subscription(MapStatus, '/mapping/status', self.on_map_status, durable)
        self.create_subscription(DepthHealth, '/mapping/depth_health', self.on_depth_health, durable)
        self.create_subscription(LocalizationStatus, '/localization/status',
                                 self.on_localization, durable)
        self.create_subscription(CameraInfo, '/sensors/d435i/depth/camera_info',
                                 self.on_camera_info, qos_profile_sensor_data)
        self.create_subscription(Clock, '/clock', self.on_clock, qos_profile_sensor_data)

    def on_raw_depth(self, msg):
        if len(self.raw_depth_headers) < 200_000:
            self.raw_depth_headers.append({'stamp_ns': stamp_ns(msg.header.stamp),
                                           'frame_id': msg.header.frame_id,
                                           'encoding': msg.encoding,
                                           'width': msg.width, 'height': msg.height})

    def on_depth(self, msg):
        if len(self.depth_frames) >= 20_000:
            self.errors.append('depth_frame_cap_reached')
            return
        stamp = stamp_ns(msg.header.stamp)
        if self.last_depth_stamp is not None and stamp <= self.last_depth_stamp:
            self.errors.append('ego_depth_stamps_not_strictly_increasing')
        self.last_depth_stamp = stamp
        record = {'stamp_ns': stamp, 'frame_id': msg.header.frame_id,
                  'encoding': msg.encoding, 'width': int(msg.width),
                  'height': int(msg.height), 'step': int(msg.step),
                  'wall_elapsed_s': round(time.monotonic()-self.started, 6)}
        if msg.encoding != '32FC1' or msg.step < msg.width*4 or len(msg.data) < msg.step*msg.height:
            record['pixels_recorded'] = False
            self.errors.append(f"unsupported_depth_image:{msg.encoding}:{msg.width}x{msg.height}")
            self.depth_frames.append(record)
            return
        dtype = np.dtype('>f4' if msg.is_bigendian else '<f4')
        image = np.ndarray((msg.height, msg.width), dtype=dtype, buffer=msg.data,
                           strides=(msg.step, 4))
        pixels = image[self.margin:msg.height-self.margin:self.stride,
                       self.margin:msg.width-self.margin:self.stride].astype(np.float32, copy=True)
        if not np.isfinite(pixels).all():
            record['nonfinite_sample_count'] = int(np.count_nonzero(~np.isfinite(pixels)))
        record.update({'pixels_recorded': True, 'sample_shape_hw': list(pixels.shape),
                       'array_index': len(self.depth_arrays),
                       'valid_sample_count': int(np.count_nonzero(np.isfinite(pixels)&(pixels>0)))})
        if self.depth_arrays and pixels.shape != self.depth_arrays[0].shape:
            self.errors.append('depth_sample_shape_changed')
            record['pixels_recorded'] = False
        else:
            self.depth_arrays.append(pixels)
        self.depth_frames.append(record)

    def on_camera_pose(self, msg):
        if len(self.camera_poses) < 200_000:
            try:
                self.camera_poses.append(pose_record(msg))
            except ValueError as error:
                self.errors.append(str(error))

    def on_odometry(self, msg):
        if len(self.odometry) < 200_000:
            p, q = msg.pose.pose.position, msg.pose.pose.orientation
            self.odometry.append({'stamp_ns': stamp_ns(msg.header.stamp),
                                  'frame_id': msg.header.frame_id,
                                  'child_frame_id': msg.child_frame_id,
                                  'position': [p.x, p.y, p.z],
                                  'quaternion': [q.x, q.y, q.z, q.w],
                                  'wall_elapsed_s': round(time.monotonic()-self.started, 6)})

    def on_fusion_trace(self, msg):
        try:
            event = json.loads(msg.data)
            event['wall_elapsed_s'] = round(time.monotonic()-self.started, 6)
            if len(self.fusion_trace) < 500_000:
                self.fusion_trace.append(event)
        except (json.JSONDecodeError, TypeError) as error:
            self.errors.append(f'bad_fusion_trace:{error}')

    def on_map_status(self, msg):
        if len(self.map_status) < 100_000:
            row = status_record(msg)
            row['wall_elapsed_s'] = round(time.monotonic()-self.started, 6)
            self.map_status.append(row)

    def on_depth_health(self, msg):
        if len(self.depth_health) < 100_000:
            self.depth_health.append({'stamp_ns': stamp_ns(msg.header.stamp),
                'state': int(msg.state), 'valid': bool(msg.valid), 'reason': msg.reason,
                'frame_id': msg.header.frame_id,
                'wall_elapsed_s': round(time.monotonic()-self.started, 6)})

    def on_localization(self, msg):
        if len(self.localization) < 100_000:
            self.localization.append({'stamp_ns': stamp_ns(msg.header.stamp),
                'epoch': msg.epoch, 'state': int(msg.state), 'valid': bool(msg.valid),
                'reason': msg.reason, 'frame_id': msg.header.frame_id,
                'wall_elapsed_s': round(time.monotonic()-self.started, 6)})

    def on_camera_info(self, msg):
        if len(self.camera_info) < 100_000:
            self.camera_info.append({'stamp_ns': stamp_ns(msg.header.stamp),
                'frame_id': msg.header.frame_id, 'width': int(msg.width),
                'height': int(msg.height), 'k': list(msg.k), 'p': list(msg.p),
                'd': list(msg.d), 'distortion_model': msg.distortion_model})

    def on_clock(self, msg):
        if len(self.clock) < 100_000:
            self.clock.append(stamp_ns(msg.clock))

    def save(self, output_dir):
        output_dir.mkdir(parents=True, exist_ok=True)
        pixel_path = output_dir/'mapping-depth-pixels.npz'
        if self.depth_arrays:
            array = np.stack(self.depth_arrays).astype(np.float32, copy=False)
        else:
            array = np.empty((0, 0, 0), dtype=np.float32)
        np.savez_compressed(pixel_path, depth_m=array)
        sha = hashlib.sha256(pixel_path.read_bytes()).hexdigest()
        trace_counts = Counter(row.get('phase', 'missing') for row in self.fusion_trace)
        report = {
            'schema': 'n04-mapping-input-capture/v1',
            'scope': 'Read-only capture of raw/forwarded depth, exact EGO camera pose, optimized VINS odometry, MapStatus and actual EGO fusion trace. No truth or control input.',
            'wall_seconds': round(time.monotonic()-self.started, 3),
            'requested_wall_seconds': self.seconds,
            'sampling': {'pixel_stride': self.stride, 'margin_px': self.margin,
                         'pixel_location_rule': 'margin + k*stride; same ROS image and source stamp as EGO input',
                         'captured_ego_input_encoding': '32FC1 meters',
                         'plan_env_projection_stride': 2, 'plan_env_depth_filter_margin_px': 2},
            'depth_frame_count': len(self.depth_frames),
            'depth_sample_array_shape': list(array.shape),
            'depth_sample_array_dtype': str(array.dtype),
            'depth_sample_array_file': pixel_path.name,
            'depth_sample_array_sha256': sha,
            'depth_frame_header_errors': self.errors,
            'raw_depth_header_count': len(self.raw_depth_headers),
            'raw_depth_headers': self.raw_depth_headers,
            'depth_frames': self.depth_frames,
            'camera_pose_count': len(self.camera_poses),
            'camera_poses': self.camera_poses,
            'optimized_odometry_count': len(self.odometry),
            'optimized_odometry': self.odometry,
            'fusion_trace_count_by_phase': dict(trace_counts),
            'fusion_trace': self.fusion_trace,
            'map_status': self.map_status,
            'depth_health': self.depth_health,
            'localization_status': self.localization,
            'depth_camera_info': self.camera_info,
            'clock_stamps_ns': self.clock,
            'qualification': 'Raw samples permit offline projection/ray analysis. They are not themselves proof of map accuracy or free/unknown classification.',
        }
        report_path = output_dir/'mapping-inputs.json'
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=45.0)
    parser.add_argument('--depth-topic', default='/drone_0_depth_image')
    parser.add_argument('--pose-topic', default='/drone_0_camera_pose')
    parser.add_argument('--pixel-stride', type=int, default=2)
    parser.add_argument('--margin-px', type=int, default=2)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.seconds <= 0 or args.pixel_stride <= 0 or args.margin_px < 0:
        raise ValueError('seconds and pixel stride must be positive; margin cannot be negative')
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    rclpy.init()
    stop_requested = False
    def request_stop(_signum, _frame):
        nonlocal stop_requested
        stop_requested = True
    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    node = InputRecorder(args.depth_topic, args.pose_topic, args.seconds,
                         args.pixel_stride, args.margin_px)
    deadline = time.monotonic()+args.seconds
    try:
        while rclpy.ok() and not stop_requested and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=min(0.1, max(0.0, deadline-time.monotonic())))
    finally:
        report = node.save(args.output_dir)
        node.destroy_node()
        rclpy.shutdown()
    print(json.dumps({key: report[key] for key in ('depth_frame_count',
          'camera_pose_count', 'optimized_odometry_count', 'fusion_trace_count_by_phase',
          'depth_sample_array_file', 'depth_sample_array_sha256')}, indent=2))


if __name__ == '__main__':
    main()
