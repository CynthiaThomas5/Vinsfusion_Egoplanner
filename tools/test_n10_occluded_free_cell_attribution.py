#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent / 'debug_truth'))
from analyze_n10_occluded_free_cells import face_margins_for_cell


class OccludedFreeCellAttributionTest(unittest.TestCase):
    def test_cell_volume_face_margins_use_all_eight_corners(self):
        center_odom, corners_local, margins = face_margins_for_cell(
            index=(0, 0, 0),
            origin=(-0.05, -0.05, -0.05),
            resolution=0.1,
            rotation=np.eye(3),
            translation=np.zeros(3),
            center_world=np.zeros(3),
            size_xyz=(1.0, 1.0, 1.0),
            yaw_rad=0.0,
        )
        self.assertTrue(np.allclose(center_odom, (0.0, 0.0, 0.0)))
        self.assertEqual(len(corners_local), 8)
        self.assertAlmostEqual(min(margins.values()), 0.45)

    def test_cell_touching_box_face_has_zero_volume_margin(self):
        _, _, margins = face_margins_for_cell(
            index=(0, 0, 0),
            origin=(-0.05, -0.05, -0.05),
            resolution=0.1,
            rotation=np.eye(3),
            translation=np.zeros(3),
            center_world=np.zeros(3),
            size_xyz=(0.1, 1.0, 1.0),
            yaw_rad=0.0,
        )
        self.assertAlmostEqual(min(margins.values()), 0.0)


if __name__ == '__main__':
    unittest.main()
