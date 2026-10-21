#!/usr/bin/env python3
"""Pure tests for depth-time pose interpolation and camera extrinsics."""
import math
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/own/uav_mapping'))
from uav_mapping.mapping_input import (depth_camera_pose, pose_at,
                                       valid_depth_sample_count)


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

    def test_depth_sample_validation_counts_only_finite_positive_values(self):
        class Header:
            frame_id = 'depth_optical_frame'

        class Message:
            header = Header()
            encoding = '32FC1'
            width = 4
            height = 2
            step = 20  # Two bytes of row padding.
            is_bigendian = False
            data = (struct.pack('<4f', 1.0, 0.0, float('nan'), 2.5) + b'\0' * 4
                    + struct.pack('<4f', float('inf'), -1.0, 0.5, 3.0) + b'\0' * 4)

        self.assertEqual(valid_depth_sample_count(
            Message(), 4, 2, 'depth_optical_frame', 1), 4)
        self.assertEqual(valid_depth_sample_count(
            Message(), 4, 2, 'wrong_frame', 1), 0)


if __name__ == '__main__':
    unittest.main()
