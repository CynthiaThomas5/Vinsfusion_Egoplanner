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
    scenario = parser.add_mutually_exclusive_group()
    scenario.add_argument('--after-completion', action='store_true')
    scenario.add_argument('--stale-after-curve', action='store_true',
                          help='Stop synthetic depth after the first certified curve while advancing clock and odometry.')
    scenario.add_argument('--swarm-emergency', action='store_true',
                          help='Inject a same-path synthetic peer trajectory to exercise EGO emergency-stop behavior.')
    scenario.add_argument('--active-obstacle-hold', action='store_true',
                          help='Move a synthetic mapped obstacle into the active curve while keeping the current hold sphere free.')
    scenario.add_argument('--active-obstacle-hold-blocked', action='store_true',
                          help='Place the synthetic obstacle inside both the active curve and the current hold sphere.')
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
    swarm_pub = node.create_publisher(Bspline, '/broadcast_bspline', 10)
    node.create_subscription(Bspline, '/drone_0_planning/bspline', curves.append, 10)
    node.create_subscription(TrajectoryCancel, '/navigation/planner_fault', faults.append, 10)
    reset = node.create_client(ResetMapping, '/mapping/reset_map')
    query = node.create_client(QueryOccupancySphere, '/mapping/query_occupancy_sphere')
    start = time.monotonic()
    surface = [4.0]
    last_depth = [0.]
    depth_enabled = [True]
    last_sim_clock = [None]

    def inputs():
        now = time.monotonic()
        sec, ns = divmod(int((10+now-start)*1e9), 1_000_000_000)
        clock = Clock()
        clock.clock.sec, clock.clock.nanosec = sec, ns
        last_sim_clock[0] = clock.clock
        clock_pub.publish(clock)
        odom = Odometry()
        odom.header.frame_id = frame
        odom.header.stamp = clock.clock
        odom.pose.pose.position.x, odom.pose.pose.position.z = 2., 1.
        odom.pose.pose.orientation.w = 1.
        odom_pub.publish(odom)
        if not depth_enabled[0] or now-last_depth[0] < .065:
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
                ('outside',(100.,0.,1.),.5,'outside_map'),
                ('invalid_radius',(2.,0.,1.),2.1,'invalid_query')]:
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
        wrong_epoch = uuid.uuid4().hex
        wrong_epoch_msg = NavigationCommand()
        wrong_epoch_msg.goal_id = uuid.uuid4().hex
        wrong_epoch_msg.epoch = wrong_epoch
        wrong_epoch_msg.map_id = map_id
        wrong_epoch_msg.target.header.frame_id = 'odom_' + wrong_epoch
        wrong_epoch_msg.target.pose.position.x = 2.8
        wrong_epoch_msg.target.pose.position.z = 1.
        wrong_epoch_msg.target.pose.orientation.w = 1.
        wrong_epoch_curves, wrong_epoch_faults = len(curves), len(faults)
        goal_pub.publish(wrong_epoch_msg)
        wrong_epoch_deadline = time.monotonic() + .25
        wait(lambda: time.monotonic() > wrong_epoch_deadline,
             'wrong-epoch goal rejection', 1.)
        if len(curves) != wrong_epoch_curves or len(faults) != wrong_epoch_faults:
            raise RuntimeError('wrong-epoch goal reached planning or emitted a safety fault')
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
        if args.active_obstacle_hold or args.active_obstacle_hold_blocked:
            surface[0] = 1.5 if args.active_obstacle_hold_blocked else 3.4
            def constant_curve(candidate):
                if candidate.goal_id != first or len(candidate.pos_pts) < 4:
                    return False
                xs = [p.x for p in candidate.pos_pts]
                ys = [p.y for p in candidate.pos_pts]
                zs = [p.z for p in candidate.pos_pts]
                return max(xs)-min(xs) < 1e-6 and max(ys)-min(ys) < 1e-6 and max(zs)-min(zs) < 1e-6
            wait(lambda: any(constant_curve(c) for c in curves)
                 or any(f.goal_id == first for f in faults),
                 'obstacle response or emergency hold', 6.)
            hold_curves = [c for c in curves if constant_curve(c)]
            observation_end = time.monotonic() + .3
            previous = len(curves)
            while time.monotonic() < observation_end:
                rclpy.spin_once(node, timeout_sec=.005)
            planner_text = log_path.read_text(errors='replace')
            transitions = [line.strip() for line in planner_text.splitlines()
                           if 'from ' in line and ' to ' in line]
            hold_transitions = [line for line in transitions if 'to EMERGENCY_STOP' in line]
            fault_rows = [{'goal_id':f.goal_id,'epoch':f.epoch,'reason':f.reason}
                          for f in faults]
            hold_faults = [f.reason for f in faults if f.goal_id == first]
            if args.active_obstacle_hold_blocked:
                expected_behavior = bool(hold_faults and not hold_curves and len(curves)==previous)
            else:
                expected_behavior = bool(hold_transitions and hold_curves and len(curves)==previous)
            report = {
                'scope':'synthetic component fixture; no flight, PX4, VINS or world truth',
                'scenario_completed':True,
                'acceptance_passed':expected_behavior,
                'scenario':('active synthetic depth obstacle at x=1.5 m; current hold sphere is expected blocked'
                            if args.active_obstacle_hold_blocked else
                            'active synthetic depth obstacle at x=3.4 m; initial hold sphere at x=2.0 m remains raw-free'),
                'emergency_stop_observed':bool(hold_transitions),
                'emergency_hold_bspline_observed':bool(hold_curves),
                'hold_curve_traj_ids':[c.traj_id for c in hold_curves],
                'hold_rejection_faults':hold_faults,
                'faults':fault_rows,
                'late_curves_after_hold':len(curves)-previous,
                'fsm_transitions':transitions,
                'certificate_metrics':[line.strip() for line in planner_text.splitlines()
                                      if 'Full-curve certificate metrics:' in line],
                'interpretation':'Planner-only hold publication; no B-spline was executed.'}
            (args.output_dir/'result.json').write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps(report))
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGINT)
                process.wait(timeout=10.)
            log.flush()
            return
        if args.swarm_emergency:
            wait(lambda: swarm_pub.get_subscription_count()>0,
                 'broadcast trajectory subscriber')
            source_curve = next(c for c in curves if c.goal_id == first)
            peer = Bspline()
            peer.order = source_curve.order
            peer.traj_id = source_curve.traj_id + 1000
            peer.drone_id = 1
            peer.start_time = last_sim_clock[0]
            peer.knots = list(source_curve.knots)
            peer.pos_pts = list(source_curve.pos_pts)
            peer.yaw_pts = list(source_curve.yaw_pts)
            peer.yaw_dt = source_curve.yaw_dt
            swarm_pub.publish(peer)
            emergency_deadline = time.monotonic() + 3.
            emergency_observed = False
            while time.monotonic() < emergency_deadline:
                rclpy.spin_once(node, timeout_sec=.01)
                planner_text = log_path.read_text(errors='replace')
                if 'to EMERGENCY_STOP' in planner_text:
                    emergency_observed = True
                    break
                if process.poll() is not None:
                    raise RuntimeError('planner exited during synthetic emergency scenario')
            emergency_curve_count = len(curves)
            if emergency_observed:
                hold_deadline = time.monotonic() + 2.
                while time.monotonic() < hold_deadline:
                    rclpy.spin_once(node, timeout_sec=.01)
            planner_text = log_path.read_text(errors='replace')
            transition_index = planner_text.find('to EMERGENCY_STOP')
            emergency_suffix = planner_text[transition_index:] if transition_index >= 0 else ''
            constant_curves = []
            for candidate in curves:
                if candidate.goal_id != first or len(candidate.pos_pts) < 4:
                    continue
                xs = [p.x for p in candidate.pos_pts]
                ys = [p.y for p in candidate.pos_pts]
                zs = [p.z for p in candidate.pos_pts]
                if max(xs)-min(xs) < 1e-6 and max(ys)-min(ys) < 1e-6 and max(zs)-min(zs) < 1e-6:
                    constant_curves.append(candidate)
            emergency_hold_curve = bool(constant_curves)
            if emergency_observed and not emergency_hold_curve:
                raise RuntimeError('EMERGENCY_STOP produced no constant-position B-spline')
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGINT)
                process.wait(timeout=10.)
            log.flush()
            transitions = [line.strip() for line in planner_text.splitlines()
                           if 'from ' in line and ' to ' in line]
            report = {
                'scope':'synthetic component fixture; no flight, PX4, VINS or world truth',
                'scenario_completed':True,
                'acceptance_passed':emergency_observed and emergency_hold_curve,
                'scenario':'same-path synthetic peer; map and freshness gates remained enabled',
                'emergency_stop_observed':emergency_observed,
                'emergency_hold_bspline_observed':emergency_hold_curve,
                'curve_count_at_observation':emergency_curve_count,
                'curve_count_after_observation':len(curves),
                'post_emergency_log':emergency_suffix.splitlines()[:24],
                'same_state_replan_transition_count':sum(
                    'from EXEC_TRAJ to EXEC_TRAJ' in line for line in transitions),
                'fsm_transitions':transitions,
                'published_curves':[{'goal_id':c.goal_id,'traj_id':c.traj_id,
                                     'constant_position':c in constant_curves}
                                    for c in curves],
                'certificate_metrics':[line.strip() for line in planner_text.splitlines()
                                      if 'Full-curve certificate metrics:' in line],
                'interpretation':('Planner-only emergency-hold publication; no B-spline was executed.'
                                  if emergency_observed and emergency_hold_curve else
                                  'The same-path peer caused repeated successful replanning but no emergency hold; odometry was static in this component fixture.')}
            (args.output_dir/'result.json').write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps(report))
            return
        if args.after_completion:
            curve = next(c for c in curves if c.goal_id==first)
            end_stamp = (curve.start_time.sec+curve.start_time.nanosec/1e9
                         +curve.knots[-curve.order-1]-curve.knots[curve.order])
            wait(lambda: 10+time.monotonic()-start>end_stamp+.2,
                 'completed curve hold', max(10.,end_stamp-10+2.))
        if args.stale_after_curve:
            depth_enabled[0] = False
        else:
            # For the completed case, place the new wall outside the body sphere
            # but inside the N05 terminal hold neighborhood. Active-curve cases
            # keep the earlier wall placement that intersects the remaining sweep.
            surface[0] = 3.75 if args.after_completion else 2.4
        if args.after_completion:
            def constant_terminal_hold(candidate):
                if candidate.goal_id != first or len(candidate.pos_pts) < 4:
                    return False
                xs = [p.x for p in candidate.pos_pts]
                ys = [p.y for p in candidate.pos_pts]
                zs = [p.z for p in candidate.pos_pts]
                return max(xs)-min(xs) < 1e-6 and max(ys)-min(ys) < 1e-6 and max(zs)-min(zs) < 1e-6
            wait(lambda: any(constant_terminal_hold(c) for c in curves)
                 or any(f.goal_id == first for f in faults),
                 'terminal hold response or refusal', 6.)
            hold_curves = [c for c in curves if constant_terminal_hold(c)]
            previous = len(curves)
            until = time.monotonic()+.3
            while time.monotonic() < until:
                rclpy.spin_once(node, timeout_sec=.005)
            planner_text = log_path.read_text(errors='replace')
            transitions = [line.strip() for line in planner_text.splitlines()
                           if 'from ' in line and ' to ' in line]
            report = {
                'scope':'synthetic component fixture; no flight, PX4, VINS or world truth',
                'scenario_completed':True,
                'acceptance_passed':bool(any('to EMERGENCY_STOP' in line for line in transitions)
                                         and hold_curves and len(curves)==previous),
                'scenario':'completed planner curve; new obstacle enters terminal-hold neighborhood',
                'emergency_stop_observed':any('to EMERGENCY_STOP' in line for line in transitions),
                'emergency_hold_bspline_observed':bool(hold_curves),
                'hold_curve_traj_ids':[c.traj_id for c in hold_curves],
                'faults':[{'goal_id':f.goal_id,'epoch':f.epoch,'reason':f.reason}
                          for f in faults],
                'late_curves_after_hold':len(curves)-previous,
                'fsm_transitions':transitions,
                'certificate_metrics':[line.strip() for line in planner_text.splitlines()
                                      if 'Full-curve certificate metrics:' in line],
                'interpretation':'Planner-only emergency hold after terminal-hold obstruction; no B-spline was executed.'}
            (args.output_dir/'result.json').write_text(json.dumps(report,indent=2)+'\n')
            print(json.dumps(report))
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGINT)
                process.wait(timeout=10.)
            log.flush()
            return
        wait(lambda: any(f.goal_id==first for f in faults), 'remaining-curve rejection', 5.)
        first_fault = next(f for f in faults if f.goal_id==first)
        expected_fault = ('full_curve_terminal_hold_' if args.after_completion
                          else 'full_curve_')
        if not first_fault.reason.startswith(expected_fault):
            raise RuntimeError('unexpected execution safety fault: '+first_fault.reason)
        if args.stale_after_curve and not any(
                marker in first_fault.reason for marker in
                ('stale', 'timeout', 'depth_pose_gate_closed', 'no_fresh_fused_depth')):
            raise RuntimeError('stale-map scenario fault was not freshness-related: '
                               + first_fault.reason)
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
        transitions = [line.strip() for line in
                       log_path.read_text(errors='replace').splitlines()
                       if 'from ' in line and ' to ' in line]
        first_goal_curves = [c for c in curves if c.goal_id == first]
        report = {'scope':'synthetic component fixture; no flight, PX4, VINS or world truth',
                  'passed':True,'after_completion':args.after_completion,
                  'stale_after_curve':args.stale_after_curve,
                  'queries':rows,'certified_curves':len(curves),
                  'first_goal_curve_count':len(first_goal_curves),
                  'emergency_stop_observed':any('EMERGENCY_STOP' in line
                                                for line in log_path.read_text(errors='replace').splitlines()),
                  'fsm_transitions':transitions,
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
