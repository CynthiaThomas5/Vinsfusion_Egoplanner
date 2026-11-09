#!/usr/bin/env python3
"""Record low-rate optimized odometry and localization status during hardware runs."""
import argparse
import json
import math
from pathlib import Path
import signal
import statistics
import time

import rclpy
from nav_msgs.msg import Odometry
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import (DurabilityPolicy, QoSProfile, ReliabilityPolicy,
                       qos_profile_sensor_data)
from rosgraph_msgs.msg import Clock
from uav_interfaces.msg import LocalizationStatus

try:
    from rclpy.signals import SignalHandlerOptions
except ImportError:  # Foxy predates signal_handler_options on rclpy.init().
    SignalHandlerOptions = None


def stamp_ns(stamp):
    return stamp.sec * 1_000_000_000 + stamp.nanosec


def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


class FreshnessProbe(Node):
    def __init__(self, project_root, session):
        hardware_mode = session.get('rig_config') == 'config/hardware/rig.json'
        super().__init__('localization_freshness_probe', parameter_overrides=[
            Parameter('use_sim_time', value=False if hardware_mode else True)])
        self.hardware_mode = hardware_mode
        self.started = time.monotonic()
        self.started_wall_epoch_s = time.time()
        self.session = session
        self.project_root = Path(project_root).resolve()
        self.freshness_policy = None
        self.freshness_policy_sha256 = session.get('health_sha256')
        if self.hardware_mode and isinstance(session.get('health_config'), str):
            policy_path = self.project_root / session['health_config']
            if policy_path.is_file():
                self.freshness_policy = json.loads(policy_path.read_text())
        self.clock_count = 0
        self.clock_first = None
        self.clock_latest = None
        self.clock_latest_wall = None
        self.raw = {
            'optimized': {'topic': session['namespace'] + '/odometry', 'count': 0, 'samples': []},
        }
        self.optimized_adapter_output = {
            'topic': '/localization/optimized_imu_odom', 'count': 0, 'samples': []}
        self.status_history = []
        self.status_receipts = []
        self.last_status_signature = None
        self.last_status_health_signature = None
        self.last_status_record_wall = -1.0

        status_qos = QoSProfile(
            depth=10, reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL)
        if not self.hardware_mode:
            self.create_subscription(Clock, '/clock', self.on_clock,
                                     QoSProfile(depth=20, reliability=ReliabilityPolicy.BEST_EFFORT))
        self.create_subscription(LocalizationStatus, '/localization/status', self.on_status, status_qos)
        for kind, topic in self.raw.items():
            self.create_subscription(Odometry, topic['topic'],
                                     lambda msg, key=kind: self.on_raw(key, msg),
                                     qos_profile_sensor_data)
        self.create_subscription(
            Odometry, self.optimized_adapter_output['topic'],
            self.on_optimized_adapter_output,
            QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE))

    def elapsed(self):
        return time.monotonic() - self.started

    def clock_rate(self):
        if self.clock_first is None or self.clock_latest is None or self.clock_latest_wall is None:
            return None
        wall_delta = self.clock_latest_wall - self.clock_first[1]
        if wall_delta <= 0:
            return None
        return (self.clock_latest[0] - self.clock_first[0]) * 1e-9 / wall_delta

    def source_clock_now(self):
        if self.hardware_mode:
            stamp = int(self.get_clock().now().nanoseconds)
            now = time.monotonic()
            self.clock_count += 1
            if self.clock_first is None:
                self.clock_first = (stamp, now)
            self.clock_latest = (stamp, now)
            self.clock_latest_wall = now
            return stamp
        return self.clock_latest[0] if self.clock_latest is not None else None

    def on_clock(self, msg):
        now = time.monotonic()
        stamp = stamp_ns(msg.clock)
        self.clock_count += 1
        if self.clock_first is None:
            self.clock_first = (stamp, now)
        self.clock_latest = (stamp, now)
        self.clock_latest_wall = now

    def on_raw(self, kind, msg):
        row = self.raw[kind]
        now = time.monotonic()
        stamp = stamp_ns(msg.header.stamp)
        clock_ns = self.source_clock_now()
        row['count'] += 1
        if len(row['samples']) < 100_000:
            sample = {
                'stamp_ns': stamp,
                'receipt_wall_elapsed_s': round(now - self.started, 6),
                'receipt_wall_epoch_s': round(time.time(), 6),
                'clock_ns_at_receipt': clock_ns,
                'source_age_at_receipt_ms': (
                    round((clock_ns - stamp) / 1e6, 3) if clock_ns is not None else None),
                'frame_id': msg.header.frame_id,
            }
            if isinstance(msg, Odometry):
                p = msg.pose.pose.position
                q = msg.pose.pose.orientation
                sample['position_m'] = [p.x, p.y, p.z]
                sample['orientation_xyzw'] = [q.x, q.y, q.z, q.w]
            row['samples'].append(sample)

    def on_optimized_adapter_output(self, msg):
        stream = self.optimized_adapter_output
        clock_ns = self.source_clock_now()
        stream['count'] += 1
        if len(stream['samples']) < 100_000:
            stream['samples'].append({
                'stamp_ns': stamp_ns(msg.header.stamp),
                'receipt_wall_elapsed_s': round(self.elapsed(), 6),
                'receipt_wall_epoch_s': round(time.time(), 6),
                'clock_ns_at_receipt': clock_ns,
                'source_age_at_receipt_ms': (round((clock_ns - stamp_ns(msg.header.stamp)) / 1e6, 3)
                                             if clock_ns is not None else None),
                'position_m': [msg.pose.pose.position.x, msg.pose.pose.position.y,
                               msg.pose.pose.position.z],
                'orientation_xyzw': [msg.pose.pose.orientation.x, msg.pose.pose.orientation.y,
                                     msg.pose.pose.orientation.z, msg.pose.pose.orientation.w],
            })

    def on_status(self, msg):
        now = time.monotonic()
        wall_elapsed = now - self.started
        clock_ns = self.source_clock_now()
        health_signature = (msg.state, msg.valid, msg.reason)
        record_health = (health_signature != self.last_status_health_signature
                         or wall_elapsed - self.last_status_record_wall >= 1.0)
        if record_health and len(self.status_receipts) < 100_000:
            self.status_receipts.append({
                'wall_elapsed_s': round(wall_elapsed, 6),
                'wall_epoch_s': round(time.time(), 6),
                'clock_stamp_ns': stamp_ns(msg.header.stamp),
                'source_stamp_ns': stamp_ns(msg.source_stamp),
                'epoch': msg.epoch,
                'state': msg.state,
                'valid': msg.valid,
                'reason': msg.reason,
                'accepted_optimized': msg.accepted_optimized,
                'accepted_propagated': msg.accepted_propagated,
            })
            self.last_status_health_signature = health_signature
            self.last_status_record_wall = wall_elapsed
        if health_signature == self.last_status_signature and not record_health:
            return
        row = {
            'wall_elapsed_s': round(wall_elapsed, 6),
            'wall_epoch_s': round(time.time(), 6),
            'state': msg.state,
            'valid': msg.valid,
            'reason': msg.reason,
            'source_age_at_status_ms': (
                round((clock_ns - stamp_ns(msg.source_stamp)) / 1e6, 3)
                if clock_ns is not None else None),
            'accepted_propagated_count': msg.accepted_propagated,
            'accepted_optimized_count': msg.accepted_optimized,
        }
        self.status_history.append(row)
        self.last_status_signature = health_signature

    def report(self, interrupted=False):
        def trajectory_summary(samples):
            poses = [row['position_m'] for row in samples if 'position_m' in row]
            if not poses:
                return None
            origin = poses[0]
            deltas = [[p[i] - origin[i] for i in range(3)] for p in poses]
            distance = [math.sqrt(sum(axis * axis for axis in delta)) for delta in deltas]
            end = deltas[-1]
            return {
                'first_position_m': origin,
                'last_position_m': poses[-1],
                'net_displacement_xyz_m': [round(value, 6) for value in end],
                'return_error_m': round(math.sqrt(sum(value * value for value in end)), 6),
                'max_excursion_from_start_m': round(max(distance), 6),
                'sample_count': len(poses),
            }

        stream_summary = {}
        for name, stream in self.raw.items():
            samples = stream['samples']
            source_ages = [sample['source_age_at_receipt_ms'] for sample in samples
                           if sample['source_age_at_receipt_ms'] is not None]
            source_stamps = [sample['stamp_ns'] for sample in samples]
            receipt_times = [sample['receipt_wall_elapsed_s'] for sample in samples]
            source_intervals_ms = [(b - a) / 1e6 for a, b in zip(source_stamps, source_stamps[1:])]
            receipt_intervals_ms = [(b - a) * 1000 for a, b in zip(receipt_times, receipt_times[1:])]
            split = max(1, len(source_ages) // 2)
            stream_summary[name] = {
                'topic': stream['topic'],
                'received_count': stream['count'],
                'recorded_count': len(samples),
                'first_stamp_ns': source_stamps[0] if source_stamps else None,
                'last_stamp_ns': source_stamps[-1] if source_stamps else None,
                'source_interval_ms': {
                    'median': round(statistics.median(source_intervals_ms), 3) if source_intervals_ms else None,
                    'p95': round(percentile(source_intervals_ms, 0.95), 3) if source_intervals_ms else None,
                    'max': round(max(source_intervals_ms), 3) if source_intervals_ms else None,
                },
                'receipt_interval_wall_ms': {
                    'median': round(statistics.median(receipt_intervals_ms), 3) if receipt_intervals_ms else None,
                    'p95': round(percentile(receipt_intervals_ms, 0.95), 3) if receipt_intervals_ms else None,
                    'max': round(max(receipt_intervals_ms), 3) if receipt_intervals_ms else None,
                },
                'source_age_at_probe_receipt_ms': {
                    'p95': round(percentile(source_ages, 0.95), 3) if source_ages else None,
                    'max': round(max(source_ages), 3) if source_ages else None,
                },
                'source_age_first_second_half_p95_ms': {
                    'first_half': round(percentile(source_ages[:split], 0.95), 3) if source_ages else None,
                    'second_half': round(percentile(source_ages[split:], 0.95), 3)
                    if len(source_ages) > split else None,
                },
                'trajectory': trajectory_summary(samples),
                'samples': samples,
            }
        for stream in (self.optimized_adapter_output,):
            samples = stream['samples']
            stamps = [row['stamp_ns'] for row in samples]
            receipts = [row['receipt_wall_elapsed_s'] for row in samples]
            ages = [row['source_age_at_receipt_ms'] for row in samples
                    if row.get('source_age_at_receipt_ms') is not None]
            stream['source_interval_ms'] = {
                'median': round(statistics.median((b-a)/1e6 for a,b in zip(stamps,stamps[1:])), 3)
                if len(stamps) > 1 else None,
                'p95': round(percentile([(b-a)/1e6 for a,b in zip(stamps,stamps[1:])], 0.95), 3)
                if len(stamps) > 1 else None,
                'max': round(max((b-a)/1e6 for a,b in zip(stamps,stamps[1:])), 3)
                if len(stamps) > 1 else None,
            }
            stream['receipt_interval_wall_ms'] = {
                'median': round(statistics.median((b-a)*1000 for a,b in zip(receipts,receipts[1:])), 3)
                if len(receipts) > 1 else None,
                'p95': round(percentile([(b-a)*1000 for a,b in zip(receipts,receipts[1:])], 0.95), 3)
                if len(receipts) > 1 else None,
                'max': round(max((b-a)*1000 for a,b in zip(receipts,receipts[1:])), 3)
                if len(receipts) > 1 else None,
            }
            stream['source_age_at_probe_receipt_ms'] = {
                'p95': round(percentile(ages, 0.95), 3) if ages else None,
                'max': round(max(ages), 3) if ages else None,
            }
            split = max(1, len(ages) // 2)
            stream['source_age_first_second_half_p95_ms'] = {
                'first_half': round(percentile(ages[:split], 0.95), 3) if ages else None,
                'second_half': round(percentile(ages[split:], 0.95), 3)
                if len(ages) > split else None,
            }
            stream['trajectory'] = trajectory_summary(samples)
        # Keep raw measurement paths small enough for review and transfer. The
        # full-rate samples above have already contributed to exact period, age,
        # and return-error summaries.
        for name, stream in stream_summary.items():
            samples = stream.pop('samples')
            if stream['trajectory'] is not None:
                stride = max(1, len(samples) // 1000)
                stream['trajectory_samples'] = samples[::stride]
                if samples and stream['trajectory_samples'][-1] is not samples[-1]:
                    stream['trajectory_samples'].append(samples[-1])
        for stream in (self.optimized_adapter_output,):
            samples = stream.pop('samples')
            stride = 1
            stream['trajectory_samples'] = samples[::stride]
            if samples and stream['trajectory_samples'][-1] is not samples[-1]:
                stream['trajectory_samples'].append(samples[-1])
        return {
            'scope': 'Read-only low-rate observation of raw and adapted optimized odometry plus 1 Hz localization status; no image, IMU, propagated-odometry, truth, control, or PX4 subscriptions',
            'epoch': self.session['epoch'],
            'namespace': self.session['namespace'],
            'wall_seconds': round(self.elapsed(), 3),
            'wall_start_epoch_s': round(self.started_wall_epoch_s, 6),
            'interrupted': interrupted,
            'clock': {
                'mode': 'system_ros_time' if self.hardware_mode else '/clock',
                'received_count': self.clock_count,
                'first_stamp_ns': self.clock_first[0] if self.clock_first else None,
                'last_stamp_ns': self.clock_latest[0] if self.clock_latest else None,
                'estimated_rate': round(self.clock_rate(), 4) if self.clock_rate() is not None else None,
            },
            'hardware_localization_freshness_policy': {
                'mode': (self.freshness_policy or {}).get('freshness', {}).get('mode', 'unbound_observation'),
                'policy_config': self.session.get('health_config'),
                'policy_sha256': self.freshness_policy_sha256,
            },
            'raw_streams': stream_summary,
            'optimized_adapter_output': self.optimized_adapter_output,
            'status_history': self.status_history,
            'status_receipts': self.status_receipts,
            'qualification': 'Observer data complements the adapter internal counters; it does not replace the session-bound admission gate.'
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-root', type=Path, required=True)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=45.0)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.seconds <= 0:
        raise ValueError('--seconds must be positive')
    session = json.loads(args.session.read_text())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    signal.signal(signal.SIGINT, signal.default_int_handler)
    if SignalHandlerOptions is None:
        rclpy.init()
    else:
        rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node = FreshnessProbe(args.project_root, session)
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    deadline = time.monotonic() + args.seconds
    interrupted = False
    try:
        while time.monotonic() < deadline and rclpy.ok():
            executor.spin_once(timeout_sec=0.05)
    except KeyboardInterrupt:
        interrupted = True
    finally:
        executor.shutdown(timeout_sec=2.0)
        report = node.report(interrupted)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    concise = dict(report)
    concise['raw_streams'] = {
        name: {key: value for key, value in row.items() if key != 'trajectory_samples'}
        for name, row in report['raw_streams'].items()
    }
    for name in ('optimized_adapter_output',):
        concise[name] = {key: value for key, value in report[name].items()
                         if key != 'trajectory_samples'}
    print(json.dumps(concise, indent=2))


if __name__ == '__main__':
    main()
