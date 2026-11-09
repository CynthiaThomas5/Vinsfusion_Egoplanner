#!/usr/bin/env python3
"""Isolated domain83 hardware EV-only node check; no Agent or physical inputs."""
import os
assert os.environ.get("ROS_DOMAIN_ID") == "83", "Requires isolated domain83"
import json,time,copy,hashlib
from pathlib import Path
import rclpy
from rclpy.qos import qos_profile_sensor_data,QoSProfile,DurabilityPolicy,ReliabilityPolicy
from nav_msgs.msg import Odometry
from uav_interfaces.msg import LocalizationStatus
from px4_msgs.msg import VehicleOdometry,TimesyncStatus,VehicleAttitude,VehicleLocalPosition,EstimatorStatusFlags
from uav_px4_bridge.px4_bridge_node import Px4BridgeNode
import uav_px4_bridge.hardware_ev as module
root=Path(__file__).resolve().parents[1];run=root/'artifacts/runs/hw08-ev-final-20261103';run.mkdir(parents=True,exist_ok=True)
actual=json.loads((root/'config/hardware/rig.json').read_text());fixture=copy.deepcopy(actual)
fixture['airframe_mount']={'status':'MEASURED','control_usable':True,'T_airframe_imu':[1,0,0,.2,0,1,0,.01,0,0,1,0,0,0,0,1],'propeller_envelope_measured':False,'qualification':'SYNTHETIC_TEST_ONLY'}
(run/'synthetic-rig.json').write_text(json.dumps(fixture,indent=2))
results=[]
for name,rig in [('actual_unmeasured',root/'config/hardware/rig.json'),('synthetic',run/'synthetic-rig.json')]:
 args=['--ros-args']
 for key,value in {'profile_path':root/'config/hardware/px4_profile.json','bridge_config_path':root/'config/hardware/px4_bridge_ev.json','frame_contract_path':root/'config/components/px4_bridge/frames_vio_closed_loop.json','rig_config':rig}.items():args+=['-p',f'{key}:={value}']
 rclpy.init(args=args);bridge=Px4BridgeNode();obs=rclpy.create_node('hw08_fixture_observer')
 output=[];sub=obs.create_subscription(VehicleOdometry,'/fmu/in/vehicle_visual_odometry',lambda x:output.append(x),qos_profile_sensor_data)
 hp=obs.create_publisher(LocalizationStatus,'/localization/status',QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL,reliability=ReliabilityPolicy.RELIABLE))
 op=obs.create_publisher(Odometry,json.loads((root/'config/hardware/px4_bridge_ev.json').read_text()).get('ev_odometry_topic','/localization/optimized_imu_odom'),qos_profile_sensor_data)
 tp=obs.create_publisher(TimesyncStatus,'/fmu/out/timesync_status',qos_profile_sensor_data)
 ap=obs.create_publisher(VehicleAttitude,'/fmu/out/vehicle_attitude',qos_profile_sensor_data)
 lp=obs.create_publisher(VehicleLocalPosition,'/fmu/out/vehicle_local_position_v1',qos_profile_sensor_data)
 fp=obs.create_publisher(EstimatorStatusFlags,'/fmu/out/estimator_status_flags',qos_profile_sensor_data)
 epoch='a'*32
 def spin(seconds,publish=True,reference=True):
  end=time.monotonic()+seconds
  while time.monotonic()<end:
   if publish:
    now=time.time_ns();stamp=now-50_000_000
    h=LocalizationStatus();h.epoch=epoch;h.valid=True;h.state=1;h.header.stamp.sec=now//10**9;h.header.stamp.nanosec=now%10**9;hp.publish(h)
    t=TimesyncStatus();t.timestamp=now//1000;t.estimated_offset=-now//1000+100_000_000;t.round_trip_time=1000;t.source_protocol=2;tp.publish(t)
    if reference:
     ap.publish(VehicleAttitude(timestamp=now//1000,q=[1.,0.,0.,0.]))
     lp.publish(VehicleLocalPosition(timestamp=now//1000,heading_good_for_control=True))
     fp.publish(EstimatorStatusFlags(timestamp=now//1000,cs_yaw_align=True))
    o=Odometry();o.header.frame_id='odom_'+'a'*32;o.child_frame_id='d435i_imu_'+'a'*32;o.header.stamp.sec=stamp//10**9;o.header.stamp.nanosec=stamp%10**9;o.pose.pose.orientation.w=1.;o.pose.pose.position.x=.2;o.pose.pose.position.y=.01;o.twist.twist.linear.x=-.01;o.twist.twist.linear.y=.2;o.twist.twist.angular.z=1.;op.publish(o)
   rclpy.spin_once(bridge,timeout_sec=.005);rclpy.spin_once(obs,timeout_sec=.005)
 spin(1.,reference=False)
 assert not output,'EV sent without independent aligned heading'
 spin(3.)
 controls={topic:len(obs.get_publishers_info_by_topic('/fmu/in/'+topic)) for topic in ('offboard_control_mode','trajectory_setpoint','vehicle_command')}
 subscriptions=[x.topic_name for x in bridge.subscriptions]
 assert all(x==0 for x in controls.values()),controls
 assert '/clock' not in subscriptions
 if name=='actual_unmeasured':
  assert not output and bridge.hardware_path.reason=='airframe_mount_unmeasured'
 else:
  assert len(output)>10,len(output)
  for x in output:
   assert x.pose_frame==VehicleOdometry.POSE_FRAME_NED
   assert x.timestamp-x.timestamp_sample>=50000
   assert max(map(abs,x.position))<1e-6
   assert max(map(abs,x.velocity))<1e-6
   assert abs(x.angular_velocity[2]-1)<1e-6
  epoch='b'*32;spin(.3);spin(.2,False);count=len(output);spin(.5)
  assert len(output)==count and bridge.hardware_path.fault=='localization_epoch_changed'
 results.append({'case':name,'ev_count':len(output),'control_publishers':controls,'clock_subscription':False,'reason':bridge.hardware_path.fault or bridge.hardware_path.reason})
 bridge.destroy_node();obs.destroy_node();rclpy.shutdown()
(run/'node-check.json').write_text(json.dumps({'scope':'Synthetic DDS domain 83, no Agent/PX4/real EV fusion','installed_module':module.__file__,'cases':results},indent=2)+'\n')
print(results)
