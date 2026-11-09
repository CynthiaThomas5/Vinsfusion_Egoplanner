#!/usr/bin/env python3
"""Read-only ROS IMU/VINS + existing MAVLink board-motion recorder.

Only wire transmission is TIMESYNC(0, host_system_ns), a clock query. No ROS
publishers, mode commands, EV, parameter writes or MAVLink shell are created.
Change phase.txt to label an operator motion; stop.txt ends this owned recorder.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import signal
import threading
import time

def timesync_pair(sent_system_ns, sent_mono_ns, received_mono_ns, fc_ns):
    rtt = received_mono_ns-sent_mono_ns
    if rtt < 0 or fc_ns <= 0:
        raise ValueError('Invalid MAVLink clock response')
    midpoint = sent_system_ns+rtt//2
    return {'rtt_ns': rtt, 'fc_hrt_ns': fc_ns,
            'host_midpoint_system_ns': midpoint, 'host_minus_fc_ns': midpoint-fc_ns}


def main():
    os.environ['MAVLINK20'] = '1'
    from pymavlink import mavutil
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import (qos_profile_sensor_data, QoSProfile, ReliabilityPolicy,
                           DurabilityPolicy)
    from nav_msgs.msg import Odometry
    from sensor_msgs.msg import Imu
    from rosidl_runtime_py.convert import message_to_ordereddict
    from uav_interfaces.msg import LocalizationStatus
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--device', required=True)
    parser.add_argument('--seconds', type=float, default=900.)
    parser.add_argument('--pose-only', action='store_true',
                        help='Record optimized pose/health/FC attitude; omit duplicate high-rate diagnostic streams')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    stop = threading.Event()
    lock = threading.Lock()
    counts = Counter()
    latest = {}
    phase = ['startup']
    raw = (args.output/'board.jsonl').open('w', buffering=1)

    def record(kind, data):
        row = {'kind': kind, 'phase': phase[0], 'system_ns': time.time_ns(),
               'monotonic_ns': time.monotonic_ns(), 'data': data}
        with lock:
            raw.write(json.dumps(row)+'\n')
            counts[kind] += 1
            latest[kind] = row

    link = mavutil.mavlink_connection(args.device, baud=115200,
                                      source_system=245, source_component=190)
    link.port.write_timeout = 2.
    heartbeat = link.wait_heartbeat(timeout=10)
    if (heartbeat is None or heartbeat.autopilot != 12 or heartbeat.base_mode & 128
            or heartbeat.get_srcSystem() != 1 or heartbeat.get_srcComponent() != 1):
        link.close(); raw.close()
        raise RuntimeError('Expected actual disarmed PX4 sysid/component 1/1')
    record('mavlink', heartbeat.to_dict())

    def mavlink_reader():
        pending = {}
        next_query = 0.
        try:
            while not stop.is_set():
                if time.monotonic() >= next_query:
                    sent_system, sent_mono = time.time_ns(), time.monotonic_ns()
                    pending[sent_system] = (sent_system, sent_mono)
                    link.mav.timesync_send(0, sent_system)
                    next_query = time.monotonic()+1.
                    pending = {k: v for k, v in pending.items()
                               if sent_mono-v[1] < 5_000_000_000}
                msg = link.recv_match(blocking=True, timeout=.03)
                if msg is None or msg.get_srcSystem() != 1 or msg.get_srcComponent() != 1:
                    continue
                kind = msg.get_type()
                selected = (('HEARTBEAT','ATTITUDE_QUATERNION','TIMESYNC','STATUSTEXT')
                            if args.pose_only else ('HEARTBEAT','ATTITUDE','ATTITUDE_QUATERNION',
                                'HIGHRES_IMU','LOCAL_POSITION_NED','TIMESYNC','STATUSTEXT'))
                if kind in selected:
                    record('mavlink', msg.to_dict())
                if kind == 'HEARTBEAT' and msg.base_mode & 128:
                    record('fatal', {'reason': 'unexpected_armed_state'}); stop.set()
                if kind == 'TIMESYNC' and msg.tc1 > 0 and msg.ts1 in pending:
                    sent_system, sent_mono = pending.pop(msg.ts1)
                    record('timesync_pair', timesync_pair(
                        sent_system, sent_mono, time.monotonic_ns(), msg.tc1))
        except Exception as exc:
            record('fatal', {'reason': str(exc)}); stop.set()

    rclpy.init()
    node = Node('hw08_board_readonly')

    def imu(msg):
        record('imu', {'stamp_ns': msg.header.stamp.sec*10**9+msg.header.stamp.nanosec,
            'frame': msg.header.frame_id,
            'gyro': [msg.angular_velocity.x, msg.angular_velocity.y, msg.angular_velocity.z],
            'accel': [msg.linear_acceleration.x, msg.linear_acceleration.y, msg.linear_acceleration.z]})

    last_propagated_stamp = [None]

    def odom(kind, msg):
        stamp = msg.header.stamp.sec*10**9+msg.header.stamp.nanosec
        # This is diagnostic storage decimation, not producer/control throttling.
        if kind == 'propagated':
            previous = last_propagated_stamp[0]
            if previous is not None and 0 <= stamp-previous < 20_000_000:
                return
            last_propagated_stamp[0] = stamp
        p, q, v, w = (msg.pose.pose.position, msg.pose.pose.orientation,
                       msg.twist.twist.linear, msg.twist.twist.angular)
        record(kind, {'stamp_ns': stamp,
            'frame': msg.header.frame_id, 'child_frame': msg.child_frame_id,
            'p': [p.x,p.y,p.z], 'q_xyzw': [q.x,q.y,q.z,q.w],
            'v_body': [v.x,v.y,v.z], 'omega_body': [w.x,w.y,w.z]})

    subscriptions = []
    if not args.pose_only:
        subscriptions.append(node.create_subscription(Imu, '/sensors/d435i/imu', imu,
                                                       qos_profile_sensor_data))
    for kind, topic in (('optimized', '/localization/optimized_imu_odom'),
                        ('propagated', '/localization/imu_odom')):
        if args.pose_only and kind == 'propagated':
            continue
        subscriptions.append(node.create_subscription(Odometry, topic,
            lambda msg, kind=kind: odom(kind,msg), qos_profile_sensor_data))
    subscriptions.append(node.create_subscription(LocalizationStatus, '/localization/status',
        lambda msg: record('health', message_to_ordereddict(msg)),
        QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                   durability=DurabilityPolicy.TRANSIENT_LOCAL)))
    worker = threading.Thread(target=mavlink_reader, daemon=True)
    worker.start()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    start, next_summary, next_phase_check = time.monotonic(), 0., 0.
    try:
        while not stop.is_set() and time.monotonic()-start < args.seconds:
            if time.monotonic() >= next_phase_check:
                path = args.output/'phase.txt'
                if path.exists():
                    requested = path.read_text().strip()
                    if requested and requested != phase[0]:
                        phase[0] = requested; record('event', {'phase': requested})
                next_phase_check = time.monotonic()+.1
            if (args.output/'stop.txt').exists():
                break
            rclpy.spin_once(node, timeout_sec=.02)
            if time.monotonic() >= next_summary:
                with lock:
                    summary = {'duration_s': time.monotonic()-start, 'phase': phase[0],
                               'counts': dict(counts), 'latest': dict(latest)}
                temporary = args.output/'summary.tmp'
                temporary.write_text(json.dumps(summary,indent=2)+'\n')
                temporary.replace(args.output/'summary.json')
                next_summary = time.monotonic()+2.
        graph = {topic: len(node.get_publishers_info_by_topic(topic))
                 for topic, _ in node.get_topic_names_and_types() if topic.startswith('/fmu/in/')}
        (args.output/'graph.json').write_text(json.dumps({
            'fmu_input_publishers': graph, 'nodes': node.get_node_names_and_namespaces()},indent=2)+'\n')
    finally:
        stop.set()
        if hasattr(link.port, 'cancel_write'):
            link.port.cancel_write()
        worker.join(timeout=3)
        link.close(); node.destroy_node(); rclpy.shutdown(); raw.close()


if __name__ == '__main__':
    main()
