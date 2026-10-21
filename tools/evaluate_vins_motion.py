#!/usr/bin/env python3
"""Measure a raw VIO trajectory against isolated truth using ONE rigid SE(3), no scale."""
import argparse
import json
from pathlib import Path
import numpy as np


def rigid_alignment(estimated, reference):
    estimated, reference = np.asarray(estimated), np.asarray(reference)
    if estimated.shape != reference.shape or estimated.ndim != 2 or estimated.shape[1] != 3 or len(estimated)<3:
        raise ValueError('Need at least three paired 3D samples')
    if not np.isfinite(estimated).all() or not np.isfinite(reference).all():
        raise ValueError('Non-finite trajectory')
    x,y = estimated-estimated.mean(axis=0),reference-reference.mean(axis=0)
    u,_,vt = np.linalg.svd(x.T@y)
    correction = np.eye(3)
    correction[2,2] = np.linalg.det(vt.T@u.T)
    rotation = vt.T@correction@u.T
    translation = reference.mean(axis=0)-rotation@estimated.mean(axis=0)
    return rotation,translation


def rotation(q):
    q=np.asarray(q,dtype=float)
    norm=np.linalg.norm(q)
    if not np.isfinite(norm) or norm<1e-9:
        raise ValueError('Invalid quaternion')
    x,y,z,w=q/norm
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                     [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                     [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])


def evaluate(motion, odometry):
    truth=motion['truth']
    states=odometry['optimized']
    tt=np.array([p['stamp'] for p in truth])
    et=np.array([p['stamp_ns']*1e-9 for p in states])
    if len(tt)<20 or len(et)<20 or not (np.diff(tt)>0).all() or not (np.diff(et)>0).all():
        raise ValueError('Missing samples or non-increasing source stamps; no timestamp repair permitted')
    if np.ptp(tt)<1:
        raise ValueError('Truth timestamps do not cover an actual time interval')
    valid=(et>=tt[0]) & (et<=tt[-1])
    et=et[valid]
    ep=np.array([p['position'] for p in states])[valid]
    if len(et)<20:
        raise ValueError('Insufficient overlapping trajectories')
    tp=np.array([p['position'] for p in truth])
    reference=np.column_stack([np.interp(et,tt,tp[:,axis]) for axis in range(3)])
    r,t=rigid_alignment(ep,reference)
    errors=np.linalg.norm((r@ep.T).T+t-reference,axis=1)
    tq=np.array([p['quaternion'] for p in truth])
    for i in range(1,len(tq)):
        if tq[i]@tq[i-1]<0:
            tq[i]*=-1
    eq=np.array([p['quaternion'] for p in states])[valid]
    quats=np.column_stack([np.interp(et,tt,tq[:,axis]) for axis in range(4)])
    angles=np.array([np.arccos(np.clip((np.trace(rotation(b).T@r@rotation(a))-1)/2,-1,1)) for a,b in zip(eq,quats)])
    imu=motion['imu']
    it=np.array([m['stamp'] for m in imu])
    if len(it)<20 or not (np.diff(it)>0).all():
        raise ValueError('Invalid IMU timestamps')
    acceleration=np.gradient(np.gradient(tp,tt,axis=0),tt,axis=0)
    expected_specific=np.array([rotation(q).T@(a-np.array([0,0,-9.80665])) for q,a in zip(tq,acceleration)])
    observed_acc=np.column_stack([np.interp(tt,it,[m['acceleration'][axis] for m in imu]) for axis in range(3)])
    yaw=np.unwrap(np.array([np.arctan2(rotation(q)[1,0],rotation(q)[0,0]) for q in tq]))
    expected_rate=np.gradient(yaw,tt)
    observed_rate=np.interp(tt,it,[m['gyro'][2] for m in imu])
    interior=(tt>max(it[0],tt[0])+.2)&(tt<min(it[-1],tt[-1])-.2)
    if np.count_nonzero(interior)<20:
        raise ValueError('Insufficient IMU / truth overlap')
    return {'scope':'Exploratory sensor-rig measurement, not frozen formal flight acceptance',
            'alignment':'Single SE(3), scale fixed to 1, no segment realignment', 'paired_samples':len(et),
            'overlap_seconds':float(et[-1]-et[0]), 'truth_position_span_m':np.ptp(reference,axis=0).tolist(),
            'truth_yaw_span_deg':float(np.ptp(yaw)*180/np.pi),
            'position_rmse_m':float(np.sqrt(np.mean(errors**2))), 'position_p95_m':float(np.percentile(errors,95)),
            'position_max_m':float(errors.max()), 'orientation_rmse_deg':float(np.sqrt(np.mean(angles**2))*180/np.pi),
            'orientation_max_deg':float(angles.max()*180/np.pi), 'alignment_rotation':r.tolist(), 'alignment_translation':t.tolist(),
            'imu_specific_force_rmse_m_s2':float(np.sqrt(np.mean((observed_acc[interior]-expected_specific[interior])**2))),
            'imu_yaw_rate_rmse_rad_s':float(np.sqrt(np.mean((observed_rate[interior]-expected_rate[interior])**2)))}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--motion',type=Path,required=True)
    parser.add_argument('--odometry',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=evaluate(json.loads(args.motion.read_text()),json.loads(args.odometry.read_text()))
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
