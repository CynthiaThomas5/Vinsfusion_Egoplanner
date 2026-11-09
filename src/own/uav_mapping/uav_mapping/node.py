"""Publish a depth freshness gate; this node does not create an occupancy map."""
import json
from pathlib import Path
import time

import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from rclpy.impl.implementation_singleton import rclpy_implementation
RCLError = rclpy_implementation.RCLError
from rclpy.qos import qos_profile_sensor_data, QoSProfile, DurabilityPolicy, ReliabilityPolicy
from sensor_msgs.msg import Image
from uav_interfaces.msg import DepthHealth

from .depth_gate import DepthFreshnessGate


class DepthHealthMonitor(Node):
    def __init__(self):
        super().__init__('depth_health_monitor')
        root = Path(self.declare_parameter('project_root', '').value).resolve()
        policy = json.loads((root/'config/components/mapping/depth_gate.json').read_text())
        self.gate = DepthFreshnessGate(policy, time.monotonic())
        qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                         durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.publisher = self.create_publisher(DepthHealth, '/mapping/depth_health', qos)
        self.subscription = self.create_subscription(
            Image, '/sensors/d435i/depth', self.on_depth, qos_profile_sensor_data)
        self.timer = self.create_timer(policy['status_period_wall_s'], self.on_timer,
                                       clock=Clock(clock_type=ClockType.STEADY_TIME))
        self.publish_status()

    def on_depth(self, msg):
        self.gate.observe(msg, time.monotonic())
        self.publish_status()

    def on_timer(self):
        self.gate.tick(time.monotonic())
        self.publish_status()

    def publish_status(self):
        msg = DepthHealth()
        msg.header.stamp = self.get_clock().now().to_msg()
        if self.gate.last_stamp_ns is not None:
            msg.source_stamp.sec, msg.source_stamp.nanosec = divmod(self.gate.last_stamp_ns, 1_000_000_000)
        msg.header.frame_id = self.gate.policy['expected_frame']
        msg.state = DepthFreshnessGate.STATES[self.gate.state]
        msg.valid = self.gate.state == 'READY'
        msg.reason = self.gate.reason
        msg.received_count = self.gate.received_count
        self.publisher.publish(msg)


def main():
    rclpy.init()
    node = None
    try:
        node = DepthHealthMonitor()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except RCLError:
        if rclpy.ok():
            raise
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
