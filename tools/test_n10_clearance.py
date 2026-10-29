import unittest

import numpy as np

from tools.debug_truth.evaluate_n10_clearance import assess_physics_step_coverage
from tools.debug_truth.evaluate_n10_tracking_clearance import (
    translation_only_clearance_lower_bound,
)


class N10PhysicsStepCoverageTests(unittest.TestCase):
    def test_exact_consecutive_solver_steps_are_identified(self):
        report = assess_physics_step_coverage(
            np.asarray([0, 4_000_000, 8_000_000, 12_000_000]), 0.004)
        self.assertTrue(report['all_received_pose_gaps_within_one_physics_step'])
        self.assertTrue(report['every_consecutive_physics_state_captured'])
        self.assertEqual(report['off_grid_pose_count'], 0)
        self.assertEqual(report['maximum_physics_step_index_gap'], 1)

    def test_gap_of_two_physics_steps_is_not_continuous_coverage(self):
        report = assess_physics_step_coverage(
            np.asarray([0, 4_000_000, 12_000_000]), 0.004)
        self.assertFalse(report['all_received_pose_gaps_within_one_physics_step'])
        self.assertFalse(report['every_consecutive_physics_state_captured'])
        self.assertEqual(report['maximum_physics_step_index_gap'], 2)

    def test_substep_periodic_samples_do_not_claim_solver_state_coverage(self):
        report = assess_physics_step_coverage(
            np.asarray([0, 3_000_000, 6_000_000, 9_000_000]), 0.004)
        self.assertFalse(report['every_consecutive_physics_state_captured'])
        self.assertEqual(report['off_grid_pose_count'], 3)

    def test_missing_physics_step_definition_is_insufficient(self):
        report = assess_physics_step_coverage(np.asarray([0, 4_000_000]), None)
        self.assertFalse(report['every_consecutive_physics_state_captured'])
        self.assertIsNone(report['longest_gap_in_physics_steps'])


class N10TranslationClearanceBudgetTests(unittest.TestCase):
    def test_positive_pointwise_translation_bound(self):
        self.assertAlmostEqual(
            translation_only_clearance_lower_bound(0.42, 0.17), 0.25)

    def test_negative_bound_means_insufficient_margin_not_collision(self):
        self.assertAlmostEqual(
            translation_only_clearance_lower_bound(0.10, 0.35), -0.25)

    def test_rejects_non_finite_or_negative_position_error(self):
        for clearance, error in ((float('nan'), 0.1), (0.1, float('inf')), (0.1, -0.1)):
            with self.subTest(clearance=clearance, error=error):
                with self.assertRaises(ValueError):
                    translation_only_clearance_lower_bound(clearance, error)


if __name__ == '__main__':
    unittest.main()
