#!/usr/bin/env python3
"""Exercise retained ROS history output and map/epoch isolation, no control I/O."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile
import time
import uuid

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
from std_msgs.msg import Header
from uav_interfaces.msg import MapStatus, LocalizationStatus
from uav_mapping.observed_history import ObservedHistory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-root', required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        shutil.copytree(Path(args.project_root)/'config', root/'config')
        epoch = uuid.uuid4().hex
        prefix = '/history_probe_'+epoch
        mapping_path = root/'config/components/mapping/ego_input.json'
        mapping = json.loads(mapping_path.read_text())
        for key in ('map_status_topic', 'localization_status_topic', 'ego_occupancy_topic'):
            mapping[key] = prefix+'/'+key
        mapping_path.write_text(json.dumps(mapping))
        policy_path = root/'config/components/mapping/observed_history.json'
        policy = json.loads(policy_path.read_text())
        policy['output_topic'] = '/visualization/mapping/history_'+epoch
        policy['publish_period_wall_s'] = .2
        policy_path.write_text(json.dumps(policy))
        session = root/'session.json'
        session.write_text(json.dumps({'epoch': epoch}))
        rclpy.init(args=['--ros-args', '-p', f'project_root:={root}',
                        '-p', f'session_manifest:={session}'])
        history = ObservedHistory()
        probe = Node('history_probe')
        executor = SingleThreadedExecutor()
        executor.add_node(history)
        executor.add_node(probe)
        retained = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        maps = probe.create_publisher(MapStatus, mapping['map_status_topic'], retained)
        locations = probe.create_publisher(LocalizationStatus, mapping['localization_status_topic'], retained)
        clouds = probe.create_publisher(PointCloud2, mapping['ego_occupancy_topic'], 10)
        output = []
        subscription = probe.create_subscription(PointCloud2, policy['output_topic'], output.append, retained)

        def wait(predicate, timeout=5):
            end = time.monotonic()+timeout
            while time.monotonic() < end:
                executor.spin_once(timeout_sec=.02)
                if predicate():
                    return
            raise AssertionError('history probe timeout')

        def cloud(points, frame=None, seconds=10):
            h = Header(frame_id=frame or history.frame)
            h.stamp.sec = seconds
            clouds.publish(point_cloud2.create_cloud_xyz32(h, points))

        def map_status(identity, ack=True, seconds=1):
            m = MapStatus(epoch=epoch, map_id=identity, reset_acknowledged=ack)
            m.header.frame_id = history.frame
            m.header.stamp.sec = seconds
            maps.publish(m)

        try:
            wait(lambda: clouds.get_subscription_count() == 1 and maps.get_subscription_count() == 1)
            map_status('first')
            wait(lambda: history.identity == 'first')
            cloud([(-8., 0., 1.)])
            wait(lambda: len(history.history.voxels) == 1)
            cloud([(8., 0., 1.)])
            wait(lambda: len(history.history.voxels) == 2)
            history.publish()
            wait(lambda: output and output[-1].width == 2)
            # A late subscriber must get the full retained cloud, not only the latest local area.
            late = []
            late_sub = probe.create_subscription(PointCloud2, policy['output_topic'], late.append, retained)
            wait(lambda: late and late[-1].width == 2)
            cloud([(0., 0., 1.)], frame='odom_old')
            end = time.monotonic()+.2
            while time.monotonic() < end:
                executor.spin_once(timeout_sec=.02)
            assert len(history.history.voxels) == 2
            map_status('second', ack=False, seconds=9)
            wait(lambda: history.identity == 'second' and not history.history.voxels)
            cloud([(0., 0., 1.)])
            map_status('second', seconds=11)
            wait(lambda: history.map_acknowledged)
            cloud([(0., 0., 1.)], seconds=10)
            end = time.monotonic()+.2
            while time.monotonic() < end:
                executor.spin_once(timeout_sec=.02)
            assert not history.history.voxels
            cloud([(0., 0., 1.)], seconds=12)
            wait(lambda: len(history.history.voxels) == 1)
            map_status('first')
            executor.spin_once(timeout_sec=.1)
            assert history.identity == 'second'
            # Time regression clears history and retires the current map identity.
            cloud([(1., 0., 1.)], seconds=11)
            wait(lambda: history.identity is None and not history.history.voxels)
            map_status('third')
            wait(lambda: history.identity == 'third')
            cloud([(0., 0., 1.)])
            wait(lambda: len(history.history.voxels) == 1)
            locations.publish(LocalizationStatus(epoch=uuid.uuid4().hex))
            wait(lambda: history.session_invalid and not history.history.voxels)
            wait(lambda: output and output[-1].width == 0)
            publishers = dict(history.get_publisher_names_and_types_by_node(
                'observed_obstacle_history', '/'))
            assert set(publishers) == {policy['output_topic'], '/parameter_events', '/rosout'}
            assert publishers[policy['output_topic']] == ['sensor_msgs/msg/PointCloud2']
            print('PASS: disjoint-area retention, late subscriber, old-frame refusal, map reset/ack, retired identity, time regression, epoch clear; visualization-only publisher')
        finally:
            probe.destroy_node()
            history.destroy_node()
            executor.shutdown()
            rclpy.shutdown()


if __name__ == '__main__':
    main()
