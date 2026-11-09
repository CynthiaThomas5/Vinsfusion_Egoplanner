#!/usr/bin/env python3
"""Fit R_BI from two stationary gravity directions; hold a third pose out.

No angle supplied by the operator enters the fit. Translation is not estimated
from gravity. This checks the reported IMU/FC coordinate relation, including
their existing calibration; it is not an external attitude ground truth.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from analyze_hw08_board import fit_rotation


def estimate(path):
    rows=[json.loads(x) for x in path.read_text().splitlines() if x]
    groups={}
    for phase in ('baseline','static_pitch_hold','static_roll_hold','static_level_hold'):
        group={}
        for kind in ('imu','mavlink'):
            data=[x['data'] for x in rows if x['phase']==phase and x['kind']==kind
                  and (kind=='imu' or x['data'].get('mavpackettype')=='HIGHRES_IMU')]
            if len(data)<30:
                raise ValueError('Insufficient stationary samples: '+phase+'/'+kind)
            accel=np.array([x['accel'] if kind=='imu' else [x[k] for k in ('xacc','yacc','zacc')]
                            for x in data])
            gyro=np.array([x['gyro'] if kind=='imu' else [x[k] for k in ('xgyro','ygyro','zgyro')]
                           for x in data])
            unit=accel/np.linalg.norm(accel,axis=1)[:,None]
            center=np.median(unit,axis=0);center/=np.linalg.norm(center)
            spread=np.degrees(np.arccos(np.clip(unit@center,-1,1)))
            group[kind]=dict(samples=len(data),unit_gravity=center.tolist(),
                accel_norm_median_m_s2=float(np.median(np.linalg.norm(accel,axis=1))),
                gyro_median_rad_s=np.median(gyro,axis=0).tolist(),
                gyro_max_deviation_rad_s=float(np.max(np.linalg.norm(gyro-np.median(gyro,axis=0),axis=1))),
                gravity_spread_p95_deg=float(np.percentile(spread,95)))
        groups[phase]=group
    train=('baseline','static_pitch_hold')
    a=np.array([groups[x]['imu']['unit_gravity'] for x in train])
    b=np.array([groups[x]['mavlink']['unit_gravity'] for x in train])
    rotation,singular=fit_rotation(a,b)
    nominal=np.array([[0,0,1],[1,0,0],[0,1,0]])
    for phase,group in groups.items():
        camera=np.array(group['imu']['unit_gravity']);body=np.array(group['mavlink']['unit_gravity'])
        for name,r in (('fitted',rotation),('nominal',nominal)):
            group[name+'_gravity_residual_deg']=float(np.degrees(np.arccos(np.clip((r@camera)@body,-1,1))))
        group['used_for_fit']=phase in train
    # Separately expose a user-accepted approximate constant for a flexible
    # bench. This uses every pose and therefore has NO independent holdout.
    # Keep the failed two-pose/holdout audit above unchanged.
    all_camera=np.array([g['imu']['unit_gravity'] for g in groups.values()])
    all_body=np.array([g['mavlink']['unit_gravity'] for g in groups.values()])
    from scipy.optimize import least_squares
    def candidate(angles):
        roll,pitch=angles
        cr,sr,cp,sp=np.cos(roll),np.sin(roll),np.cos(pitch),np.sin(pitch)
        rx=np.array([[1,0,0],[0,cr,-sr],[0,sr,cr]])
        ry=np.array([[cp,0,sp],[0,1,0],[-sp,0,cp]])
        return ry@rx@nominal
    angles=least_squares(lambda x: (all_camera@candidate(x).T-all_body).ravel(),[0.,0.]).x
    approximate=candidate(angles)
    residual=np.degrees(np.arccos(np.clip(np.sum((all_camera@approximate.T)*all_body,axis=1),-1,1)))
    return dict(scope='two static gravity directions fitted; independent static roll/level held out',
        R_body_imu=rotation.tolist(),determinant=float(np.linalg.det(rotation)),
        singular_values=singular.tolist(),
        training_gravity_separation_camera_deg=float(np.degrees(np.arccos(np.clip(a[0]@a[1],-1,1)))),
        training_gravity_separation_fc_deg=float(np.degrees(np.arccos(np.clip(b[0]@b[1],-1,1)))),
        groups=groups,approximate_all_static_candidate=dict(
            scope='all four static poses fitted with relative yaw fixed at user-declared parallel-forward nominal; no independent validation; flexible bench approximation only',
            roll_pitch_correction_deg=np.degrees(angles).tolist(),
            R_body_imu=approximate.tolist(),
            gravity_residual_deg=dict(zip(groups.keys(),residual.tolist()))))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path',type=Path)
    args=parser.parse_args()
    print(json.dumps(estimate(args.path),indent=2))
