#!/usr/bin/env python3
"""Persistent read-only hardware observer; start before VINS to avoid CLI startup load."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, qos_profile_sensor_data
from rosidl_runtime_py.convert import message_to_ordereddict
from geometry_msgs.msg import PoseStamped
from uav_interfaces.msg import LocalizationStatus, MapStatus
from uav_interfaces.srv import GetOccupancySnapshot


class Observer(Node):
    def __init__(self, directory):
        super().__init__('hw05_read_only_observer')
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.record = (directory / 'observations.jsonl').open('a', buffering=1)
        self.latest = {}
        self.last_command = ''
        self.future = None
        retained = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                              durability=DurabilityPolicy.TRANSIENT_LOCAL)
        for kind, msg_type, topic, qos in (
                ('map', MapStatus, '/mapping/status', retained),
                ('localization', LocalizationStatus, '/localization/status', retained),
                ('camera_pose', PoseStamped, '/drone_0_camera_pose', qos_profile_sensor_data)):
            self.create_subscription(msg_type, topic,
                lambda msg, key=kind: self.receive(key, msg), qos)
        self.client = self.create_client(GetOccupancySnapshot, '/mapping/get_occupancy_snapshot')
        self.create_timer(1.0, self.tick)

    def receive(self, kind, msg):
        previous = self.latest.get(kind, {})
        value = message_to_ordereddict(msg)
        self.latest[kind] = value
        if kind == 'map' and (previous.get('epoch'), previous.get('map_id')) != (value['epoch'], value['map_id']):
            self.record.write(json.dumps({'event': 'map_identity_changed',
                'monotonic_s': time.monotonic(), 'ros_ns': self.get_clock().now().nanoseconds,
                **self.latest}) + '\n')

    def tick(self):
        self.record.write(json.dumps({'monotonic_s': time.monotonic(),
            'ros_ns': self.get_clock().now().nanoseconds, **self.latest}) + '\n')
        path = self.directory / 'capture-command.json'
        if self.future is not None or not path.is_file() or not self.client.service_is_ready():
            return
        raw = path.read_text()
        if raw == self.last_command or 'map' not in self.latest:
            return
        command = json.loads(raw)
        if command.get('wait_ready'):
            status = self.latest['map']
            if (not status['input_ready'] or not self.latest.get('localization', {}).get('valid')
                    or status['epoch'] != command.get('epoch', status['epoch'])
                    or status['occupied_point_count'] < command.get('minimum_occupied_points', 1)):
                return
        name = command['name']
        if not name or Path(name).name != name or name in ('.', '..'):
            raise ValueError('Snapshot name must be a simple path component')
        self.last_command = raw
        request = GetOccupancySnapshot.Request()
        request.expected_epoch = command.get('epoch', self.latest['map']['epoch'])
        request.expected_map_id = command.get('map_id', self.latest['map']['map_id'])
        before = dict(self.latest)
        self.future = self.client.call_async(request)
        self.future.add_done_callback(lambda future: self.capture_done(future, name, before))

    def capture_done(self, future, name, before):
        self.future = None
        response = future.result()
        metadata = message_to_ordereddict(response)
        metadata.pop('occupancy_data')
        metadata.pop('inflated_data')
        metadata['observation_before'] = before
        metadata['observation_after'] = dict(self.latest)
        target = self.directory / 'snapshots' / name
        target.mkdir(parents=True, exist_ok=False)
        if response.accepted:
            shape = (response.size_x, response.size_y, response.size_z)
            raw = np.asarray(response.occupancy_data, dtype=np.int8).reshape(shape)
            inflated = np.asarray(response.inflated_data, dtype=np.uint8).reshape(shape)
            assert np.isin(raw, (-1, 0, 100)).all() and np.isin(inflated, (0, 1)).all()
            archive = target / 'occupancy.npz'
            np.savez_compressed(archive, occupancy=raw, inflated=inflated)
            with np.load(archive, allow_pickle=False) as readback:
                assert np.array_equal(raw, readback['occupancy'])
                assert np.array_equal(inflated, readback['inflated'])
            metadata['archive_sha256'] = hashlib.sha256(archive.read_bytes()).hexdigest()
            metadata['archive_readback_exact'] = True
        (target / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
        self.get_logger().info(f'Snapshot {name}: accepted={response.accepted} reason={response.reason}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=600)
    args = parser.parse_args()
    rclpy.init()
    node = Observer(args.directory)
    end = time.monotonic() + args.seconds
    try:
        while rclpy.ok() and time.monotonic() < end:
            rclpy.spin_once(node, timeout_sec=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        node.record.close()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
