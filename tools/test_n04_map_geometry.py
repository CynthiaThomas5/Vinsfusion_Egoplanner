#!/usr/bin/env python3
"""Focused checks for N04's plan_env ray and raw class reference helpers."""
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from evaluate_n04_map_geometry import (_camera_truth_pose, _project_returns, _ray_cells,
                                       _reference_class_metrics)


class N04MapGeometryTests(unittest.TestCase):
    def test_ray_cells_excludes_return_cell_and_matches_axis_steps(self):
        cells = _ray_cells([0.05, 0.05, 0.05], [0.35, 0.05, 0.05],
                           np.zeros(3), 0.1, (8, 8, 8))
        self.assertEqual(cells, [(0, 0, 0), (1, 0, 0), (2, 0, 0)])

    def test_ray_cells_matches_plan_env_tie_priority(self):
        cells = _ray_cells([0.05, 0.05, 0.05], [0.25, 0.25, 0.05],
                           np.zeros(3), 0.1, (8, 8, 8))
        self.assertEqual(cells, [(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 2, 0)])

    def test_return_projection_reports_filter_and_clipped_depths(self):
        image = np.array([[1.0, 4.0], [6.0, 0.0]], dtype=np.float32)
        frame = {'margin_px': 0}
        pose = {'position': [0.0, 0.0, 0.0], 'quaternion': [0.0, 0.0, 0.0, 1.0]}
        k = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
        points, _, counts = _project_returns(image, frame, pose, k, 2, 2,
                                              1.5, 5.0, 4.5)
        self.assertEqual(len(points), 2)
        self.assertEqual(counts['valid_depth_pixels'], 3)
        self.assertEqual(counts['below_minimum_pixels'], 1)
        self.assertEqual(counts['over_filter_max_pixels'], 1)
        self.assertEqual(counts['projected_pixels'], 2)

    def test_expected_classes_are_reported_against_raw_occupancy(self):
        occupancy = np.array([[[0, 100, -1]]], dtype=np.int8)
        free = np.array([[[True, False, False]]])
        surface = np.array([[[False, True, False]]])
        ambiguous = np.array([[[False, False, True]]])
        metrics = _reference_class_metrics(occupancy, free, surface, ambiguous)
        self.assertEqual(metrics['expected_visible_free']['actual_raw_free'], 1)
        self.assertEqual(metrics['expected_surface_hit_without_conflicting_free']['actual_raw_occupied'], 1)
        self.assertEqual(metrics['ray_vote_ambiguous']['actual_raw_unknown'], 1)
        self.assertEqual(metrics['observed_return_any_hit']['voxel_count'], 2)
        self.assertEqual(metrics['observed_return_any_hit']['actual_raw_unknown'], 1)

    def test_truth_pose_uses_motion_seconds_against_nanosecond_depth_stamp(self):
        truth = [
            {'stamp': 1.0, 'position': [0.0, 0.0, 0.0], 'quaternion': [0, 0, 0, 1]},
            {'stamp': 1.02, 'position': [1.0, 0.0, 0.0], 'quaternion': [0, 0, 0, 1]},
        ]
        rig = {'imu': {'translation': [0.0, 0.0, 0.0]},
               'cameras': {'depth': {'translation': [0.0, 0.0, 0.0],
                                     'R_body_optical': [1, 0, 0, 0, 1, 0, 0, 0, 1]}}}
        pose = _camera_truth_pose(truth, 1_010_000_000, rig)
        self.assertIsNotNone(pose)
        np.testing.assert_allclose(pose[0], [0.5, 0.0, 0.0])


if __name__ == '__main__':
    unittest.main()
