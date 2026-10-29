#!/usr/bin/env python3
"""Synthetic ROS test: official unknown query, airborne handoff, cancel and refusal."""
import argparse
import math
import threading
import time
import uuid

import rclpy
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.experimental.events_executor import EventsExecutor
from rclpy.qos import QoSProfile, DurabilityPolicy
from uav_interfaces.msg import LocalizationStatus, MapStatus, NavigationCommand, TrajectoryCancel, Px4BridgeStatus
from uav_interfaces.srv import QueryOccupancySphere
from uav_interfaces.action import NavigateToPose
from uav_navigation.node import NavigationNode


def wait(predicate, timeout=5):
    deadline = time.monotonic()+timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.01)
    raise TimeoutError('official navigation probe timed out')


def completed(future):
    wait(future.done)
    return future.result()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--project-root', required=True)
    args = p.parse_args()
    rclpy.init()
    nav = NavigationNode(parameter_overrides=[rclpy.parameter.Parameter('project_root', value=args.project_root),
                                              rclpy.parameter.Parameter('use_sim_time', value=True)])
    assert nav.official_ego and nav.query_radius_m == 0
    peer = Node('official_navigation_peer')
    executor = EventsExecutor()
    executor.add_node(nav)
    executor.add_node(peer)
    epoch, map_id = uuid.uuid4().hex, uuid.uuid4().hex
    mode = {'reason': 'unobserved_not_occupied', 'airborne': False}
    goals, cancels, queries = [], [], []
    q = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    lp = peer.create_publisher(LocalizationStatus, '/localization/status', q)
    mp = peer.create_publisher(MapStatus, '/mapping/status', q)
    op = peer.create_publisher(Odometry, '/localization/optimized_imu_odom', 10)
    bp = peer.create_publisher(Px4BridgeStatus, '/uav_px4_bridge/status', 10)
    cp = peer.create_publisher(Clock, '/clock', 10)
    peer.create_subscription(NavigationCommand, '/navigation/ego_goal', goals.append, 10)
    peer.create_subscription(TrajectoryCancel, '/navigation/trajectory_cancel', cancels.append, 10)

    def publish():
        c = Clock(); c.clock.sec = 10; cp.publish(c)
        l = LocalizationStatus(); l.epoch = epoch; l.valid = True; l.state = 1; lp.publish(l)
        m = MapStatus(); m.epoch = epoch; m.map_id = map_id; m.input_ready = True; m.reset_acknowledged = True; mp.publish(m)
        o = Odometry(); o.header.frame_id = 'odom_'+epoch; o.header.stamp.sec = 10; o.pose.pose.orientation.w = 1.; op.publish(o)
        b = Px4BridgeStatus(); b.phase = 'ACTIVE' if mode['airborne'] else 'DISABLED'
        b.armed = mode['airborne']; b.control_enabled = mode['airborne']; b.landed = not mode['airborne']; bp.publish(b)

    timer = peer.create_timer(.02, publish)

    def query(req, res):
        queries.append(req)
        res.accepted = True; res.reason = mode['reason']
        res.free = res.reason in ('free', 'unobserved_not_occupied')
        res.epoch = req.expected_epoch; res.map_id = req.expected_map_id
        res.header.frame_id = req.frame_id; res.header.stamp.sec = 10
        res.last_fusion_stamp.sec = 10; res.last_depth_source_stamp.sec = 10
        res.center = req.center; res.radius_m = req.radius_m
        res.unknown_count = int(res.reason == 'unobserved_not_occupied')
        res.free_count = int(res.reason == 'free'); res.occupied_count = int(res.reason == 'occupied')
        return res

    service = peer.create_service(QueryOccupancySphere, '/mapping/query_planning_occupancy', query)
    client = ActionClient(peer, NavigateToPose, '/navigation/navigate_to_pose')
    thread = threading.Thread(target=executor.spin, daemon=True); thread.start()

    def send():
        goal = NavigateToPose.Goal(); goal.target.header.frame_id = 'odom_'+epoch
        goal.target.pose.position.x = 1.; goal.target.pose.position.z = 1.
        goal.target.pose.orientation.w = 1.; goal.position_tolerance_m = .05
        goal.yaw_tolerance_rad = .1; goal.dwell_s = 1.; goal.timeout_s = 3.
        handle = completed(client.send_goal_async(goal)); assert handle.accepted
        return handle

    try:
        wait(lambda: client.wait_for_server(timeout_sec=0.) and nav.core.localization_ready
             and nav._map_ready(time.monotonic()) and nav._ego_goal_pub.get_subscription_count()>0
             and nav._trajectory_cancel_pub.get_subscription_count()>0 and nav._map_query.service_is_ready())
        result = completed(send().get_result_async())
        assert result.result.reason == 'vehicle_not_airborne' and not goals
        mode['airborne'] = True
        wait(lambda: nav._airborne_ready(time.monotonic()))
        handle = send(); wait(lambda: len(goals)==1)
        assert queries[-1].radius_m == 0 and goals[0].map_id == map_id
        completed(handle.cancel_goal_async()); result = completed(handle.get_result_async())
        assert result.status == 5 and result.result.outcome == 'canceled'
        for reason in ('occupied', 'outside_map'):
            mode['reason'] = reason
            result = completed(send().get_result_async())
            assert result.status == 6 and result.result.reason == 'map_query_'+reason
        assert len(goals)==1
        print('PASS: official unknown point is forwarded only airborne; raw-free gate absent; cancel, occupied and outside refusal preserved')
    finally:
        executor.shutdown(); thread.join(timeout=2)
        nav.destroy_node(); peer.destroy_node(); rclpy.shutdown()


if __name__ == '__main__':
    main()
