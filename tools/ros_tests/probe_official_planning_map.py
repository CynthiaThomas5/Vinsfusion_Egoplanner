#!/usr/bin/env python3
"""Read-only live comparison of raw classes and official planning occupancy."""
import argparse
import json
from pathlib import Path
import time

import rclpy
from rclpy.qos import QoSProfile, DurabilityPolicy
from uav_interfaces.msg import MapStatus
from uav_interfaces.srv import QueryOccupancySphere


def main():
    p = argparse.ArgumentParser(); p.add_argument('output', type=Path); args = p.parse_args()
    rclpy.init(); node = rclpy.create_node('official_planning_map_probe')
    latest = {}
    q = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    sub = node.create_subscription(MapStatus, '/mapping/status', lambda m: latest.update(map=m), q)
    raw = node.create_client(QueryOccupancySphere, '/mapping/query_occupancy_sphere')
    planning = node.create_client(QueryOccupancySphere, '/mapping/query_planning_occupancy')
    deadline = time.monotonic()+20
    while time.monotonic()<deadline:
        rclpy.spin_once(node, timeout_sec=.05)
        if (latest.get('map') and latest['map'].input_ready and raw.service_is_ready()
                and planning.service_is_ready()):
            break
    identity = latest['map']; rows = []

    def query(client, xyz, epoch=None):
        req = QueryOccupancySphere.Request(); req.expected_epoch = epoch or identity.epoch
        req.expected_map_id = identity.map_id; req.frame_id = 'odom_'+identity.epoch
        req.center.x, req.center.y, req.center.z = xyz; req.radius_m = 0.001 if client is raw else 0.
        f = client.call_async(req); rclpy.spin_until_future_complete(node, f, timeout_sec=2)
        if not f.done(): raise TimeoutError('planning query timeout')
        r = f.result()
        return {'accepted':r.accepted,'free':r.free,'reason':r.reason,
                'unknown':r.unknown_count,'known_free':r.free_count,'occupied':r.occupied_count,
                'epoch':r.epoch,'map_id':r.map_id}

    try:
        unknown = None; blocked = None
        for x in (-.55, -.85, -1.25):
            point = (x, .05, .75)
            a, b = query(raw, point), query(planning, point)
            rows.append({'point':point,'raw':a,'planning':b})
            if a['reason']=='unknown' and b['reason']=='unobserved_not_occupied':
                unknown = rows[-1]; break
        for z in (-.35, -.25, -.15, .05):
            if blocked: break
            for x in (.55, .85, 1.25, 1.75):
                point = (x, .05, z)
                a, b = query(raw,point), query(planning,point)
                rows.append({'point':point,'raw':a,'planning':b})
                if b['reason']=='occupied': blocked = rows[-1]; break
        outside = query(planning, (50.,0.,1.))
        stale_epoch = query(planning, (0.,0.,1.), epoch='0'*32)
        checks = {
            'raw_unknown_retained_and_official_predicate_traversable': bool(unknown and unknown['raw']['unknown']>0 and unknown['planning']['free'] and unknown['planning']['unknown']==1 and unknown['planning']['known_free']==0),
            'inflated_occupied_is_blocked': bool(blocked and not blocked['planning']['free'] and blocked['planning']['occupied']==1),
            'outside_map_rejected': not outside['accepted'] and outside['reason']=='outside_map',
            'wrong_epoch_rejected': not stale_epoch['accepted'] and stale_epoch['reason']=='epoch_mismatch',
        }
        report = {'schema':'official-ego-live-map-policy/v1','passed':all(checks.values()),
                  'checks':checks,'epoch':identity.epoch,'map_id':identity.map_id,
                  'queries':rows,'outside':outside,'wrong_epoch':stale_epoch,
                  'control_or_goal_published':False,'truth_subscribed':False}
        args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(checks))
        if not report['passed']: raise SystemExit(1)
    finally:
        node.destroy_node();rclpy.shutdown()


if __name__=='__main__': main()
