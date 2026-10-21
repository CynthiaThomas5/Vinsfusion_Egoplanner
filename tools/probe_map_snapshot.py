#!/usr/bin/env python3
"""Low-load, read-only MapStatus/occupied-cloud snapshot observer."""
import argparse
from collections import Counter, deque
import json
import math
from pathlib import Path
import struct
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import PointCloud2, PointField
from uav_interfaces.msg import DepthHealth, LocalizationStatus, MapStatus


def stamp_ns(stamp):
    return stamp.sec * 1_000_000_000 + stamp.nanosec


def status_record(msg):
    return {
        'header_stamp_ns': stamp_ns(msg.header.stamp),
        'header_frame_id': msg.header.frame_id,
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
    }


class SnapshotProbe(Node):
    def __init__(self):
        super().__init__(
            'map_snapshot_probe',
            parameter_overrides=[rclpy.parameter.Parameter('use_sim_time', value=True)])
        status_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                                durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.started = time.monotonic()
        self.status_samples = []
        self.localization = []
        self.depth = []
        self.map_samples = []
        self.clouds = deque(maxlen=128)
        self.matched_snapshot = None
        self.matched_status = None
        self.matched_stamp_ns = None
        self.last_clock_ns = None
        self.create_subscription(MapStatus, '/mapping/status', self.on_status, status_qos)
        self.create_subscription(LocalizationStatus, '/localization/status', self.on_localization,
                                 status_qos)
        self.create_subscription(DepthHealth, '/mapping/depth_health', self.on_depth, status_qos)
        self.create_subscription(PointCloud2, '/grid_map/occupancy', self.on_cloud,
                                 qos_profile_sensor_data)
        self.create_subscription(Clock, '/clock', self.on_clock, qos_profile_sensor_data)

    def on_clock(self, msg):
        self.last_clock_ns = stamp_ns(msg.clock)

    def on_status(self, msg):
        if len(self.status_samples) < 100_000:
            sample = status_record(msg)
            sample.update({
                'wall_elapsed_s': round(time.monotonic() - self.started, 6),
                'wall_epoch_s': round(time.time(), 6),
                'clock_stamp_ns_at_receipt': self.last_clock_ns,
            })
            self.status_samples.append(sample)
            self.try_capture_status(sample)

    def on_localization(self, msg):
        self.localization.append({
            'wall_elapsed_s': round(time.monotonic() - self.started, 6),
            'epoch': msg.epoch, 'state': int(msg.state), 'valid': bool(msg.valid),
            'reason': msg.reason, 'frame_id': msg.header.frame_id,
        })

    def on_depth(self, msg):
        self.depth.append({
            'wall_elapsed_s': round(time.monotonic() - self.started, 6),
            'state': int(msg.state), 'valid': bool(msg.valid), 'reason': msg.reason,
            'source_stamp_ns': stamp_ns(msg.header.stamp),
        })

    def on_cloud(self, msg):
        count = int(msg.width) * int(msg.height)
        sample = {
            'stamp_ns': stamp_ns(msg.header.stamp),
            'wall_elapsed_s': round(time.monotonic() - self.started, 6),
            'wall_epoch_s': round(time.time(), 6),
            'clock_stamp_ns_at_receipt': self.last_clock_ns,
            'points': count,
            'frame_id': msg.header.frame_id,
        }
        self.map_samples.append(sample)
        self.clouds.append((msg, sample))
        for status in reversed(self.status_samples[-16:]):
            self.try_capture_status(status)

    def try_capture_status(self, status):
        epoch = status['epoch']
        if not (epoch and status['input_ready'] and status['reset_acknowledged']
                and status['occupancy_cloud_received']
                and status['occupied_point_count'] > 0
                and status['last_occupancy_stamp_ns'] > 0
                and status['header_frame_id'] == f'odom_{epoch}'
                and status['map_id'].startswith(f'{epoch}-')):
            return
        if status['last_occupancy_stamp_ns'] == self.matched_stamp_ns:
            return
        for msg, sample in reversed(self.clouds):
            if (sample['stamp_ns'] == status['last_occupancy_stamp_ns']
                    and sample['frame_id'] == status['header_frame_id']
                    and sample['points'] == status['occupied_point_count']):
                matched = dict(status)
                matched.update({
                    'wall_elapsed_s': sample['wall_elapsed_s'],
                    'wall_epoch_s': sample['wall_epoch_s'],
                    'clock_stamp_ns_at_receipt': sample['clock_stamp_ns_at_receipt'],
                })
                snapshot = self.materialize(msg, sample, matched)
                self.matched_snapshot = snapshot
                self.matched_status = matched
                self.matched_stamp_ns = status['last_occupancy_stamp_ns']
                return

    @staticmethod
    def materialize(msg, sample, status):
        fields = {field.name: field for field in msg.fields}
        xyz_fields = [fields.get(name) for name in ('x', 'y', 'z')]
        if any(field is None or field.datatype != PointField.FLOAT32 for field in xyz_fields):
            raise ValueError('occupancy cloud must contain float32 x/y/z fields')
        endian = '>' if msg.is_bigendian else '<'
        points = []
        for row in range(msg.height):
            for col in range(msg.width):
                base = row * msg.row_step + col * msg.point_step
                point = [struct.unpack_from(endian + 'f', msg.data, base + field.offset)[0]
                         for field in xyz_fields]
                if not all(math.isfinite(value) for value in point):
                    raise ValueError('occupancy cloud contains non-finite xyz')
                points.append(point)
        return {
            'stamp_ns': sample['stamp_ns'],
            'frame_id': sample['frame_id'],
            'width': msg.width,
            'height': msg.height,
            'points': points,
            'map_status': status,
        }

    def matching_snapshot(self):
        return self.matched_snapshot, self.matched_status

    def report(self, duration_s, matched):
        return {
            'schema': 'live-map-snapshot-probe/v1',
            'scope': 'Read-only MapStatus, localization/depth status, clock, and occupancy cloud observer; no goal, PX4, or control publisher',
            'wall_seconds': round(time.monotonic() - self.started, 3),
            'requested_wall_seconds': duration_s,
            'map_status_sample_count': len(self.status_samples),
            'map_status_reasons': dict(Counter(row['reason'] for row in self.status_samples)),
            'map_status_ready_count': sum(row['input_ready'] for row in self.status_samples),
            'map_status_occupied_count_max': max(
                (row['occupied_point_count'] for row in self.status_samples), default=0),
            'localization_history': self.localization,
            'depth_history': self.depth,
            'map_samples': self.map_samples,
            'map_status_cloud_pair': {
                'matched': matched is not None,
                'epoch': matched.get('epoch') if matched else None,
                'map_id': matched.get('map_id') if matched else None,
                'frame_id': matched.get('header_frame_id') if matched else None,
                'stamp_ns': matched.get('last_occupancy_stamp_ns') if matched else None,
                'point_count': matched.get('occupied_point_count') if matched else None,
            },
            'qualification': 'One exact same-stamp/frame/epoch MapStatus-cloud match is a snapshot handoff check, not map coverage or navigation acceptance',
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=40.0)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cloud-output', type=Path, required=True)
    parser.add_argument('--require-pair', action='store_true')
    args = parser.parse_args()
    if args.seconds <= 0:
        raise ValueError('--seconds must be positive')
    for path in (args.output, args.cloud_output):
        if path.exists():
            raise FileExistsError(path)
        path.parent.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    node = SnapshotProbe()
    try:
        deadline = time.monotonic() + args.seconds
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=min(0.1, max(0.0, deadline-time.monotonic())))
        snapshot, matched = node.matching_snapshot()
        report = node.report(args.seconds, matched)
        args.output.write_text(json.dumps(report, indent=2) + '\n')
        if snapshot is not None:
            args.cloud_output.write_text(json.dumps(snapshot, indent=2) + '\n')
        print(json.dumps(report, indent=2))
        if args.require_pair and snapshot is None:
            raise SystemExit('No ready same-epoch MapStatus/cloud pair was observed')
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
