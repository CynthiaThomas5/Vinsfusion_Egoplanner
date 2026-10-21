#!/usr/bin/env python3
"""Read-only recording of raw VINS outputs, original stamps and internal telemetry."""
import argparse
import json
import math
from pathlib import Path
import time

import rclpy
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu
from std_msgs.msg import String


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=30)
    parser.add_argument('--truth-topic', choices=['/debug_truth/base_odometry'])
    parser.add_argument('--imu-topic', choices=['/sensors/d435i/imu'])
    args = parser.parse_args()
    if bool(args.truth_topic) != bool(args.imu_topic):
        parser.error('--truth-topic and --imu-topic must be supplied together for diagnostic evaluation')
    manifest = json.loads(args.session.read_text())
    rclpy.init()
    node = rclpy.create_node('raw_vins_readonly_probe')
    rows, telemetry, parse_errors = {'optimized':[], 'propagated':[]}, [], []
    truth, imu = [], []
    def odom(name, msg):
        p,q,v = msg.pose.pose.position, msg.pose.pose.orientation, msg.twist.twist.linear
        rows[name].append({'stamp_ns':msg.header.stamp.sec*1000000000+msg.header.stamp.nanosec,
                           'receipt_wall_ns':time.time_ns(), 'frame':msg.header.frame_id, 'child_frame':msg.child_frame_id,
                           'position':[p.x,p.y,p.z], 'quaternion':[q.x,q.y,q.z,q.w], 'velocity':[v.x,v.y,v.z]})
    def health(msg):
        try:
            telemetry.append(json.loads(msg.data))
        except ValueError as exc:
            parse_errors.append(str(exc))
    def truth_odometry(msg):
        p, q = msg.pose.pose.position, msg.pose.pose.orientation
        stamp_ns = msg.header.stamp.sec*1_000_000_000+msg.header.stamp.nanosec
        truth.append({'stamp':stamp_ns*1e-9, 'stamp_ns':stamp_ns,
                      'receipt_wall_ns':time.time_ns(), 'frame':msg.header.frame_id,
                      'child_frame':msg.child_frame_id, 'position':[p.x,p.y,p.z],
                      'quaternion':[q.x,q.y,q.z,q.w]})
    def imu_sample(msg):
        stamp_ns = msg.header.stamp.sec*1_000_000_000+msg.header.stamp.nanosec
        imu.append({'stamp':stamp_ns*1e-9, 'stamp_ns':stamp_ns,
                    'receipt_wall_ns':time.time_ns(),
                    'acceleration':[msg.linear_acceleration.x,
                                    msg.linear_acceleration.y,
                                    msg.linear_acceleration.z],
                    'gyro':[msg.angular_velocity.x,
                            msg.angular_velocity.y,
                            msg.angular_velocity.z]})
    namespace = manifest['namespace']
    subscriptions = [node.create_subscription(Odometry, namespace+'/'+topic, lambda m,n=name:odom(n,m), qos_profile_sensor_data)
                     for name,topic in [('optimized','odometry'),('propagated','imu_propagate')]]
    subscriptions.append(node.create_subscription(String, namespace+'/estimator_telemetry', health, qos_profile_sensor_data))
    if args.truth_topic:
        subscriptions.extend([
            node.create_subscription(Odometry, args.truth_topic, truth_odometry, qos_profile_sensor_data),
            node.create_subscription(Imu, args.imu_topic, imu_sample, qos_profile_sensor_data),
        ])
    graph = {}
    discovered_nodes, discovered_topics = set(), set()
    target_topics = [namespace+'/'+name for name in ['odometry', 'imu_propagate', 'estimator_telemetry']]
    publisher_endpoints = {topic: [] for topic in target_topics}
    start = time.monotonic()
    while time.monotonic()-start < args.seconds:
        rclpy.spin_once(node, timeout_sec=.1)
        discovered_nodes.update(node.get_node_names_and_namespaces())
        discovered_topics.update(name for name, _ in node.get_topic_names_and_types())
        for topic in target_topics:
            publisher_endpoints[topic] = [
                {'node_name': endpoint.node_name, 'node_namespace': endpoint.node_namespace,
                 'topic_type': endpoint.topic_type, 'endpoint_gid': bytes(endpoint.endpoint_gid).hex()}
                for endpoint in node.get_publishers_info_by_topic(topic)
            ]
        if not graph and ('vins_estimator', namespace) in node.get_node_names_and_namespaces():
            graph = {'subscriptions': node.get_subscriber_names_and_types_by_node('vins_estimator', namespace),
                     'publishers': node.get_publisher_names_and_types_by_node('vins_estimator', namespace)}
    summary = {'scope':('Raw VINS only; no localization health gate, trajectory accuracy or flight qualification'
                        if not args.truth_topic else
                        'Read-only diagnostic capture; Gazebo truth is an evaluator input only, never a navigation or control input'),
               'epoch':manifest['epoch'], 'namespace':namespace, 'wall_seconds':time.monotonic()-start,
               'diagnostic_truth_enabled':bool(args.truth_topic),
               'truth_topic':args.truth_topic, 'imu_topic':args.imu_topic,
               'discovered_nodes':[{'name':name,'namespace':ns} for name,ns in sorted(discovered_nodes)],
               'discovered_topics':sorted(discovered_topics), 'expected_topic_publishers':publisher_endpoints,
               'node_graph':graph, 'counts':{key:len(value) for key,value in rows.items()}, 'telemetry_count':len(telemetry),
               'truth_sample_count':len(truth), 'imu_sample_count':len(imu),
               'initialized_telemetry_count':sum(t.get('initialized') is True for t in telemetry), 'parse_errors':parse_errors}
    summary['all_output_finite'] = all(math.isfinite(x) for values in rows.values() for row in values for key in ['position','quaternion','velocity'] for x in row[key])
    summary['source_rates_hz'] = {name:(len(values)-1)*1e9/(values[-1]['stamp_ns']-values[0]['stamp_ns']) for name,values in rows.items() if len(values)>1 and values[-1]['stamp_ns']>values[0]['stamp_ns']}
    summary['max_position_norm_m'] = max((math.sqrt(sum(v*v for v in row['position'])) for row in rows['optimized']), default=None)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/'raw-odometry.json').write_text(json.dumps(rows, indent=2)+'\n')
    (args.output/'telemetry.json').write_text(json.dumps(telemetry, indent=2)+'\n')
    if args.truth_topic:
        (args.output/'truth-motion.json').write_text(json.dumps({
            'scope':summary['scope'], 'truth_topic':args.truth_topic,
            'imu_topic':args.imu_topic, 'truth':truth, 'imu':imu,
            'wall_seconds':summary['wall_seconds']}, indent=2)+'\n')
    (args.output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary))
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
