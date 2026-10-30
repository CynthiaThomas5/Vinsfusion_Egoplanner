"""Publish a session-bound historical obstacle cloud exclusively for RViz."""
import json
import math
from pathlib import Path
import re

import rclpy
from rclpy.clock import Clock, ClockType, JumpThreshold
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.qos import (QoSProfile, DurabilityPolicy, ReliabilityPolicy,
                       qos_profile_sensor_data)
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
from std_msgs.msg import Header
from uav_interfaces.msg import LocalizationStatus, MapStatus

from .voxel_history import VoxelHistory


def stamp_ns(stamp):
    return stamp.sec*1_000_000_000+stamp.nanosec


class ObservedHistory(Node):
    def __init__(self):
        super().__init__('observed_obstacle_history')
        root = Path(self.declare_parameter('project_root', '').value)
        session = json.loads(Path(self.declare_parameter('session_manifest', '').value).read_text())
        planner_path = self.declare_parameter(
            'planner_config', 'config/components/mapping/ego_planner.json').value
        planner = json.loads((root/planner_path).read_text())
        mapping = json.loads((root/'config/components/mapping/ego_input.json').read_text())
        policy = json.loads((root/'config/components/mapping/observed_history.json').read_text())
        self.epoch = session['epoch']
        if not re.fullmatch('[0-9a-f]{32}', self.epoch):
            raise ValueError('invalid history session epoch')
        if (policy['schema'] != 1
                or not policy['output_topic'].startswith('/visualization/mapping/')
                or not math.isfinite(policy['publish_period_wall_s'])
                or policy['publish_period_wall_s'] < .2
                or type(policy['max_voxels']) is not int
                or not 1 <= policy['max_voxels'] <= 500000):
            raise ValueError('invalid observed history policy')
        self.frame = f'odom_{self.epoch}'
        size = planner['map_size_m']
        self.history = VoxelHistory(planner.get('map_resolution_m', .1),
                                    (-size[0]/2, -size[1]/2, planner['ground_height_m']),
                                    size, policy['max_voxels'])
        self.identity = None
        self.map_acknowledged = False
        self.retired_ids = set()
        self.session_invalid = False
        self.cutoff_ns = 0
        self.last_cloud_ns = None
        self.capacity_warned = False
        retained = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                              durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.publisher = self.create_publisher(PointCloud2, policy['output_topic'], retained)
        self.subscriptions_owned = [
            self.create_subscription(MapStatus, mapping['map_status_topic'], self.on_map, retained),
            self.create_subscription(LocalizationStatus, mapping['localization_status_topic'],
                                     self.on_localization, retained),
            self.create_subscription(PointCloud2, mapping['ego_occupancy_topic'],
                                     self.on_cloud, qos_profile_sensor_data),
        ]
        self.jump_handle = self.get_clock().create_jump_callback(
            JumpThreshold(min_forward=None, min_backward=Duration(nanoseconds=-1), on_clock_change=False),
            post_callback=self.on_clock_jump)
        self.timer = self.create_timer(policy['publish_period_wall_s'], self.publish,
                                       clock=Clock(clock_type=ClockType.STEADY_TIME))
        self.publish()
        self.get_logger().info('Historical raw occupied observations only; no planning/control output')

    def clear(self):
        self.history.clear()
        self.last_cloud_ns = None
        self.capacity_warned = False
        self.publish()

    def on_clock_jump(self, _jump):
        if self.identity:
            self.retired_ids.add(self.identity)
        self.identity = None
        self.map_acknowledged = False
        self.clear()

    def on_localization(self, msg):
        if msg.epoch and msg.epoch != self.epoch:
            self.session_invalid = True
            self.identity = None
            self.clear()

    def on_map(self, msg):
        if self.session_invalid or msg.epoch != self.epoch or msg.header.frame_id != self.frame:
            if msg.epoch and msg.epoch != self.epoch:
                self.session_invalid = True
                self.identity = None
                self.clear()
            return
        if not msg.map_id or msg.map_id in self.retired_ids:
            return
        if msg.map_id != self.identity:
            if self.identity:
                self.retired_ids.add(self.identity)
            self.identity = msg.map_id
            self.map_acknowledged = False
            self.cutoff_ns = stamp_ns(msg.header.stamp)
            self.clear()
        if msg.reset_acknowledged and not self.map_acknowledged:
            self.cutoff_ns = max(self.cutoff_ns, stamp_ns(msg.header.stamp))
        self.map_acknowledged = msg.reset_acknowledged

    def on_cloud(self, msg):
        source_ns = stamp_ns(msg.header.stamp)
        if (self.session_invalid or not self.identity or not self.map_acknowledged
                or msg.header.frame_id != self.frame
                or source_ns < self.cutoff_ns):
            return
        if self.last_cloud_ns is not None and source_ns < self.last_cloud_ns:
            self.on_clock_jump(None)
            return
        self.last_cloud_ns = source_ns
        try:
            points = point_cloud2.read_points(msg, field_names=('x', 'y', 'z'), skip_nans=True)
            self.history.add((float(p[0]), float(p[1]), float(p[2])) for p in points)
        except (ValueError, AssertionError, KeyError) as exc:
            self.get_logger().warning(f'Ignoring malformed historical display cloud: {exc}')
            return
        if self.history.rejected_new_voxels and not self.capacity_warned:
            self.capacity_warned = True
            self.get_logger().warning('Historical display capacity reached; new voxels omitted until map reset')

    def publish(self):
        header = Header(frame_id=self.frame, stamp=self.get_clock().now().to_msg())
        self.publisher.publish(point_cloud2.create_cloud_xyz32(header, self.history.centers()))


def main():
    rclpy.init()
    node = ObservedHistory()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
