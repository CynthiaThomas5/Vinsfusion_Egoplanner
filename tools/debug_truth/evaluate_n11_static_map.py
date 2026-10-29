#!/usr/bin/env python3
"""Offline static-wall measurement using the frozen N10 numerical limits."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate_n10_clearance import parse_obstacles


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path): return json.loads(Path(path).read_text())

def wall_measurements(raw, inflated, origin, resolution, rotation, translation, walls):
    if raw.shape != inflated.shape or raw.ndim != 3 or not np.isfinite(resolution) or resolution <= 0:
        raise ValueError('invalid snapshot geometry')
    if not np.isin(raw, [-1,0,100]).all() or not np.isin(inflated,[0,1]).all():
        raise ValueError('invalid occupancy codes')
    indices=np.argwhere(raw != -1)
    centers=(np.asarray(origin)+(indices+0.5)*resolution)@rotation.T+translation
    values=raw[tuple(indices.T)]
    corners=np.array([[a,b,c] for a in [-1,1] for b in [-1,1] for c in [-1,1]])*resolution/2
    corner_world=corners@rotation.T
    rows=[]
    for wall in walls:
        yaw=wall['yaw_rad'];c,s=math.cos(yaw),math.sin(yaw)
        basis=np.array([[c,-s,0],[s,c,0],[0,0,1]])
        local=(centers-np.array(wall['center_xyz_m']))@basis
        half=np.array(wall['size_xyz_m'])/2
        excess=np.abs(local)-half
        distance=np.linalg.norm(np.maximum(excess,0),axis=1)
        inside=np.all(excess<=0,axis=1)
        distance[inside]=np.min(half-np.abs(local[inside]),axis=1)
        supported=(values==100)&(distance<=1.5*resolution)
        # Full-cell solid membership: centers alone cannot establish false free.
        full_inside=np.all(np.abs(local[:,None,:]+corner_world[None,:,:]@basis)<=half+1e-9,axis=(1,2))
        rows.append({'wall':wall['name'],'surface_sample_count':int(supported.sum()),
                     'surface_error_max_m':float(distance[supported].max()) if supported.any() else None,
                     'solid_known_cell_count':int(full_inside.sum()),
                     'solid_free_cell_count':int(np.count_nonzero(full_inside&(values==0))),
                     'supported_inflated_count':int(np.count_nonzero(inflated[tuple(indices[supported].T)]))})
    return rows


def visibility_measurements(raw, origin, resolution, rotation, translation,
                            walls, camera_origin, camera_rotation, camera):
    """Whole-voxel ray occlusion in wall ROIs; independent visible free controls."""
    from evaluate_n10_camera_map_support import box_hits
    signs=np.array([[a,b,c] for a in [-1,1] for b in [-1,1] for c in [-1,1]])
    offsets=signs*resolution/2
    world_offsets=offsets@rotation.T
    free_indices=np.argwhere(raw==0)
    visible_free=0
    for start in range(0,len(free_indices),20000):
        indices=free_indices[start:start+20000]
        centers=(np.asarray(origin)+(indices+.5)*resolution)@rotation.T+translation
        corners=centers[:,None,:]+world_offsets
        optical=(corners-camera_origin)@camera_rotation
        z=optical[:,:,2]
        k=camera['K']; good=(z>camera['near'])&(z<camera['far'])
        u=k[0]*optical[:,:,0]/np.maximum(z,1e-12)+k[2]
        v=k[4]*optical[:,:,1]/np.maximum(z,1e-12)+k[5]
        good&=(u>=0)&(u<camera['width'])&(v>=0)&(v<camera['height'])&(corners[:,:,2]>0)
        candidates=np.flatnonzero(np.all(good,axis=1))
        if not len(candidates): continue
        targets=corners[candidates].reshape(-1,3)
        blocked=np.zeros(len(targets),dtype=bool)
        for wall in walls:
            blocked|=box_hits(camera_origin,targets-camera_origin,wall,0,1-1e-8)<1
        visible_free+=int(np.count_nonzero(~blocked.reshape(-1,8).any(axis=1)))
    occluded_count=0;occluded_free_count=0
    for wall in walls:
        yaw=wall['yaw_rad'];c,s=math.cos(yaw),math.sin(yaw)
        basis=np.array([[c,-s,0],[s,c,0],[0,0,1]])
        # Restrict work to a one-metre band around each static wall.
        half=np.array(wall['size_xyz_m'])/2+1
        local_corners=signs*half
        world=local_corners@basis.T+wall['center_xyz_m']
        grid=((world-translation)@rotation-np.asarray(origin))/resolution
        low=np.maximum(np.floor(grid.min(axis=0)).astype(int),0)
        high=np.minimum(np.ceil(grid.max(axis=0)).astype(int),raw.shape)
        if np.any(high<=low):continue
        ranges=[np.arange(low[i],high[i]) for i in range(3)]
        indices=np.stack(np.meshgrid(*ranges,indexing='ij'),axis=-1).reshape(-1,3)
        for start in range(0,len(indices),20000):
            idx=indices[start:start+20000]
            centers=(np.asarray(origin)+(idx+.5)*resolution)@rotation.T+translation
            corners=centers[:,None,:]+world_offsets
            targets=corners.reshape(-1,3)
            hits=box_hits(camera_origin,targets-camera_origin,wall,0,1-1e-8)
            occluded=(hits.reshape(-1,8)<1).all(axis=1)&(corners[:,:,2]>0).all(axis=1)
            occluded_count+=int(occluded.sum())
            occluded_free_count+=int(np.count_nonzero(occluded&(raw[tuple(idx.T)]==0)))
    return {'visible_free_control_count':visible_free,'fully_occluded_roi_cell_count':occluded_count,
            'fully_occluded_raw_free_count':occluded_free_count,
            'method':'all eight voxel-corner rays hit the same static wall before reaching the voxel; static one-metre wall ROI'}


def evaluate(run, config):
    run=Path(run);cfg=load(config);obs=load(run/'n11-static-map-observation.json')
    alignment=load(run/'arrival-evaluation.json');flight=load(run/'flight.json')
    contract=load(run/'runtime-contract.json');launch=load(run/'n11-launch-record.json')
    identity={'run_id':run.name,'runtime_contract_sha256':contract['sha256'],
              'goal_id':flight['goal_id'],'epoch':flight['localization_epoch'],'map_id':launch['map_id']}
    rotation=np.asarray(alignment['ground_rotation']);translation=np.asarray(alignment['ground_translation'])
    if rotation.shape!=(3,3) or translation.shape!=(3,) or not np.isfinite(rotation).all() or not np.isfinite(translation).all():
        raise ValueError('invalid fixed PRESTREAM alignment')
    if not np.allclose(rotation.T@rotation,np.eye(3),atol=1e-6) or not np.isclose(np.linalg.det(rotation),1,atol=1e-6):
        raise ValueError('alignment is not a rigid rotation')
    walls,skipped=parse_obstacles(run/'vio_initialization.sdf')
    if len(walls)!=4 or any(w['kind']!='vertical_box' for w in walls):
        raise ValueError('expected exactly four static wall boxes')
    sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[2]/'src/own/uav_sim')]
    from truth_reference import imu_truth_samples
    from uav_sim.geometry import calibration
    from evaluate_n10_precontact import sample_at, stamps_for
    from evaluate_vins_motion import rotation as quaternion_rotation
    import xml.etree.ElementTree as ET
    camera_path=Path(__file__).resolve().parents[2]/'simulation/models/d435i/model.sdf'
    if sha(camera_path)!=contract['files'].get('simulation/models/d435i/model.sdf'):
        raise ValueError('camera model identity mismatch')
    rig=calibration(camera_path);camera=dict(rig['cameras']['depth'])
    clip=ET.parse(camera_path).getroot().find("model/link/sensor[@name='depth']/camera/clip")
    camera.update(near=float(clip.findtext('near')),far=float(clip.findtext('far')))
    truth,_=imu_truth_samples(run,load(run/'debug-truth-evaluation.json'))
    truth_stamps=stamps_for(truth,'stamp_ns')
    results=[];rejected=[];visibility=[]
    for row in obs['snapshots']:
        try:
            if any(row[k]!=identity[k] for k in ('goal_id','epoch','map_id')) or row['frame_id']!='odom_'+identity['epoch']:
                raise ValueError('snapshot goal/epoch/map/frame mismatch')
            path=(run/row['path']).resolve()
            if not path.is_relative_to(run.resolve()) or sha(path)!=row['sha256']:
                raise ValueError('snapshot path/hash mismatch')
            if not (0<row['source_stamp_ns']<=row['fusion_stamp_ns']<=row['snapshot_stamp_ns']):
                raise ValueError('snapshot source/fusion ordering invalid')
            with np.load(path,allow_pickle=False) as arrays:
                if list(arrays['occupancy'].shape)!=row['shape']: raise ValueError('snapshot shape mismatch')
                measured=wall_measurements(arrays['occupancy'],arrays['inflated'],row['origin_m'],row['resolution_m'],rotation,translation,walls)
            p,gap=sample_at(truth,truth_stamps,row['source_stamp_ns'],'xyz',4_000_001)
            q,_=sample_at(truth,truth_stamps,row['source_stamp_ns'],'q_xyzw',4_000_001,True)
            body=quaternion_rotation(q)
            camera_origin=p+body@(np.asarray(camera['translation'])-rig['imu']['translation'])
            optical_rotation=body@np.asarray(camera['R_body_optical']).reshape(3,3)
            with np.load(path,allow_pickle=False) as arrays:
                visible=visibility_measurements(arrays['occupancy'],row['origin_m'],row['resolution_m'],rotation,translation,walls,camera_origin,optical_rotation,camera)
            visibility.append(visible)
            results.extend(measured)
        except (ValueError,KeyError,OSError) as exc: rejected.append(str(exc))
    supported=[r['surface_error_max_m'] for r in results if r['surface_sample_count']]
    solid=sum(r['solid_known_cell_count'] for r in results);false_free=sum(r['solid_free_cell_count'] for r in results)
    limit=cfg['metrics']['raw_map_surface_geometry']['thresholds']['surface_center_error_sample_max_m']
    classification_limit=cfg['metrics']['raw_map_classification']['thresholds']['truth_occluded_raw_free_count_max']
    surface='FAIL' if supported and max(supported)>limit else 'INSUFFICIENT' if not supported or rejected else 'PASS'
    occluded_free=sum(v['fully_occluded_raw_free_count'] for v in visibility)
    controls=sum(v['visible_free_control_count'] for v in visibility)
    occluded_support=sum(v['fully_occluded_roi_cell_count'] for v in visibility)
    classification=('FAIL' if false_free>classification_limit or occluded_free>classification_limit
                    else 'PASS' if controls and occluded_support and not rejected else 'INSUFFICIENT')
    return {'schema':'n11-static-map-evaluation/v1','run_identity':identity,'acceptance_config_sha256':sha(config),
            'active_world_sha256':sha(run/'vio_initialization.sdf'),'evaluator_sha256':sha(__file__),
            'observation_sha256':sha(run/'n11-static-map-observation.json'),'wall_measurements':results,
            'rejected_snapshots':rejected,'visibility_controls':visibility,'metrics':{
                'raw_map_surface_geometry':{'status':surface,'maximum_observed_error_m':max(supported) if supported else None,'threshold_m':limit},
                'raw_map_classification':{'status':classification,'fully_solid_known_cells':solid,'fully_solid_free_cells':false_free,'fully_occluded_free_cells':occluded_free,'visible_free_controls':controls,'threshold':classification_limit}},
            'limitation':'Static wall ROI and current-source visible-free controls only; unobserved faces are not inferred. No truth feedback.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--config',type=Path,default=Path('config/acceptance.json'));p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.write_text(json.dumps(evaluate(a.run,a.config),indent=2,allow_nan=False)+'\n')
