#!/usr/bin/env python3
"""Observe VINS propagated-odometry freshness beside the localization health gate."""
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
from rclpy.qos import (DurabilityPolicy, QoSProfile, ReliabilityPolicy,
                       qos_profile_sensor_data)
from rclpy.signals import SignalHandlerOptions
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import Imu
from uav_interfaces.msg import LocalizationStatus


def stamp_ns(stamp):
    return stamp.sec * 1_000_000_000 + stamp.nanosec


def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(fraction * len(ordered)) - 1)]


class FreshnessProbe(Node):
    def __init__(self, project_root, session):
        super().__init__('localization_freshness_probe')
        self.started = time.monotonic()
        self.started_wall_epoch_s = time.time()
        self.session = session
        policy = json.loads((Path(project_root) / 'config/components/localization/health.json').read_text())
        self.max_source_age_s = policy['max_source_age_s']['propagated']
        self.max_receipt_age_s = policy['max_receipt_age_s']['propagated']
        self.clock_count = 0
        self.clock_first = None
        self.clock_latest = None
        self.clock_latest_wall = None
        self.raw = {
            'd435i_imu_input': {'topic': '/sensors/d435i/imu', 'count': 0, 'samples': []},
            'optimized': {'topic': session['namespace'] + '/odometry', 'count': 0, 'samples': []},
            'propagated': {'topic': session['namespace'] + '/imu_propagate', 'count': 0, 'samples': []},
        }
        self.adapter_output = {
            'count': 0, 'last_stamp_ns': None, 'last_receipt_wall_s': None,
            'samples': [],
        }
        self.optimized_adapter_output = {
            'topic': '/localization/optimized_imu_odom', 'count': 0, 'samples': []}
        self.status_history = []
        self.status_receipts = []
        self.last_status_signature = None

        status_qos = QoSProfile(
            depth=10, reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(Clock, '/clock', self.on_clock,
                                 QoSProfile(depth=20, reliability=ReliabilityPolicy.BEST_EFFORT))
        self.create_subscription(LocalizationStatus, '/localization/status', self.on_status, status_qos)
        for kind, topic in self.raw.items():
            msg_type = Imu if kind == 'd435i_imu_input' else Odometry
            self.create_subscription(msg_type, topic['topic'],
                                     lambda msg, key=kind: self.on_raw(key, msg),
                                     qos_profile_sensor_data)
        self.create_subscription(Odometry, '/localization/imu_odom', self.on_adapter_output,
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
        clock_ns = self.clock_latest[0] if self.clock_latest is not None else None
        row['count'] += 1
        if len(row['samples']) < 100_000:
            row['samples'].append({
                'stamp_ns': stamp,
                'receipt_wall_elapsed_s': round(now - self.started, 6),
                'receipt_wall_epoch_s': round(time.time(), 6),
                'clock_ns_at_receipt': clock_ns,
                'source_age_at_receipt_ms': (
                    round((clock_ns - stamp) / 1e6, 3) if clock_ns is not None else None),
            })

    def on_adapter_output(self, msg):
        now = time.monotonic()
        wall_elapsed = now - self.started
        stamp = stamp_ns(msg.header.stamp)
        self.adapter_output['count'] += 1
        self.adapter_output['last_stamp_ns'] = stamp
        self.adapter_output['last_receipt_wall_s'] = round(wall_elapsed, 6)
        if len(self.adapter_output['samples']) < 100_000:
            self.adapter_output['samples'].append({
                'stamp_ns': stamp,
                'receipt_wall_elapsed_s': round(wall_elapsed, 6),
                'receipt_wall_epoch_s': round(time.time(), 6),
                'clock_ns_at_receipt': self.clock_latest[0] if self.clock_latest else None,
            })

    def on_optimized_adapter_output(self, msg):
        stream = self.optimized_adapter_output
        stream['count'] += 1
        if len(stream['samples']) < 100_000:
            stream['samples'].append({
                'stamp_ns': stamp_ns(msg.header.stamp),
                'receipt_wall_elapsed_s': round(self.elapsed(), 6),
                'receipt_wall_epoch_s': round(time.time(), 6),
                'clock_ns_at_receipt': self.clock_latest[0] if self.clock_latest else None,
            })

    def on_status(self, msg):
        now = time.monotonic()
        wall_elapsed = now - self.started
        signature = (msg.state, msg.valid, msg.reason,
                     msg.accepted_optimized, msg.accepted_propagated)
        if len(self.status_receipts) < 100_000:
            self.status_receipts.append({
                'wall_elapsed_s': round(wall_elapsed, 6),
                'wall_epoch_s': round(time.time(), 6),
                'clock_stamp_ns': stamp_ns(msg.header.stamp),
                'source_stamp_ns': stamp_ns(msg.source_stamp),
                'state': msg.state,
                'valid': msg.valid,
                'reason': msg.reason,
                'accepted_optimized': msg.accepted_optimized,
                'accepted_propagated': msg.accepted_propagated,
            })
        if signature == self.last_status_signature:
            return
        clock_ns = stamp_ns(msg.header.stamp)
        raw_last = self.raw['propagated']['samples'][-1] if self.raw['propagated']['samples'] else None
        receipt_age_s = None
        raw_source_age_s = None
        if raw_last is not None:
            receipt_age_s = now - self.started - raw_last['receipt_wall_elapsed_s']
            raw_source_age_s = (clock_ns - raw_last['stamp_ns']) * 1e-9
        rate = self.clock_rate()
        row = {
            'wall_elapsed_s': round(now - self.started, 6),
            'wall_epoch_s': round(time.time(), 6),
            'state': msg.state,
            'valid': msg.valid,
            'reason': msg.reason,
            'clock_stamp_ns': clock_ns,
            'adapter_last_published_propagated_stamp_ns': stamp_ns(msg.source_stamp),
            'adapter_output_age_at_status_s': round(
                (clock_ns - stamp_ns(msg.source_stamp)) * 1e-9, 6),
            'accepted_propagated_count': msg.accepted_propagated,
            'observed_raw_propagated_last_stamp_ns': raw_last['stamp_ns'] if raw_last else None,
            'observed_raw_propagated_source_age_s': (
                round(raw_source_age_s, 6) if raw_source_age_s is not None else None),
            'observed_raw_propagated_receipt_age_wall_s': (
                round(receipt_age_s, 6) if receipt_age_s is not None else None),
            'observed_raw_propagated_receipt_age_clock_s': (
                round(receipt_age_s * rate, 6)
                if receipt_age_s is not None and rate is not None else None),
            'estimated_clock_rate': round(rate, 4) if rate is not None else None,
            'source_age_limit_s': self.max_source_age_s,
            'receipt_age_limit_clock_s': self.max_receipt_age_s,
        }
        if msg.reason == 'propagated_stale':
            row['probe_guard_estimate'] = {
                'source_age_exceeded': (raw_source_age_s is not None
                                        and raw_source_age_s > self.max_source_age_s),
                'receipt_age_exceeded': (receipt_age_s is not None and rate is not None
                                         and receipt_age_s * rate > self.max_receipt_age_s),
                'note': 'Probe subscriber timing is an estimate; the adapter may receive DDS samples at a different instant.'
            }
        self.status_history.append(row)
        self.last_status_signature = signature

    def report(self, interrupted=False):
        stream_summary = {}
        for name, stream in self.raw.items():
            samples = stream['samples']
            source_ages = [sample['source_age_at_receipt_ms'] for sample in samples
                           if sample['source_age_at_receipt_ms'] is not None]
            source_stamps = [sample['stamp_ns'] for sample in samples]
            receipt_times = [sample['receipt_wall_elapsed_s'] for sample in samples]
            source_intervals_ms = [(b - a) / 1e6 for a, b in zip(source_stamps, source_stamps[1:])]
            receipt_intervals_ms = [(b - a) * 1000 for a, b in zip(receipt_times, receipt_times[1:])]
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
                'samples': samples,
            }
        return {
            'scope': 'Read-only freshness observation of D435i IMU input, raw VINS odometry, and adapted propagated odometry; no truth topics, control, or PX4',
            'epoch': self.session['epoch'],
            'namespace': self.session['namespace'],
            'wall_seconds': round(self.elapsed(), 3),
            'wall_start_epoch_s': round(self.started_wall_epoch_s, 6),
            'interrupted': interrupted,
            'clock': {
                'received_count': self.clock_count,
                'first_stamp_ns': self.clock_first[0] if self.clock_first else None,
                'last_stamp_ns': self.clock_latest[0] if self.clock_latest else None,
                'estimated_rate': round(self.clock_rate(), 4) if self.clock_rate() is not None else None,
            },
            'propagated_freshness_guard': {
                'max_source_age_s': self.max_source_age_s,
                'max_receipt_age_clock_s': self.max_receipt_age_s,
            },
            'raw_streams': stream_summary,
            'adapter_output': self.adapter_output,
            'optimized_adapter_output': self.optimized_adapter_output,
            'status_history': self.status_history,
            'status_receipts': self.status_receipts,
            'qualification': 'Diagnostic subscriber measurements; a guard estimate does not prove the adapter observed the same DDS timing.'
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
    print(json.dumps({key: value for key, value in report.items() if key != 'raw_streams'}, indent=2))


if __name__ == '__main__':
    main()
