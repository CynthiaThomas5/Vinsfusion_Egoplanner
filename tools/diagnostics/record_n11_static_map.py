#!/usr/bin/env python3
"""Read-only periodic raw/inflated snapshots for the N11 static-room protocol."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np
import rclpy
from uav_interfaces.msg import NavigationCommand, MapStatus
from uav_interfaces.srv import GetOccupancySnapshot
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from capture_live_occupancy_snapshot import SnapshotClient, stamp_ns


def decode(response):
    shape = tuple(int(getattr(response, 'size_' + axis)) for axis in 'xyz')
    if any(x <= 0 for x in shape) or response.data_order != 'x_major_y_mid_z_fastest':
        raise ValueError('invalid snapshot shape/order')
    raw = np.asarray(response.occupancy_data, dtype=np.int64)
    inflated = np.asarray(response.inflated_data, dtype=np.int64)
    if raw.size != int(np.prod(shape)) or inflated.size != raw.size:
        raise ValueError('snapshot array size mismatch')
    if not np.isin(raw, [-1, 0, 100]).all() or not np.isin(inflated, [0, 1]).all():
        raise ValueError('invalid raw/inflated codes')
    return raw.astype(np.int8).reshape(shape), inflated.astype(np.uint8).reshape(shape)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run', type=Path)
    p.add_argument('--max-wall-s', type=float, default=1800)
    p.add_argument('--period-s', type=float, default=5)
    a = p.parse_args()
    run = a.run.resolve(); out = run/'n11-static-map'; out.mkdir(exist_ok=False)
    rclpy.init(); node = SnapshotClient('/mapping/get_map_status', '/mapping/get_occupancy_snapshot')
    state = {'goal':None, 'map':None}
    node.create_subscription(NavigationCommand, '/navigation/ego_goal', lambda m: state.update(goal=m), 10)
    node.create_subscription(MapStatus, '/mapping/status', lambda m: state.update(map=m), 10)
    rows=[]; errors=[]; started=time.monotonic(); due=started
    terminal=False
    try:
        while rclpy.ok() and time.monotonic()-started < a.max_wall_s:
            rclpy.spin_once(node,timeout_sec=0.1)
            if (run/'flight.json').is_file():
                try:
                    flight=json.loads((run/'flight.json').read_text())
                except (OSError,ValueError):
                    flight={}
                terminal=isinstance(flight,dict) and flight.get('landed_and_disarmed') is True
                if terminal: break
            goal,status=state['goal'],state['map']
            if goal is None or status is None or time.monotonic()<due: continue
            due=time.monotonic()+a.period_s
            try:
                request=GetOccupancySnapshot.Request()
                request.expected_epoch=status.epoch; request.expected_map_id=status.map_id
                response=node.request(node.snapshot_client,request,3)
                if not response.accepted: raise ValueError('snapshot rejected: '+response.reason)
                if goal.epoch!=status.epoch or goal.map_id!=status.map_id or response.epoch!=status.epoch or response.map_id!=status.map_id or response.header.frame_id!='odom_'+status.epoch:
                    raise ValueError('snapshot identity changed during request')
                raw,inflated=decode(response)
                path=out/f'{len(rows):04d}.npz';np.savez_compressed(path,occupancy=raw,inflated=inflated)
                rows.append({'path':str(path.relative_to(run)), 'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                    'goal_id':goal.goal_id, 'epoch':response.epoch,'map_id':response.map_id,
                    'frame_id':response.header.frame_id,'snapshot_stamp_ns':stamp_ns(response.header.stamp),
                    'source_stamp_ns':stamp_ns(response.last_depth_source_stamp),'fusion_stamp_ns':stamp_ns(response.last_fusion_stamp),
                    'resolution_m':response.resolution,'origin_m':[response.origin.x,response.origin.y,response.origin.z],
                    'shape':list(raw.shape),'data_order':response.data_order})
                compatibility=run/'n10-map-snapshot'
                compatibility.mkdir(exist_ok=True)
                if not (compatibility/'metadata.json').exists():
                    (compatibility/'metadata.json').write_text(json.dumps({'schema':'n11-static-snapshot-identity-alias/v1','source':rows[-1]['path'],'epoch':response.epoch,'map_id':response.map_id,'frame_id':response.header.frame_id,'last_fused_depth_source_stamp_ns':stamp_ns(response.last_depth_source_stamp)},indent=2)+'\n')
            except Exception as exc:
                errors.append({'elapsed_wall_s':time.monotonic()-started,'error':str(exc)})
    finally:
        from n10_run_identity import read_run_identity
        identity=read_run_identity(run,goal_id=getattr(state['goal'],'goal_id',None),epoch=getattr(state['map'],'epoch',None),map_id=getattr(state['map'],'map_id',None))
        report={'schema':'n11-static-map-observation/v1','run_id':run.name,'snapshots':rows,'errors':errors,
                'terminal_flight_record_observed':terminal,'control_publishers':[], 'truth_subscriptions':[],
                'run_identity':identity,'recorder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
        (run/'n11-static-map-observation.json').write_text(json.dumps(report,indent=2)+'\n')
        node.destroy_node();rclpy.shutdown()

if __name__=='__main__':main()
