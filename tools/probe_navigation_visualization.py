#!/usr/bin/env python3
"""Synthetic ROS display integration; isolated domain, no sensors or control."""
from collections import defaultdict
import json
from pathlib import Path
import tempfile
import time

import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from geometry_msgs.msg import Point
from nav_msgs.msg import Odometry, Path as PathMessage
from visualization_msgs.msg import Marker
from traj_utils.msg import Bspline
from uav_interfaces.msg import LocalizationStatus, MapStatus, NavigationCommand, TrajectoryCancel
from uav_navigation.visualization import NavigationVisualization


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='rviz-display-probe-') as tmp:
        session = Path(tmp) / 'session.json'
        epoch = 'a' * 32
        frame = 'odom_' + epoch
        session.write_text(json.dumps({'epoch': epoch}))
        rclpy.init(args=['--ros-args', '-p', f'project_root:={args.project_root}',
                         '-p', f'session_manifest:={session}'])
        viewer = NavigationVisualization()
        peer = Node('visualization_probe')
        executor = SingleThreadedExecutor()
        executor.add_node(viewer)
        executor.add_node(peer)
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        loc = peer.create_publisher(LocalizationStatus, '/localization/status', latched)
        mapping = peer.create_publisher(MapStatus, '/mapping/status', latched)
        odom = peer.create_publisher(Odometry, '/localization/optimized_imu_odom', 10)
        goal_pub = peer.create_publisher(NavigationCommand, '/navigation/ego_goal', 10)
        curve_pub = peer.create_publisher(Bspline, '/drone_0_planning/bspline', 10)
        cancel_pub = peer.create_publisher(TrajectoryCancel, '/navigation/trajectory_cancel', 10)
        raw_marker = peer.create_publisher(Marker, '/drone_0_plan_vis/init_list', 10)
        received = defaultdict(list)
        subscriptions = []
        for name, message_type in [('planned_path', PathMessage), ('actual_path', PathMessage),
                                   ('goal', Marker), ('initial_candidates', Marker), ('status', Marker)]:
            subscriptions.append(peer.create_subscription(
                message_type, '/visualization/ego/' + name,
                lambda msg, name=name: received[name].append(msg), latched))
        x = 0.0
        valid = True

        def pump(seconds):
            nonlocal x
            until = time.monotonic() + seconds
            while time.monotonic() < until:
                status = LocalizationStatus()
                status.header.frame_id, status.epoch = frame, epoch
                status.valid = valid
                status.state = LocalizationStatus.TRACKING if valid else LocalizationStatus.LOCKED
                status.reason = 'synthetic_tracking' if valid else 'injected_localization_loss'
                loc.publish(status)
                ms = MapStatus()
                ms.header.frame_id, ms.epoch, ms.map_id = frame, epoch, 'map-one'
                ms.input_ready = True
                mapping.publish(ms)
                message = Odometry()
                message.header.frame_id = frame
                message.header.stamp = peer.get_clock().now().to_msg()
                x += 0.03
                message.pose.pose.position.x = x
                message.pose.pose.orientation.w = 1.0
                odom.publish(message)
                executor.spin_once(timeout_sec=0.01)

        checks = {}
        try:
            pump(1.0)
            target = NavigationCommand()
            target.epoch, target.goal_id, target.map_id = epoch, 'goal-one', 'map-one'
            target.target.header.frame_id = frame
            target.target.pose.position.x = 1.0
            target.target.pose.orientation.w = 1.0
            goal_pub.publish(target)
            pump(0.3)
            curve = Bspline()
            curve.epoch, curve.goal_id, curve.traj_id, curve.order = epoch, 'goal-one', 7, 3
            curve.start_time = peer.get_clock().now().to_msg()
            curve.start_time.sec += 10
            curve.knots = [0., 0., 0., 0., 1., 1., 1., 1.]
            curve.pos_pts = [Point(x=0., y=0., z=0.), Point(x=0., y=1., z=0.),
                             Point(x=1., y=1., z=0.), Point(x=1., y=0., z=0.)]
            curve_pub.publish(curve)
            marker = Marker()
            marker.header.frame_id, marker.ns, marker.id = 'world', 'candidate', 37
            marker.type, marker.pose.orientation.w = Marker.LINE_STRIP, 1.0
            marker.scale.x, marker.color.a = 0.05, 1.0
            marker.points = [Point(x=0., y=0., z=0.), Point(x=1., y=1., z=0.)]
            raw_marker.publish(marker)
            pump(0.5)
            displayed = [p for p in received['planned_path'] if p.poses]
            assert displayed and displayed[-1].header.frame_id == frame
            midpoint = displayed[-1].poses[len(displayed[-1].poses)//2].pose.position
            assert abs(midpoint.x - 0.5) < 1e-9 and abs(midpoint.y - 0.75) < 1e-9
            assert len(received['actual_path'][-1].poses) > 1
            assert any(m.type == Marker.ARROW and m.action == Marker.ADD for m in received['goal'])
            assert any(m.header.frame_id == frame and m.id == 37 for m in received['initial_candidates'])
            assert marker.header.frame_id == 'world'
            checks['actual_curve_path_target_and_diagnostic_frame'] = True
            before = len(displayed)
            curve.epoch = 'b' * 32
            curve_pub.publish(curve)
            pump(0.2)
            assert len([p for p in received['planned_path'] if p.poses]) == before
            checks['foreign_epoch_ignored'] = True
            cancel = TrajectoryCancel(epoch=epoch, goal_id='goal-one', reason='synthetic_cancel')
            cancel_pub.publish(cancel)
            pump(0.2)
            assert not received['planned_path'][-1].poses
            curve.epoch = epoch
            curve_pub.publish(curve)
            pump(0.2)
            assert not received['planned_path'][-1].poses
            checks['cancel_clears_and_late_curve_ignored'] = True
            valid = False
            pump(0.3)
            assert not received['actual_path'][-1].poses
            assert any('injected_localization_loss' in m.text for m in received['status'])
            checks['localization_loss_clears_paths_and_remains_visible'] = True
            pubs = peer.get_publisher_names_and_types_by_node('navigation_visualization', '/')
            assert all(name.startswith('/visualization/ego/') or name in ['/rosout', '/parameter_events']
                       for name, _types in pubs)
            checks['display_only_publishers'] = True
            report = {'passed': True, 'type': 'synthetic_ROS_display_integration',
                      'checks': checks, 'scope': 'No Gazebo, PX4, flight or GUI rendering',
                      'publishers': pubs}
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + '\n')
            print(json.dumps(report, indent=2))
        finally:
            executor.remove_node(viewer)
            executor.remove_node(peer)
            viewer.destroy_node()
            peer.destroy_node()
            executor.shutdown()
            rclpy.shutdown()


if __name__ == '__main__':
    main()
