#!/usr/bin/env python3
"""Read-only per-event EV/sync/fusion recording, with bounded source decoding."""
import argparse
import json
import math
from pathlib import Path
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.convert import message_to_ordereddict
from nav_msgs.msg import Odometry
from std_msgs.msg import String
from px4_msgs.msg import TimesyncStatus, VehicleStatus, EstimatorStatusFlags, VehicleOdometry, VehicleLocalPosition
from uav_interfaces.msg import LocalizationStatus


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--seconds', type=float, default=120.)
    a = p.parse_args()
    if not math.isfinite(a.seconds) or not 0 < a.seconds <= 600:
        p.error('seconds must be finite, positive and <=600')
    a.output.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    node = Node('hw10_sync_audit_readonly')
    counts, last, gaps, subs = {}, {}, {}, []
    started = time.monotonic()
    armed_seen = False
    with (a.output/'events.jsonl').open('w', buffering=1) as f:
        def record(kind, msg):
            nonlocal armed_seen
            now = time.monotonic()
            counts[kind] = counts.get(kind, 0)+1
            if kind in last: gaps[kind] = max(gaps.get(kind, 0), now-last[kind])
            last[kind] = now
            if kind == 'status' and msg.arming_state != VehicleStatus.ARMING_STATE_DISARMED:
                armed_seen = True
            value = json.loads(msg.data) if kind == 'detail' else message_to_ordereddict(msg)
            f.write(json.dumps(dict(kind=kind, monotonic_s=now, system_ns=time.time_ns(), message=value))+'\n')

        for kind, typ, topic in [
            ('sync', TimesyncStatus, '/fmu/out/timesync_status'),
            ('status', VehicleStatus, '/fmu/out/vehicle_status_v1'),
            ('flags', EstimatorStatusFlags, '/fmu/out/estimator_status_flags'),
            ('local', VehicleLocalPosition, '/fmu/out/vehicle_local_position_v1'),
            ('ev', VehicleOdometry, '/fmu/in/vehicle_visual_odometry'),
            ('health', LocalizationStatus, '/localization/status'),
            ('detail', String, '/px4_bridge/hardware_ev/detail')]:
            subs.append(node.create_subscription(typ, topic, lambda m,k=kind: record(k,m), qos_profile_sensor_data))
        source_last = [0.]

        def source(data):
            now = time.monotonic()
            if now-source_last[0] >= .04:
                source_last[0] = now
                record('source_sampled_25hz', deserialize_message(data, Odometry))

        subs.append(node.create_subscription(Odometry, '/localization/imu_odom', source, qos_profile_sensor_data, raw=True))
        (a.output/'ready').write_text('Subscriptions ready; observer publishes nothing\n')
        try:
            while time.monotonic()-started < a.seconds and not armed_seen:
                rclpy.spin_once(node, timeout_sec=.05)
        except KeyboardInterrupt:
            pass
        finally:
            inputs = {t:len(node.get_publishers_info_by_topic(t)) for t,_ in node.get_topic_names_and_types() if t.startswith('/fmu/in/')}
            result = dict(duration_s=time.monotonic()-started, counts=counts, max_gap_s=gaps,
                armed_seen=armed_seen, fmu_input_publishers=inputs,
                scope='DDS receipt observation; flags are sampled state, not per-measurement EKF fusion proof')
            (a.output/'summary.json').write_text(json.dumps(result, indent=2)+'\n')
            print(json.dumps(result))
            node.destroy_node()
            rclpy.shutdown()


if __name__ == '__main__':
    main()
