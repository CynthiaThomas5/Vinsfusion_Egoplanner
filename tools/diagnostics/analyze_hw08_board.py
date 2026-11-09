#!/usr/bin/env python3
"""Offline board-axis comparison and held-out rigid rotation estimate.

Clock responses map FC HRT into the recording host epoch. Static median gyro
biases are removed for comparison only; raw data/configuration are unchanged.
"""
import argparse
import json
from pathlib import Path
import numpy as np


def fit_rotation(camera, body):
    """Wahba fit of R_BI from simultaneous, baseline-corrected gyro vectors."""
    u, singular, vt = np.linalg.svd(body.T @ camera)
    rotation = u @ np.diag([1.,1.,np.linalg.det(u @ vt)]) @ vt
    return rotation, singular


def analyze(path):
    imu, fc, clocks, attitude = [], [], [], []
    with path.open() as source:
        for line in source:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                if line.endswith('\n'):
                    raise
                break  # A live snapshot may end in one incomplete final line.
            data, phase = row['data'], row['phase']
            if row['kind'] == 'imu':
                imu.append((data['stamp_ns'], data['gyro'], phase))
            elif row['kind'] == 'timesync_pair' and data['rtt_ns'] <= 10_000_000:
                clocks.append(data)
            elif row['kind'] == 'mavlink':
                if data['mavpackettype'] == 'HIGHRES_IMU':
                    fc.append((data['time_usec']*1000,
                               [data['xgyro'],data['ygyro'],data['zgyro']], phase))
                elif data['mavpackettype'] == 'ATTITUDE':
                    attitude.append((phase, [data['roll'],data['pitch'],data['yaw']]))
    if not clocks or not imu or not fc:
        raise ValueError('Need actual camera/FC IMU samples and clock responses')
    origin = imu[0][0]
    clocks.sort(key=lambda x:x['fc_hrt_ns'])
    hrt0 = clocks[0]['fc_hrt_ns']
    clock_x = np.array([x['fc_hrt_ns']-hrt0 for x in clocks],dtype=float)
    clock_y = np.array([x['host_midpoint_system_ns']-origin for x in clocks],dtype=float)
    fc_t = np.interp([x[0]-hrt0 for x in fc], clock_x, clock_y)/1e9
    imu_t = np.array([x[0]-origin for x in imu],dtype=float)/1e9
    cam_g = np.array([x[1] for x in imu]);fc_g = np.array([x[1] for x in fc])
    cam_rest = np.array([x[2]=='baseline' for x in imu])
    fc_rest = np.array([x[2]=='baseline' for x in fc])
    if cam_rest.sum()<100 or fc_rest.sum()<30:
        raise ValueError('Insufficient independent static bias baseline')
    cam_bias = np.median(cam_g[cam_rest],axis=0)
    fc_bias = np.median(fc_g[fc_rest],axis=0)
    cam_interp = np.column_stack([np.interp(fc_t,imu_t,cam_g[:,i]-cam_bias[i]) for i in range(3)])
    # Predeclared optical->FRD hypothesis: (right,down,forward)->(forward,right,down).
    cam_body = cam_interp[:,[2,0,1]]
    fc_body = fc_g-fc_bias
    indices = np.clip(np.searchsorted(imu_t,fc_t),1,len(imu_t)-1)
    gap = imu_t[indices]-imu_t[indices-1]
    valid = ((fc_t >= imu_t[0]) & (fc_t <= imu_t[-1]) & (gap <= .03)
             & (np.array([x[0] for x in fc]) >= clocks[0]['fc_hrt_ns'])
             & (np.array([x[0] for x in fc]) <= clocks[-1]['fc_hrt_ns']))
    result = {'clock_pairs_under_10ms':len(clocks),
              'rtt_ms_max':max(x['rtt_ns'] for x in clocks)/1e6,
              'camera_static_bias_rad_s':cam_bias.tolist(),
              'fc_static_bias_rad_s':fc_bias.tolist(),'phases':{}}
    fc_phases = np.array([x[2] for x in fc])
    for name in ('yaw_left_return','pitch_up_return','roll_right_return'):
        select = (fc_phases==name) & valid
        moving = select & (np.linalg.norm(fc_body,axis=1)>.04)
        moving &= np.linalg.norm(cam_body,axis=1)>.04
        row = {'fc_samples':int(select.sum()),'moving_samples':int(moving.sum())}
        angles = np.array([x[1] for x in attitude if x[0]==name])
        if len(angles):
            angles = np.unwrap(angles,axis=0)*180/np.pi
            row['angle_start_end_deg']=[angles[0].tolist(),angles[-1].tolist()]
            row['angle_min_max_deg']=[angles.min(axis=0).tolist(),angles.max(axis=0).tolist()]
        if moving.sum():
            a,b=fc_body[moving],cam_body[moving]
            row['gyro_rmse_vector_rad_s']=float(np.sqrt(np.mean(np.sum((a-b)**2,axis=1))))
            cos=np.sum(a*b,axis=1)/(np.linalg.norm(a,axis=1)*np.linalg.norm(b,axis=1))
            row['direction_cos_median']=float(np.median(cos))
            row['dominant_fc_axis']=int(np.argmax(np.sum(a*a,axis=0)))
            row['dominant_camera_mapped_axis']=int(np.argmax(np.sum(b*b,axis=0)))
        result['phases'][name]=row
    train = np.zeros(len(fc),dtype=bool)
    holdout = np.zeros(len(fc),dtype=bool)
    outward_counts, return_counts = {}, {}
    for name, axis, outward_sign in (('yaw_left_return',2,-1),
                                     ('pitch_up_return',1,1), ('roll_right_return',0,1)):
        selected = (fc_phases==name) & valid
        selected &= np.linalg.norm(fc_body,axis=1)<1.5
        outward = selected & (fc_body[:,axis]*outward_sign>.04)
        returning = selected & (fc_body[:,axis]*outward_sign<-.04)
        train |= outward;holdout |= returning
        outward_counts[name]=int(outward.sum());return_counts[name]=int(returning.sum())
    if min(outward_counts.values())>=20 and min(return_counts.values())>=20:
        rotation, singular = fit_rotation(cam_interp[train],fc_body[train])
        prediction = cam_interp[holdout] @ rotation.T
        error = prediction-fc_body[holdout]
        nominal = np.array([[0,0,1],[1,0,0],[0,1,0]])
        delta = rotation @ nominal.T
        result['rotation_estimate'] = {
            'scope':'outward motions fit; opposite return motions held out',
            'R_body_imu':rotation.tolist(),'singular_values':singular.tolist(),
            'outward_counts':outward_counts,'return_counts':return_counts,
            'determinant':float(np.linalg.det(rotation)),
            'delta_from_nominal_deg':float(np.arccos(np.clip((np.trace(delta)-1)/2,-1,1))*180/np.pi),
            'return_gyro_rmse_rad_s':float(np.sqrt(np.mean(np.sum(error**2,axis=1)))),
            'nominal_return_gyro_rmse_rad_s':float(np.sqrt(np.mean(np.sum(
                (cam_body[holdout]-fc_body[holdout])**2,axis=1))))}
        # Residual diagnostic: choose lag using outward samples only, then keep
        # both lag and rotation fixed for independent opposite return samples.
        scan=[]
        for lag in np.linspace(-.1,.1,101):
            trial=np.column_stack([np.interp(fc_t[train]+lag,imu_t,cam_g[:,i]-cam_bias[i])
                                   for i in range(3)])
            trial_rotation,_=fit_rotation(trial,fc_body[train])
            score=float(np.sqrt(np.mean(np.sum((trial @ trial_rotation.T-fc_body[train])**2,axis=1))))
            scan.append((score,float(lag),trial_rotation))
        score,lag,lag_rotation=min(scan,key=lambda x:x[0])
        returned=np.column_stack([np.interp(fc_t[holdout]+lag,imu_t,cam_g[:,i]-cam_bias[i])
                                  for i in range(3)])
        lag_delta=lag_rotation @ nominal.T
        result['lag_diagnostic']={
            'selection':'outward training error only; no production stamp changes',
            'camera_timestamp_shift_s':lag,'training_rmse_rad_s':score,
            'return_rmse_rad_s':float(np.sqrt(np.mean(np.sum(
                (returned @ lag_rotation.T-fc_body[holdout])**2,axis=1)))),
            'R_body_imu':lag_rotation.tolist(),
            'delta_from_nominal_deg':float(np.arccos(np.clip((np.trace(lag_delta)-1)/2,-1,1))*180/np.pi),
            'scan_outward_rmse':[[x[1],x[0]] for x in scan]}
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('path',type=Path)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=analyze(a.path);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
