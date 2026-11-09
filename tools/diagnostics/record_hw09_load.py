#!/usr/bin/env python3
"""Small ground load driver/recorder: real action goals, no pose/control publication."""
import argparse
import json
import math
from pathlib import Path
import time

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy, qos_profile_sensor_data
from nav_msgs.msg import Odometry
from std_msgs.msg import String
from uav_interfaces.action import NavigateToPose
from uav_interfaces.msg import LocalizationStatus, MapStatus, PositionCommand
from traj_utils.msg import Bspline


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True)
    p.add_argument('--duration',type=float,default=300.)
    args=p.parse_args();out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    rclpy.init();node=Node('hw09_load_observer');latest={};counts={};last={};gaps={};ages={}
    log=(out/'load.jsonl').open('w',buffering=1)
    def emit(kind,data):
        log.write(json.dumps({'monotonic_s':time.monotonic(),'wall_s':time.time(),'kind':kind,'data':data})+'\n')
    def receive(kind,msg):
        now=time.monotonic();counts[kind]=counts.get(kind,0)+1
        if kind in last:gaps[kind]=max(gaps.get(kind,0.),now-last[kind])
        last[kind]=now;latest[kind]=msg
        if kind in ('odom','command'):
            stamp=msg.header.stamp.sec+msg.header.stamp.nanosec/1e9
            ages.setdefault(kind,[]).append(time.time()-stamp)
        if kind=='bridge':emit('bridge',json.loads(msg.data))
    qos=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL,reliability=ReliabilityPolicy.RELIABLE)
    subs=[node.create_subscription(typ,topic,lambda m,k=kind:receive(k,m),q) for kind,typ,topic,q in [
        ('health',LocalizationStatus,'/localization/status',qos),('map',MapStatus,'/mapping/status',qos),
        ('odom',Odometry,'/localization/optimized_imu_odom',qos_profile_sensor_data),
        ('command',PositionCommand,'/position_cmd',10),('plan',Bspline,'/planning/bspline',10),
        ('bridge',String,'/hardware/bridge_compute',10)]]
    client=ActionClient(node,NavigateToPose,'/navigation/navigate_to_pose')
    start=time.monotonic();valid_start=None;last_goal=-math.inf;last_sample=0.;handle=None;pending=None;goal_count=0;accepted=0
    invalid_after_start=False;resources_previous={}
    def resource():
        nonlocal resources_previous
        processes=[];ticks=time.monotonic()
        for path in Path('/proc').glob('[0-9]*/stat'):
            try:
                cmd=(path.parent/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
                if not any(s in cmd for s in ('vins_node','localization_adapter','ego_planner_node','mapping_input_adapter','traj_server','navigation_supervisor','px4_bridge','realsense2_camera_node','depth_to_meters')):continue
                fields=path.read_text().rsplit(')',1)[1].split();cpu=int(fields[11])+int(fields[12]);rss=int(fields[21])*4096
                previous=resources_previous.get(path.parent.name);percent=None if previous is None else (cpu-previous[0])/(ticks-previous[1])
                resources_previous[path.parent.name]=(cpu,ticks)
                processes.append({'pid':int(path.parent.name),'state':fields[0], 'cmd':cmd,'rss_bytes':rss,'cpu_percent':percent})
            except (OSError,ValueError,IndexError):continue
        thermal={}
        for path in Path('/sys/class/thermal').glob('thermal_zone*'):
            try:thermal[(path/'type').read_text().strip()]=int((path/'temp').read_text())/1000.
            except OSError:pass
        return {'processes':processes,'temperature_c':thermal,'loadavg':Path('/proc/loadavg').read_text().strip()}
    (out/'ready').write_text(str(time.monotonic()))
    try:
        while rclpy.ok():
            rclpy.spin_once(node,timeout_sec=.02);now=time.monotonic()
            health=latest.get('health');m=latest.get('map');odom=latest.get('odom');bridge=latest.get('bridge')
            ready=(health is not None and health.valid and m is not None and m.input_ready
                   and odom is not None and m.epoch==health.epoch and bridge is not None
                   and json.loads(bridge.data)['counts']['ev_computed']>0)
            if ready and valid_start is None:
                valid_start=now;emit('window_start',{'epoch':health.epoch,'duration_s':args.duration})
            if valid_start is not None and not ready:
                invalid_after_start=True
                emit('window_invalid',{'reason':health.reason if health else 'missing_health'})
                break
            if valid_start is None and now-start>100:raise RuntimeError('Full load did not become ready within 100s')
            if valid_start is not None and now-valid_start>=args.duration:break
            if ready and now-last_goal>=25. and pending is None:
                if handle is not None and handle.accepted:handle.cancel_goal_async()
                goal=NavigateToPose.Goal();goal.target.header.frame_id=odom.header.frame_id
                pos=odom.pose.pose.position;goal.target.pose.position.x=pos.x+(0.7 if goal_count%2==0 else -0.7)
                goal.target.pose.position.y=pos.y+0.3;goal.target.pose.position.z=pos.z+0.3
                goal.target.pose.orientation=odom.pose.pose.orientation
                # Convert optical IMU forward to world yaw, matching the hardware nav adapter.
                from uav_navigation.node import yaw_from_odometry
                yaw=yaw_from_odometry(odom.pose.pose.orientation)
                goal.target.pose.orientation.x=0.;goal.target.pose.orientation.y=0.
                goal.target.pose.orientation.z=math.sin(yaw/2);goal.target.pose.orientation.w=math.cos(yaw/2)
                goal.position_tolerance_m=.05;goal.yaw_tolerance_rad=.2;goal.dwell_s=2.;goal.timeout_s=24.
                if client.wait_for_server(timeout_sec=.1):
                    pending=client.send_goal_async(goal);goal_count+=1;last_goal=now
                    emit('goal_sent',{'number':goal_count,'x':goal.target.pose.position.x,'y':goal.target.pose.position.y,'z':goal.target.pose.position.z})
            if pending is not None and pending.done():
                handle=pending.result();pending=None;accepted+=int(handle.accepted)
                emit('goal_response',{'number':goal_count,'accepted':handle.accepted})
            if now-last_sample>=2.:
                last_sample=now
                d={'counts':dict(counts),'max_gaps_s':dict(gaps),'ready':bool(ready),
                   'localization_reason':health.reason if health else None,
                   'map':None if m is None else {k:getattr(m,k) for k in ('input_ready','reason','pending_depth_count','pending_depth_high_water_count','dropped_depth_count','forwarded_depth_count')},
                   'resources':resource()}
                for kind,values in ages.items():
                    a=sorted(values);d[kind+'_age_s']={'p95':a[int((len(a)-1)*.95)],'p99':a[int((len(a)-1)*.99)],'max':a[-1]}
                ages.clear();emit('sample',d)
        emit('graph',{'fmu_input_publishers':{name:len(node.get_publishers_info_by_topic(name)) for name,_ in node.get_topic_names_and_types() if name.startswith('/fmu/in/')},'nodes':node.get_node_names()})
        summary={'duration_s':None if valid_start is None else time.monotonic()-valid_start,'invalid_after_start':invalid_after_start,'goals_sent':goal_count,'goals_accepted':accepted,'counts':counts,'max_gaps_s':gaps}
        (out/'load-summary.json').write_text(json.dumps(summary,indent=2)+'\n');emit('summary',summary)
    finally:
        if handle is not None and handle.accepted:
            f=handle.cancel_goal_async();end=time.monotonic()+3
            while not f.done() and time.monotonic()<end:rclpy.spin_once(node,timeout_sec=.05)
        node.destroy_node();rclpy.shutdown();log.close()


if __name__=='__main__':main()
