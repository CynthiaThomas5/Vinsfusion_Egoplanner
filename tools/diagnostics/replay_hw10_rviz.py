#!/usr/bin/env python3
"""Replay only the verified static HW10 interval to display topics; no vehicle I/O."""
import json,time,bisect
from pathlib import Path
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path as ROSPath
from visualization_msgs.msg import Marker,MarkerArray
from pyulog import ULog
from hardware_live_rviz import px4_quaternion,display_mount,vins_body_pose,body_odometry_and_tf
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster

ROOT=Path(__file__).resolve().parents[2]

def main():
 report=json.loads((ROOT/'artifacts/runs/hw10-20261104-01/ulog-analysis.json').read_text())
 matrix=display_mount()
 start,end=report['fc_interval_us'];u=ULog(str(ROOT/'artifacts/runs/hw10-20261104-01/log100.ulg'))
 pos=next(d.data for d in u.data_list if d.name=='vehicle_local_position')
 att=next(d.data for d in u.data_list if d.name=='vehicle_attitude')
 offset=-1792445508307642
 vins=[]
 for line in (ROOT/'artifacts/runs/hw10-20261104-05/localization.log').read_text().splitlines():
  if 'localization_age_observation ' not in line:continue
  d=json.loads(line.split('localization_age_observation ',1)[1]);p=d.get('pose_observation')
  if p and d['status']['valid']:vins.append((p['stamp_ns']/1000+offset,p))
 assert vins and end>start
 rclpy.init();node=Node('hw10_recorded_view')
 pubs={k:node.create_publisher(typ,'/hardware_view/'+k,1) for k,typ in [('vins_path',ROSPath),('vins_pose',PoseStamped),('px4_path',ROSPath),('px4_pose',PoseStamped),('status',MarkerArray)]}
 odom_pub=node.create_publisher(Odometry,'/hardware_view/vins_odom',1);tf_pub=TransformBroadcaster(node)
 paths={k:ROSPath() for k in ('vins_path','px4_path')}
 times=[t for t,_ in vins];origin=time.monotonic();last_t=None
 def pose(p,q):
  m=PoseStamped();m.header.frame_id='hardware_display';m.header.stamp=node.get_clock().now().to_msg()
  m.pose.position.x,m.pose.position.y,m.pose.position.z=map(float,p)
  m.pose.orientation.x,m.pose.orientation.y,m.pose.orientation.z,m.pose.orientation.w=map(float,q)
  return m
 def tick():
  nonlocal last_t
  t=start+((time.monotonic()-origin)*1e6)%(end-start)
  if last_t is not None and t<last_t:
   for p in paths.values():p.poses=[]
  last_t=t
  iv=max(0,bisect.bisect_right(times,t)-1);v=vins[iv][1]
  ip=max(0,int(pos['timestamp'].searchsorted(t,side='right'))-1);iq=max(0,int(att['timestamp'].searchsorted(t,side='right'))-1)
  messages={'vins':pose(*vins_body_pose(v,matrix)),
    'px4':pose((pos['y'][ip]+3,pos['x'][ip],-pos['z'][ip]),px4_quaternion([att['q[%d]'%i][iq] for i in range(4)]))}
  for k,m in messages.items():
   if k=='vins':
    o,tf=body_odometry_and_tf(m,'hardware_view/vins_body');odom_pub.publish(o);tf_pub.sendTransform(tf)
   pubs[k+'_pose'].publish(m);p=paths[k+'_path'];p.header=m.header;p.poses.append(m);pubs[k+'_path'].publish(p)
  array=MarkerArray()
  for i,(x,label) in enumerate([(0.,'RECORDED VINS BODY | approximate mount')]):
   m=Marker();m.header.frame_id='hardware_display';m.header.stamp=node.get_clock().now().to_msg();m.id=i;m.type=Marker.TEXT_VIEW_FACING;m.pose.position.x=x;m.pose.position.z=1.2;m.pose.orientation.w=1.;m.scale.z=.11;m.color.a=1.;m.color.r=.2 if i==0 else 1.;m.color.g=.85;m.color.b=1. if i==0 else .2
   m.text='RECORDED - NOT LIVE\nVINS body FLU | approx mount\n%.1f / %.1f s'%((t-start)/1e6,(end-start)/1e6);array.markers.append(m)
  pubs['status'].publish(array)
 node.create_timer(.1,tick)
 try:rclpy.spin(node)
 except KeyboardInterrupt:pass
 finally:node.destroy_node();rclpy.shutdown()

if __name__=='__main__':main()
