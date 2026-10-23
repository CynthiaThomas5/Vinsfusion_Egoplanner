#!/usr/bin/env python3
"""Offline goal/landing-column audit; never authorizes a flight or publishes ROS."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from audit_vehicle_envelope import audit
from world_geometry import load_obstacles, distances, segment_bound


def offset(text):
    try:result=[float(v) for v in text.split(',')]
    except ValueError as exc:raise argparse.ArgumentTypeError('Finite x,y,z offset required') from exc
    if len(result)!=3 or not np.isfinite(result).all():raise argparse.ArgumentTypeError('Finite x,y,z offset required')
    return result


def evaluate(root, run, profile, candidates, step):
    load=lambda path:json.loads(path.read_text())
    flight=load(run/'flight.json');odom=load(run/'odometry-evaluation.json');scene=load(run/'world.json')
    if flight['localization_epoch']!=odom['epoch']:raise ValueError('Epoch mismatch; no session stitching')
    world=run/'vio_initialization.sdf'
    if hashlib.sha256(world.read_bytes()).hexdigest()!=scene['output_sha256']:raise ValueError('Recorded world hash mismatch')
    obstacles=load_obstacles(world);envelope=audit();radius=envelope['max_orientation_invariant_radius_all_rotor_angles_m']
    alignment=odom['alignment'];r=np.array(alignment['rotation']);t=np.array(alignment['translation_m'])
    if r.shape!=(3,3) or t.shape!=(3,) or not np.isfinite(r).all() or not np.isfinite(t).all() or not np.allclose(r.T@r,np.eye(3),atol=1e-6) or np.linalg.det(r)<.999999:
        raise ValueError('Invalid fixed alignment')
    origin=np.asarray(flight['airborne_origin_enu'],dtype=float)
    if origin.shape!=(3,) or not np.isfinite(origin).all():raise ValueError('Invalid airborne origin')
    cfg=load(profile);historical=cfg.get('goals',[cfg]);rows=[]
    for kind,entries in [('configured',[p['target_offset_enu_m'] for p in historical]),('candidate',candidates)]:
        for value in entries:
            if not isinstance(value,(list,tuple)) or len(value)!=3 or any(type(v) not in (int,float) for v in value):raise ValueError('Three numeric goal offsets required')
            vector=np.asarray(value,dtype=float)
            if vector.shape!=(3,) or not np.isfinite(vector).all():raise ValueError('Invalid goal offset')
            p=r@(origin+vector)+t;d,names=distances([p],obstacles)
            # The ground reference is the fixed pre-enable alignment origin; only nonground obstacles are checked.
            ground=p.copy();ground[2]=t[2]
            rows.append({'kind':kind,'offset_enu_m':vector.tolist(),'world_imu_goal_xyz':p.tolist(),
                         'signed_point_distance_m':float(d[0]),'nearest_obstacle':str(names[0]),
                         'nominal_sphere_margin_m':float(d[0]-radius),'point_inside_obstacle':bool(d[0]<0),
                         'static_non_ground_endpoint_clear':bool(d[0]>radius),
                         'vertical_column_to_preflight_ground_height':segment_bound(p,ground,obstacles,radius,step)})
    reference=r@(origin+np.asarray(historical[0]['target_offset_enu_m']))+t
    for row in rows:
        row['straight_connector_from_first_goal']=segment_bound(reference,row['world_imu_goal_xyz'],obstacles,radius,step)
    inputs=[run/n for n in ['flight.json','odometry-evaluation.json','world.json','runtime-contract.json']]+[world,profile]
    return {'scope':__doc__,'run_id':run.name,'epoch':odom['epoch'],'alignment':alignment,
            'profile_enabled':cfg.get('enabled',True),'nominal_sphere_radius_m':radius,'envelope_source_sha256':envelope['source_sha256'],'max_sampling_step_m':step,
            'goals':rows,'online_goal_map_classification':'NOT_AVAILABLE: no goal-time raw voxel snapshot was captured by this mission recorder',
            'ground_plane_checked':False,'flight_admissible':False,
            'input_sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
            'limitations':['Static scene geometry and conservative nominal body sphere only; no tracking/localization/braking error budget.',
                           'Ground plane omitted deliberately; landing column is only a geometric nonground check, not a landing controller qualification.',
                           'Straight connectors are geometry hypotheses, not recorded or newly approved planner trajectories.',
                           'Endpoint clearance cannot establish connected known-free space; current-epoch map identity, freshness and full trajectory sweep remain required.',
                           'Candidate offsets stay in this offline report; no enabled flight configuration is generated.']}


def plot(report, run, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    obstacles=load_obstacles(run/'vio_initialization.sdf')
    fig,ax=plt.subplots(figsize=(11,6))
    for o in obstacles:
        t=o['transform'];shape=o['shape']
        if o['kind']=='cylinder':
            ax.add_patch(plt.Circle(t[:2,3],shape[0],color='0.5'))
        else:
            corners=np.array([[-shape[0],-shape[1],0],[shape[0],-shape[1],0],[shape[0],shape[1],0],[-shape[0],shape[1],0]])@t[:3,:3].T+t[:3,3]
            ax.add_patch(plt.Polygon(corners[:,:2],color='0.7'))
    for i,row in enumerate(report['goals']):
        p=row['world_imu_goal_xyz'];color='red' if not row['static_non_ground_endpoint_clear'] else ('#1565c0' if row['kind']=='candidate' else '#25852a')
        ax.add_patch(plt.Circle(p[:2],report['nominal_sphere_radius_m'],color=color,fill=False,ls='--'))
        label=f"{row['offset_enu_m'][0]:g}m / {('candidate' if row['kind']=='candidate' else 'old profile')}"
        ax.scatter(*p[:2],c=color,s=25);ax.annotate(label,p[:2],xytext=(0,45 if i%2==0 else -45),textcoords='offset points',ha='center',fontsize=8,arrowprops={'arrowstyle':'-','color':color,'lw':.6})
    ax.set(xlim=(-9,9),ylim=(-3,3),xlabel='World X (m)',ylabel='World Y (m)',title='Offline endpoints only — no online map or flight approval')
    ax.set_aspect('equal');ax.grid(alpha=.2);fig.tight_layout();fig.savefig(output,dpi=160);plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path)
    p.add_argument('--profile',type=Path,default=ROOT/'config/components/navigation/room_loop_goal.json')
    p.add_argument('--candidate-offset',type=offset,action='append',default=[])
    p.add_argument('--max-step-m',type=float,default=.02);p.add_argument('--output',type=Path,required=True);p.add_argument('--plot',action='store_true')
    args=p.parse_args();report=evaluate(ROOT,args.run.resolve(),args.profile.resolve(),args.candidate_offset,args.max_step_m)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    if args.plot:plot(report,args.run,args.output.with_suffix('.png'))
    print(json.dumps(report,indent=2))
