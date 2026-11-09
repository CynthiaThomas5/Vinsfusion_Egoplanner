#!/usr/bin/env python3
import sys,math
from pathlib import Path
from types import SimpleNamespace as S
from dataclasses import replace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src/own/uav_px4_bridge'))
from uav_px4_bridge.ev_reference import EVNEDReference,yaw
from uav_px4_bridge.vision_odometry import PX4VisualOdometry
v=PX4VisualOdometry(10000000,9990000,(1.,2.,3.),(1.,0.,0.,0.),(1.,0.,0.),(0.,0.,.1),(.01,)*3,(.01,)*3,(.01,)*3,50,'a'*32)
def reference(aligned=True,ev=False):
 r=EVNEDReference();r.update('attitude',S(timestamp=9990000,q=(math.sqrt(.5),0.,0.,math.sqrt(.5))),1000000000)
 r.update('local',S(timestamp=9990000,heading_good_for_control=aligned,xy_valid=False,z_valid=True,x=float('nan'),y=float('nan'),z=-.2),1000000000)
 r.update('flags',S(timestamp=9990000,cs_yaw_align=aligned,cs_ev_yaw=ev,cs_mag_fault=False,cs_mag_field_disturbed=False),1000000000);return r
r=reference();out=r.apply(v,10000000000,1000000000)
assert max(abs(a-b) for a,b in zip(out.position_ned,(0.,0.,-.2)))<1e-9
assert abs(yaw(out.quaternion_ned_frd_wxyz)-math.pi/2)<1e-9
out2=r.apply(replace(v,position_ned=(2.,2.,3.)),10000000000,1000000000)
assert abs(out2.position_ned[0])<1e-9 and abs(out2.position_ned[1]-1.)<1e-9
assert out2.velocity_body_frd==v.velocity_body_frd and out2.timestamp_sample==v.timestamp_sample
for bad,sys,mono in [(reference(False),10000000000,1000000000),(reference(ev=True),10000000000,1000000000),(reference(),13000000000,4000000000)]:
 try:bad.apply(v,sys,mono)
 except ValueError:pass
 else:raise AssertionError('unaligned/self-referenced/stale reference admitted')
try:r.apply(replace(v,epoch='b'*32),10000000000,1000000000)
except ValueError:pass
else:raise AssertionError('epoch stitched')
print('Independent NED binding, real yaw rotation/free origin, source preservation, reference/epoch guards PASS')
