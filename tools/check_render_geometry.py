#!/usr/bin/env python3
"""Offline debug check: project known calibration markers into recorded mono images."""
import argparse
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import cv2
import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import Image
from evaluate_vins_motion import rotation

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/own/uav_sim'))
from uav_sim.geometry import calibration


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--bag',type=Path,required=True)
    parser.add_argument('--motion',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    truth=json.loads(args.motion.read_text())['truth']
    tt=np.array([p['stamp'] for p in truth])
    if len(tt)<20 or not (np.diff(tt)>0).all():
        raise ValueError('Invalid truth timestamps')
    poses=np.array([p['position'] for p in truth])
    quats=np.array([p['quaternion'] for p in truth])
    for i in range(1,len(quats)):
        if quats[i]@quats[i-1]<0:quats[i]*=-1
    wall=ET.parse(ROOT/'simulation/worlds/sensor_calibration.sdf').find('world/model[@name="calibration_wall"]')
    wall_pose=np.array([float(v) for v in wall.findtext('pose').split()])
    if np.any(wall_pose[3:]!=0):raise ValueError('Marker projection currently requires aligned wall')
    points=[]
    for visual in wall.findall('link/visual'):
        if not visual.get('name').startswith('marker_'):continue
        pose=np.array([float(v) for v in visual.findtext('pose').split()])
        size=np.array([float(v) for v in visual.findtext('geometry/box/size').split()])
        if np.any(pose[3:]!=0):raise ValueError('Aligned markers required')
        points.extend(wall_pose[:3]+pose[:3]+[-size[0]/2,sy*size[1]/2,sz*size[2]/2] for sy in [-1,1] for sz in [-1,1])
    points=np.array(points)
    camera=calibration(ROOT/'simulation/models/d435i/model.sdf')['cameras']['infra1']
    k=np.array(camera['K']).reshape(3,3)
    rc=np.array(camera['R_body_optical']).reshape(3,3)
    tc=np.array(camera['translation'])
    reader=rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=str(args.bag),storage_id='mcap'),rosbag2_py.ConverterOptions('',''))
    samples=[]
    last=-1e9
    while reader.has_next():
        topic,data,_=reader.read_next()
        if topic!='/sensors/d435i/infra1/image_rect':continue
        msg=deserialize_message(data,Image)
        stamp=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
        if stamp<tt[0] or stamp>tt[-1] or stamp-last<.5:continue
        last=stamp
        p=np.array([np.interp(stamp,tt,poses[:,i]) for i in range(3)])
        q=np.array([np.interp(stamp,tt,quats[:,i]) for i in range(4)])
        rb=rotation(q)
        pc=(rc.T@rb.T@(points-p-rb@tc).T).T
        expected=(k@pc.T).T
        expected=expected[:,:2]/expected[:,2:]
        visible=(pc[:,2]>.2)&(expected[:,0]>5)&(expected[:,0]<msg.width-5)&(expected[:,1]>5)&(expected[:,1]<msg.height-5)
        expected=expected[visible]
        gray=np.frombuffer(bytes(msg.data),dtype=np.uint8).reshape(msg.height,msg.step)[:,:msg.width].copy()
        corners=cv2.goodFeaturesToTrack(gray,180,.01,5)
        if corners is None or not len(expected):continue
        corners=cv2.cornerSubPix(gray,corners,(5,5),(-1,-1),(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,30,.001)).reshape(-1,2)
        distances=np.linalg.norm(expected[:,None,:]-corners[None,:,:],axis=2).min(axis=1)
        samples.append({'stamp':stamp,'expected_visible':len(expected),'detected_corners':len(corners),'median_error_px':float(np.median(distances)), 'p95_error_px':float(np.percentile(distances,95))})
    if len(samples)<5:raise ValueError('Insufficient images / truth overlap')
    result={'scope':'Offline known marker projection; truth never enters estimator', 'samples':samples,
            'median_of_median_pixel_error':float(np.median([s['median_error_px'] for s in samples])),
            'max_p95_pixel_error':max(s['p95_error_px'] for s in samples)}
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='samples'}))


if __name__=='__main__':main()
