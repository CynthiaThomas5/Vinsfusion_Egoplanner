#!/usr/bin/env python3
"""Bounded read-only live map queries; never enables, arms or sends a goal."""
import argparse
import json
from pathlib import Path
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, qos_profile_sensor_data
from rosidl_runtime_py.convert import message_to_ordereddict
from nav_msgs.msg import Odometry
from px4_msgs.msg import VehicleStatus
from uav_interfaces.msg import MapStatus, NavigationCommand
from uav_interfaces.srv import QueryOccupancySphere


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    rclpy.init()
    node = Node('readonly_goal_admission_probe', parameter_overrides=[
        rclpy.parameter.Parameter('use_sim_time', value=True)])
    latest = {}
    goals = []
    statuses = []
    qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)
    node.create_subscription(MapStatus, '/mapping/status', lambda m: latest.update(map=m), qos)
    node.create_subscription(Odometry, '/localization/optimized_imu_odom',
                             lambda m: latest.update(odom=m), 10)
    node.create_subscription(VehicleStatus, '/fmu/out/vehicle_status_v1',
                             lambda m: statuses.append(m.arming_state), qos_profile_sensor_data)
    node.create_subscription(NavigationCommand, '/navigation/ego_goal', goals.append, 10)
    client = node.create_client(QueryOccupancySphere, '/mapping/query_occupancy_sphere')
    rows = []
    deadline = time.monotonic() + 60
    try:
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.02)
            if (client.service_is_ready() and 'map' in latest and 'odom' in latest
                    and latest['map'].input_ready):
                break
        else:
            raise RuntimeError('no ready live map within 60 seconds')
        root = Path('/workspace')
        policy = json.loads((root/'config/components/mapping/ego_planner.json').read_text())
        radius = policy['obstacles_inflation_m']
        samples = [('near_ground', (0.,0.,0.)), ('near_ahead', (1.,0.,1.)),
                   ('ahead', (2.,0.,1.)), ('far_unknown', (13.,0.,1.)),
                   ('outside', (100.,0.,1.)), ('small_diagnostic', (1.,0.,.2))]
        for repeat in range(4):
            for label, xyz in samples:
                m = latest['map']
                req = QueryOccupancySphere.Request()
                req.expected_epoch, req.expected_map_id = m.epoch, m.map_id
                req.frame_id = latest['odom'].header.frame_id
                req.center.x, req.center.y, req.center.z = xyz
                req.radius_m = .05 if label == 'small_diagnostic' else radius
                if repeat == 1 and label == 'outside':
                    req.expected_map_id = 'invalid-map-id'
                if repeat == 2 and label == 'outside':
                    req.expected_epoch = 'invalid-epoch'
                if repeat == 3 and label == 'outside':
                    req.frame_id = 'world'
                start = time.monotonic()
                future = client.call_async(req)
                while not future.done() and time.monotonic() - start < 1.0:
                    rclpy.spin_once(node, timeout_sec=.01)
                if not future.done():
                    raise RuntimeError('query did not reply within one wall second')
                rows.append({'label': label, 'repeat': repeat,
                             'wall_round_trip_s': time.monotonic()-start,
                             'request': message_to_ordereddict(req),
                             'response': message_to_ordereddict(future.result())})
                until = time.monotonic()+.11
                while time.monotonic() < until:
                    rclpy.spin_once(node, timeout_sec=.01)
        if not statuses or any(s != VehicleStatus.ARMING_STATE_DISARMED for s in statuses):
            raise RuntimeError('disarmed status not continuously observed')
        if goals:
            raise RuntimeError('unexpected navigation goal during read-only probe')
        report = {'scope': 'unarmed read-only live grid query, no flight or path qualification',
                  'rows': rows, 'vehicle_status_samples': len(statuses),
                  'arming_states': sorted(set(statuses)), 'navigation_commands_observed': len(goals)}
        args.output.write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps({'responses':len(rows), 'reasons':sorted(set(r['response']['reason'] for r in rows)),
                          'disarmed_samples':len(statuses), 'navigation_commands':len(goals)}))
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
