import argparse
import json
import math
import os
import sys
import time

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image, Imu


TOPICS = {
    '/sensors/d435i/infra1/image_rect_raw': ('infra1', Image),
    '/sensors/d435i/infra2/image_rect_raw': ('infra2', Image),
    '/sensors/d435i/infra1/camera_info': ('infra1_info', CameraInfo),
    '/sensors/d435i/infra2/camera_info': ('infra2_info', CameraInfo),
    '/sensors/d435i/depth/image_rect_raw': ('depth_native', Image),
    '/sensors/d435i/depth': ('depth_meters', Image),
    '/sensors/d435i/depth/camera_info': ('depth_info', CameraInfo),
    '/sensors/d435i/imu': ('imu', Imu),
    '/camera_b/imu': ('imu_native_diagnostic', Imu),
    '/camera_b/gyro/sample': ('gyro_native_diagnostic', Imu),
    '/camera_b/accel/sample': ('accel_native_diagnostic', Imu),
    '/sensors/d435i/color/image_raw': ('color', Image),
    '/sensors/d435i/color/camera_info': ('color_info', CameraInfo),
}


def stamp_seconds(message):
    return float(message.header.stamp.sec) + float(message.header.stamp.nanosec) * 1e-9


def percentile(values, percent):
    if not values:
        return None
    return float(np.percentile(np.asarray(values, dtype=np.float64), percent))


def stream_summary(record, duration):
    stamps = record['stamps']
    gaps = [b - a for a, b in zip(stamps, stamps[1:])]
    positive_gaps = [gap for gap in gaps if gap > 0.0]
    return {
        'messages': len(stamps),
        'measured_hz': ((len(stamps) - 1) / (stamps[-1] - stamps[0]))
        if len(stamps) > 1 and stamps[-1] > stamps[0] else 0.0,
        'nominal_capture_hz': len(stamps) / duration if duration > 0 else 0.0,
        'stamp_monotonic': all(gap > 0.0 for gap in gaps),
        'non_monotonic_intervals': sum(gap <= 0.0 for gap in gaps),
        'max_positive_stamp_gap_s': max(positive_gaps) if positive_gaps else None,
        'source_age_s': {
            'median': percentile(record['ages'], 50),
            'p95': percentile(record['ages'], 95),
            'max': max(record['ages']) if record['ages'] else None,
            'negative_count': sum(age < 0.0 for age in record['ages']),
        },
        'frame_ids': sorted(record['frame_ids']),
        'encodings': sorted(record['encodings']),
        'sizes': sorted(record['sizes']),
    }


class SensorCapture(Node):
    def __init__(self, duration_s, output_path):
        super().__init__('hw02_sensor_capture')
        self.duration_s = duration_s
        self.output_path = output_path
        self.started_wall = time.time()
        self.started_monotonic = time.monotonic()
        self.records = {
            name: {
                'stamps': [], 'ages': [], 'frame_ids': set(),
                'encodings': set(), 'sizes': set(),
            }
            for name, _ in TOPICS.values()
        }
        self.camera_info = {}
        self.depth_native_center = []
        self.depth_native_valid_fractions = []
        self.depth_meter_center = []
        self.depth_valid_fractions = []
        self.imu_angular = []
        self.imu_acceleration = []
        self.imu_finite_count = 0
        self.imu_nonfinite_count = 0
        self._subscriptions = []
        for topic, (name, message_type) in TOPICS.items():
            callback = lambda message, key=name: self._on_message(key, message)
            self._subscriptions.append(
                self.create_subscription(message_type, topic, callback, qos_profile_sensor_data)
            )
        self.get_logger().info(
            'Capturing {} seconds of D435i topic statistics; image payloads are not saved.'.format(
                duration_s
            )
        )

    def _record_header(self, key, message):
        record = self.records[key]
        stamp = stamp_seconds(message)
        record['stamps'].append(stamp)
        record['ages'].append(time.time() - stamp)
        record['frame_ids'].add(message.header.frame_id)
        return record

    def _on_message(self, key, message):
        record = self._record_header(key, message)
        if isinstance(message, Image):
            record['encodings'].add(message.encoding)
            record['sizes'].add('{}x{}'.format(message.width, message.height))
            if key == 'depth_native':
                self._sample_native_depth(message)
            elif key == 'depth_meters':
                self._sample_meter_depth(message)
        elif isinstance(message, CameraInfo):
            current = {
                'width': message.width,
                'height': message.height,
                'frame_id': message.header.frame_id,
                'distortion_model': message.distortion_model,
                'K': list(message.k),
                'D': list(message.d),
                'R': list(message.r),
                'P': list(message.p),
            }
            self.camera_info[key] = current
        elif isinstance(message, Imu):
            if key != 'imu':
                return
            angular = [message.angular_velocity.x, message.angular_velocity.y, message.angular_velocity.z]
            accel = [message.linear_acceleration.x, message.linear_acceleration.y, message.linear_acceleration.z]
            if all(math.isfinite(value) for value in angular + accel):
                self.imu_finite_count += 1
                self.imu_angular.append(angular)
                self.imu_acceleration.append(accel)
            else:
                self.imu_nonfinite_count += 1

    def _sample_native_depth(self, message):
        if message.encoding != '16UC1' or message.step < message.width * 2:
            return
        dtype = np.dtype('>u2' if message.is_bigendian else '<u2')
        image = np.ndarray((message.height, message.width), dtype=dtype,
                           buffer=message.data, strides=(message.step, 2))
        y0, y1 = message.height * 2 // 5, message.height * 3 // 5
        x0, x1 = message.width * 2 // 5, message.width * 3 // 5
        center = image[y0:y1, x0:x1]
        valid = center > 0
        self.depth_native_valid_fractions.append(float(np.count_nonzero(valid)) / valid.size)
        if np.any(valid):
            self.depth_native_center.append(float(np.median(center[valid])))

    def _sample_meter_depth(self, message):
        if message.encoding != '32FC1' or message.step < message.width * 4:
            return
        dtype = np.dtype('>f4' if message.is_bigendian else '<f4')
        image = np.ndarray((message.height, message.width), dtype=dtype,
                           buffer=message.data, strides=(message.step, 4))
        y0, y1 = message.height * 2 // 5, message.height * 3 // 5
        x0, x1 = message.width * 2 // 5, message.width * 3 // 5
        center = image[y0:y1, x0:x1]
        valid = np.isfinite(center) & (center > 0.0)
        self.depth_valid_fractions.append(float(np.count_nonzero(valid)) / valid.size)
        if np.any(valid):
            self.depth_meter_center.append(float(np.median(center[valid])))

    def _vector_stats(self, vectors):
        if not vectors:
            return None
        values = np.asarray(vectors, dtype=np.float64)
        mean = np.mean(values, axis=0)
        std = np.std(values, axis=0)
        return {
            'mean_xyz': mean.tolist(),
            'std_xyz': std.tolist(),
            'mean_vector_magnitude': float(np.linalg.norm(mean)),
            'sample_count': int(values.shape[0]),
        }

    def build_report(self, ended_wall):
        duration = time.monotonic() - self.started_monotonic
        stream_report = {
            key: stream_summary(record, duration)
            for key, record in self.records.items()
        }
        left = self.records['infra1']['stamps']
        right = self.records['infra2']['stamps']
        i = j = 0
        pair_deltas = []
        while i < len(left) and j < len(right):
            delta = left[i] - right[j]
            if abs(delta) <= 0.010:
                pair_deltas.append(abs(delta))
                i += 1
                j += 1
            elif delta < 0.0:
                i += 1
            else:
                j += 1
        native_stamps = self.records['depth_native']['stamps']
        meter_stamps = self.records['depth_meters']['stamps']
        meter_set = set(meter_stamps)
        imu_count = self.imu_finite_count + self.imu_nonfinite_count
        return {
            'capture': {
                'started_unix_s': self.started_wall,
                'ended_unix_s': ended_wall,
                'elapsed_s': duration,
                'requested_s': self.duration_s,
                'image_payload_saved': False,
            },
            'streams': stream_report,
            'stereo_pairing': {
                'pair_tolerance_s': 0.010,
                'pairs': len(pair_deltas),
                'left_unpaired': len(left) - len(pair_deltas),
                'right_unpaired': len(right) - len(pair_deltas),
                'pair_stamp_delta_median_s': percentile(pair_deltas, 50),
                'pair_stamp_delta_p95_s': percentile(pair_deltas, 95),
                'pair_stamp_delta_max_s': max(pair_deltas) if pair_deltas else None,
            },
            'camera_info': self.camera_info,
            'depth_adapter': {
                'native_topic': '/sensors/d435i/depth/image_rect_raw',
                'canonical_topic': '/sensors/d435i/depth',
                'scale_m_per_u16': 0.001,
                'native_encoding': sorted(self.records['depth_native']['encodings']),
                'canonical_encoding': sorted(self.records['depth_meters']['encodings']),
                'native_center_median_u16': percentile(self.depth_native_center, 50),
                'native_center_valid_fraction_median': percentile(self.depth_native_valid_fractions, 50),
                'canonical_center_median_m': percentile(self.depth_meter_center, 50),
                'canonical_center_valid_fraction_median': percentile(self.depth_valid_fractions, 50),
                'native_to_canonical_equal_stamp_count': len(set(native_stamps) & meter_set),
                'native_stamp_count': len(native_stamps),
                'canonical_stamp_count': len(meter_stamps),
                'all_native_stamps_preserved': len(native_stamps) == len(meter_stamps)
                and native_stamps == meter_stamps,
            },
            'imu': {
                'finite_angular_and_acceleration_messages': self.imu_finite_count,
                'nonfinite_messages': self.imu_nonfinite_count,
                'finite_fraction': self.imu_finite_count / imu_count if imu_count else None,
                'angular_velocity_rad_s': self._vector_stats(self.imu_angular),
                'linear_acceleration_m_s2': self._vector_stats(self.imu_acceleration),
                'orientation_checked': False,
            },
        }


def main():
    parser = argparse.ArgumentParser(description='Collect live HW02 D435i stream statistics.')
    parser.add_argument('--duration-s', type=float, default=60.0)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(sys.argv[1:])
    if args.duration_s <= 0.0:
        parser.error('--duration-s must be positive')

    rclpy.init(args=[])
    node = SensorCapture(args.duration_s, args.output)
    try:
        while rclpy.ok() and time.monotonic() - node.started_monotonic < args.duration_s:
            rclpy.spin_once(node, timeout_sec=0.1)
        report = node.build_report(time.time())
        output_path = os.path.abspath(args.output)
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as stream:
            json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write('\n')
        print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
