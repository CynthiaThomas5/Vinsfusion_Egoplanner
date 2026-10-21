#!/usr/bin/env python3
"""Known-axis and profile-boundary tests for the PX4 frame conversion core."""

from pathlib import Path
import json
import math
import sys
import unittest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/own/uav_px4_bridge'))

from uav_px4_bridge.trajectory import (  # noqa: E402
    angle_difference,
    compute_ned_frame_alignment,
    compute_ned_origin_offset,
    compute_rig_frame_alignment,
    enu_to_ned,
    position_command_to_ned,
    px4_sensor_position_ned,
    rotate_ned_yaw,
    ros_enu_flu_quaternion_to_px4_ned_frd,
    validate_debug_truth_profile,
    yaw_enu_to_ned,
)
from uav_px4_bridge.vision_odometry import odometry_to_px4_values  # noqa: E402


EPOCH = '0123456789abcdef0123456789abcdef'
PROFILE = json.loads((ROOT / 'config/profiles/debug_truth.json').read_text())
FRAME_CONTRACT = json.loads((ROOT / 'config/components/px4_bridge/frames.json').read_text())


def command(**overrides):
    values = dict(
        TRAJECTORY_STATUS_READY=1,
        trajectory_flag=1,
        header=SimpleNamespace(frame_id='odom_' + EPOCH),
        position=SimpleNamespace(x=1.0, y=2.0, z=3.0),
        velocity=SimpleNamespace(x=4.0, y=5.0, z=6.0),
        acceleration=SimpleNamespace(x=7.0, y=8.0, z=9.0),
        yaw=0.0,
        yaw_dot=0.25,
        trajectory_id=4,
        goal_id='goal-1',
        epoch=EPOCH,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def odometry(**overrides):
    values = dict(
        header=SimpleNamespace(
            frame_id='odom_' + EPOCH,
            stamp=SimpleNamespace(sec=12, nanosec=345_000_000),
        ),
        child_frame_id='d435i_imu_' + EPOCH,
        pose=SimpleNamespace(pose=SimpleNamespace(
            position=SimpleNamespace(x=1.0, y=2.0, z=3.0),
            orientation=SimpleNamespace(x=0.0, y=0.0, z=0.0, w=1.0),
        )),
        twist=SimpleNamespace(twist=SimpleNamespace(
            linear=SimpleNamespace(x=4.0, y=5.0, z=6.0),
            angular=SimpleNamespace(x=0.1, y=0.2, z=0.3),
        )),
    )
    values.update(overrides)
    return SimpleNamespace(**values)


class Px4BridgeFrameTests(unittest.TestCase):
    def test_known_enu_axes_map_to_px4_ned(self):
        self.assertEqual(enu_to_ned((1.0, 2.0, 3.0)), (2.0, 1.0, -3.0))
        self.assertEqual(enu_to_ned((0.0, 0.0, -1.0)), (0.0, 0.0, 1.0))

    def test_ned_origin_offset_is_added_only_to_positions(self):
        offset = compute_ned_origin_offset((10.0, 20.0, 3.0), (4.0, 5.0, -2.0))
        self.assertEqual(offset, (-16.0, -5.0, 1.0))
        self.assertEqual(enu_to_ned((10.0, 20.0, 3.0), offset), (4.0, 5.0, -2.0))
        result = position_command_to_ned(command(), PROFILE, FRAME_CONTRACT,
                                          expected_epoch=EPOCH, origin_offset_ned=offset)
        self.assertEqual(result.position, (-14.0, -4.0, -2.0))
        self.assertEqual(result.velocity, (5.0, 4.0, -6.0))

    def test_paired_px4_origin_and_heading_alignment(self):
        alignment = compute_ned_frame_alignment(
            (10.0, 20.0, 3.0), 0.0, (4.0, 5.0, -2.0), 0.0)
        self.assertAlmostEqual(alignment.yaw_offset_ned, -math.pi / 2.0)
        for actual, expected in zip(alignment.origin_offset_ned, (-6.0, 25.0, 1.0)):
            self.assertAlmostEqual(actual, expected)
        source_ned = rotate_ned_yaw(enu_to_ned((10.0, 20.0, 3.0)),
                                    alignment.yaw_offset_ned)
        self.assertEqual(tuple(a + b for a, b in zip(
            source_ned, alignment.origin_offset_ned)), (4.0, 5.0, -2.0))
        with self.assertRaises(ValueError):
            compute_ned_frame_alignment((0.0, 0.0, 0.0), math.nan,
                                        (0.0, 0.0, 0.0), 0.0)

    def test_rig_alignment_accounts_for_d435i_sensor_leverarm(self):
        leverarm = (0.12, 0.0, -0.08)
        source_sensor_enu = (2.0, 1.12, -2.92)
        alignment = compute_rig_frame_alignment(
            source_sensor_enu, math.pi / 2.0, (1.0, 2.0, 3.0),
            (1.0, 0.0, 0.0, 0.0), 0.0, leverarm)
        self.assertAlmostEqual(alignment.yaw_offset_ned, 0.0)
        for actual in alignment.origin_offset_ned:
            self.assertAlmostEqual(actual, 0.0)
        self.assertEqual(px4_sensor_position_ned(
            (1.0, 2.0, 3.0), (1.0, 0.0, 0.0, 0.0), leverarm),
            (1.12, 2.0, 2.92))

    def test_rig_alignment_rotates_leverarm_with_px4_attitude(self):
        q_yaw_90 = (math.sqrt(0.5), 0.0, 0.0, math.sqrt(0.5))
        position = px4_sensor_position_ned(
            (1.0, 2.0, 3.0), q_yaw_90, (0.12, 0.0, -0.08))
        for actual, expected in zip(position, (1.0, 2.12, 2.92)):
            self.assertAlmostEqual(actual, expected)

    def test_heading_difference_wraps_at_pi(self):
        self.assertAlmostEqual(angle_difference(-math.pi + 0.01, math.pi - 0.01), 0.02)

    def test_identity_enu_flu_orientation_maps_to_east_facing_ned_frd(self):
        q_wxyz = ros_enu_flu_quaternion_to_px4_ned_frd((0.0, 0.0, 0.0, 1.0))
        self.assertAlmostEqual(abs(q_wxyz[0]), math.sqrt(0.5))
        self.assertAlmostEqual(q_wxyz[1], 0.0)
        self.assertAlmostEqual(q_wxyz[2], 0.0)
        self.assertAlmostEqual(abs(q_wxyz[3]), math.sqrt(0.5))
        with self.assertRaises(ValueError):
            ros_enu_flu_quaternion_to_px4_ned_frd((0.0, 0.0, 0.0, 0.0))

    def test_external_odometry_maps_all_axes_and_requires_explicit_px4_sample_time(self):
        with self.assertRaises(ValueError):
            odometry_to_px4_values(odometry(), PROFILE, FRAME_CONTRACT, 50_000,
                                   0.01, 0.02, 0.03, 100)
        result = odometry_to_px4_values(
            odometry(), PROFILE, FRAME_CONTRACT, 50_000, 0.01, 0.02, 0.03, 100,
            expected_epoch=EPOCH, timestamp_sample_us=49_800)
        self.assertEqual(result.position_ned, (2.0, 1.0, -3.0))
        self.assertAlmostEqual(abs(result.quaternion_ned_frd_wxyz[0]), math.sqrt(0.5))
        self.assertEqual(result.velocity_body_frd, (4.0, -5.0, -6.0))
        self.assertEqual(result.angular_velocity_body_frd, (0.1, -0.2, -0.3))
        self.assertEqual(result.position_variance, (0.01, 0.01, 0.01))
        self.assertEqual((result.timestamp, result.timestamp_sample, result.quality),
                         (50_000, 49_800, 100))

    def test_external_odometry_applies_paired_origin_and_heading(self):
        result = odometry_to_px4_values(
            odometry(), PROFILE, FRAME_CONTRACT, 50_000, 0.01, 0.02,
            0.03, 100, expected_epoch=EPOCH, timestamp_sample_us=49_800,
            origin_offset_ned=(-6.0, 25.0, 1.0),
            yaw_offset_ned=-math.pi / 2.0)
        self.assertAlmostEqual(result.position_ned[0], -5.0)
        self.assertAlmostEqual(result.position_ned[1], 23.0)
        self.assertEqual(result.position_ned[2], -2.0)
        self.assertAlmostEqual(abs(result.quaternion_ned_frd_wxyz[0]), 1.0)
        self.assertAlmostEqual(result.quaternion_ned_frd_wxyz[3], 0.0)

    def test_external_odometry_rejects_wrong_frame_epoch_and_variance(self):
        args = (PROFILE, FRAME_CONTRACT, 50_000, 0.01, 0.02, 0.03, 100)
        with self.assertRaises(ValueError):
            odometry_to_px4_values(odometry(child_frame_id='d435i_imu_' + 'f' * 32), *args,
                                   expected_epoch=EPOCH, timestamp_sample_us=49_800)
        wrong_epoch = odometry()
        wrong_epoch.header.frame_id = 'odom_' + 'f' * 32
        with self.assertRaises(ValueError):
            odometry_to_px4_values(wrong_epoch, *args, expected_epoch=EPOCH,
                                   timestamp_sample_us=49_800)
        with self.assertRaises(ValueError):
            odometry_to_px4_values(odometry(), PROFILE, FRAME_CONTRACT, 50_000,
                                   0.0, 0.02, 0.03, expected_epoch=EPOCH,
                                   source_quality=100,
                                   timestamp_sample_us=49_800)
        with self.assertRaises(ValueError):
            odometry_to_px4_values(odometry(), PROFILE, FRAME_CONTRACT, 50_000,
                                   0.01, 0.02, 0.03, 101, expected_epoch=EPOCH,
                                   timestamp_sample_us=49_800)

    def test_yaw_cardinals_map_from_enu_to_ned(self):
        self.assertAlmostEqual(yaw_enu_to_ned(0.0), math.pi / 2.0)
        self.assertAlmostEqual(yaw_enu_to_ned(math.pi / 2.0), 0.0)
        self.assertAlmostEqual(abs(yaw_enu_to_ned(-math.pi / 2.0)), math.pi)

    def test_ready_command_converts_all_trajectory_fields(self):
        result = position_command_to_ned(command(), PROFILE, FRAME_CONTRACT,
                                          expected_epoch=EPOCH)
        self.assertEqual(result.position, (2.0, 1.0, -3.0))
        self.assertEqual(result.velocity, (5.0, 4.0, -6.0))
        self.assertEqual(result.acceleration, (8.0, 7.0, -9.0))
        self.assertAlmostEqual(result.yaw, math.pi / 2.0)
        self.assertEqual(result.yaw_speed, -0.25)
        self.assertEqual((result.trajectory_id, result.goal_id, result.epoch),
                         (4, 'goal-1', EPOCH))

    def test_ready_command_uses_paired_heading_for_position_velocity_and_yaw(self):
        result = position_command_to_ned(
            command(), PROFILE, FRAME_CONTRACT, expected_epoch=EPOCH,
            yaw_offset_ned=-math.pi / 2.0)
        self.assertAlmostEqual(result.position[0], 1.0)
        self.assertAlmostEqual(result.position[1], -2.0)
        self.assertEqual(result.position[2], -3.0)
        self.assertAlmostEqual(result.velocity[0], 4.0)
        self.assertAlmostEqual(result.velocity[1], -5.0)
        self.assertEqual(result.velocity[2], -6.0)
        self.assertAlmostEqual(result.acceleration[0], 7.0)
        self.assertAlmostEqual(result.acceleration[1], -8.0)
        self.assertEqual(result.yaw, 0.0)

    def test_ready_command_converts_sensor_path_to_px4_body_reference(self):
        result = position_command_to_ned(
            command(), PROFILE, FRAME_CONTRACT, expected_epoch=EPOCH,
            sensor_leverarm_body_frd=(0.12, 0.0, -0.08))
        for actual, expected in zip(result.position, (2.0, 0.88, -2.92)):
            self.assertAlmostEqual(actual, expected)
        for actual, expected in zip(result.velocity, (4.97, 4.0, -6.0)):
            self.assertAlmostEqual(actual, expected)

    def test_non_ready_command_cannot_become_a_setpoint(self):
        self.assertIsNone(position_command_to_ned(command(trajectory_flag=4), PROFILE,
                                                  FRAME_CONTRACT))

    def test_vio_profile_is_rejected_for_debug_conversion(self):
        profile = json.loads((ROOT / 'config/profiles/vio_closed_loop.json').read_text())
        with self.assertRaises(ValueError):
            validate_debug_truth_profile(profile, FRAME_CONTRACT)

    def test_unsupported_frame_contract_is_rejected(self):
        bad_contract = dict(FRAME_CONTRACT, source_world_frame='arbitrary_vio_world')
        with self.assertRaises(ValueError):
            validate_debug_truth_profile(PROFILE, bad_contract)

    def test_epoch_frame_mismatch_is_rejected(self):
        msg = command()
        msg.header.frame_id = 'world'
        with self.assertRaises(ValueError):
            position_command_to_ned(msg, PROFILE, FRAME_CONTRACT)

    def test_nonfinite_trajectory_is_rejected(self):
        msg = command()
        msg.velocity.y = float('nan')
        with self.assertRaises(ValueError):
            position_command_to_ned(msg, PROFILE, FRAME_CONTRACT)


if __name__ == '__main__':
    unittest.main()
