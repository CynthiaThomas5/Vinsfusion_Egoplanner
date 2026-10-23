#!/usr/bin/env python3
"""Isolated production EGO map/curve gate with synthetic depth; no PX4 or Gazebo."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import uuid

import numpy as np
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image
from rosgraph_msgs.msg import Clock
from traj_utils.msg import Bspline
from uav_interfaces.msg import NavigationCommand, TrajectoryCancel
from uav_interfaces.srv import ResetMapping, QueryOccupancySphere


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--after-completion', action='store_true')
    args = parser.parse_args()
    planner_config = json.loads((Path(__file__).resolve().parents[1]
                                 / 'config/components/mapping/ego_planner.json').read_text())
    envelope_config = json.loads((Path(__file__).resolve().parents[1]
                                  / 'config/components/navigation/vehicle_envelope.json').read_text())
    args.output_dir.mkdir(parents=True, exist_ok=False)
    log_path = args.output_dir/'planner.log'
    log = log_path.open('w')
    process = subprocess.Popen([
        'ros2', 'launch', 'ego_planner', 'advanced_param.launch.py',
        'flight_type:=1', 'odometry_topic:=/probe/odom',
        'map_size_x_:=12.0', 'map_size_y_:=12.0', 'map_size_z_:=6.0',
        'ground_height:=-2.0', 'cx:=79.5', 'cy:=59.5', 'fx:=80.0', 'fy:=80.0',
        'max_vel:=0.5', 'max_acc:=0.8', 'planning_horizon:=3.0',
        f'obstacles_inflation:={planner_config["obstacles_inflation_m"]}',
        f'terminal_hold_neighborhood:={envelope_config["map_policy"]["terminal_hold_neighborhood_radius_m"]}',
        f'odom_depth_timeout:={planner_config["odom_depth_timeout_sim_s"]}'],
        stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    rclpy.init()
    node = Node('isolated_ego_safety_probe')
    epoch = uuid.uuid4().hex
    map_id = epoch+'-synthetic-wall'
    frame = 'odom_'+epoch
    rows, faults, curves = [], [], []
    clock_pub = node.create_publisher(Clock, '/clock', 10)
    pose_pub = node.create_publisher(PoseStamped, '/drone_0_camera_pose', 10)
    depth_pub = node.create_publisher(Image, '/drone_0_depth_image', 10)
    odom_pub = node.create_publisher(Odometry, '/probe/odom', 10)
    goal_pub = node.create_publisher(NavigationCommand, '/navigation/ego_goal', 10)
    node.create_subscription(Bspline, '/drone_0_planning/bspline', curves.append, 10)
    node.create_subscription(TrajectoryCancel, '/navigation/planner_fault', faults.append, 10)
    reset = node.create_client(ResetMapping, '/mapping/reset_map')
    query = node.create_client(QueryOccupancySphere, '/mapping/query_occupancy_sphere')
    start = time.monotonic()
    surface = [4.0]
    last_depth = [0.]

    def inputs():
        now = time.monotonic()
        sec, ns = divmod(int((10+now-start)*1e9), 1_000_000_000)
        clock = Clock()
        clock.clock.sec, clock.clock.nanosec = sec, ns
        clock_pub.publish(clock)
        odom = Odometry()
        odom.header.frame_id = frame
        odom.header.stamp = clock.clock
        odom.pose.pose.position.x, odom.pose.pose.position.z = 2., 1.
        odom.pose.pose.orientation.w = 1.
        odom_pub.publish(odom)
        if now-last_depth[0] < .065:
            return
        last_depth[0] = now
        # An earlier camera view at x=0 observes the synthetic wall. Independent
        # odometry at x=2 exercises the planner; this is a component fixture.
        pose = PoseStamped()
        pose.header = odom.header
        pose.pose.position.z = 1.
        q = pose.pose.orientation
        q.x, q.y, q.z, q.w = -.5, .5, -.5, .5
        image = Image()
        image.header = pose.header
        image.width, image.height, image.step = 160, 120, 640
        image.encoding = '32FC1'
        image.data = np.full((120,160), surface[0], dtype=np.float32).tobytes()
        pose_pub.publish(pose)
        depth_pub.publish(image)

    timer = node.create_timer(.01, inputs)

    def wait(predicate, label, timeout=10.):
        end = time.monotonic()+timeout
        while time.monotonic()<end:
            if process.poll() is not None:
                raise RuntimeError('planner exited during '+label)
            rclpy.spin_once(node, timeout_sec=.005)
            if predicate():
                return
        raise RuntimeError('timeout: '+label)

    def call(client, request):
        future = client.call_async(request)
        wait(future.done, 'service response')
        return future.result()

    def goal(x, target_map_id=None):
        msg = NavigationCommand()
        msg.goal_id, msg.epoch, msg.map_id = uuid.uuid4().hex, epoch, target_map_id or map_id
        msg.target.header.frame_id = frame
        msg.target.pose.position.x, msg.target.pose.position.z = x, 1.
        msg.target.pose.orientation.w = 1.
        goal_pub.publish(msg)
        return msg.goal_id

    try:
        wait(lambda: reset.service_is_ready() and query.service_is_ready(), 'services')
        req = ResetMapping.Request()
        req.epoch, req.map_id = epoch, map_id
        response = call(reset, req)
        assert response.accepted, response.reason
        wait(lambda: pose_pub.get_subscription_count()>0 and depth_pub.get_subscription_count()>0,
             'depth subscribers')
        end = time.monotonic()+2.
        wait(lambda: time.monotonic()>end, 'depth fusion warmup', 4.)
        for label, point, radius, expected in [
                ('free_body',(2.,0.,1.),.5,'free'),
                ('occupied_return',(4.05,0.,1.),.01,'occupied'),
                ('unknown_behind',(-2.,0.,1.),.5,'unknown'),
                ('outside',(100.,0.,1.),.5,'outside_map')]:
            deadline = time.monotonic()+2.
            while True:
                req = QueryOccupancySphere.Request()
                req.expected_epoch, req.expected_map_id, req.frame_id = epoch,map_id,frame
                req.center.x, req.center.y, req.center.z = point
                req.radius_m = radius
                response = call(query,req)
                rows.append({'label':label,'reason':response.reason,'accepted':response.accepted,
                             'free':response.free,'counts':[response.free_count,response.unknown_count,response.occupied_count]})
                if response.reason==expected:
                    break
                if response.reason!='no_fresh_fused_depth' or time.monotonic()>deadline:
                    raise RuntimeError(f'{label}: expected {expected}, got {response.reason}')
        wait(lambda: goal_pub.get_subscription_count()>0, 'goal subscriber')
        wrong = goal(2.8, 'wrong-map-id')
        wait(lambda: any(f.goal_id==wrong for f in faults), 'wrong-map rejection')
        if any(c.goal_id==wrong for c in curves):
            raise RuntimeError('curve from wrong map identity was published')
        if next(f for f in faults if f.goal_id==wrong).reason != 'full_curve_map_id_mismatch':
            raise RuntimeError('wrong map identity did not fail certification')
        first = goal(2.8)
        wait(lambda: any(c.goal_id==first for c in curves)
             or any(f.goal_id==first for f in faults), 'certified curve')
        if any(f.goal_id==first for f in faults) or not curves:
            raise RuntimeError('known-free full curve did not publish')
        if args.after_completion:
            curve = next(c for c in curves if c.goal_id==first)
            end_stamp = (curve.start_time.sec+curve.start_time.nanosec/1e9
                         +curve.knots[-curve.order-1]-curve.knots[curve.order])
            wait(lambda: 10+time.monotonic()-start>end_stamp+.2,
                 'completed curve hold', max(10.,end_stamp-10+2.))
        # Fault injection intersects the active curve or its completed endpoint hold.
        surface[0] = 2.4
        wait(lambda: any(f.goal_id==first for f in faults), 'remaining-curve rejection', 5.)
        first_fault = next(f for f in faults if f.goal_id==first)
        if not first_fault.reason.startswith('full_curve_'):
            raise RuntimeError('unexpected execution safety fault: '+first_fault.reason)
        previous = len(curves)
        until = time.monotonic()+.3
        wait(lambda: time.monotonic()>until, 'latched rejection', 1.)
        assert len(curves)==previous, 'published after full-curve fault'
        second = goal(2.8)
        wait(lambda: any(f.goal_id==second for f in faults), 'blocked new goal')
        assert not any(c.goal_id==second for c in curves), 'blocked trajectory published'
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGINT)
            process.wait(timeout=10.)
        log.flush()
        report = {'scope':'synthetic component fixture; no flight, PX4, VINS or world truth',
                  'passed':True,'after_completion':args.after_completion,'queries':rows,'certified_curves':len(curves),
                  'faults':[{'goal_id':f.goal_id,'epoch':f.epoch,'reason':f.reason} for f in faults],
                  'late_curves_after_fault':len(curves)-previous,
                  'certificate_metrics': [line.strip() for line in
                      log_path.read_text(errors='replace').splitlines()
                      if 'Full-curve certificate metrics:' in line]}
        (args.output_dir/'result.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report))
    finally:
        node.destroy_timer(timer)
        node.destroy_node()
        rclpy.shutdown()
        if process.poll() is None:
            os.killpg(process.pid,signal.SIGINT)
            try: process.wait(timeout=10.)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGTERM)
                process.wait(timeout=5.)
        log.close()


if __name__=='__main__':
    main()
