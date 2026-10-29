#!/usr/bin/env python3
"""Read-only measured corridor traversal and pre-entry side-wall map evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.debug_truth.evaluate_n13_route import plane_crossings


def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def passage(rows,key,width=2.4):
    if len(rows)<2:raise ValueError('path_missing')
    stamps=[int(r['source_stamp_ns']) for r in rows]
    if any(b<a for a,b in zip(stamps,stamps[1:])):raise ValueError('backward_source_time')
    points=np.asarray([r[key] for r in rows],float)
    if points.shape!=(len(rows),3) or not np.isfinite(points).all():raise ValueError('invalid_path')
    crossings=[]
    for x in [-3.,3.]:
        crossings.append(plane_crossings(rows,key,{'center_xyz_m':[x,0,1.5],
             'radius_m':0.,'z_min_m':0.,'z_max_m':3.}))
    if not all(crossings):raise ValueError('entry_or_exit_not_observed')
    entry=crossings[0][0]['source_stamp_ns']
    exit=crossings[1][-1]['source_stamp_ns']
    if entry>=exit:raise ValueError('entry_exit_order')
    inside=points[(points[:,0]>=-3)&(points[:,0]<=3)]
    boundary=np.asarray([c['world_xyz_m'] for group in crossings for c in group])
    measured=np.vstack([inside,boundary])
    outside=bool(np.any(np.abs(measured[:,1])>=width/2) or np.any(measured[:,2]<=0) or np.any(measured[:,2]>=3))
    return {'entry_source_ns':entry,'exit_source_ns':exit,'in_corridor_samples':len(inside),
            'entry_crossings':crossings[0],'exit_crossings':crossings[1],
            'sampled_center_path_within_passage':not outside,
            'maximum_abs_y_m':float(np.abs(measured[:,1]).max()),
            'classification':'sampled center path; actual body collision checked independently'}


def evaluate(run,config=None):
    run=Path(run).resolve();missing=[];fail=[]
    report={'schema':'n14-corridor-route/v1','run_id':run.name,'runtime_control_effect':False,
            'evaluator_sha256':sha(__file__)}
    try:
        world=ET.parse(run/'vio_initialization.sdf').getroot().find('world')
        for side,sign in [('left',1),('right',-1)]:
            m=world.find(f"model[@name='n14_corridor_{side}']")
            if m is None:raise ValueError('declared_corridor_missing')
            pose=np.array(list(map(float,m.findtext('pose').split())))
            size=np.array(list(map(float,m.findtext('link/collision/geometry/box/size').split())))
            if (m.findtext('static') not in ['true','1'] or not np.allclose(pose,[0,sign*1.3,1.5,0,0,0])
                    or not np.allclose(size,[6,.2,3])):raise ValueError('corridor_geometry_mismatch')
        flight=load(run/'flight.json');tracking=load(run/'n10-tracking-clearance-relation.json')
        rows=tracking['per_sample'];actual=passage(rows,'truth_xyz_world_m');reference=passage(rows,'command_xyz_world_m')
        report.update(actual=actual,reference=reference)
        for name,result in [('actual',actual),('reference',reference)]:
            if not result['sampled_center_path_within_passage']:fail.append(name+'_path_outside_passage')
        planner=load(run/'planner-observation.json')
        ids={m['message']['traj_id'] for m in planner['messages'] if m['type']=='bspline'
             and m['message'].get('goal_id')==flight['goal_id']
             and m['message'].get('epoch')==flight['localization_epoch']}
        used={r['trajectory_id'] for r in rows if actual['entry_source_ns']<=r['source_stamp_ns']<=actual['exit_source_ns']}
        if not used or not used.issubset(ids):missing.append('corridor_commands_not_bound_to_goal_epoch_splines')
        report['executed_matching_trajectory_ids']=sorted(used&ids)
        arrival=load(run/'arrival-evaluation.json');rotation=np.asarray(arrival['ground_rotation']);translation=np.asarray(arrival['ground_translation'])
        if (rotation.shape!=(3,3) or translation.shape!=(3,) or not np.allclose(rotation.T@rotation,np.eye(3),atol=1e-6)
                or not np.isclose(np.linalg.det(rotation),1,atol=1e-6)):raise ValueError('invalid_fixed_alignment')
        observation=load(run/'n11-static-map-observation.json');launch=load(run/'n11-launch-record.json');contract=load(run/'runtime-contract.json')
        identity={'run_id':run.name,'runtime_contract_sha256':contract['sha256'],'goal_id':flight['goal_id'],
                  'epoch':flight['localization_epoch'],'map_id':launch['map_id']}
        if any(observation['run_identity'].get(k)!=v for k,v in identity.items()):raise ValueError('map_observer_identity_mismatch')
        support={'left':[],'right':[]};rejected=[]
        for snapshot in observation['snapshots']:
            try:
                if snapshot['snapshot_stamp_ns']>actual['entry_source_ns']:continue
                if (any(snapshot.get(k)!=identity[k] for k in ['goal_id','epoch','map_id'])
                        or snapshot['frame_id']!='odom_'+identity['epoch']):raise ValueError('snapshot_identity')
                path=(run/snapshot['path']).resolve()
                if not path.is_relative_to(run) or sha(path)!=snapshot['sha256']:raise ValueError('snapshot_hash_or_path')
                if not 0<snapshot['source_stamp_ns']<=snapshot['fusion_stamp_ns']<=snapshot['snapshot_stamp_ns']:raise ValueError('snapshot_time_order')
                with np.load(path,allow_pickle=False) as a:
                    raw=a['occupancy'];inflated=a['inflated']
                    if raw.shape!=inflated.shape or list(raw.shape)!=snapshot['shape']:raise ValueError('snapshot_shape')
                    res=float(snapshot['resolution_m'])
                    if not np.isfinite(res) or res<=0:raise ValueError('snapshot_resolution')
                    cells=np.argwhere(raw==100);points=(np.asarray(snapshot['origin_m'])+(cells+.5)*res)@rotation.T+translation
                    for side,sign in [('left',1),('right',-1)]:
                        selected=((np.abs(points[:,1]-sign*1.2)<=1.5*res)&(np.abs(points[:,0])<=3)
                                  &(points[:,2]>.3)&(points[:,2]<2.7))
                        indices=cells[selected];count=int(np.count_nonzero(inflated[tuple(indices.T)])) if len(indices) else 0
                        if count:support[side].append({'snapshot':snapshot['path'],'sha256':snapshot['sha256'],
                            'snapshot_stamp_ns':snapshot['snapshot_stamp_ns'],'raw_occupied_count':len(indices),'same_cell_inflated_count':count})
            except (OSError,ValueError,KeyError,TypeError) as exc:rejected.append(str(exc))
        for side in support:
            if not support[side]:missing.append(side+'_wall_not_observed_before_entry')
        if rejected:missing.append('rejected_pre_entry_snapshots')
        report.update(run_identity=identity,pre_entry_wall_support=support,rejected_snapshots=rejected)
    except (OSError,ValueError,KeyError,TypeError,AttributeError,ET.ParseError) as exc:missing.append(str(exc))
    report.update(status='FAIL' if fail else 'INSUFFICIENT' if missing else 'PASS',failures=fail,insufficient=missing)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=evaluate(a.run)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n');print(r['status'])
