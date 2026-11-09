#!/usr/bin/env python3
"""Domain83: real bridge compute mode, no PX4 output/service, epoch latch."""
import os
assert os.environ.get('ROS_DOMAIN_ID') == '83'
import json
import time
from pathlib import Path
import rclpy
from nav_msgs.msg import Odometry
from uav_interfaces.msg import LocalizationStatus, PositionCommand
from rclpy.qos import qos_profile_sensor_data, QoSProfile, DurabilityPolicy, ReliabilityPolicy
from uav_px4_bridge.px4_bridge_node import Px4BridgeNode
root=Path(__file__).resolve().parents[1]
args=['--ros-args']
for k,v in {'profile_path':root/'config/hardware/px4_profile.json','bridge_config_path':root/'config/hardware/px4_bridge_control.json','frame_contract_path':root/'config/components/px4_bridge/frames_vio_closed_loop.json','rig_config':root/'config/hardware/rig.json','runtime_mode':'compute_only'}.items():args+=['-p',str(k)+':='+str(v)]
rclpy.init(args=args);bridge=Px4BridgeNode();obs=rclpy.create_node('hw09_compute_fixture')
hp=obs.create_publisher(LocalizationStatus,'/localization/status',QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL,reliability=ReliabilityPolicy.RELIABLE))
op=obs.create_publisher(Odometry,'/localization/optimized_imu_odom',qos_profile_sensor_data)
cp=obs.create_publisher(PositionCommand,'/position_cmd',10)
epoch='a'*32

def spin(seconds):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  now=time.time_ns();stamp=now-50_000_000
  h=LocalizationStatus();h.valid=True;h.epoch=epoch;hp.publish(h)
  o=Odometry();o.header.frame_id='odom_'+'a'*32;o.child_frame_id='d435i_imu_'+'a'*32;o.header.stamp.sec=stamp//10**9;o.header.stamp.nanosec=stamp%10**9;o.pose.pose.orientation.w=1.;op.publish(o)
  c=PositionCommand();c.header.frame_id=o.header.frame_id;c.header.stamp=o.header.stamp;c.epoch='a'*32;c.goal_id='fixture';c.trajectory_id=1;c.trajectory_flag=1;cp.publish(c)
  rclpy.spin_once(bridge,timeout_sec=.005);rclpy.spin_once(obs,timeout_sec=.005)
spin(3.)
path=bridge.hardware_path
assert path.counts['ev_computed']>10,path.counts
assert path.counts['commands_computed']>10,path.counts
assert all(not p.topic_name.startswith('/fmu/') for p in bridge.publishers)
assert not any(s.srv_name.endswith('enable_offboard') for s in bridge.services)
assert '/clock' not in [s.topic_name for s in bridge.subscriptions]
epoch='b'*32;spin(.3);count=dict(path.counts);spin(.3)
assert path.counts['ev_computed']==count['ev_computed'] and path.counts['commands_computed']==count['commands_computed']
assert path.fault=='localization_epoch_changed'
print(json.dumps({'counts':path.counts,'fault':path.fault,'px4_publishers':0,'enable_services':0,'clock_subscriptions':0}))
bridge.destroy_node();obs.destroy_node();rclpy.shutdown()
