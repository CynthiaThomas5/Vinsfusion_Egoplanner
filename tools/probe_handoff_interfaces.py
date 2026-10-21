#!/usr/bin/env python3
"""Read map/keyframe/localization APIs and exercise navigation without controls."""
import argparse
import json
import math
from pathlib import Path
import time

import rclpy
from action_msgs.msg import GoalStatus
from nav_msgs.msg import Odometry
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy, qos_profile_sensor_data
from uav_interfaces.action import NavigateToPose
from uav_interfaces.msg import LocalizationStatus, RGBDKeyframe
from uav_interfaces.srv import GetMapStatus


def stamp_ns(stamp):
    return stamp.sec * 1_000_000_000 + stamp.nanosec


def finite_pose(pose):
    values = (pose.position.x, pose.position.y, pose.position.z,
              pose.orientation.x, pose.orientation.y,
              pose.orientation.z, pose.orientation.w)
    return all(math.isfinite(value) for value in values)


class HandoffProbe(Node):
    def __init__(self, wait_s, action_timeout_s):
        super().__init__(
            'handoff_interface_probe',
            parameter_overrides=[Parameter('use_sim_time', value=True)])
        status_qos = QoSProfile(
            depth=1, reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.localization = None
        self.odom = None
        self.keyframes = []
        self.feedback = []
        self.map_response = None
        self.action_result = None
        self.action_accepted = False
        self.wait_s = wait_s
        self.action_timeout_s = action_timeout_s
        self.create_subscription(
            LocalizationStatus, '/localization/status', self.on_localization, status_qos)
        self.create_subscription(
            Odometry, '/localization/optimized_imu_odom', self.on_odom,
            qos_profile_sensor_data)
        self.create_subscription(
            RGBDKeyframe, '/mapping/rgbd_keyframes', self.on_keyframe,
            QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE))
        self.map_client = self.create_client(GetMapStatus, '/mapping/get_map_status')
        self.nav_client = ActionClient(self, NavigateToPose, '/navigation/navigate_to_pose')

    def on_localization(self, msg):
        self.localization = msg

    def on_odom(self, msg):
        self.odom = msg

    def on_keyframe(self, msg):
        self.keyframes.append(msg)
        self.keyframes = self.keyframes[-4:]

    def query_map(self, epoch):
        request = GetMapStatus.Request()
        request.expected_epoch = epoch
        future = self.map_client.call_async(request)
        end = time.monotonic() + min(2.0, self.wait_s)
        while rclpy.ok() and not future.done() and time.monotonic() < end:
            rclpy.spin_once(self, timeout_sec=0.05)
        return future.result() if future.done() else None

    def wait_for_inputs(self):
        deadline = time.monotonic() + self.wait_s
        last_query_wall = 0.0
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.05)
            loc = self.localization
            odom = self.odom
            if (loc is None or odom is None or not loc.valid
                    or loc.state != LocalizationStatus.TRACKING
                    or not loc.epoch or odom.header.frame_id != f'odom_{loc.epoch}'):
                continue
            if time.monotonic() - last_query_wall >= 0.5:
                if self.map_client.service_is_ready():
                    self.map_response = self.query_map(loc.epoch)
                last_query_wall = time.monotonic()
            response = self.map_response
            map_ready = (response is not None and response.accepted
                         and response.status.input_ready
                         and response.status.epoch == loc.epoch
                         and bool(response.status.map_id))
            if map_ready and self.keyframes:
                frame = self.keyframes[-1]
                if (frame.epoch == loc.epoch
                        and frame.map_id == response.status.map_id
                        and frame.calibration_sha256
                        and frame.color.width > 0 and frame.depth.width > 0):
                    return response, frame
        raise TimeoutError('localization, ready map status, and matching RGB-D keyframe did not arrive')

    def send_navigation_probe(self, epoch, odom):
        if not self.nav_client.wait_for_server(timeout_sec=min(5.0, self.wait_s)):
            raise TimeoutError('navigation action server unavailable')
        target = NavigateToPose.Goal()
        target.target.header.frame_id = f'odom_{epoch}'
        target.target.header.stamp = self.get_clock().now().to_msg()
        target.target.pose = odom.pose.pose
        # Submit the observed pose itself as the handoff target. No PX4 control
        # topic or Offboard service is used by this tool.
        target.position_tolerance_m = 0.30
        target.yaw_tolerance_rad = math.radians(15.0)
        target.dwell_s = 3.0
        target.timeout_s = self.action_timeout_s
        send_future = self.nav_client.send_goal_async(
            target, feedback_callback=self.on_feedback)
        end = time.monotonic() + min(10.0, self.wait_s)
        while rclpy.ok() and not send_future.done() and time.monotonic() < end:
            rclpy.spin_once(self, timeout_sec=0.05)
        if not send_future.done():
            raise TimeoutError('navigation goal acceptance timed out')
        handle = send_future.result()
        self.action_accepted = bool(handle.accepted)
        if not handle.accepted:
            raise RuntimeError('navigation action rejected the handoff goal')
        result_future = handle.get_result_async()
        end = time.monotonic() + max(15.0, self.wait_s)
        while rclpy.ok() and not result_future.done() and time.monotonic() < end:
            rclpy.spin_once(self, timeout_sec=0.05)
        if not result_future.done():
            handle.cancel_goal_async()
            raise TimeoutError('navigation action produced no terminal result')
        wrapped = result_future.result()
        result = wrapped.result
        status_text = {
            GoalStatus.STATUS_SUCCEEDED: 'succeeded',
            GoalStatus.STATUS_ABORTED: 'aborted',
            GoalStatus.STATUS_CANCELED: 'canceled',
        }.get(wrapped.status, f'status_{wrapped.status}')
        self.action_result = {
            'status': status_text,
            'success': bool(result.success),
            'outcome': result.outcome,
            'reason': result.reason,
            'final_frame': result.final_pose.header.frame_id,
        }

    def on_feedback(self, future):
        feedback = future.feedback
        self.feedback.append({
            'position_error_m': feedback.position_error_m,
            'yaw_error_rad': feedback.yaw_error_rad,
            'frame_id': feedback.current_pose.header.frame_id,
        })


def keyframe_report(msg):
    color_ns = stamp_ns(msg.color.header.stamp)
    depth_ns = stamp_ns(msg.depth.header.stamp)
    return {
        'epoch': msg.epoch,
        'map_id': msg.map_id,
        'header_stamp_ns': stamp_ns(msg.header.stamp),
        'header_frame': msg.header.frame_id,
        'calibration_sha256': msg.calibration_sha256,
        'color': {
            'stamp_ns': color_ns, 'frame': msg.color.header.frame_id,
            'encoding': msg.color.encoding, 'size': [msg.color.width, msg.color.height],
            'camera_info_stamp_ns': stamp_ns(msg.color_camera_info.header.stamp),
            'camera_info_frame': msg.color_camera_info.header.frame_id,
            'pose_stamp_ns': stamp_ns(msg.color_pose.header.stamp),
            'pose_frame': msg.color_pose.header.frame_id,
            'pose_finite': finite_pose(msg.color_pose.pose),
        },
        'depth': {
            'stamp_ns': depth_ns, 'frame': msg.depth.header.frame_id,
            'encoding': msg.depth.encoding, 'size': [msg.depth.width, msg.depth.height],
            'camera_info_stamp_ns': stamp_ns(msg.depth_camera_info.header.stamp),
            'camera_info_frame': msg.depth_camera_info.header.frame_id,
            'pose_stamp_ns': stamp_ns(msg.depth_pose.header.stamp),
            'pose_frame': msg.depth_pose.header.frame_id,
            'pose_finite': finite_pose(msg.depth_pose.pose),
        },
        'rgbd_stamp_delta_s': abs(color_ns - depth_ns) / 1e9,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--wait-seconds', type=float, default=45.0)
    parser.add_argument('--action-timeout-seconds', type=float, default=5.0)
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        'classification': 'interface_integration_probe_no_control',
        'result': 'FAIL',
    }
    rclpy.init()
    node = HandoffProbe(args.wait_seconds, args.action_timeout_seconds)
    try:
        status, keyframe = node.wait_for_inputs()
        frame = keyframe_report(keyframe)
        expected_frame = f'odom_{status.status.epoch}'
        stale_epoch = '0' * 32 if status.status.epoch != '0' * 32 else '1' * 32
        stale_response = node.query_map(stale_epoch)
        if (stale_response is None or stale_response.accepted
                or stale_response.reason != 'epoch_mismatch'
                or stale_response.status.epoch != status.status.epoch):
            raise RuntimeError('map status service did not reject a stale expected epoch')
        probe_topics = [
            name for name, _ in node.get_publisher_names_and_types_by_node(
                node.get_name(), node.get_namespace())]
        control_topics = [name for name in probe_topics if name.startswith('/fmu/in/')]
        if (frame['rgbd_stamp_delta_s'] > status.status.keyframe_max_rgbd_stamp_delta_s
                or frame['header_stamp_ns'] != frame['depth']['stamp_ns']
                or frame['header_frame'] != frame['depth']['frame']
                or frame['color']['frame'] != frame['color']['camera_info_frame']
                or frame['depth']['frame'] != frame['depth']['camera_info_frame']
                or frame['color']['pose_stamp_ns'] != frame['color']['stamp_ns']
                or frame['depth']['pose_stamp_ns'] != frame['depth']['stamp_ns']
                or frame['color']['pose_frame'] != expected_frame
                or frame['depth']['pose_frame'] != expected_frame
                or not frame['color']['pose_finite']
                or not frame['depth']['pose_finite']):
            raise RuntimeError('RGB-D keyframe source-time or pose validation failed')
        report.update({
            'epoch': status.status.epoch,
            'map_status': {
                'accepted': status.accepted,
                'reason': status.reason,
                'map_id': status.status.map_id,
                'input_ready': status.status.input_ready,
                'occupancy_cloud_received': status.status.occupancy_cloud_received,
                'occupied_point_count': status.status.occupied_point_count,
                'forwarded_depth_count': status.status.forwarded_depth_count,
                'calibration_sha256': status.status.calibration_sha256,
                'input_config_sha256': status.status.input_config_sha256,
                'keyframe_max_rgbd_stamp_delta_s': (
                    status.status.keyframe_max_rgbd_stamp_delta_s),
                'stale_epoch_probe': {
                    'expected_epoch': stale_epoch,
                    'accepted': stale_response.accepted,
                    'reason': stale_response.reason,
                    'reported_epoch': stale_response.status.epoch,
                },
            },
            'rgbd_keyframe': frame,
            'localization': {
                'valid': node.localization.valid,
                'state': int(node.localization.state),
                'reason': node.localization.reason,
                'source_stamp_ns': stamp_ns(node.localization.source_stamp),
            },
            'probe_published_topics': probe_topics,
            'probe_control_topics': control_topics,
        })
        node.send_navigation_probe(status.status.epoch, node.odom)
        report['navigation'] = {
            'accepted': node.action_accepted,
            'target_source': 'observed_localization_odometry_pose',
            'target_pose': {
                'position': [node.odom.pose.pose.position.x,
                             node.odom.pose.pose.position.y,
                             node.odom.pose.pose.position.z],
                'orientation_xyzw': [node.odom.pose.pose.orientation.x,
                                     node.odom.pose.pose.orientation.y,
                                     node.odom.pose.pose.orientation.z,
                                     node.odom.pose.pose.orientation.w],
            },
            'feedback_samples': len(node.feedback),
            'terminal_result': node.action_result,
        }
        report['result'] = (
            'PASS' if node.action_result and not control_topics else 'FAIL')
    except Exception as exc:  # noqa: BLE001
        report['failure'] = f'{type(exc).__name__}: {exc}'
    finally:
        node.destroy_node()
        rclpy.shutdown()
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
