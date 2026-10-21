#!/usr/bin/env python3
"""Synthetic ROS integration probe for map isolation across localization epochs."""
import argparse
import json
from pathlib import Path
import time
import uuid

import rclpy

from probe_mapping_adapter import MappingProbe, spin


class EpochProbe(MappingProbe):
    def __init__(self):
        super().__init__()
        self.pose_frames = []

    def on_pose(self, msg):
        super().on_pose(msg)
        self.pose_frames.append(msg.header.frame_id)


def publish_frame(node, stamp_ns):
    node.publish_localization_status()
    node.publish_odom(stamp_ns - 20_000_000)
    node.publish_depth(stamp_ns)
    node.publish_odom(stamp_ns + 20_000_000)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    rclpy.init()
    node = EpochProbe()
    start = time.monotonic()
    try:
        deadline = start + 15.0
        frame = 0
        while time.monotonic() < deadline:
            publish_frame(node, 20_000_000_000 + frame * 100_000_000)
            frame += 1
            spin(node, 0.1)
            if (len(node.depth_stamps & node.pose_stamps) >= 3
                    and node.max_occupied_points > 0):
                break

        mapped_before_switch = bool(node.map_points and max(node.map_points) > 0)
        if mapped_before_switch:
            # Drain callbacks already emitted by the first epoch before measuring
            # whether the reset barrier admits anything from the new epoch.
            spin(node, 0.2)

        old_epoch = node.epoch
        old_frame = f'odom_{old_epoch}'
        new_epoch = uuid.uuid4().hex
        node.epoch = new_epoch
        new_frame = f'odom_{new_epoch}'
        depth_before_switch = node.depth_outputs
        pose_before_switch = node.pose_outputs
        depth_stamps_before_switch = set(node.depth_stamps)
        pose_stamps_before_switch = set(node.pose_stamps)
        map_index_at_switch = len(node.map_points)
        pose_frame_index_at_switch = len(node.pose_frames)
        node.publish_localization_status()

        reset_deadline = time.monotonic() + 4.0
        empty_map_after_switch = False
        while time.monotonic() < reset_deadline:
            node.publish_localization_status()
            spin(node, 0.1)
            if any(points == 0 for points in node.map_points[map_index_at_switch:]):
                empty_map_after_switch = True
                break

        # Keep the new localization status fresh while withholding all sensor
        # samples. The reset acknowledgement must not release old cached pairs.
        hold_deadline = time.monotonic() + 0.4
        while time.monotonic() < hold_deadline:
            node.publish_localization_status()
            spin(node, 0.1)

        counts_after_reset_hold = [node.depth_outputs, node.pose_outputs]
        empty_map_index = next(
            (index for index in range(map_index_at_switch, len(node.map_points))
             if node.map_points[index] == 0),
            None,
        )
        frame = max(frame, 1)
        rebuild_deadline = time.monotonic() + 5.0
        while time.monotonic() < rebuild_deadline:
            publish_frame(node, 20_000_000_000 + frame * 100_000_000)
            frame += 1
            spin(node, 0.1)
            new_pairs = ((node.depth_stamps - depth_stamps_before_switch)
                         & (node.pose_stamps - pose_stamps_before_switch))
            if (len(new_pairs) >= 3 and node.map_points
                    and max(node.map_points[map_index_at_switch:] or [0]) > 0):
                break

        post_switch_frames = node.pose_frames[pose_frame_index_at_switch:]
        post_switch_pairs = sorted(
            (node.depth_stamps - depth_stamps_before_switch)
            & (node.pose_stamps - pose_stamps_before_switch)
        )
        new_frame_count = sum(frame_id == new_frame for frame_id in post_switch_frames)
        old_frame_after_switch = old_frame in post_switch_frames
        post_reset_maps = node.map_points[map_index_at_switch:]
        result = {
            'old_epoch': old_epoch,
            'new_epoch': new_epoch,
            'elapsed_wall_s': round(time.monotonic() - start, 3),
            'mapped_before_switch': mapped_before_switch,
            'occupied_points_before_switch': max(node.map_points[:map_index_at_switch] or [0]),
            'empty_map_after_switch': empty_map_after_switch,
            'map_point_counts_after_switch': post_reset_maps,
            'outputs_before_switch': [depth_before_switch, pose_before_switch],
            'outputs_after_reset_hold_without_sensor_samples': counts_after_reset_hold,
            'reset_barrier_blocked_outputs': counts_after_reset_hold == [depth_before_switch, pose_before_switch],
            'post_switch_pose_frames': post_switch_frames,
            'new_epoch_pose_frame_count': new_frame_count,
            'new_epoch_paired_output_stamp_count': len(post_switch_pairs),
            'new_epoch_paired_output_stamps': post_switch_pairs,
            'old_epoch_pose_frame_after_switch': old_frame_after_switch,
            'final_depth_outputs': node.depth_outputs,
            'final_pose_outputs': node.pose_outputs,
            'depth_health_ready_observed': node.depth_health_ready,
            'last_pose_frame': node.last_pose_frame,
            'qualification': 'synthetic ROS integration only; validates plan_env reset barrier across adapter epochs, not clock rollback, physical geometry, planner response, or PX4 qualification',
        }
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))

        if (not mapped_before_switch or not empty_map_after_switch
                or not result['reset_barrier_blocked_outputs']
                or new_frame_count < 3 or old_frame_after_switch
                or node.last_pose_frame != new_frame):
            raise SystemExit('Mapping epoch reset did not clear and isolate old inputs before rebuilding the new epoch map')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
