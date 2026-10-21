#!/usr/bin/env python3
"""Observe fail-closed map reset and clean new-epoch recovery after a live VINS restart."""
import argparse
import json
from pathlib import Path
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import (DurabilityPolicy, QoSProfile, ReliabilityPolicy,
                       qos_profile_sensor_data)
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image, PointCloud2
from uav_interfaces.msg import LocalizationStatus


class VinsEpochRestartProbe(Node):
    def __init__(self, args):
        super().__init__('vins_epoch_restart_probe')
        self.args = args
        self.started = time.monotonic()
        self.old_epoch = None
        self.new_epoch = None
        self.new_epoch_wall = None
        self.last_status = None
        self.localization_history = []
        self.map_history = []
        self.depth_outputs = 0
        self.pose_outputs = 0
        self.optimized_outputs = 0
        self.propagated_outputs = 0
        self.pose_frames = []
        self.odometry_frames = []
        self.current_map_points = 0
        self.phase1_ready = None
        self.old_fault = None
        self.old_map_empty_wall = None
        self.phase1_settled_counts = None
        self.phase1_settled_wall = None
        self.phase1_failed = None
        self.phase2_empty_map = False
        self.new_tracking_wall = None
        self.new_map_wall = None
        self.final_stable_since = None
        self.final_result = None

        status_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                                durability=DurabilityPolicy.TRANSIENT_LOCAL)
        output_qos = QoSProfile(depth=100, reliability=ReliabilityPolicy.RELIABLE)
        self.create_subscription(LocalizationStatus, '/localization/status',
                                 self.on_localization, status_qos)
        self.create_subscription(PointCloud2, '/grid_map/occupancy', self.on_map, 10)
        self.create_subscription(Image, '/drone_0_depth_image', self.on_depth, output_qos)
        self.create_subscription(PoseStamped, '/drone_0_camera_pose', self.on_pose, output_qos)
        self.create_subscription(Odometry, '/localization/optimized_imu_odom',
                                 self.on_optimized, qos_profile_sensor_data)
        self.create_subscription(Odometry, '/localization/imu_odom',
                                 self.on_propagated, qos_profile_sensor_data)

    def elapsed(self):
        return round(time.monotonic() - self.started, 3)

    def output_counts(self):
        return {
            'ego_depth': self.depth_outputs,
            'ego_pose': self.pose_outputs,
            'optimized_odometry': self.optimized_outputs,
            'propagated_odometry': self.propagated_outputs,
        }

    def write_marker(self, path, data):
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(data, indent=2) + '\n')

    def on_localization(self, msg):
        current = (msg.epoch, msg.state, msg.valid, msg.reason)
        if current != self.last_status:
            self.localization_history.append({
                'wall_elapsed_s': self.elapsed(),
                'epoch': msg.epoch,
                'state': msg.state,
                'valid': msg.valid,
                'reason': msg.reason,
                'accepted_optimized': msg.accepted_optimized,
                'accepted_propagated': msg.accepted_propagated,
            })
            self.last_status = current
        if self.old_epoch is None and msg.epoch:
            self.old_epoch = msg.epoch
        if (self.old_epoch and msg.epoch == self.old_epoch and not msg.valid
                and msg.state in (LocalizationStatus.LOST, LocalizationStatus.LOCKED)
                and self.phase1_ready is not None and self.old_fault is None):
            self.old_fault = {
                'wall_elapsed_s': self.elapsed(),
                'state': msg.state,
                'reason': msg.reason,
                'output_counts': self.output_counts(),
            }
        if (self.old_epoch and msg.epoch and msg.epoch != self.old_epoch
                and self.new_epoch is None):
            self.new_epoch = msg.epoch
            self.new_epoch_wall = self.elapsed()
        if (self.new_epoch and msg.epoch == self.new_epoch and msg.valid
                and msg.state == LocalizationStatus.TRACKING and self.new_tracking_wall is None):
            self.new_tracking_wall = self.elapsed()

    def on_map(self, msg):
        self.current_map_points = msg.width * msg.height
        row = {'wall_elapsed_s': self.elapsed(), 'points': self.current_map_points}
        self.map_history.append(row)
        if (self.phase1_ready is None and self.last_status is not None
                and self.last_status[0] == self.old_epoch and self.last_status[1] == LocalizationStatus.TRACKING
                and self.last_status[2] and self.current_map_points > 0
                and self.depth_outputs > 0 and self.pose_outputs > 0):
            self.phase1_ready = {
                'wall_elapsed_s': self.elapsed(),
                'epoch': self.old_epoch,
                'map_points': self.current_map_points,
                'output_counts': self.output_counts(),
            }
            self.write_marker(self.args.phase1_ready, self.phase1_ready)
        if self.old_fault and self.current_map_points == 0 and self.old_map_empty_wall is None:
            self.old_map_empty_wall = self.elapsed()
        if (self.new_epoch and self.new_epoch_wall is not None
                and row['wall_elapsed_s'] >= self.new_epoch_wall and self.current_map_points == 0):
            self.phase2_empty_map = True
        if (self.new_tracking_wall is not None and self.current_map_points > 0
                and self.new_map_wall is None):
            self.new_map_wall = self.elapsed()

    def on_depth(self, _msg):
        self.depth_outputs += 1

    def on_pose(self, msg):
        self.pose_outputs += 1
        self.pose_frames.append({'wall_elapsed_s': self.elapsed(), 'frame_id': msg.header.frame_id})

    def on_optimized(self, msg):
        self.optimized_outputs += 1
        self.odometry_frames.append({'wall_elapsed_s': self.elapsed(), 'frame_id': msg.header.frame_id})

    def on_propagated(self, msg):
        self.propagated_outputs += 1
        self.odometry_frames.append({'wall_elapsed_s': self.elapsed(), 'frame_id': msg.header.frame_id})

    def maybe_write_phase1_failure(self):
        if not self.old_fault or self.old_map_empty_wall is None or self.phase1_failed:
            return
        if self.elapsed() < self.old_map_empty_wall + self.args.phase1_settle_s:
            return
        if self.phase1_settled_counts is None:
            self.phase1_settled_counts = self.output_counts()
            self.phase1_settled_wall = self.elapsed()
            return
        if self.elapsed() < self.phase1_settled_wall + self.args.phase1_confirm_s:
            return
        final_counts = self.output_counts()
        if final_counts != self.phase1_settled_counts:
            self.phase1_settled_counts = final_counts
            self.phase1_settled_wall = self.elapsed()
            return
        self.phase1_failed = {
            'old_epoch': self.old_epoch,
            'localization_fault': self.old_fault,
            'map_empty_wall_elapsed_s': self.old_map_empty_wall,
            'output_counts_at_settle': self.phase1_settled_counts,
            'output_counts_after_confirm': final_counts,
            'outputs_stable_after_confirm': True,
            'map_points_after_fault': [row for row in self.map_history
                                       if row['wall_elapsed_s'] >= self.old_fault['wall_elapsed_s']],
        }
        self.write_marker(self.args.phase1_failed, self.phase1_failed)

    def maybe_finish(self):
        if (self.new_tracking_wall is None or self.new_map_wall is None
                or not self.phase2_empty_map or self.final_stable_since is None):
            return
        if self.elapsed() < self.final_stable_since + self.args.phase2_confirm_s:
            return
        post_epoch_poses = [row for row in self.pose_frames
                            if row['wall_elapsed_s'] >= self.new_epoch_wall]
        post_epoch_odom = [row for row in self.odometry_frames
                           if row['wall_elapsed_s'] >= self.new_epoch_wall]
        self.final_result = {
            'scope': 'Live Gazebo D435i/VINS restart followed by a fresh VINS session epoch; read-only observation, no truth/control inputs',
            'wall_seconds': self.elapsed(),
            'old_epoch': self.old_epoch,
            'new_epoch': self.new_epoch,
            'epochs_differ': bool(self.old_epoch and self.new_epoch and self.old_epoch != self.new_epoch),
            'initial_tracking_and_nonempty_map': self.phase1_ready,
            'old_session_fault_and_map_clear': self.phase1_failed,
            'new_epoch_empty_map_observed': self.phase2_empty_map,
            'new_epoch_tracking_wall_elapsed_s': self.new_tracking_wall,
            'new_epoch_nonempty_map_wall_elapsed_s': self.new_map_wall,
            'pose_frames_after_new_epoch': post_epoch_poses,
            'odometry_frames_after_new_epoch': post_epoch_odom,
            'old_pose_frame_after_new_epoch': any(row['frame_id'] == f'odom_{self.old_epoch}' for row in post_epoch_poses),
            'old_odometry_frame_after_new_epoch': any(row['frame_id'] == f'odom_{self.old_epoch}' for row in post_epoch_odom),
            'final_output_counts': self.output_counts(),
            'map_point_counts': self.map_history,
            'localization_history': self.localization_history,
            'qualification': 'single live simulation restart/reset/recovery observation; not repeated fault-injection or flight qualification',
        }
        self.write_marker(self.args.output, self.final_result)
        rclpy.shutdown()

    def spin(self):
        deadline = self.started + self.args.max_wall_s
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.05)
            self.maybe_write_phase1_failure()
            if (self.new_tracking_wall is not None and self.new_map_wall is not None
                    and self.phase2_empty_map):
                if self.final_stable_since is None:
                    self.final_stable_since = self.elapsed()
                self.maybe_finish()
            else:
                self.final_stable_since = None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max-wall-s', type=float, default=120.0)
    parser.add_argument('--phase1-settle-s', type=float, default=0.8)
    parser.add_argument('--phase1-confirm-s', type=float, default=0.8)
    parser.add_argument('--phase2-confirm-s', type=float, default=1.5)
    parser.add_argument('--phase1-ready', required=True)
    parser.add_argument('--phase1-failed', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if min(args.max_wall_s, args.phase1_settle_s, args.phase1_confirm_s, args.phase2_confirm_s) <= 0:
        parser.error('all wall timeouts must be positive')
    rclpy.init()
    node = VinsEpochRestartProbe(args)
    try:
        node.spin()
    finally:
        if rclpy.ok():
            rclpy.shutdown()
        node.destroy_node()
    result = node.final_result
    if not result:
        raise SystemExit('VINS restart probe did not observe old-map clear and new-epoch map recovery before timeout')
    if (not result['epochs_differ'] or not result['new_epoch_empty_map_observed']
            or result['old_pose_frame_after_new_epoch'] or result['old_odometry_frame_after_new_epoch']):
        raise SystemExit('VINS restart did not isolate the new epoch from old map/pose/odometry frames')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
