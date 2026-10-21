"""Epoch-isolated Gazebo truth adapter for P3 SITL diagnostics only."""
from copy import deepcopy
import json
import math
from pathlib import Path
import time
import uuid

import rclpy
from rclpy.clock import Clock as ROSClock, ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import (QoSProfile, DurabilityPolicy, ReliabilityPolicy,
                       qos_profile_sensor_data)
from rclpy.signals import SignalHandlerOptions
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock as ClockMessage
from uav_interfaces.msg import LocalizationStatus


def stamp_ns(header):
    return header.stamp.sec * 1_000_000_000 + header.stamp.nanosec


def finite_odometry(msg):
    pose = msg.pose.pose
    twist = msg.twist.twist
    values = (pose.position.x, pose.position.y, pose.position.z,
              pose.orientation.x, pose.orientation.y, pose.orientation.z,
              pose.orientation.w, twist.linear.x, twist.linear.y,
              twist.linear.z, twist.angular.x, twist.angular.y,
              twist.angular.z)
    if not all(math.isfinite(value) for value in values):
        return False
    qnorm = math.sqrt(sum(value * value for value in values[3:7]))
    return 0.99 <= qnorm <= 1.01


class DebugTruthAdapter(Node):
    def __init__(self):
        super().__init__('debug_truth_adapter')
        root = Path(self.declare_parameter('project_root', '').value).resolve()
        use_sim_time = self.get_parameter('use_sim_time').value
        profile_path = root / 'config/profiles/debug_truth.json'
        settings_path = root / 'config/components/px4_bridge/debug_truth.json'
        profile = json.loads(profile_path.read_text())
        settings = json.loads(settings_path.read_text())
        if (profile.get('name') != 'debug_truth'
                or profile.get('ground_truth_online_allowed') is not True
                or profile.get('evaluation_ground_truth_read_only') is not True
                or profile.get('gps_position_aiding_allowed') is not False
                or settings.get('profile') != 'debug_truth'):
            raise ValueError('debug truth adapter requires the guarded debug_truth profile')
        if use_sim_time is not True:
            raise ValueError('debug truth adapter requires use_sim_time=true')

        self.settings = settings
        self.epoch = uuid.uuid4().hex
        self.clock_ns = None
        self.clock_receipt_wall = None
        self.last_source_stamp_ns = None
        self.last_odom_receipt_wall = None
        self.accepted = 0
        self.locked_reason = ''

        status_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                                durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.odom_pub = self.create_publisher(
            Odometry, settings['debug_truth_odometry_topic'],
            QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE))
        self.status_pub = self.create_publisher(
            LocalizationStatus, settings['debug_truth_status_topic'], status_qos)
        self.subscriptions_owned = [
            self.create_subscription(ClockMessage, settings['debug_truth_clock_topic'],
                                     self.on_clock, qos_profile_sensor_data),
            self.create_subscription(Odometry, settings['debug_truth_raw_odometry_topic'],
                                     self.on_odometry, qos_profile_sensor_data),
        ]
        self.timer = self.create_timer(
            settings['status_period_wall_s'], self.on_timer,
            clock=ROSClock(clock_type=ClockType.STEADY_TIME))
        self.publish_status(LocalizationStatus.INITIALIZING, False, 'waiting_for_truth')

    def publish_status(self, state, valid, reason, source_stamp=None):
        msg = LocalizationStatus()
        msg.header.frame_id = f'odom_{self.epoch}'
        if source_stamp is not None:
            msg.header.stamp = source_stamp
            msg.source_stamp = source_stamp
        msg.epoch = self.epoch
        msg.state = state
        msg.valid = valid
        msg.reason = reason
        msg.body_frame = f"{self.settings['debug_truth_output_body_frame_prefix']}{self.epoch}"
        msg.covariance_valid = False
        msg.normalized_cost = 0.0
        msg.good_pairs = 0
        msg.accepted_optimized = 0
        msg.accepted_propagated = 0
        self.status_pub.publish(msg)

    def lock(self, reason):
        if not self.locked_reason:
            self.locked_reason = reason
            self.publish_status(LocalizationStatus.LOCKED, False, reason)
            self.get_logger().error(f'debug truth gate locked: {reason}')

    def on_clock(self, msg):
        now = time.monotonic()
        value = msg.clock.sec * 1_000_000_000 + msg.clock.nanosec
        if value <= 0:
            return
        if self.clock_ns is not None and value < self.clock_ns:
            return self.lock('clock_regression')
        self.clock_ns = value
        self.clock_receipt_wall = now

    def on_odometry(self, msg):
        if self.locked_reason:
            return
        now = time.monotonic()
        source_stamp = stamp_ns(msg.header)
        expected_source_frame = self.settings['debug_truth_source_world_frame']
        expected_child_frame = self.settings['debug_truth_source_body_frame']
        if (msg.header.frame_id != expected_source_frame
                or msg.child_frame_id != expected_child_frame):
            return self.lock('truth_frame_mismatch')
        if source_stamp <= 0 and self.last_source_stamp_ns is None:
            return
        if source_stamp <= 0 or not finite_odometry(msg):
            return self.lock('truth_odometry_invalid')
        if self.last_source_stamp_ns is not None and source_stamp <= self.last_source_stamp_ns:
            return self.lock('truth_stamp_not_increasing')
        if self.clock_ns is None or self.clock_receipt_wall is None:
            return
        max_age = self.settings['debug_truth_source_max_age_sim_s']
        age = (self.clock_ns - source_stamp) / 1e9
        if abs(age) > max_age:
            return self.lock('truth_stamp_outside_sim_clock')

        output = deepcopy(msg)
        output.header.frame_id = f'odom_{self.epoch}'
        output.child_frame_id = (
            f"{self.settings['debug_truth_output_body_frame_prefix']}{self.epoch}")
        self.odom_pub.publish(output)
        self.last_source_stamp_ns = source_stamp
        self.last_odom_receipt_wall = now
        self.accepted += 1
        self.publish_status(LocalizationStatus.TRACKING, True,
                            'debug_truth_tracking', msg.header.stamp)

    def on_timer(self):
        if self.locked_reason:
            return
        now = time.monotonic()
        if (self.clock_receipt_wall is not None
                and now - self.clock_receipt_wall > self.settings['debug_truth_clock_stall_wall_s']):
            return self.lock('clock_stalled')
        if (self.last_odom_receipt_wall is not None
                and now - self.last_odom_receipt_wall > self.settings['debug_truth_odometry_max_receipt_age_wall_s']):
            return self.lock('truth_odometry_stale')
        if self.last_odom_receipt_wall is None:
            self.publish_status(LocalizationStatus.INITIALIZING, False,
                                'waiting_for_truth_odometry')


def main(args=None):
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    node = None
    try:
        node = DebugTruthAdapter()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except RuntimeError:
        if rclpy.ok():
            raise
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
