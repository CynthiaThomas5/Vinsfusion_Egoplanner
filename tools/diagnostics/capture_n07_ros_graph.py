#!/usr/bin/env python3
"""Read-only ROS graph audit for N07's sole PX4 control publisher."""
import json
from pathlib import Path
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from uav_interfaces.msg import Px4BridgeStatus
from n07_ros_graph_evidence import CONTROL_TOPICS, qualify_report


class GraphAudit(Node):
    def __init__(self):
        super().__init__('n07_readonly_ros_graph_audit')
        self.bridge_status = None
        self.create_subscription(
            Px4BridgeStatus, '/uav_px4_bridge/status', self.on_bridge_status,
            QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE))

    def on_bridge_status(self, msg):
        self.bridge_status = {
            'phase': msg.phase,
            'armed': bool(msg.armed),
            'landed': bool(msg.landed),
            'control_enabled': bool(msg.control_enabled),
        }

    @staticmethod
    def endpoint(info):
        gid = getattr(info, 'endpoint_gid', b'')
        try:
            gid = bytes(gid).hex()
        except (TypeError, ValueError):
            gid = str(gid)
        return {
            'node_name': info.node_name,
            'node_namespace': info.node_namespace,
            'topic_type': info.topic_type,
            'endpoint_gid': gid,
        }

    def snapshot(self, label):
        topic_types = dict(self.get_topic_names_and_types())
        publishers = {}
        subscribers = {}
        topics = sorted(set(topic_types) | set(CONTROL_TOPICS))
        for topic in topics:
            publishers[topic] = [
                self.endpoint(info) for info in self.get_publishers_info_by_topic(topic)]
            subscribers[topic] = [
                self.endpoint(info) for info in self.get_subscriptions_info_by_topic(topic)]
        nodes = sorted({
            f'{namespace.rstrip("/")}/{name}' if namespace != '/' else f'/{name}'
            for name, namespace in self.get_node_names_and_namespaces()
        })
        truth_topics = [topic for topic in topic_types
                        if 'truth' in topic.lower() or 'groundtruth' in topic.lower()]
        truth_nodes = [name for name in nodes
                       if 'truth' in name.lower() or 'ground_truth' in name.lower()]
        unique_control_publishers = all(
            len(publishers[topic]) == 1
            and publishers[topic][0]['node_name'] == 'uav_px4_bridge'
            for topic in CONTROL_TOPICS)
        return {
            'label': label,
            'bridge_status': self.bridge_status,
            'node_names': nodes,
            'topic_names_and_types': [
                {'name': name, 'types': topic_types[name]} for name in sorted(topic_types)],
            'publishers': publishers,
            'subscribers': subscribers,
            'truth_named_ros_topics': truth_topics,
            'truth_named_ros_nodes': truth_nodes,
            'checks': {
                'one_uav_px4_bridge_publisher_per_px4_control_topic': unique_control_publishers,
                'no_ros_truth_topic_or_node': not truth_topics and not truth_nodes,
            },
        }


def main():
    if len(sys.argv) != 2:
        raise SystemExit('Usage: capture_n07_ros_graph.py RUN_DIRECTORY')
    run = Path(sys.argv[1]).resolve()
    flight_file = run / 'flight.json'
    rclpy.init()
    node = GraphAudit()
    snapshots = []
    started = time.monotonic()
    initial_captured = False
    airborne_captured = False
    while rclpy.ok() and time.monotonic() - started < 380 and not flight_file.exists():
        rclpy.spin_once(node, timeout_sec=0.05)
        elapsed = time.monotonic() - started
        if elapsed >= 1.0 and not initial_captured:
            time.sleep(0.25)
            snapshots.append(node.snapshot('pre_enable_or_early_run'))
            initial_captured = True
        status = node.bridge_status or {}
        if status.get('phase') == 'ACTIVE' and status.get('armed') and not airborne_captured:
            time.sleep(0.25)
            snapshots.append(node.snapshot('airborne_active'))
            airborne_captured = True
    if not flight_file.exists():
        snapshots.append(node.snapshot('collector_timeout'))
    else:
        snapshots.append(node.snapshot('flight_result_written'))
    result = {
        'scope': __doc__,
        'read_only': True,
        'control_topics': list(CONTROL_TOPICS),
        'airborne_snapshot_captured': airborne_captured,
        'snapshots': snapshots,
        'checks_passed': bool(snapshots) and all(
            all(snapshot['checks'].values()) for snapshot in snapshots),
    }
    result = qualify_report(result)
    (run / 'ros-graph-audit.json').write_text(
        json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    node.destroy_node()
    rclpy.shutdown()
    print(json.dumps({
        'checks_passed': result['checks_passed'],
        'airborne_snapshot_captured': airborne_captured,
        'snapshot_count': len(snapshots),
    }, indent=2))
    if not result['checks_passed'] or not airborne_captured:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
