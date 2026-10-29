"""Observe one VINS/EGO session and publish only /visualization/ego outputs."""
from collections import deque
from copy import deepcopy
import json
import math
from pathlib import Path
import re
import time

import rclpy
from rclpy.clock import Clock, ClockType, JumpThreshold
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import (QoSProfile, DurabilityPolicy, ReliabilityPolicy,
                       qos_profile_sensor_data)
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry, Path as PathMessage
from visualization_msgs.msg import Marker
from traj_utils.msg import Bspline
from uav_interfaces.msg import (LocalizationStatus, MapStatus, NavigationCommand,
                                TrajectoryCancel)

from .visualization_geometry import sample_bspline


class NavigationVisualization(Node):
    def __init__(self):
        super().__init__('navigation_visualization')
        root = Path(self.declare_parameter('project_root', '').value)
        session = json.loads(Path(self.declare_parameter('session_manifest', '').value).read_text())
        self.epoch = session['epoch']
        if not re.fullmatch('[0-9a-f]{32}', self.epoch):
            raise ValueError('invalid visualization session')
        self.frame = f'odom_{self.epoch}'
        self.policy = json.loads((root / 'config/components/navigation/visualization.json').read_text())
        nav = json.loads((root / 'config/components/navigation/task_supervisor.json').read_text())
        planner = json.loads((root / 'config/components/mapping/ego_planner.json').read_text())
        envelope = json.loads((root / 'config/components/navigation/vehicle_envelope.json').read_text())
        self.radius = envelope['spatial_budget']['body_reference_clearance_radius_m']
        self.hold_radius = self.radius + envelope['map_policy']['terminal_hold_neighborhood_radius_m']
        if (self.policy['schema'] != 1 or self.policy['output_prefix'] != '/visualization/ego'
                or not 2 <= self.policy['max_curve_samples'] <= 2000
                or not 4 <= self.policy['max_control_points'] <= 2000
                or not 2 <= self.policy['max_path_poses'] <= 10000
                or not all(math.isfinite(self.policy[key]) and self.policy[key] > 0
                           for key in ['sample_period_s', 'path_min_distance_m',
                                       'path_max_interval_s', 'publish_period_wall_s'])):
            raise ValueError('invalid visualization policy')
        self.ready = False
        self.received = 0.0
        self.loc_reason = 'waiting_for_localization'
        self.map_reason = 'waiting_for_map'
        self.map_source_ns = 0
        self.map_received = 0.0
        self.map_id = ''
        self.goal_id = ''
        self.planner_reason = 'waiting_for_trajectory'
        self.poses = deque(maxlen=self.policy['max_path_poses'])
        self.last_stamp = None
        self.current_pose = None
        self.status_pose = None
        self.odometry_received = 0.0
        self.clock_invalid = False
        self.canceled_goals = deque(maxlen=128)
        self.curve_end_ns = None
        self.markers = {}
        output_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                                durability=DurabilityPolicy.TRANSIENT_LOCAL)
        status_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                                durability=DurabilityPolicy.TRANSIENT_LOCAL)
        prefix = self.policy['output_prefix']
        self.actual_pub = self.create_publisher(PathMessage, prefix + '/actual_path', output_qos)
        self.planned_pub = self.create_publisher(PathMessage, prefix + '/planned_path', output_qos)
        names = ['goal', 'global_reference', 'initial_candidates', 'control_polygon',
                 'astar', 'envelope', 'hold_envelope', 'status']
        self.marker_pubs = {name: self.create_publisher(Marker, prefix + '/' + name, output_qos)
                            for name in names}
        self.subs = [
            self.create_subscription(LocalizationStatus, nav['localization_status_topic'], self.on_localization, status_qos),
            self.create_subscription(Odometry, nav['odometry_topic'], self.on_odometry, qos_profile_sensor_data),
            self.create_subscription(MapStatus, '/mapping/status', self.on_map, status_qos),
            self.create_subscription(NavigationCommand, nav['ego_goal_topic'], self.on_goal, 10),
            self.create_subscription(TrajectoryCancel, nav['trajectory_cancel_topic'], self.on_cancel, 10),
            self.create_subscription(TrajectoryCancel, '/navigation/planner_fault', self.on_cancel, 10),
            self.create_subscription(Bspline, f"/drone_{planner['drone_id']}_planning/bspline", self.on_spline, 10),
        ]
        self.debug_topics = {
            target: f"/drone_{planner['drone_id']}_plan_vis/{source}"
            for source, target in [('global_list', 'global_reference'), ('init_list', 'initial_candidates'),
                                   ('optimal_list', 'control_polygon'), ('a_star_list', 'astar')]}
        self.debug_subs = {}
        self.jump_handle = self.get_clock().create_jump_callback(
            JumpThreshold(min_forward=None, min_backward=Duration(nanoseconds=-1), on_clock_change=False),
            post_callback=lambda _jump: self.invalidate('clock_reversed'))
        self.timer = self.create_timer(self.policy['publish_period_wall_s'], self.publish,
                                       clock=Clock(clock_type=ClockType.STEADY_TIME))

    def header(self):
        msg = PoseStamped()
        msg.header.frame_id = self.frame
        msg.header.stamp = self.get_clock().now().to_msg()
        return msg.header

    def empty_path(self):
        msg = PathMessage()
        msg.header = self.header()
        return msg

    def clear_planning(self):
        if self.goal_id:
            self.canceled_goals.append(self.goal_id)
        self.goal_id = ''
        self.curve_end_ns = None
        self.planned_pub.publish(self.empty_path())
        for name, pub in self.marker_pubs.items():
            if name in ['status', 'envelope', 'hold_envelope']:
                continue
            msg = Marker()
            msg.header = self.header()
            msg.action = Marker.DELETEALL
            pub.publish(msg)
        self.markers.clear()

    def invalidate(self, reason):
        if reason in ['clock_reversed', 'odometry_time_reversed']:
            self.clock_invalid = True
        self.ready = False
        self.loc_reason = reason
        self.clear_planning()
        self.poses.clear()
        self.last_stamp = None
        self.current_pose = None
        self.actual_pub.publish(self.empty_path())
        for name in ['envelope', 'hold_envelope']:
            msg = Marker()
            msg.header = self.header()
            msg.action = Marker.DELETEALL
            self.marker_pubs[name].publish(msg)

    def on_localization(self, msg):
        self.received = time.monotonic()
        if self.clock_invalid:
            self.invalidate('clock_reversed')
            return
        valid = (not self.clock_invalid and msg.epoch == self.epoch
                 and msg.header.frame_id == self.frame and msg.valid)
        if not valid or msg.state != LocalizationStatus.TRACKING:
            self.invalidate(msg.reason or 'localization_session_invalid')
        else:
            self.ready = True
            self.loc_reason = msg.reason or 'tracking'

    def on_map(self, msg):
        if msg.epoch != self.epoch or msg.header.frame_id != self.frame:
            self.clear_planning()
            self.map_reason = 'map_session_mismatch'
            return
        if self.map_id and msg.map_id != self.map_id:
            self.clear_planning()
        self.map_id = msg.map_id
        self.map_received = time.monotonic()
        self.map_source_ns = msg.last_depth_source_stamp.sec * 10**9 + msg.last_depth_source_stamp.nanosec
        self.map_reason = msg.reason or ('ready' if msg.input_ready else 'not_ready')
        if not msg.input_ready:
            self.clear_planning()

    def on_odometry(self, msg):
        if not self.ready or msg.header.frame_id != self.frame:
            return
        stamp = msg.header.stamp.sec * 10**9 + msg.header.stamp.nanosec
        if self.last_stamp is not None and stamp <= self.last_stamp:
            if stamp < self.last_stamp:
                self.invalidate('odometry_time_reversed')
            return
        p, q = msg.pose.pose.position, msg.pose.pose.orientation
        if not all(math.isfinite(v) for v in [p.x, p.y, p.z, q.x, q.y, q.z, q.w]):
            return
        pose = PoseStamped(header=deepcopy(msg.header), pose=deepcopy(msg.pose.pose))
        self.current_pose = pose
        self.status_pose = pose
        self.odometry_received = time.monotonic()
        if self.poses:
            last = self.poses[-1]
            lp = last.pose.position
            distance = math.dist((p.x, p.y, p.z), (lp.x, lp.y, lp.z))
            elapsed = stamp - (last.header.stamp.sec * 10**9 + last.header.stamp.nanosec)
            if distance < self.policy['path_min_distance_m'] and elapsed < self.policy['path_max_interval_s'] * 10**9:
                self.last_stamp = stamp
                return
        self.poses.append(pose)
        self.last_stamp = stamp

    def on_goal(self, msg):
        if (not self.ready or msg.epoch != self.epoch or msg.target.header.frame_id != self.frame
                or (self.map_id and msg.map_id != self.map_id)):
            return
        if msg.goal_id == self.goal_id:
            return
        self.clear_planning()
        self.goal_id = msg.goal_id
        marker = Marker()
        marker.header = deepcopy(msg.target.header)
        marker.ns = 'accepted_target_yaw'
        marker.type = Marker.ARROW
        marker.pose = deepcopy(msg.target.pose)
        marker.scale.x, marker.scale.y, marker.scale.z = 0.65, 0.10, 0.10
        marker.color.r, marker.color.g, marker.color.a = 1.0, 0.8, 1.0
        self.marker_pubs['goal'].publish(marker)
        self.planner_reason = 'target_received'

    def on_cancel(self, msg):
        if msg.epoch == self.epoch:
            self.canceled_goals.append(msg.goal_id)
        if msg.epoch == self.epoch and (not self.goal_id or msg.goal_id == self.goal_id):
            self.clear_planning()
            self.planner_reason = msg.reason or 'trajectory_canceled'

    def on_spline(self, msg):
        if not self.ready or msg.epoch != self.epoch or msg.goal_id in self.canceled_goals:
            return
        if self.goal_id and msg.goal_id != self.goal_id:
            return
        try:
            points = sample_bspline([(p.x, p.y, p.z) for p in msg.pos_pts], list(msg.knots),
                                    msg.order, self.policy['sample_period_s'],
                                    self.policy['max_curve_samples'], self.policy['max_control_points'])
        except ValueError as exc:
            self.clear_planning()
            self.planner_reason = str(exc)
            return
        now = self.get_clock().now().nanoseconds
        end = msg.start_time.sec * 10**9 + msg.start_time.nanosec + int((msg.knots[len(msg.pos_pts)] - msg.knots[msg.order]) * 10**9)
        if end <= now:
            self.planner_reason = 'expired_curve'
            return
        path = self.empty_path()
        for p in points:
            pose = PoseStamped()
            pose.header = deepcopy(path.header)
            pose.pose.position.x, pose.pose.position.y, pose.pose.position.z = p
            pose.pose.orientation.w = 1.0
            path.poses.append(pose)
        self.goal_id = msg.goal_id
        self.curve_end_ns = end
        self.planned_pub.publish(path)
        self.planner_reason = f'trajectory {msg.traj_id}'

    def on_debug(self, msg, target):
        if not self.ready or msg.header.frame_id not in ['world', self.frame]:
            return
        # The dedicated planner consumes this session's odometry. Its upstream
        # drawing helper labels those same numerical coordinates as "world".
        # Relabel only these diagnostic copies; do not introduce a TF or alter
        # any input, trajectory, map or control message.
        marker = deepcopy(msg)
        marker.header.frame_id = self.frame
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.lifetime = Duration(seconds=0.0 if target == 'global_reference' else 2.0).to_msg()
        self.markers[(target, marker.ns, marker.id)] = marker
        if len(self.markers) > 256:
            del self.markers[next(iter(self.markers))]

    def publish(self):
        # Upstream drawing functions do extra work when someone subscribes.
        # Subscribe only while an actual RViz/debug consumer enables that layer.
        for target, topic in self.debug_topics.items():
            enabled = self.marker_pubs[target].get_subscription_count() > 0
            if enabled and target not in self.debug_subs:
                self.debug_subs[target] = self.create_subscription(
                    Marker, topic, lambda msg, target=target: self.on_debug(msg, target), 10)
            elif not enabled and target in self.debug_subs:
                self.destroy_subscription(self.debug_subs.pop(target))
                self.markers = {key: value for key, value in self.markers.items() if key[0] != target}
                marker = Marker()
                marker.header = self.header()
                marker.action = Marker.DELETEALL
                self.marker_pubs[target].publish(marker)
        if self.curve_end_ns is not None and self.get_clock().now().nanoseconds >= self.curve_end_ns:
            self.planned_pub.publish(self.empty_path())
            self.curve_end_ns = None
            self.planner_reason = 'trajectory_elapsed'
        actual = self.empty_path()
        actual.poses = list(self.poses)
        self.actual_pub.publish(actual)
        for marker_key, marker in list(self.markers.items()):
            age = self.get_clock().now().nanoseconds - (marker.header.stamp.sec * 10**9 + marker.header.stamp.nanosec)
            if marker_key[0] != 'global_reference' and age > 2 * 10**9:
                del self.markers[marker_key]
            else:
                self.marker_pubs[marker_key[0]].publish(marker)
        for name, radius, alpha in [('envelope', self.radius, 0.12), ('hold_envelope', self.hold_radius, 0.05)]:
            marker = Marker()
            marker.header = self.header()
            if self.current_pose is None:
                marker.action = Marker.DELETEALL
                self.marker_pubs[name].publish(marker)
                continue
            marker.ns = 'provisional_display_only'
            marker.type = Marker.SPHERE
            marker.pose = deepcopy(self.current_pose.pose)
            marker.scale.x = marker.scale.y = marker.scale.z = 2 * radius
            marker.color.g, marker.color.b, marker.color.a = 0.7, 1.0, alpha
            self.marker_pubs[name].publish(marker)
        marker = Marker()
        marker.header = self.header()
        marker.type = Marker.TEXT_VIEW_FACING
        if self.status_pose is not None:
            marker.pose = deepcopy(self.status_pose.pose)
        else:
            marker.pose.orientation.w = 1.0
        marker.pose.position.z += 1.2
        marker.scale.z = 0.16
        marker.color.r = marker.color.g = marker.color.b = marker.color.a = 1.0
        map_label = self.map_reason
        if self.map_source_ns:
            age = (self.get_clock().now().nanoseconds - self.map_source_ns) / 10**9
            map_label += f' (source {age:.2f}s)'
        marker.text = f'VIO: {self.loc_reason}\nMap: {map_label}\nEGO: {self.planner_reason}'
        self.marker_pubs['status'].publish(marker)


def main(args=None):
    rclpy.init(args=args)
    node = NavigationVisualization()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
