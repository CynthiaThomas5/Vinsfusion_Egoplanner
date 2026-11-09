#!/usr/bin/env python3
"""Pure tests for depth-time pose interpolation and camera extrinsics."""
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/own/uav_mapping'))
from uav_mapping.mapping_input import (camera_info_matches, depth_camera_pose,
                                       depth_layout_valid, pose_at)


class MappingInputTests(unittest.TestCase):
    def test_pose_interpolation_uses_bracketing_samples(self):
        history = [
            (1_000_000_000, (0.0, 2.0, 1.0), (0.0, 0.0, 0.0, 1.0)),
            (1_100_000_000, (1.0, 4.0, 3.0), (0.0, 0.0, 0.7071067812, 0.7071067812)),
        ]
        result = pose_at(history, 1_050_000_000, 100_000_000)
        self.assertIsNotNone(result)
        position, quaternion = result
        self.assertEqual(position, (0.5, 3.0, 2.0))
        self.assertAlmostEqual(quaternion[2], math.sin(math.pi / 8), places=6)
        self.assertAlmostEqual(quaternion[3], math.cos(math.pi / 8), places=6)

    def test_pose_interpolation_refuses_extrapolation_and_wide_brackets(self):
        history = [(100, (0, 0, 0), (0, 0, 0, 1)),
                   (300, (1, 0, 0), (0, 0, 0, 1))]
        self.assertIsNone(pose_at(history, 99, 300))
        self.assertIsNone(pose_at(history, 200, 199))
        self.assertEqual(pose_at(history, 300, 1), ((1, 0, 0), (0, 0, 0, 1)))

    def test_camera_pose_composes_sdf_optical_rotation_and_offset(self):
        rotation_body_optical = (0, 0, 1, -1, 0, 0, 0, -1, 0)
        position, orientation = depth_camera_pose(
            (1, 2, 3), (0, 0, 0, 1), (0, 0, 0), (0, 0.025, 0),
            rotation_body_optical)
        self.assertEqual(position, (1.0, 2.025, 3.0))
        self.assertAlmostEqual(orientation[0], 0.5, places=6)
        self.assertAlmostEqual(orientation[1], -0.5, places=6)
        self.assertAlmostEqual(orientation[2], 0.5, places=6)
        self.assertAlmostEqual(orientation[3], -0.5, places=6)

    def test_depth_layout_accepts_zero_valid_pixels_without_a_project_health_threshold(self):
        class Header:
            frame_id = 'depth_optical_frame'

        class Message:
            header = Header()
            encoding = '32FC1'
            width = 4
            height = 2
            step = 16
            data = bytes(32)

        self.assertTrue(depth_layout_valid(
            Message(), 4, 2, 'depth_optical_frame'))

    def test_live_camera_info_must_match_real_rig_frame_size_and_intrinsics(self):
        camera = {
            'frame': 'depth_optical',
            'image_frame': 'depth_optical',
            'camera_info_frame': 'depth_optical',
            'width': 640,
            'height': 480,
            'K': [386.7, 0.0, 322.1, 0.0, 386.7, 241.5, 0.0, 0.0, 1.0],
        }

        class Header:
            frame_id = 'depth_optical'

        class Message:
            header = Header()
            width = 640
            height = 480
            k = list(camera['K'])

        self.assertTrue(camera_info_matches(Message(), camera))
        Message.k[2] += 0.01
        self.assertFalse(camera_info_matches(Message(), camera))
        Message.k = list(camera['K'])
        Message.header.frame_id = 'other_optical'
        self.assertFalse(camera_info_matches(Message(), camera))
        Message.header.frame_id = 'depth_optical'
        Message.width = 320
        self.assertFalse(camera_info_matches(Message(), camera))
        self.assertFalse(camera_info_matches(None, camera))


if __name__ == '__main__':
    unittest.main()
