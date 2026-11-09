#!/usr/bin/env python3
"""Subscribe only: actual HW07 DDS decoding, timestamps, QoS and graph."""
import argparse
import json
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rosidl_runtime_py.convert import message_to_ordereddict
from px4_msgs.msg import (VehicleStatus, VehicleAttitude, VehicleLocalPosition,
                          TimesyncStatus, EstimatorStatusFlags)

TOPICS = {
    '/fmu/out/vehicle_status_v1': VehicleStatus,
    '/fmu/out/vehicle_attitude': VehicleAttitude,
    '/fmu/out/vehicle_local_position_v1': VehicleLocalPosition,
    '/fmu/out/timesync_status': TimesyncStatus,
    '/fmu/out/estimator_status_flags': EstimatorStatusFlags,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=60.)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    node = Node('hw07_readonly_observer')
    records = {topic: [] for topic in TOPICS}
    raw = (args.output / 'dds.jsonl').open('w', buffering=1)

    def callback(topic, msg):
        row = {'topic': topic, 'monotonic_s': time.monotonic(),
               'system_ns': time.time_ns(), 'message': message_to_ordereddict(msg)}
        records[topic].append(row)
        raw.write(json.dumps(row) + '\n')

    subscriptions = [node.create_subscription(
        cls, topic, lambda msg, topic=topic: callback(topic, msg), qos_profile_sensor_data)
        for topic, cls in TOPICS.items()]
    start = time.monotonic()
    try:
        while time.monotonic() - start < args.seconds:
            rclpy.spin_once(node, timeout_sec=.1)
        result = {'duration_s': time.monotonic() - start,
                  'subscription_qos': 'BEST_EFFORT / VOLATILE / KEEP_LAST depth=5',
                  'topics': {}, 'graph': {}}
        for topic, rows in records.items():
            gaps = [b['monotonic_s'] - a['monotonic_s'] for a, b in zip(rows, rows[1:])]
            stamps = [r['message']['timestamp'] for r in rows]
            ages = [(r['system_ns'] / 1000 - r['message']['timestamp']) / 1000 for r in rows]
            result['topics'][topic] = {
                'count': len(rows), 'max_gap_s': max(gaps, default=None),
                'timestamp_regressions': sum(b < a for a, b in zip(stamps, stamps[1:])),
                'unique_timestamps': len(set(stamps)),
                'age_ms_min': min(ages, default=None), 'age_ms_max': max(ages, default=None),
                'first': rows[0] if rows else None, 'last': rows[-1] if rows else None,
                'publishers': [str(info) for info in node.get_publishers_info_by_topic(topic)]}
        result['graph'] = dict(node.get_topic_names_and_types())
        result['fmu_input_publishers'] = {
            topic: [str(info) for info in node.get_publishers_info_by_topic(topic)]
            for topic in result['graph'] if topic.startswith('/fmu/in/')}
        result['nodes'] = node.get_node_names_and_namespaces()
        (args.output / 'dds-summary.json').write_text(json.dumps(result, indent=2) + '\n')
    finally:
        raw.close()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
