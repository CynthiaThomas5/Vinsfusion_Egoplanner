"""Offline N13 per-obstacle blockage/map/bypass and executed replacement proof."""
import hashlib,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/debug_truth')]
from evaluate_n10_clearance import parse_obstacles
from evaluate_n10_camera_map_support import cylinder_hits

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p): return json.loads(Path(p).read_text())

def direct_hit(start,end,cylinder):
    start,end=np.asarray(start,float),np.asarray(end,float)
    if start.shape!=(3,) or end.shape!=(3,) or not np.isfinite([start,end]).all():
        raise ValueError('invalid_direct_segment')
    hit=float(cylinder_hits(start,(end-start)[None,:],cylinder,0,1)[0])
    return hit if np.isfinite(hit) and 0<hit<1 else None

def plane_crossings(rows,key,cylinder):
    if len(rows)<2: raise ValueError('insufficient_path_samples')
    stamps=[int(r['source_stamp_ns']) for r in rows]
    if any(b<a for a,b in zip(stamps,stamps[1:])): raise ValueError('nonmonotonic_path_stamps')
    cx=cylinder['center_xyz_m'][0]
    out=[]
    for a,b in zip(rows,rows[1:]):
        p,q=np.asarray(a[key],float),np.asarray(b[key],float)
        if not np.isfinite([p,q]).all(): raise ValueError('nonfinite_path')
        if p[0]<cx<=q[0]:
            if int(a['source_stamp_ns']) == int(b['source_stamp_ns']):
                raise ValueError('ambiguous_same_stamp_obstacle_plane_crossing')
            u=float((cx-p[0])/(q[0]-p[0]));x=p+u*(q-p)
            solid=abs(x[1]-cylinder['center_xyz_m'][1])<=cylinder['radius_m'] and cylinder['z_min_m']<=x[2]<=cylinder['z_max_m']
            out.append({'source_stamp_ns':int(a['source_stamp_ns']+u*(b['source_stamp_ns']-a['source_stamp_ns'])),
                        'world_xyz_m':x.tolist(),'inside_solid':bool(solid),
                        'bracket_source_gap_sim_s':(b['source_stamp_ns']-a['source_stamp_ns'])/1e9,
                        'trajectory_ids':[a.get('trajectory_id'),b.get('trajectory_id')]})
    return out

def surface_measure(raw,inflated,origin,res,R,t,cylinder,z_center):
    if raw.ndim!=3 or raw.shape!=inflated.shape or res<=0: raise ValueError('invalid_snapshot_arrays')
    if not np.isin(raw,[-1,0,100]).all() or not np.isin(inflated,[0,1]).all(): raise ValueError('invalid_snapshot_codes')
    idx=np.argwhere(raw==100)
    points=(np.asarray(origin)+(idx+.5)*res)@R.T+t
    radial=np.linalg.norm(points[:,:2]-cylinder['center_xyz_m'][:2],axis=1)
    err=np.abs(radial-cylinder['radius_m'])
    # Lateral surface near the direct segment height; no floor/cap support credit.
    valid=(err<=1.5*res)&(np.abs(points[:,2]-z_center)<=cylinder['radius_m'])&(points[:,2]>cylinder['z_min_m']+res)&(points[:,2]<cylinder['z_max_m']-res)
    pts=points[valid];selected=idx[valid]
    inflated_count=int(np.count_nonzero(inflated[tuple(selected.T)])) if len(selected) else 0
    sectors=sorted(set((np.floor((np.arctan2(pts[:,1]-cylinder['center_xyz_m'][1],pts[:,0]-cylinder['center_xyz_m'][0])+np.pi)/(2*np.pi)*8).astype(int)%8).tolist())) if len(pts) else []
    return {'surface_raw_occupied_count':int(valid.sum()),'same_snapshot_surface_inflated_count':inflated_count,
            'surface_center_error_max_m':float(err[valid].max()) if valid.any() else None,
            'supported_azimuth_sectors_of_8':sectors,'unsupported_azimuth_sectors_of_8':[i for i in range(8) if i not in sectors],
            'support_roi':'lateral surface,abs(z-direct_segment_at_obstacle_plane)<=cylinder_radius; cap/floor excluded'}

def evaluate_obstacle(run,config,index,*,obstacle_prefix=None):
    run=Path(run);fail=[];missing=[];result={'schema':'n13-obstacle-route/v1','run_id':run.name,'control_effect':False}
    try:
        cfg=load(config);flight=load(run/'flight.json');contract=load(run/'runtime-contract.json')
        arrival=load(run/'arrival-evaluation.json');obs=load(run/'n11-static-map-observation.json')
        launch=load(run/'n11-launch-record.json')
        obstacles,_=parse_obstacles(run/'vio_initialization.sdf')
        prefix=obstacle_prefix or f'n13_staggered_cylinder_{index}/'
        cs=[o for o in obstacles if o['name'].startswith(prefix)]
        if len(cs)!=1 or cs[0]['kind']!='vertical_cylinder': raise ValueError('declared_staggered_cylinder_missing')
        cylinder=cs[0];result['obstacle']=cylinder
        R=np.asarray(arrival['ground_rotation']);t=np.asarray(arrival['ground_translation'])
        if R.shape!=(3,3) or t.shape!=(3,) or not np.allclose(R.T@R,np.eye(3),atol=1e-6) or not np.isclose(np.linalg.det(R),1,atol=1e-6): raise ValueError('invalid_fixed_alignment')
        start=R@np.asarray(flight['airborne_origin_enu'])+t
        end=R@np.asarray(flight['goal']['target_enu'])+t
        hit=direct_hit(start,end,cylinder)
        result['direct_segment']={'start_world_m':start.tolist(),'end_world_m':end.tolist(),'first_solid_hit_parameter':hit}
        if hit is None: fail.append('direct_path_not_blocked_by_solid_obstacle')
        tracking=load(run/'n10-tracking-clearance-relation.json')
        rows=tracking['per_sample']
        actual=plane_crossings(rows,'truth_xyz_world_m',cylinder)
        reference=plane_crossings(rows,'command_xyz_world_m',cylinder)
        result['actual_crossings']=actual;result['reference_crossings']=reference
        if not actual: fail.append('actual_path_did_not_pass_obstacle_plane')
        if not reference: fail.append('ego_reference_did_not_pass_obstacle_plane')
        if any(x['inside_solid'] for x in actual): fail.append('actual_crossing_inside_obstacle')
        if any(x['inside_solid'] for x in reference): fail.append('reference_crossing_inside_obstacle')
        planner=load(run/'planner-observation.json')
        splines=[x['message'] for x in planner['messages'] if x['type']=='bspline' and x['message'].get('goal_id')==flight['goal_id'] and x['message'].get('epoch')==flight['localization_epoch']]
        ids={x['traj_id'] for x in splines}
        matched=bool(reference) and all(all(k in ids for k in x['trajectory_ids']) for x in reference)
        if not matched: missing.append('reference_crossing_not_bound_to_matching_ego_spline')
        result['matching_spline_count']=len(splines);result['reference_crossing_spline_identity_bound']=matched
        expected={'run_id':run.name,'runtime_contract_sha256':contract['sha256'],'goal_id':flight['goal_id'],'epoch':flight['localization_epoch'],'map_id':launch['map_id']}
        result['run_identity']=expected
        if any(obs['run_identity'].get(k)!=v for k,v in expected.items()): raise ValueError('map_observer_identity_mismatch')
        cx=cylinder['center_xyz_m'][0]
        if end[0]==start[0]: raise ValueError('direct_segment_parallel_to_obstacle_plane')
        z=float(start[2]+(cx-start[0])/(end[0]-start[0])*(end[2]-start[2]))
        surface=[];rejected=[]
        passage=min((x['source_stamp_ns'] for x in actual),default=0)
        for row in obs['snapshots']:
            try:
                if any(row.get(k)!=expected[k] for k in ('goal_id','epoch','map_id')) or row['frame_id']!='odom_'+expected['epoch']: raise ValueError('snapshot_identity_mismatch')
                p=(run/row['path']).resolve()
                if not p.is_relative_to(run.resolve()) or sha(p)!=row['sha256']: raise ValueError('snapshot_hash_or_path_mismatch')
                if not 0<row['source_stamp_ns']<=row['fusion_stamp_ns']<=row['snapshot_stamp_ns']: raise ValueError('snapshot_source_order')
                with np.load(p,allow_pickle=False) as a:
                    if list(a['occupancy'].shape)!=row['shape']: raise ValueError('snapshot_shape_mismatch')
                    measured=surface_measure(a['occupancy'],a['inflated'],row['origin_m'],row['resolution_m'],R,t,cylinder,z)
                surface.append({**measured,'source_stamp_ns':row['source_stamp_ns'],'fusion_stamp_ns':row['fusion_stamp_ns'],'snapshot_stamp_ns':row['snapshot_stamp_ns'],'snapshot_path':row['path'],'snapshot_sha256':row['sha256'],'before_actual_crossing':bool(passage and row['snapshot_stamp_ns']<=passage)})
            except (ValueError,KeyError,OSError) as exc: rejected.append(str(exc))
        supported=[x for x in surface if x['surface_raw_occupied_count'] and x['same_snapshot_surface_inflated_count']]
        before=[x for x in supported if x['before_actual_crossing']]
        limit=None  # User#521: surface error is diagnostic only.
        if not before: missing.append('no_pre_crossing_identity_bound_raw_inflated_surface_support')
        maximum=max((x['surface_center_error_max_m'] for x in supported),default=None)

        if rejected: missing.append('rejected_obstacle_snapshots')
        result.update(surface_snapshots=surface,rejected_snapshots=rejected,pre_crossing_supported_snapshot_count=len(before),maximum_supported_surface_error_m=maximum,surface_error_threshold_m=limit)
        if not flight.get('action_success') or not flight.get('landed_and_disarmed'): fail.append('mission_or_terminal_not_successful')
    except (ValueError,KeyError,OSError) as exc: missing.append(str(exc))
    result.update(status='FAIL' if fail else 'INSUFFICIENT' if missing else 'PASS',failures=fail,insufficient=missing)
    return result


def evaluate(run, config):
    run = Path(run)
    rows = [evaluate_obstacle(run, config, i) for i in (1, 2, 3)]
    failures = [f"obstacle_{i}:{reason}" for i, row in enumerate(rows, 1)
                for reason in row['failures']]
    missing = [f"obstacle_{i}:{reason}" for i, row in enumerate(rows, 1)
               for reason in row['insufficient']]
    executed = []
    try:
        flight = load(run/'flight.json')
        planner = load(run/'planner-observation.json')
        tracking = load(run/'n10-tracking-clearance-relation.json')
        ids = {m['message']['traj_id'] for m in planner['messages']
               if m['type'] == 'bspline'
               and m['message'].get('goal_id') == flight['goal_id']
               and m['message'].get('epoch') == flight['localization_epoch']}
        executed = sorted({r['trajectory_id'] for r in tracking['per_sample']
                           if r.get('trajectory_id') in ids})
        if len(executed) < 2:
            missing.append('no_executed_matching_replacement_trajectory')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        missing.append('executed_replanning:'+str(exc))
    updates = {s['fusion_stamp_ns'] for row in rows
               for s in row.get('surface_snapshots', [])
               if s['before_actual_crossing'] and s['surface_raw_occupied_count']
               and s['same_snapshot_surface_inflated_count']}
    if len(updates) < 2:
        missing.append('multiple_observed_map_updates_not_demonstrated')
    return {'schema':'n13-staggered-route/v1', 'run_id':run.name,
            'status':'FAIL' if failures else 'INSUFFICIENT' if missing else 'PASS',
            'obstacles':rows, 'failures':failures, 'insufficient':missing,
            'executed_matching_trajectory_ids':executed,
            'supported_distinct_map_update_count':len(updates),
            'evaluator_sha256':sha(__file__), 'runtime_control_effect':False,
            'limitations':['sampled path geometry; prohibited contacts evaluated independently',
                          'functional route evidence only; arrival/terminal/core identity also required']}

if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('run',type=Path)
    p.add_argument('--config',type=Path,default=ROOT/'config/acceptance_n13.json')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();report=evaluate(a.run,a.config)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(report['status'])
