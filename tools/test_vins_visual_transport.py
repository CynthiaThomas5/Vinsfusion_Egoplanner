#!/usr/bin/env python3
"""Actual standard-message roundtrip, frame/epoch and payload rejection."""
import sys,json,zlib,base64
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'diagnostics'))
from vins_visual_transport import decode_visual,TYPES
from rclpy.serialization import serialize_message
from builtin_interfaces.msg import Time
from geometry_msgs.msg import Point32
E='a'*32;stamp=Time(sec=5)

def packet(kind,data,fmt):return {'kind':kind,'epoch':E,'format':fmt,'payload':base64.b64encode(zlib.compress(data)).decode()}
for kind in ('points','history','image'):
 m=TYPES[kind]();m.header.frame_id='vins_'+E+'_world'
 if kind=='image':m.width=2;m.height=1;m.encoding='bgr8';m.step=6;m.data=[1,2,3,4,5,6]
 else:m.points=[Point32(x=1.,y=2.,z=3.)]
 row=packet(kind,serialize_message(m),'cdr');out=decode_visual(row,E,stamp)
 assert out.header.frame_id=='hardware_display' and out.header.stamp.sec==5
 if kind=='image':assert bytes(out.data)==bytes(m.data)
 else:assert out.points[0].z==3.
 try:decode_visual(row,'b'*32,stamp)
 except ValueError:pass
 else:raise AssertionError('epoch accepted')
cam={'markers':[{'header':{'frame_id':'vins_'+E+'_world'},'ns':'camera','id':1,'type':5,'points':[{'x':1.,'y':2.,'z':3.}]}]}
row=packet('camera',json.dumps(cam).encode(),'marker_json');out=decode_visual(row,E,stamp)
assert out.markers[0].points[0].x==1. and out.markers[0].header.frame_id=='hardware_display'
cam['markers'][0]['header']['frame_id']='wrong'
try:decode_visual(packet('camera',json.dumps(cam).encode(),'marker_json'),E,stamp)
except ValueError:pass
else:raise AssertionError('wrong frame accepted')
try:decode_visual({'kind':'points','epoch':E,'format':'cdr','payload':'!!!!'},E,stamp)
except ValueError:pass
else:raise AssertionError('bad payload accepted')
print('Visual sensor roundtrips, Foxy marker subset, epoch/frame/corruption checks PASS')
# Lossy preview keeps dimensions and frame contract; body remains standard odometry.
import cv2,numpy as np
ok,jpeg=cv2.imencode('.jpg',np.full((240,640,3),80,dtype=np.uint8))
row={'kind':'image','epoch':E,'format':'jpeg','source_frame':'vins_'+E+'_world','payload':base64.b64encode(jpeg).decode()}
out=decode_visual(row,E,stamp);assert (out.width,out.height,out.step)==(640,240,1920)
assert abs(np.frombuffer(out.data,dtype=np.uint8).mean()-80)<2
row['source_frame']='wrong'
try:decode_visual(row,E,stamp)
except ValueError:pass
else:raise AssertionError('wrong JPEG frame accepted')
m=TYPES['body']();m.header.frame_id='vins_'+E+'_world';m.pose.pose.orientation.w=1.;m.pose.pose.position.x=3.
out=decode_visual(packet('body',serialize_message(m),'cdr'),E,stamp);assert out.pose.pose.position.x==3.
print('JPEG preview and propagated odometry roundtrip PASS')
