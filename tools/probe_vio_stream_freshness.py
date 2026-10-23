#!/usr/bin/env python3
"""Read-only timing probe for raw VINS inputs, telemetry, odometry and health."""

import argparse
from collections import deque
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


def _observation_stop_state(now, deadline, end_marker, marker_seen, post_end_s):
    """Return (marker_seen, stop_reason) for the bounded observation loop."""
    if end_marker is not None and end_marker.exists():
        if marker_seen is None:
            marker_seen = now
        if now - marker_seen >= post_end_s:
            return marker_seen, 'end_marker_tail_complete'
    if now >= deadline:
        reason = 'max_duration_end_marker_missing' if end_marker is not None else 'max_duration'
        return marker_seen, reason
    return marker_seen, None


def _spin_timeout(now, deadline, marker_seen, post_end_s):
    timeout = min(0.02, max(0.0, deadline - now))
    if marker_seen is not None:
        timeout = min(timeout, max(0.0, post_end_s - (now - marker_seen)))
    return timeout


class StreamProbe:
    def __init__(self, session_manifest, events_output=None):
        self.node = rclpy.create_node('vio_stream_freshness_probe')
        session = json.loads(Path(session_manifest).read_text(encoding='utf-8'))
        namespace = session['namespace'].rstrip('/')
        self.telemetry_topic = namespace + '/estimator_telemetry'
        self.started = time.monotonic()
        self.clock_ns = None
        self.stats = {}
        self.transitions = []
        self.last_localization = None
        self.recent_sources = {}
        self.event_topics = set()
        self.events = None
        self.event_count = 0
        if events_output is not None:
            event_path = Path(events_output)
            event_path.parent.mkdir(parents=True, exist_ok=True)
            self.events = event_path.open('x', encoding='utf-8', buffering=1)
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
            (self.telemetry_topic, String, self.on_telemetry, qos_profile_sensor_data),
            (namespace + '/odometry', Odometry, self.on_header, qos_profile_sensor_data),
            (namespace + '/imu_propagate', Odometry, self.on_header, qos_profile_sensor_data),
            ('/localization/optimized_imu_odom', Odometry, self.on_header, qos_profile_sensor_data),
            ('/localization/imu_odom', Odometry, self.on_header, qos_profile_sensor_data),
            ('/localization/status', LocalizationStatus, self.on_localization, status_qos),
        )
        self.topics = [item[0] for item in subscriptions]
        if self.events is not None:
            self.event_topics = {
                self.telemetry_topic, namespace + '/odometry',
                '/localization/optimized_imu_odom', '/localization/status',
            }
        for topic, msg_type, callback, qos in subscriptions:
            self.subscriptions.append(self.node.create_subscription(
                msg_type, topic, lambda msg, t=topic, cb=callback: cb(t, msg), qos))

    def record(self, topic, source_ns=None, extra=None):
        now = time.monotonic()
        receipt_monotonic_ns = time.monotonic_ns()
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
        if source_ns is not None:
            recent = self.recent_sources.setdefault(topic, deque(maxlen=16))
            recent.append({'source_stamp_ns': source_ns,
                           'receive_monotonic_ns': receipt_monotonic_ns,
                           'clock_stamp_ns_at_receipt': self.clock_ns})
        if self.events is not None and topic in self.event_topics:
            event = {
                'topic': topic,
                'source_stamp_ns': source_ns,
                'receive_monotonic_ns': receipt_monotonic_ns,
                'wall_elapsed_s': wall_elapsed,
                'clock_stamp_ns_at_receipt': self.clock_ns,
                'clock_age_s_at_receipt': age,
            }
            if extra:
                event.update(extra)
            if topic.endswith('/estimator_telemetry'):
                # Keep the latest sample of each input at telemetry receipt.
                # The summary retains interval maxima/percentiles; duplicating
                # 16 source stamps in every telemetry event adds substantial
                # JSON and callback overhead without improving trigger-frame
                # association.
                event['latest_input_stamps'] = {}
                for name in ('/sensors/d435i/infra1/image_rect',
                             '/sensors/d435i/infra2/image_rect',
                             '/sensors/d435i/imu'):
                    samples = self.recent_sources.get(name, ())
                    event['latest_input_stamps'][name] = (
                        dict(samples[-1]) if samples else None)
            self.events.write(json.dumps(event, separators=(',', ':'), sort_keys=True) + '\n')
            self.event_count += 1
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
        extra = {}
        if isinstance(msg, Image):
            extra = {'frame_id': msg.header.frame_id, 'encoding': msg.encoding,
                     'width': int(msg.width), 'height': int(msg.height)}
        elif isinstance(msg, Imu):
            extra = {'frame_id': msg.header.frame_id}
        elif isinstance(msg, Odometry):
            extra = {'frame_id': msg.header.frame_id, 'child_frame_id': msg.child_frame_id}
        self.record(topic, _header_stamp_ns(msg), extra)

    def on_telemetry(self, topic, msg):
        try:
            metrics = json.loads(msg.data)
            stamp = int(metrics['stamp_ns'])
            features = int(metrics.get('input_features', -1))
        except (ValueError, TypeError, KeyError):
            stamp, features, metrics = None, None, {'raw': msg.data}
        self.record(topic, stamp, {'input_features': features, 'telemetry': metrics})

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
        status_header_stamp_ns = _header_stamp_ns(msg)
        propagated_source_stamp_ns = (
            int(msg.source_stamp.sec) * 1_000_000_000 + int(msg.source_stamp.nanosec))
        telemetry_samples = self.recent_sources.get(self.telemetry_topic)
        latest_telemetry = dict(telemetry_samples[-1]) if telemetry_samples else None
        self.record(topic, status_header_stamp_ns, {
            'epoch': str(msg.epoch), 'state': int(msg.state), 'valid': bool(msg.valid),
            'reason': str(msg.reason), 'good_pairs': int(msg.good_pairs),
            'normalized_cost': float(msg.normalized_cost),
            'status_header_stamp_ns': status_header_stamp_ns,
            'propagated_source_stamp_ns': propagated_source_stamp_ns,
            'latest_telemetry_at_callback': latest_telemetry,
            'accepted_optimized': int(msg.accepted_optimized),
            'accepted_propagated': int(msg.accepted_propagated),
        })

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
            'event_count': self.event_count,
            'qualification': 'Diagnostic timing only; does not override localization freshness gates or prove estimator accuracy.',
        }

    def close(self):
        if self.events is not None:
            self.events.flush()
            self.events.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--session-manifest', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=45.0)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--events-output', type=Path)
    parser.add_argument('--end-marker', type=Path,
                        help='Keep observing until this file exists, then capture a bounded tail.')
    parser.add_argument('--post-end-s', type=float, default=2.0)
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or args.seconds <= 0:
        raise ValueError('--seconds must be positive and finite')
    if not math.isfinite(args.post_end_s) or not 0 <= args.post_end_s <= 10:
        raise ValueError('--post-end-s must be finite and in [0,10]')
    rclpy.init()
    probe = StreamProbe(args.session_manifest, args.events_output)
    started = time.monotonic()
    deadline = started + args.seconds
    marker_seen = None
    stop_reason = 'max_duration'
    try:
        while rclpy.ok():
            now = time.monotonic()
            marker_seen, reason = _observation_stop_state(
                now, deadline, args.end_marker, marker_seen, args.post_end_s)
            if reason is not None:
                stop_reason = reason
                break
            rclpy.spin_once(probe.node, timeout_sec=_spin_timeout(
                now, deadline, marker_seen, args.post_end_s))
    finally:
        result = probe.result(time.monotonic() - started)
        result['stop_reason'] = stop_reason
        result['end_marker'] = str(args.end_marker) if args.end_marker else None
        result['end_marker_seen'] = marker_seen is not None
        result['post_end_observation_s'] = time.monotonic() - marker_seen if marker_seen is not None else None
        probe.close()
        payload = json.dumps(result, indent=2, sort_keys=True) + '\n'
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding='utf-8')
        probe.node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    print(payload, end='')


if __name__ == '__main__':
    main()
