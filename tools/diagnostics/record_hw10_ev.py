#!/usr/bin/env python3
"""Bounded-rate actual DDS/EV observation; publishes no control."""
import json,time,argparse
from pathlib import Path
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rosidl_runtime_py.convert import message_to_ordereddict
from px4_msgs.msg import VehicleStatus,VehicleAttitude,VehicleLocalPosition,TimesyncStatus,EstimatorStatusFlags,VehicleOdometry
from std_msgs.msg import String
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
rclpy.init();n=Node('hw10_readonly_ev_observer');latest={};counts={};subs=[]
for topic,typ in [('/fmu/out/vehicle_status_v1',VehicleStatus),('/fmu/out/vehicle_attitude',VehicleAttitude),('/fmu/out/vehicle_local_position_v1',VehicleLocalPosition),('/fmu/out/timesync_status',TimesyncStatus),('/fmu/out/estimator_status_flags',EstimatorStatusFlags),('/fmu/in/vehicle_visual_odometry',VehicleOdometry),('/px4_bridge/hardware_ev/detail',String)]:
 def callback(m,t=topic):
  latest[t]={'receipt_mono':time.monotonic(),'message':message_to_ordereddict(m)};counts[t]=counts.get(t,0)+1
 subs.append(n.create_subscription(typ,topic,callback,qos_profile_sensor_data))
f=(out/'ev.jsonl').open('w',buffering=1)
def tick():
 row={'system_ns':time.time_ns(),'monotonic_s':time.monotonic(),'counts':dict(counts),'latest':dict(latest)}
 f.write(json.dumps(row)+'\n');(out/'latest.json').write_text(json.dumps(row,indent=2))
n.create_timer(1.,tick)
try:rclpy.spin(n)
except KeyboardInterrupt:pass
finally:
 (out/'graph.json').write_text(json.dumps({t:len(n.get_publishers_info_by_topic(t)) for t,_ in n.get_topic_names_and_types() if t.startswith('/fmu/in/')},indent=2));n.destroy_node();rclpy.shutdown();f.close()
