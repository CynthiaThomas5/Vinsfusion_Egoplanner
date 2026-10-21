#!/usr/bin/env python3
"""Read-only timing probe for raw VINS inputs, telemetry, odometry and health."""

import argparse
import json
import math
from pathlib import Path
import time

import rclpy
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, qos_profile_sensor_data
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import Image, Imu
from std_msgs.msg import String
from uav_interfaces.msg import LocalizationStatus


def _percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round((len(ordered) - 1) * fraction))]


def _header_stamp_ns(msg):
    return int(msg.header.stamp.sec) * 1_000_000_000 + int(msg.header.stamp.nanosec)


class StreamProbe:
    def __init__(self, session_manifest):
        self.node = rclpy.create_node('vio_stream_freshness_probe')
        session = json.loads(Path(session_manifest).read_text(encoding='utf-8'))
        namespace = session['namespace'].rstrip('/')
        self.started = time.monotonic()
        self.clock_ns = None
        self.stats = {}
        self.transitions = []
        self.last_localization = None
        self.subscriptions = []
        status_qos = QoSProfile(
            depth=10,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL)
        subscriptions = (
            ('/clock', Clock, self.on_clock, qos_profile_sensor_data),
            ('/sensors/d435i/infra1/image_rect', Image, self.on_header, qos_profile_sensor_data),
            ('/sensors/d435i/infra2/image_rect', Image, self.on_header, qos_profile_sensor_data),
            ('/sensors/d435i/imu', Imu, self.on_header, qos_profile_sensor_data),
            (namespace + '/estimator_telemetry', String, self.on_telemetry, qos_profile_sensor_data),
            (namespace + '/odometry', Odometry, self.on_header, qos_profile_sensor_data),
            (namespace + '/imu_propagate', Odometry, self.on_header, qos_profile_sensor_data),
            ('/localization/status', LocalizationStatus, self.on_localization, status_qos),
        )
        self.topics = [item[0] for item in subscriptions]
        for topic, msg_type, callback, qos in subscriptions:
            self.subscriptions.append(self.node.create_subscription(
                msg_type, topic, lambda msg, t=topic, cb=callback: cb(t, msg), qos))

    def record(self, topic, source_ns=None, extra=None):
        now = time.monotonic()
        wall_elapsed = now - self.started
        stat = self.stats.setdefault(topic, {
            'count': 0, 'first_receipt_wall_s': wall_elapsed,
            'last_receipt_wall_s': wall_elapsed, 'first_source_stamp_ns': source_ns,
            'last_source_stamp_ns': source_ns, 'max_receipt_gap_s': 0.0,
            'max_source_gap_s': 0.0, 'max_clock_age_s': None,
            'receipt_intervals_s': [], 'source_intervals_s': [], 'age_extremes': [],
            'gap_events': [],
        })
        previous_receipt = stat['last_receipt_wall_s']
        previous_source = stat['last_source_stamp_ns']
        receipt_gap = wall_elapsed - previous_receipt
        stat['count'] += 1
        stat['last_receipt_wall_s'] = wall_elapsed
        stat['max_receipt_gap_s'] = max(stat['max_receipt_gap_s'], receipt_gap)
        if stat['count'] > 1 and topic != '/clock':
            stat['receipt_intervals_s'].append(receipt_gap)
        source_gap = None
        if source_ns is not None:
            if stat['first_source_stamp_ns'] is None:
                stat['first_source_stamp_ns'] = source_ns
            stat['last_source_stamp_ns'] = source_ns
            if previous_source is not None:
                source_gap = (source_ns - previous_source) * 1e-9
                stat['max_source_gap_s'] = max(stat['max_source_gap_s'], source_gap)
                if topic != '/clock':
                    stat['source_intervals_s'].append(source_gap)
        age = ((self.clock_ns - source_ns) * 1e-9
               if self.clock_ns is not None and source_ns is not None else None)
        if age is not None:
            if stat['max_clock_age_s'] is None or age > stat['max_clock_age_s']:
                stat['max_clock_age_s'] = age
            if len(stat['age_extremes']) < 20 and abs(age) > 0.15:
                stat['age_extremes'].append({'wall_elapsed_s': wall_elapsed,
                                             'clock_age_s': age,
                                             'source_stamp_ns': source_ns})
        if len(stat['gap_events']) < 40 and (receipt_gap > 0.25 or
                                             (source_gap is not None and source_gap > 0.25)):
            event = {'wall_elapsed_s': wall_elapsed,
                     'receipt_gap_s': receipt_gap,
                     'source_gap_s': source_gap,
                     'source_stamp_ns': source_ns,
                     'clock_age_s': age}
            if extra:
                event.update(extra)
            stat['gap_events'].append(event)

    def on_clock(self, topic, msg):
        self.clock_ns = int(msg.clock.sec) * 1_000_000_000 + int(msg.clock.nanosec)
        self.record(topic, self.clock_ns)

    def on_header(self, topic, msg):
        self.record(topic, _header_stamp_ns(msg))

    def on_telemetry(self, topic, msg):
        try:
            metrics = json.loads(msg.data)
            stamp = int(metrics['stamp_ns'])
            features = int(metrics.get('input_features', -1))
        except (ValueError, TypeError, KeyError):
            stamp, features = None, None
        self.record(topic, stamp, {'input_features': features})

    def on_localization(self, topic, msg):
        transition = (int(msg.state), bool(msg.valid), str(msg.reason))
        if transition != self.last_localization:
            self.transitions.append({
                'wall_elapsed_s': time.monotonic() - self.started,
                'state': transition[0], 'valid': transition[1], 'reason': transition[2],
                'good_pairs': int(msg.good_pairs),
                'source_stamp_ns': _header_stamp_ns(msg) if msg.source_stamp.sec or msg.source_stamp.nanosec else 0,
            })
            self.last_localization = transition
        self.record(topic, _header_stamp_ns(msg))

    def result(self, duration_s):
        wall_elapsed = time.monotonic() - self.started
        topics = {}
        for name, raw in self.stats.items():
            topics[name] = {key: value for key, value in raw.items()
                            if key not in ('receipt_intervals_s', 'source_intervals_s')}
            topics[name]['receipt_gap_p50_s'] = _percentile(raw['receipt_intervals_s'], 0.50)
            topics[name]['receipt_gap_p95_s'] = _percentile(raw['receipt_intervals_s'], 0.95)
            topics[name]['source_gap_p50_s'] = _percentile(raw['source_intervals_s'], 0.50)
            topics[name]['source_gap_p95_s'] = _percentile(raw['source_intervals_s'], 0.95)
            topics[name]['last_receipt_age_s'] = wall_elapsed - raw['last_receipt_wall_s']
        return {
            'read_only': True,
            'publishes': [],
            'requested_duration_wall_s': duration_s,
            'observed_duration_wall_s': wall_elapsed,
            'clock_stamp_ns': self.clock_ns,
            'localization_transitions': self.transitions,
            'topics': topics,
            'qualification': 'Diagnostic timing only; does not override localization freshness gates or prove estimator accuracy.',
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--session-manifest', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=45.0)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or args.seconds <= 0:
        raise ValueError('--seconds must be positive and finite')
    rclpy.init()
    probe = StreamProbe(args.session_manifest)
    try:
        deadline = time.monotonic() + args.seconds
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(probe.node, timeout_sec=0.02)
    finally:
        payload = json.dumps(probe.result(args.seconds), indent=2, sort_keys=True) + '\n'
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding='utf-8')
        probe.node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    print(payload, end='')


if __name__ == '__main__':
    main()
