#!/usr/bin/env python3
"""Offline geometric visibility upper bound and historical-map support audit."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'tools/debug_truth'), str(ROOT/'src/own/uav_sim')]
from uav_sim.geometry import calibration
from evaluate_n10_precontact import sample_at, stamps_for
from evaluate_n10_clearance import parse_obstacles
from evaluate_vins_motion import rotation


def cylinder_hits(origin, directions, obstacle, near=0.0, far=np.inf):
    """First optical-ray parameter hitting a closed vertical cylinder."""
    d = np.asarray(directions, dtype=float)
    o = np.asarray(origin, dtype=float) - obstacle['center_xyz_m']
    aa = np.sum(d[:, :2]**2, axis=1)
    bb = 2 * (d[:, 0]*o[0] + d[:, 1]*o[1])
    cc = o[0]**2 + o[1]**2 - obstacle['radius_m']**2
    disc = bb**2 - 4*aa*cc
    root = np.sqrt(np.maximum(disc, 0.0))
    hits = np.full(len(d), np.inf)
    zmin, zmax = obstacle['z_min_m'], obstacle['z_max_m']
    with np.errstate(divide='ignore', invalid='ignore'):
        for sign in (-1, 1):
            t = (-bb + sign*root)/(2*aa)
            z = origin[2] + t*d[:, 2]
            good = ((aa > 1e-15) & (disc >= 0) & (t >= near) & (t <= far)
                    & (z >= zmin) & (z <= zmax))
            hits = np.minimum(hits, np.where(good, t, np.inf))
        for z in (zmin, zmax):
            t = (z-origin[2])/d[:, 2]
            x, y = o[0]+t*d[:, 0], o[1]+t*d[:, 1]
            good = ((np.abs(d[:, 2]) > 1e-15) & (t >= near) & (t <= far)
                    & (x*x+y*y <= obstacle['radius_m']**2))
            hits = np.minimum(hits, np.where(good, t, np.inf))
    return hits


def box_hits(origin, directions, obstacle, near=0.0, far=np.inf):
    yaw = obstacle['yaw_rad']
    c, s = np.cos(yaw), np.sin(yaw)
    r = np.array([[c,s,0],[-s,c,0],[0,0,1]])
    o = r @ (np.asarray(origin)-obstacle['center_xyz_m'])
    d = np.asarray(directions) @ r.T
    half = np.asarray(obstacle['size_xyz_m'])/2
    parallel = np.abs(d) < 1e-15
    with np.errstate(divide='ignore', invalid='ignore'):
        a, b = (-half-o)/d, (half-o)/d
    lower, upper = np.minimum(a,b), np.maximum(a,b)
    inside = np.abs(o) <= half
    lower = np.where(parallel, np.where(inside,-np.inf,np.inf), lower)
    upper = np.where(parallel, np.where(inside,np.inf,-np.inf), upper)
    enter, leave = lower.max(axis=1), upper.min(axis=1)
    t = np.where(enter >= near,enter,leave)
    return np.where((leave >= np.maximum(enter,near)) & (t >= near) & (t <= far),t,np.inf)


def camera_grid(camera, margin, skip):
    u,v = np.meshgrid(np.arange(margin,camera['width']-margin,skip),
                      np.arange(margin,camera['height']-margin,skip))
    k = camera['K']
    rays = np.column_stack(((u.ravel()-k[2])/k[0],
                            (v.ravel()-k[5])/k[4],np.ones(u.size)))
    return u.ravel(),v.ravel(),rays


def evaluate(run):
    run = Path(run).resolve()
    load = lambda path:json.loads(Path(path).read_text())
    pre = load(run/'n10-precontact-diagnostic.json')
    truth = load(run/'debug-truth-evaluation.json')['samples']
    stamps = stamps_for(truth,'stamp_ns')
    model = ROOT/'simulation/models/d435i/model.sdf'
    runtime = load(run/'runtime-contract.json')
    if runtime['files'].get(str(model.relative_to(ROOT))) != hashlib.sha256(model.read_bytes()).hexdigest():
        raise ValueError('camera source model not bound to archived runtime')
    rig = calibration(model)
    camera = rig['cameras']['depth']
    camera_xml = ET.parse(model).getroot().find("model/link/sensor[@name='depth']/camera")
    near,far = [float(camera_xml.findtext('clip/'+key)) for key in ['near','far']]
    param_path = run/'n10-postfault-effective-planner-params.yaml'
    params = next(iter(yaml.safe_load(param_path.read_text()).values()))['ros__parameters']
    for name,index in [('fx',0),('fy',4),('cx',2),('cy',5)]:
        if abs(params['grid_map/'+name]-camera['K'][index])>1e-9:
            raise ValueError('effective camera intrinsic conflicts with source model')
    u,v,rays = camera_grid(camera,params['grid_map/depth_filter_margin'],params['grid_map/skip_pixel'])
    obstacles,_ = parse_obstacles(run/'vio_initialization.sdf')
    observation = load(run/'n10-live-obstacle-observation.json')
    dynamic = observation.get('obstacle',{})
    # The created diagnostic box uses yaw=0 in the frozen protocol.
    if observation.get('gazebo_create',{}).get('acknowledged'):
        box_model = ET.parse(run/'n10-live-replan-box.sdf').getroot().find('model')
        pose = [float(x) for x in box_model.findtext('pose').split()]
        size = [float(x) for x in box_model.findtext('link/collision/geometry/box/size').split()]
        box = {'name':box_model.get('name')+'/link/collision','kind':'vertical_box',
               'center_xyz_m':pose[:3],'size_xyz_m':size,'yaw_rad':pose[5]}
    else:
        box = None
    target = pre['target_obstacle']
    end = pre['first_contact']['stamp_ns']
    meta_path = run/'n10-map-snapshot-before-injection/metadata.json'
    meta = load(meta_path)
    # Keep the snapshot's historic source stamp explicit; never retime it.
    times = sorted(set([meta['last_fused_depth_source_stamp_ns']]+
                       [end-int(t*1e9) for t in [10,5,3,2,1,0]]))
    observations=[]
    r_bo = np.asarray(camera['R_body_optical']).reshape(3,3)
    offset = np.asarray(camera['translation'])-rig['imu']['translation']
    for stamp in times:
        p,gap = sample_at(truth,stamps,stamp,'xyz',40_000_000)
        q,_ = sample_at(truth,stamps,stamp,'q_xyzw',40_000_000,True)
        body = rotation(q)
        origin = p+body@offset
        directions = rays@(body@r_bo).T
        hit = cylinder_hits(origin,directions,target,near,far)
        blockers=list(obstacles)
        if box and stamp>=observation['gazebo_create']['request_sim_ns']:
            blockers.append(box)
        closest = np.full(len(rays),np.inf)
        for obstacle in blockers:
            if obstacle['name']==target['name']:continue
            fn = cylinder_hits if obstacle['kind']=='vertical_cylinder' else box_hits
            closest=np.minimum(closest,fn(origin,directions,obstacle,near,far))
        with np.errstate(divide='ignore',invalid='ignore'):
            ground=-origin[2]/directions[:,2]
        closest=np.minimum(closest,np.where((ground>=near)&(ground<=far),ground,np.inf))
        visible=np.isfinite(hit)&(hit<=closest+1e-9)
        eligible=(visible & (hit>=params['grid_map/depth_filter_mindist'])
                  & (hit<=params['grid_map/depth_filter_maxdist'])
                  & (hit*np.linalg.norm(directions,axis=1)<=params['grid_map/max_ray_length']))
        def bounds(mask):
            return {'u_min':int(u[mask].min()),'u_max':int(u[mask].max()),
                    'v_min':int(v[mask].min()),'v_max':int(v[mask].max())} if mask.any() else None
        observations.append({'source_stamp_ns':stamp,'truth_bracket_ns':gap,
            'camera_origin_world_m':origin.tolist(),'sampled_rays':len(rays),
            'target_intersection_rays_ignoring_occlusion':int(np.isfinite(hit).sum()),
            'unoccluded_target_rays':int(visible.sum()),'mapper_hit_eligible_geometric_rays':int(eligible.sum()),
            'unoccluded_pixel_bounds':bounds(visible),'eligible_pixel_bounds':bounds(eligible)})
    snap_path=meta_path.parent/meta['archive']['file']
    if hashlib.sha256(snap_path.read_bytes()).hexdigest()!=meta['archive']['sha256']:
        raise ValueError('snapshot archive digest mismatch')
    if meta['epoch']!=pre['epoch']:
        raise ValueError('snapshot epoch differs')
    arrays=np.load(snap_path);occ,inf=arrays['occupancy'],arrays['inflated']
    align=np.asarray(pre['fixed_alignment']['rotation']);translation=np.asarray(pre['fixed_alignment']['translation_m'])
    origin=np.asarray(meta['origin_m']);res=meta['resolution_m']
    def query(world):
        odom=align.T@(np.asarray(world)-translation)
        cell=np.floor((odom-origin)/res).astype(int)
        if np.any(cell<0) or np.any(cell>=occ.shape):return None
        index=tuple(cell)
        return {'raw_code':int(occ[index]),'inflated':bool(inf[index]),'cell':cell.tolist()}
    surface=[]
    center=np.asarray(target['center_xyz_m'])
    for z in [.5,1.,1.5]:
        for theta in np.linspace(0,2*np.pi,72,endpoint=False):
            surface.append(query([center[0]+target['radius_m']*np.cos(theta),
                                  center[1]+target['radius_m']*np.sin(theta),z]))
    counts={str(code):sum(row is not None and row['raw_code']==code for row in surface) for code in [-1,0,100]}
    commands=[{'command_source_stamp_ns':row['source_stamp_ns'],
               'historical_snapshot_depth_source_ns':meta['last_fused_depth_source_stamp_ns'],
               'age_of_snapshot_at_command_sim_s':(row['source_stamp_ns']-meta['last_fused_depth_source_stamp_ns'])/1e9,
               'historical_cell':query(row['command_world_m'])}
              for row in pre['diagnostic_samples']]
    files=[model,param_path,meta_path,snap_path,run/'n10-precontact-diagnostic.json',run/'debug-truth-evaluation.json',run/'vio_initialization.sdf',run/'runtime-contract.json',
           run/'n10-live-obstacle-observation.json',run/'n10-live-replan-box.sdf']
    return {'schema':'n10-camera-historical-map-support/v1','run_id':run.name,
        'classification':'offline ideal geometric visibility and dated map only; not current map attribution',
        'camera':camera,'sensor_clip_optical_depth_m':[near,far],
        'mapper_sampling_and_range':{k:v for k,v in params.items() if k in [
            'grid_map/depth_filter_margin','grid_map/skip_pixel','grid_map/depth_filter_mindist',
            'grid_map/depth_filter_maxdist','grid_map/max_ray_length']},
        'visibility_samples':observations,
        'historical_surface_samples':{'count':len(surface),'raw_counts':counts,
            'inflated_count':sum(row is not None and row['inflated'] for row in surface),
            'depth_source_ns':meta['last_fused_depth_source_stamp_ns']},
        'historical_command_queries':commands,
        'input_sha256':{str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in files},
        'limits':['Ray hits are ideal geometric opportunities, not observed valid depth, occupied voxels, or planner inputs.',
            'Uses true calibrated poses solely offline, and the declared static world plus acknowledged diagnostic box.',
            'Pixel grid, clipping, depth and max-ray limits are accounted for; rendering, quantization, noise, fusion votes and timing are not replayed.',
            'The only complete snapshot is earlier than contact and cannot establish collision-time map classification.',
            'No flight-control gate, threshold or safety pass is produced.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir',type=Path)
    args=parser.parse_args()
    result=evaluate(args.run_dir)
    path=args.run_dir/'n10-camera-map-support.json'
    path.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'output':str(path),'visibility':result['visibility_samples'],
                      'historic_surface':result['historical_surface_samples'],
                      'historic_commands':result['historical_command_queries']},indent=2))

if __name__=='__main__':main()
