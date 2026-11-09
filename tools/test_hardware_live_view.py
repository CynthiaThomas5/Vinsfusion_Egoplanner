#!/usr/bin/env python3
"""Workstation display rotation; no hardware connection."""
import math
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'diagnostics'))
from hardware_live_rviz import px4_quaternion,product,vins_body_pose,body_odometry_and_tf,native_vins_pose,write_live_status,resource_snapshot
q=px4_quaternion([1,0,0,0])
yaw=math.atan2(2*(q[3]*q[2]+q[0]*q[1]),1-2*(q[1]**2+q[2]**2))
assert abs(yaw-math.pi/2)<1e-8
assert abs(sum(v*v for v in q)-1)<1e-8
assert product((0,0,0,1),(0,0,0,1))==(0,0,0,1)
print('3 display-frame checks PASS')

# Optical IMU X=right, Y=down, Z=forward; body FRD lever is .2m forward/.01m right.
m=[0,0,1,.2,1,0,0,.01,0,1,0,0,0,0,0,1]
p,q=vins_body_pose({'position_m':[1,2,3],'orientation_xyzw':[0,0,0,1]},m)
assert all(abs(a-b)<1e-8 for a,b in zip(p,(.99,2.,2.8)))
# Body FLU forward, left and up must map to optical +Z, -X and -Y respectively.
from uav_px4_bridge.trajectory import rotate_frd_to_ned
for axis,expected in [((1,0,0),(0,0,1)),((0,1,0),(-1,0,0)),((0,0,1),(0,-1,0))]:
 got=rotate_frd_to_ned(axis,(q[3],*q[:3]))
 assert all(abs(a-b)<1e-8 for a,b in zip(got,expected))
print('Body reference-point / forward-left-up axes checks PASS')

from geometry_msgs.msg import PoseStamped
m=PoseStamped();m.header.frame_id='hardware_display';m.pose.position.x=1.;m.pose.orientation.w=1.
o,tf=body_odometry_and_tf(m,'hardware_view/vins_body')
assert o.header.frame_id==tf.header.frame_id=='hardware_display'
assert o.child_frame_id==tf.child_frame_id=='hardware_view/vins_body'
assert o.pose.pose.position.x==tf.transform.translation.x==1.
assert math.isnan(o.twist.twist.linear.x)
assert all(math.isfinite(v) for v in o.pose.covariance)
print('Display odometry/TF consistency and unknown twist PASS')

a=native_vins_pose('time: 1792446000.123456, t: 1.0 -2.0 3.0 q: 1.0 0.0 0.0 0.0 ')
assert a['position_m']==[1.,-2.,3.] and a['orientation_xyzw']==[0.,0.,0.,1.]
for bad in ['n_pts size: 20','time: nan, t: 0 0 0 q: 1 0 0 0','time: 10, t: 0 0 0 q: 0 0 0 0']:
 assert native_vins_pose(bad) is None
print('Native optimized-pose log parsing valid/invalid checks PASS')

import json,tempfile
with tempfile.TemporaryDirectory() as directory:
 status=Path(directory)/'status.json';samples=Path(directory)/'samples.jsonl'
 snapshot={'clock_offset_s':75.0,'monotonic_s':12.5,'visual_counts':{'image':3}}
 with samples.open('x',buffering=1) as stream:
  write_live_status(status,stream,snapshot)
  write_live_status(status,stream,{**snapshot,'monotonic_s':12.7})
 assert json.loads(status.read_text())['monotonic_s']==12.7
 records=[json.loads(line) for line in samples.read_text().splitlines()]
 assert len(records)==2 and records[0]['clock_offset_s']==75.0 and records[1]['monotonic_s']==12.7
print('Live status snapshots and append-only time series PASS')

resources=resource_snapshot()
assert resources.get('host_loadavg') and len(resources['host_loadavg'])==3
assert resources.get('viewer_process_rss_bytes',0)>0
print('Best-effort host/container resource snapshot PASS')
