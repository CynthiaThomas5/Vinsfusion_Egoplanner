#!/usr/bin/env python3
"""Compare initial local voxels with final local/history clouds, read-only."""
import argparse
import json
from pathlib import Path
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    parser.add_argument('--seconds', type=float, default=600)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    session = json.loads((args.run.parent/(args.run.name+'-stack')/'session/session.json').read_text())
    planner = json.loads((root/'config/components/mapping/ego_planner.json').read_text())
    mapping = json.loads((root/'config/components/mapping/ego_input.json').read_text())
    policy = json.loads((root/'config/components/mapping/observed_history.json').read_text())
    frame = 'odom_'+session['epoch']
    resolution = planner.get('map_resolution_m', .1)
    origin = [-planner['map_size_m'][0]/2, -planner['map_size_m'][1]/2, planner['ground_height_m']]
    import math
    initial, local, history = set(), set(), set()
    messages = {'local': 0, 'history': 0}
    stamps = {}
    rclpy.init()
    node = Node('observed_history_readonly_recorder')

    def receive(msg, kind):
        nonlocal initial, local, history
        if msg.header.frame_id != frame:
            return
        cells = set()
        for point in point_cloud2.read_points(msg, field_names=('x','y','z'), skip_nans=True):
            cells.add(tuple(math.floor((float(point[i])-origin[i])/resolution) for i in range(3)))
        messages[kind] += 1
        stamps[kind] = msg.header.stamp.sec*1_000_000_000+msg.header.stamp.nanosec
        if kind == 'local':
            local = cells
            if not initial and len(cells) >= 50:
                initial = cells.copy()
                (args.run/'history-recorder-ready').write_text('initial local observation captured\n')
        else:
            history = cells

    local_sub = node.create_subscription(PointCloud2, mapping['ego_occupancy_topic'],
                                          lambda m: receive(m, 'local'), qos_profile_sensor_data)
    retained = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    history_sub = node.create_subscription(PointCloud2, policy['output_topic'],
                                            lambda m: receive(m, 'history'), retained)
    start = time.monotonic()
    terminal_seen = None
    try:
        while time.monotonic()-start < args.seconds:
            rclpy.spin_once(node, timeout_sec=.1)
            if (args.run/'qualification.json').is_file():
                terminal_seen = terminal_seen or time.monotonic()
                if time.monotonic()-terminal_seen >= 2:
                    break
        result = {
            'schema': 'observed-history-live-retention/v1', 'frame_id': frame,
            'read_only': True, 'runtime_effect': False, 'messages': messages,
            'latest_cloud_source_ns': stamps, 'initial_local_voxels': len(initial),
            'final_local_voxels': len(local), 'final_history_voxels': len(history),
            'initial_voxels_retained_in_history': len(initial & history),
            'initial_voxels_still_in_final_local': len(initial & local),
            'historical_voxels_outside_final_local': len(history-local),
            'passed': bool(initial) and bool(initial & history) and not (initial & local)
                      and len(history) > len(local) and terminal_seen is not None,
            'scope': 'Observed raw occupied union only; no collision/coverage/global-SLAM claim',
        }
        (args.run/'observed-history-retention.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result))
        if not result['passed']:
            raise SystemExit(1)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
