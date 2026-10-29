#!/usr/bin/env python3
"""Read-only source/output record for controlled unarmed callback-coherence checks."""
import json
from pathlib import Path
import sys,time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile,ReliabilityPolicy,DurabilityPolicy,qos_profile_sensor_data
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock
from std_msgs.msg import String
from uav_interfaces.msg import LocalizationStatus

run=Path(sys.argv[1]).resolve();start=time.monotonic();events=[];latest={'clock':None,'valid_since':None,'epoch':None,'counts':{}}
rclpy.init();node=Node('n08_callback_coherence_readonly_probe')
def stamp(s):return int(s.sec)*1000000000+int(s.nanosec)
def add(stream,source,**fields):
 now=time.monotonic();latest['counts'][stream]=latest['counts'].get(stream,0)+1
 events.append({'stream':stream,'wall_monotonic_s':now,'source_stamp_ns':source,
                'clock_ns_at_receipt':latest['clock'],**fields})
def on_clock(msg):latest['clock']=stamp(msg.clock)
def on_odom(msg,kind):add(kind,stamp(msg.header.stamp))
def on_telemetry(msg):
 try:add('raw_telemetry',int(json.loads(msg.data)['stamp_ns']))
 except (ValueError,KeyError,TypeError):add('malformed_telemetry',None)
def on_status(msg):
 add('status',stamp(msg.source_stamp),valid=bool(msg.valid),state=int(msg.state),reason=msg.reason,header_stamp_ns=stamp(msg.header.stamp))
 current=run/'coherence-probe-current.json'
 temporary=current.with_suffix('.json.tmp')
 temporary.write_text(json.dumps({'wall_monotonic_s':time.monotonic(),'valid':bool(msg.valid),
                                  'reason':msg.reason,'source_stamp_ns':stamp(msg.source_stamp)})+'\n')
 temporary.replace(current)
 if msg.epoch and latest['epoch'] is None:
  latest['epoch']=msg.epoch;ns='/vins_raw/s_'+msg.epoch
  node.create_subscription(Odometry,ns+'/imu_propagate',lambda m:on_odom(m,'raw_propagated'),qos_profile_sensor_data)
  node.create_subscription(String,ns+'/estimator_telemetry',on_telemetry,qos_profile_sensor_data)
 if msg.valid:
  if latest['valid_since'] is None:latest['valid_since']=time.monotonic()
  if time.monotonic()-latest['valid_since']>1 and latest['counts'].get('adapted',0)>20:
   ready=run/'coherence-probe-ready.json'
   if not ready.exists():ready.write_text(json.dumps({'epoch':msg.epoch,'wall_monotonic_s':time.monotonic()})+'\n')
 else:latest['valid_since']=None
q=QoSProfile(depth=1,reliability=ReliabilityPolicy.RELIABLE,durability=DurabilityPolicy.TRANSIENT_LOCAL)
node.create_subscription(Clock,'/clock',on_clock,qos_profile_sensor_data)
node.create_subscription(LocalizationStatus,'/localization/status',on_status,q)
node.create_subscription(Odometry,'/localization/imu_odom',lambda m:on_odom(m,'adapted'),qos_profile_sensor_data)
try:
 while rclpy.ok() and time.monotonic()-start<90 and not (run/'coherence-probe-stop').exists():
  rclpy.spin_once(node,timeout_sec=.02)
finally:
 (run/'coherence-probe.json').write_text(json.dumps({'scope':__doc__,'epoch':latest['epoch'],'counts':latest['counts'],'events':events},indent=2)+'\n')
 node.destroy_node()
 if rclpy.ok():rclpy.shutdown()
