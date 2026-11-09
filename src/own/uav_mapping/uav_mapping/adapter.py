"""Time-align structurally valid depth inputs before the EGO plan_env mapper."""
from collections import deque
import hashlib
import json
import math
from pathlib import Path
import re
import time
import uuid

import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import (QoSProfile, DurabilityPolicy, ReliabilityPolicy,
                       qos_profile_sensor_data)
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import CameraInfo, Image, PointCloud2
from uav_interfaces.msg import LocalizationStatus, MapStatus, RGBDKeyframe
from uav_interfaces.srv import GetMapStatus, ResetMapping
from uav_sim.geometry import load_session_rig

from .mapping_input import (camera_info_matches, depth_camera_pose,
                            depth_layout_valid, pose_at)


def stamp_ns(header):
    return header.stamp.sec * 1_000_000_000 + header.stamp.nanosec


class MappingInputAdapter(Node):
    def __init__(self):
        super().__init__('mapping_input_adapter')
        root = Path(self.declare_parameter('project_root', '').value).resolve()
        policy_relative = self.declare_parameter(
            'policy_config', 'config/components/mapping/ego_input.json').value
        policy_path = (root / policy_relative).resolve()
        if root not in policy_path.parents:
            raise ValueError('Mapping policy must be inside project_root')
        self.policy = json.loads(policy_path.read_text())
        self.policy_sha256 = hashlib.sha256(policy_path.read_bytes()).hexdigest()
        session_path = self.declare_parameter('session_manifest', '').value.strip()
        rig_override = self.declare_parameter('rig_config', '').value.strip()
        session = json.loads(Path(session_path).read_text()) if session_path else {}
        self.rig = load_session_rig(root, session, rig_override or None)
        self.rgb_enabled = bool(self.rig.get('rgb_enabled', 'color' in self.rig['cameras']))
        self.max_bracket_ns = int(self.policy['max_pose_bracket_s'] * 1e9)
        self.odom_history = deque(maxlen=self.policy['odom_history_size'])
        self.pending_depth = deque()
        self.color_history = deque(maxlen=12)
        self.pending_keyframe_depth = deque()
        self.color_camera_info = None
        self.depth_camera_info = None
        self.last_keyframe_stamp_ns = None
        self.keyframe_count = 0
        self.keyframe_dropped = 0
        self.last_map_source_stamp_ns = None
        self.last_occupancy_stamp_ns = None
        self.occupied_point_count = 0
        self.occupancy_cloud_received = False
        self.epoch = ''
        self.map_id = ''
        self.map_ready = False
        self.map_dirty = False
        self.reset_needed = False
        self.reset_future = None
        self.reset_inflight = None
        self.loc_ok = False
        self.depth_layout_ok = False
        self.latched = False
        self.reason = 'waiting_for_status'
        self.loc_receipt_wall = None
        self.last_odom_stamp = None
        self.last_depth_stamp = None
        self.forwarded = 0
        self.dropped = 0
        self.depth_callback_count = 0
        self.pending_depth_high_water_count = 0
        self.last_depth_forward_monotonic_ns = 0

        sensor_qos = qos_profile_sensor_data
        status_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                                durability=DurabilityPolicy.TRANSIENT_LOCAL)
        ego_qos = QoSProfile(depth=50, reliability=ReliabilityPolicy.RELIABLE)
        keyframe_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE)
        self.depth_pub = self.create_publisher(Image, self.policy['ego_depth_topic'], ego_qos)
        self.pose_pub = self.create_publisher(PoseStamped, self.policy['ego_pose_topic'], ego_qos)
        self.keyframe_pub = self.create_publisher(
            RGBDKeyframe, self.policy['keyframe_topic'], keyframe_qos)
        self.status_pub = self.create_publisher(
            MapStatus, self.policy['map_status_topic'], status_qos)
        self.reset_client = self.create_client(ResetMapping, self.policy['map_reset_service'])
        self.status_service = self.create_service(
            GetMapStatus, self.policy['map_status_service'], self.on_get_map_status)
        self.subscriptions_owned = [
            self.create_subscription(Image, self.policy['depth_topic'], self.on_depth, sensor_qos),
            self.create_subscription(
                CameraInfo, self.policy['depth_camera_info_topic'],
                self.on_depth_camera_info, sensor_qos),
            self.create_subscription(Odometry, self.policy['optimized_odometry_topic'], self.on_odom, sensor_qos),
            self.create_subscription(LocalizationStatus, self.policy['localization_status_topic'], self.on_localization, status_qos),
            self.create_subscription(
                PointCloud2, self.policy['ego_occupancy_topic'],
                self.on_occupancy, qos_profile_sensor_data),
        ]
        if self.rgb_enabled:
            self.subscriptions_owned.extend([
                self.create_subscription(Image, self.policy['color_topic'], self.on_color, sensor_qos),
                self.create_subscription(
                    CameraInfo, self.policy['color_camera_info_topic'],
                    self.on_color_camera_info, sensor_qos),
            ])
        self.last_status_publish_wall = 0.0
        self.timer = self.create_timer(0.05, self.on_timer,
                                       clock=Clock(clock_type=ClockType.STEADY_TIME))
        self.get_logger().info('mapping input adapter closed; waiting for valid epoch, depth, and plan_env reset service')

    def new_map_id(self):
        self.map_id = f'{self.epoch}-{uuid.uuid4().hex}'
        self.map_ready = False
        self.reset_needed = True
        self.pending_keyframe_depth.clear()
        self.last_keyframe_stamp_ns = None
        self.last_map_source_stamp_ns = None
        self.last_depth_forward_monotonic_ns = 0
        self.last_occupancy_stamp_ns = None
        self.occupied_point_count = 0
        self.occupancy_cloud_received = False
        self._pump_reset()

    def clear_pending(self):
        self.pending_depth.clear()
        self.pending_keyframe_depth.clear()
        self.color_history.clear()
        self.odom_history.clear()
        self.last_odom_stamp = None
        self.last_depth_stamp = None

    def invalidate(self, reason):
        self.reason = reason
        self.depth_layout_ok = False
        self.clear_pending()
        if self.map_dirty:
            self.map_dirty = False
            self.new_map_id()
        self.get_logger().warning(f'mapping gate closed: {reason}')

    def switch_epoch(self, epoch):
        self.clear_pending()
        self.epoch = epoch
        self.loc_ok = False
        self.depth_layout_ok = False
        self.latched = False
        self.reason = 'resetting_new_epoch'
        self.map_dirty = False
        self.new_map_id()
        self.get_logger().info(f'new localization epoch {epoch}; map reset required before input')

    def _pump_reset(self):
        if not self.reset_needed or not self.epoch or self.reset_future is not None:
            return
        if not self.reset_client.service_is_ready():
            return
        epoch, map_id = self.epoch, self.map_id
        request = ResetMapping.Request()
        request.epoch = epoch
        request.map_id = map_id
        self.reset_needed = False
        self.reset_inflight = (epoch, map_id)
        self.reset_future = self.reset_client.call_async(request)
        self.reset_future.add_done_callback(lambda future, e=epoch, m=map_id: self._reset_done(future, e, m))

    def _reset_done(self, future, epoch, map_id):
        self.reset_future = None
        inflight, self.reset_inflight = self.reset_inflight, None
        try:
            response = future.result()
        except Exception as exc:  # noqa: BLE001
            response = None
            self.get_logger().error(f'map reset service failed: {exc}')
        if (epoch, map_id) != (self.epoch, self.map_id):
            self.reset_needed = True
        elif response is not None and response.accepted:
            self.map_ready = True
            self.reason = 'map_reset_acknowledged'
            self.get_logger().info(f'plan_env cleared for map_id {map_id}')
            self._flush()
        else:
            self.reset_needed = True
            self.map_ready = False
            self.reason = response.reason if response is not None else 'map_reset_failed'
        self._pump_reset()

    def on_localization(self, msg):
        epoch = msg.epoch
        if epoch and not re.fullmatch(r'[0-9a-f]{32}', epoch):
            self.latched = True
            self.loc_ok = False
            self.invalidate('invalid_localization_epoch')
            return
        if epoch and epoch != self.epoch:
            self.switch_epoch(epoch)
        if not epoch:
            self.loc_ok = False
            return
        self.loc_receipt_wall = time.monotonic()
        valid = (msg.header.frame_id == f'odom_{epoch}'
                 and msg.body_frame == f'd435i_imu_{epoch}')
        if self.rig.get('source_kind') == 'hardware_json':
            valid = valid and msg.valid and msg.state == LocalizationStatus.TRACKING
        was_valid = self.loc_ok
        self.loc_ok = valid and not self.latched
        if not self.loc_ok:
            self.reason = msg.reason or 'localization_invalid'
            if was_valid or self.map_dirty:
                self.invalidate(msg.reason or 'localization_invalid')
            return
        self._flush()

    def on_odom(self, msg):
        if not self.loc_ok or self.latched:
            return
        if msg.header.frame_id != f'odom_{self.epoch}' or msg.child_frame_id != f'd435i_imu_{self.epoch}':
            self.latched = True
            self.loc_ok = False
            self.invalidate('odometry_frame_mismatch')
            return
        stamp = stamp_ns(msg.header)
        if self.last_odom_stamp is not None and stamp <= self.last_odom_stamp:
            self.latched = True
            self.loc_ok = False
            self.invalidate('odometry_stamp_not_increasing')
            return
        p, q = msg.pose.pose.position, msg.pose.pose.orientation
        values = (p.x, p.y, p.z, q.x, q.y, q.z, q.w)
        if not all(math.isfinite(value) for value in values):
            self.latched = True
            self.loc_ok = False
            self.invalidate('non_finite_odometry')
            return
        self.last_odom_stamp = stamp
        self.odom_history.append((stamp, (p.x, p.y, p.z), (q.x, q.y, q.z, q.w)))
        self._flush()

    def on_depth(self, msg):
        self.depth_callback_count += 1
        if self.latched:
            return
        stamp = stamp_ns(msg.header)
        if self.last_depth_stamp is not None and stamp <= self.last_depth_stamp:
            self.latched = True
            self.invalidate('depth_stamp_not_increasing')
            return
        self.last_depth_stamp = stamp
        rig_depth = self.rig['cameras']['depth']
        if not depth_layout_valid(msg, rig_depth['width'], rig_depth['height'],
                                  rig_depth.get('image_frame', rig_depth['frame'])):
            self.depth_layout_ok = False
            if self.map_dirty:
                self.invalidate('depth_layout_invalid')
            self.dropped += 1
            return
        # Invalid pixels stay invalid/unknown in EGO; do not add a project
        # minimum-valid-pixel health gate before forwarding a valid image.
        self.depth_layout_ok = True
        if self.rgb_enabled:
            self.pending_keyframe_depth.append((msg, time.monotonic()))
            while len(self.pending_keyframe_depth) > 8:
                self.pending_keyframe_depth.popleft()
                self.keyframe_dropped += 1
        if not self._inputs_ready(time.monotonic()):
            self.dropped += 1
            return
        self.pending_depth.append((msg, time.monotonic()))
        while len(self.pending_depth) > self.policy['pending_depth_size']:
            self.pending_depth.popleft()
            self.dropped += 1
        self.pending_depth_high_water_count = max(
            self.pending_depth_high_water_count, len(self.pending_depth))
        self._flush()

    def on_color(self, msg):
        if not self.rgb_enabled:
            return
        camera = self.rig['cameras']['color']
        if (msg.header.frame_id != camera.get('image_frame', camera['frame'])
                or msg.width != camera['width']
                or msg.height != camera['height'] or msg.encoding.lower() not in ('rgb8', 'bgr8')):
            self.keyframe_dropped += 1
            return
        stamp = stamp_ns(msg.header)
        if self.color_history and stamp <= stamp_ns(self.color_history[-1].header):
            self.keyframe_dropped += 1
            return
        self.color_history.append(msg)
        self._flush_keyframes()

    def _camera_info_matches(self, msg, camera):
        return camera_info_matches(msg, camera)

    def on_color_camera_info(self, msg):
        self.color_camera_info = msg if self._camera_info_matches(
            msg, self.rig['cameras']['color']) else None
        self._flush_keyframes()

    def on_depth_camera_info(self, msg):
        was_valid = self.depth_camera_info is not None
        matches = self._camera_info_matches(msg, self.rig['cameras']['depth'])
        self.depth_camera_info = msg if matches else None
        if self.rig.get('source_kind') != 'hardware_json':
            self._flush_keyframes()
            return
        if not matches:
            if was_valid and self.map_dirty:
                self.invalidate('depth_camera_info_mismatch')
            else:
                self.reason = 'depth_camera_info_mismatch'
            return
        self._flush()
        self._flush_keyframes()

    def on_occupancy(self, msg):
        if not self.epoch or msg.header.frame_id != f'odom_{self.epoch}':
            return
        self.last_occupancy_stamp_ns = stamp_ns(msg.header)
        self.occupied_point_count = min(
            int(msg.width) * int(msg.height), 0xffffffff)
        self.occupancy_cloud_received = True

    def _make_map_status(self):
        status = MapStatus()
        status.header.stamp = self.get_clock().now().to_msg()
        status.header.frame_id = f'odom_{self.epoch}' if self.epoch else ''
        status.epoch = self.epoch
        status.map_id = self.map_id
        status.reset_acknowledged = bool(self.map_ready)
        status.input_ready = self._inputs_ready(time.monotonic())
        if self.rig.get('source_kind') == 'hardware_json' and self.last_map_source_stamp_ns is None:
            status.input_ready = False
            if self.loc_ok:
                self.reason = 'waiting_for_first_map_input'
        status.reason = 'ready' if status.input_ready else self.reason
        for value, target in (
                (self.last_map_source_stamp_ns, status.last_depth_source_stamp),
                (self.last_occupancy_stamp_ns, status.last_occupancy_stamp)):
            if value is not None:
                target.sec, target.nanosec = divmod(value, 1_000_000_000)
        status.occupancy_cloud_received = self.occupancy_cloud_received
        status.occupied_point_count = self.occupied_point_count
        status.forwarded_depth_count = self.forwarded
        status.depth_callback_count = self.depth_callback_count
        status.pending_depth_count = len(self.pending_depth)
        status.pending_depth_high_water_count = self.pending_depth_high_water_count
        status.dropped_depth_count = self.dropped
        status.last_depth_forward_monotonic_ns = self.last_depth_forward_monotonic_ns
        status.calibration_sha256 = self.rig['calibration_sha256']
        status.input_config_sha256 = self.policy_sha256
        status.keyframe_count = self.keyframe_count
        status.keyframe_dropped_count = self.keyframe_dropped
        status.keyframe_max_rgbd_stamp_delta_s = self.policy[
            'keyframe_max_rgbd_stamp_delta_s']
        return status

    def on_get_map_status(self, request, response):
        response.status = self._make_map_status()
        if not self.epoch:
            response.accepted = False
            response.reason = 'no_active_epoch'
        elif request.expected_epoch and request.expected_epoch != self.epoch:
            response.accepted = False
            response.reason = 'epoch_mismatch'
        else:
            response.accepted = True
            response.reason = 'ok'
        return response

    def _flush_keyframes(self):
        if not self.rgb_enabled or not self.pending_keyframe_depth:
            return
        if not (self._inputs_ready(time.monotonic()) and self.map_dirty and self.map_id):
            return
        max_delta_ns = int(self.policy['keyframe_max_rgbd_stamp_delta_s'] * 1e9)
        min_period_ns = int(self.policy['keyframe_min_period_s'] * 1e9)
        color_calibration = self.rig['cameras']['color']
        depth_calibration = self.rig['cameras']['depth']
        while self.pending_keyframe_depth:
            depth, queued_wall = self.pending_keyframe_depth[0]
            depth_stamp = stamp_ns(depth.header)
            if time.monotonic() - queued_wall > self.policy['max_pending_depth_wall_s']:
                self.pending_keyframe_depth.popleft()
                self.keyframe_dropped += 1
                continue
            if (self.last_keyframe_stamp_ns is not None
                    and depth_stamp - self.last_keyframe_stamp_ns < min_period_ns):
                self.pending_keyframe_depth.popleft()
                continue
            if (not self._camera_info_matches(self.color_camera_info, color_calibration)
                    or not self._camera_info_matches(self.depth_camera_info, depth_calibration)):
                return
            color = min(self.color_history,
                        key=lambda item: abs(stamp_ns(item.header) - depth_stamp),
                        default=None)
            if color is None:
                return
            color_stamp = stamp_ns(color.header)
            if abs(color_stamp - depth_stamp) > max_delta_ns:
                if color_stamp > depth_stamp + max_delta_ns:
                    self.pending_keyframe_depth.popleft()
                    self.keyframe_dropped += 1
                    continue
                return
            depth_pose = pose_at(self.odom_history, depth_stamp, self.max_bracket_ns)
            color_pose = pose_at(self.odom_history, color_stamp, self.max_bracket_ns)
            if depth_pose is None or color_pose is None:
                latest_odom = self.odom_history[-1][0] if self.odom_history else None
                if latest_odom is None or latest_odom < max(depth_stamp, color_stamp):
                    return
                self.pending_keyframe_depth.popleft()
                self.keyframe_dropped += 1
                continue

            keyframe = RGBDKeyframe()
            keyframe.header.stamp = depth.header.stamp
            keyframe.header.frame_id = depth.header.frame_id
            keyframe.epoch = self.epoch
            keyframe.map_id = self.map_id
            keyframe.color = color
            keyframe.depth = depth
            keyframe.color_camera_info = self.color_camera_info
            keyframe.depth_camera_info = self.depth_camera_info
            keyframe.calibration_sha256 = self.rig['calibration_sha256']
            for output, image, camera in (
                    (keyframe.color_pose, color, color_calibration),
                    (keyframe.depth_pose, depth, depth_calibration)):
                sample = color_pose if image is color else depth_pose
                position, orientation = depth_camera_pose(
                    sample[0], sample[1], self.rig['imu']['translation'],
                    camera['translation'], camera['R_body_optical'])
                output.header.frame_id = f'odom_{self.epoch}'
                output.header.stamp = image.header.stamp
                output.pose.position.x, output.pose.position.y, output.pose.position.z = position
                (output.pose.orientation.x, output.pose.orientation.y,
                 output.pose.orientation.z, output.pose.orientation.w) = orientation
            self.keyframe_pub.publish(keyframe)
            self.keyframe_count += 1
            self.last_keyframe_stamp_ns = depth_stamp
            self.pending_keyframe_depth.popleft()
            while (self.color_history
                   and stamp_ns(self.color_history[0].header) < depth_stamp - max_delta_ns):
                self.color_history.popleft()

    def _inputs_ready(self, wall):
        return (self.map_ready and self.loc_ok and self.depth_layout_ok
                and (self.rig.get('source_kind') != 'hardware_json'
                     or self.depth_camera_info is not None)
                and not self.latched
                and self.loc_receipt_wall is not None)

    def _flush(self):
        wall = time.monotonic()
        if self._inputs_ready(wall):
            while self.pending_depth:
                image, received_wall = self.pending_depth[0]
                stamp = stamp_ns(image.header)
                if wall - received_wall > self.policy['max_pending_depth_wall_s']:
                    self.pending_depth.popleft()
                    self.dropped += 1
                    continue
                pose = pose_at(self.odom_history, stamp, self.max_bracket_ns)
                if pose is None:
                    if self.odom_history and self.odom_history[-1][0] >= stamp:
                        self.pending_depth.popleft()
                        self.dropped += 1
                        continue
                    break
                optical = self.rig['cameras']['depth']
                camera_position, camera_orientation = depth_camera_pose(
                    pose[0], pose[1], self.rig['imu']['translation'],
                    optical['translation'], optical['R_body_optical'])
                out_pose = PoseStamped()
                out_pose.header.stamp = image.header.stamp
                out_pose.header.frame_id = f'odom_{self.epoch}'
                out_pose.pose.position.x, out_pose.pose.position.y, out_pose.pose.position.z = camera_position
                (out_pose.pose.orientation.x, out_pose.pose.orientation.y,
                 out_pose.pose.orientation.z, out_pose.pose.orientation.w) = camera_orientation
                self.last_depth_forward_monotonic_ns = time.monotonic_ns()
                self.depth_pub.publish(image)
                self.pose_pub.publish(out_pose)
                self.pending_depth.popleft()
                self.map_dirty = True
                self.last_map_source_stamp_ns = stamp
                self.forwarded += 1
        self._flush_keyframes()

    def on_timer(self):
        now = time.monotonic()
        self._pump_reset()
        self._flush()
        if now - self.last_status_publish_wall >= 0.2:
            self.status_pub.publish(self._make_map_status())
            self.last_status_publish_wall = now


def main():
    rclpy.init()
    node = None
    try:
        node = MappingInputAdapter()
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    except Exception:
        if rclpy.ok():
            raise
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
