#!/usr/bin/env python3
"""Record real HW06 interfaces and issue only requested action/service operations.

Commands are atomic JSON files: send {offset_camera_m:[x,y,z]}, cancel,
query {point:[x,y,z]}, graph, or stop. Never publishes localization or control.
"""
import argparse
import json
import math
import threading
import time
from pathlib import Path

import rclpy
from rclpy.action import ActionClient
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy, qos_profile_sensor_data
from rosidl_runtime_py.convert import message_to_ordereddict
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from uav_navigation.node import yaw_from_odometry
from uav_interfaces.action import NavigateToPose
from uav_interfaces.msg import LocalizationStatus, MapStatus, PositionCommand, NavigationCommand, TrajectoryCancel
from uav_interfaces.srv import QueryOccupancySphere
from traj_utils.msg import Bspline


def transform(q, v):
    x,y,z,w=q.x,q.y,q.z,q.w
    return [(1-2*(y*y+z*z))*v[0]+2*(x*y-z*w)*v[1]+2*(x*z+y*w)*v[2],
            2*(x*y+z*w)*v[0]+(1-2*(x*x+z*z))*v[1]+2*(y*z-x*w)*v[2],
            2*(x*z-y*w)*v[0]+2*(y*z+x*w)*v[1]+(1-2*(x*x+y*y))*v[2]]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    args=parser.parse_args();out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    rclpy.init();node=Node('hw06_plan_observer');lock=threading.RLock()
    log=(out/'events.jsonl').open('a',buffering=1);latest={};handles={};last={};counts={};stats={}
    def record(kind,data):
        with lock:log.write(json.dumps({'kind':kind,'wall_s':time.time(),'monotonic_s':time.monotonic(),'data':data})+'\n')
    def on(kind,msg):
        latest[kind]=msg
        now=time.monotonic()
        counts[kind]=counts.get(kind,0)+1
        if kind=='position_cmd':
            st=stats.setdefault(kind,{'first':now,'last':now,'max_interval_s':0.,'max_source_age_s':0.,'count':0})
            st['max_interval_s']=max(st['max_interval_s'],now-st['last'])
            st['last']=now;st['count']+=1
            stamp=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
            st['max_source_age_s']=max(st['max_source_age_s'],time.time()-stamp)

        if kind in ('position_cmd','camera_pose','odometry','localization','map') and now-last.get(kind,0)<.5 and not (kind=='position_cmd' and msg.trajectory_flag != PositionCommand.TRAJECTORY_STATUS_READY):return
        last[kind]=now;record(kind,message_to_ordereddict(msg))
    qos=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL,reliability=ReliabilityPolicy.RELIABLE)
    subscriptions=[]
    for kind,typ,topic,q in [('localization',LocalizationStatus,'/localization/status',qos),('map',MapStatus,'/mapping/status',qos),('camera_pose',PoseStamped,'/drone_0_camera_pose',qos_profile_sensor_data),('odometry',Odometry,'/localization/optimized_imu_odom',10),('position_cmd',PositionCommand,'/position_cmd',100),('bspline',Bspline,'/planning/bspline',10),('command',NavigationCommand,'/navigation/ego_goal',10),('cancel',TrajectoryCancel,'/navigation/trajectory_cancel',10)]:
        subscriptions.append(node.create_subscription(typ,topic,lambda m,k=kind:on(k,m),q))
    client=ActionClient(node,NavigateToPose,'/navigation/navigate_to_pose')
    query=node.create_client(QueryOccupancySphere,'/mapping/query_planning_occupancy')
    executor=MultiThreadedExecutor(num_threads=2);executor.add_node(node)
    thread=threading.Thread(target=executor.spin,daemon=True);thread.start()
    def wait(f,timeout=10):
        end=time.monotonic()+timeout
        while not f.done() and time.monotonic()<end:time.sleep(.02)
        if not f.done():raise TimeoutError('ROS operation timed out')
        return f.result()
    timer=node.create_timer(1.,lambda:record('rates',{'counts':dict(counts),'stats':stats}))
    record('started',{})
    try:
        while rclpy.ok():
            path=out/'command.json'
            if not path.exists():time.sleep(.1);continue
            command=json.loads(path.read_text());path.unlink();label=command['label'];op=command['op']
            record('request',command)
            try:
                if op=='send':
                    loc=latest['localization'];m=latest['map'];pose=latest['camera_pose']
                    if not loc.valid or not m.input_ready or loc.epoch!=m.epoch:raise RuntimeError('real localization/map not ready')
                    goal=NavigateToPose.Goal();goal.target.header.frame_id='odom_'+loc.epoch
                    p=pose.pose.position;delta=transform(pose.pose.orientation,command['offset_camera_m'])
                    goal.target.pose.position.x=p.x+delta[0];goal.target.pose.position.y=p.y+delta[1];goal.target.pose.position.z=p.z+delta[2]
                    # Keep target level at the measured IMU height in this tabletop session.
                    goal.target.pose.position.z=command.get('target_z',0.05)
                    odometry=latest['odometry']
                    if odometry.header.frame_id != goal.target.header.frame_id:
                        raise RuntimeError('optimized odometry epoch mismatch')
                    yaw=yaw_from_odometry(odometry.pose.pose.orientation)
                    goal.target.pose.orientation.z=math.sin(yaw/2.)
                    goal.target.pose.orientation.w=math.cos(yaw/2.)
                    goal.position_tolerance_m=.05;goal.yaw_tolerance_rad=.2;goal.dwell_s=2.;goal.timeout_s=120.
                    if not client.wait_for_server(timeout_sec=3.):raise RuntimeError('action unavailable')
                    h=wait(client.send_goal_async(goal,feedback_callback=lambda f:record('feedback',{'label':label,'message':message_to_ordereddict(f.feedback)})))
                    handles[label]=h
                    record('goal_response',{'label':label,'accepted':h.accepted,'goal_id':bytes(h.goal_id.uuid).hex(),'epoch':loc.epoch,'map_id':m.map_id,'goal':message_to_ordereddict(goal)})
                    if h.accepted:
                        h.get_result_async().add_done_callback(lambda f,l=label:record('result',{'label':l,'message':message_to_ordereddict(f.result())}))
                elif op=='cancel':
                    h=handles[command['goal']];record('cancel_response',{'label':label,'response':message_to_ordereddict(wait(h.cancel_goal_async()))})
                elif op=='query':
                    m=latest['map'];req=QueryOccupancySphere.Request();req.expected_epoch=m.epoch;req.expected_map_id=m.map_id;req.frame_id=m.header.frame_id
                    req.center.x,req.center.y,req.center.z=command['point'];req.radius_m=command.get('radius',0.)
                    record('query',{'label':label,'request':message_to_ordereddict(req),'response':message_to_ordereddict(wait(query.call_async(req)))})
                elif op=='graph':
                    graph={}
                    for topic,types in node.get_topic_names_and_types():
                        graph[topic]={'types':types,'publishers':[{'node':p.node_name,'namespace':p.node_namespace} for p in node.get_publishers_info_by_topic(topic)],'subscribers':[{'node':p.node_name,'namespace':p.node_namespace} for p in node.get_subscriptions_info_by_topic(topic)]}
                    (out/(label+'-graph.json')).write_text(json.dumps(graph,indent=2)+'\n');record('graph',{'label':label})
                elif op=='stop':break
                else:raise ValueError(op)
                record('done',{'label':label})
            except Exception as exc:record('error',{'label':label,'error':repr(exc)})
    finally:
        record('stopped',{});executor.shutdown();node.destroy_node();rclpy.shutdown();thread.join(timeout=3);log.close()


if __name__=='__main__':main()
