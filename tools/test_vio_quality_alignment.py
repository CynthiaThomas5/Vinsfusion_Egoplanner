#!/usr/bin/env python3
import unittest

import numpy as np

from evaluate_vins_motion import rotation
from evaluate_vio_quality_alignment import evaluate


def qz(yaw):
    return [0.0, 0.0, float(np.sin(yaw / 2.0)), float(np.cos(yaw / 2.0))]


def fixture(nonmonotonic=False):
    truth = []
    for step in range(1101):
        t = step * 0.02
        truth.append({
            'stamp_ns': int(round(t * 1e9)), 'stamp': t,
            'frame': 'world', 'child_frame': 'd435i_link',
            'position': [0.0, 0.0, 0.02 * t], 'quaternion': qz(0.0),
        })
    align = rotation(qz(0.7))
    translation = np.array([2.0, -3.0, 1.0])
    optimized, telemetry, health = [], [], []
    for step in range(1, 22):
        stamp_ns = step * 1_000_000_000
        truth_position = np.array([0.0, 0.0, 0.02 * step])
        drift = np.array([0.0, 0.0, 0.0]) if step < 14 else np.array([0.0, 0.0, 0.15])
        estimated_position = align.T @ (truth_position - translation) + drift
        estimated_stamp = (stamp_ns - 1_000_000_000
                           if nonmonotonic and step == 3 else stamp_ns)
        optimized.append({
            'stamp_ns': estimated_stamp,
            'frame': 'vins_test_world', 'child_frame': 'vins_test_imu',
            'position': estimated_position.tolist(), 'quaternion': qz(-0.7),
        })
        cost = 0.1 if step < 14 else 1.2
        telemetry.append({'stamp_ns': stamp_ns, 'final_cost': cost ** 2 * 872,
                          'residual_components': 1744, 'input_features': 120,
                          'continued_tracks': 36, 'long_tracks': 36,
                          'solve_seconds': 0.01})
        health.append({'stamp_ns': stamp_ns, 'source_stamp_ns': stamp_ns,
                       'normalized_cost': cost,
                       'reason': 'normalized_cost_exceeded' if step >= 14 else 'fresh_inputs_and_usable_solver'})
    return {'truth': truth, 'optimized': optimized, 'telemetry': telemetry}, {
        'localization_quality_history': health}


class VioQualityAlignmentTest(unittest.TestCase):
    def test_vertical_path_uses_one_pose_alignment_and_keeps_error_observable(self):
        capture, report = fixture()
        result = evaluate(capture, report)
        self.assertEqual(result['paired_samples'], 21)
        self.assertLess(result['orientation_error_deg']['max'], 1e-5)
        self.assertAlmostEqual(result['position_error_m']['median'], 0.0, places=8)
        self.assertAlmostEqual(result['position_error_m']['max'], 0.15, places=8)
        self.assertEqual(result['samples_above_health_limit'], 8)
        self.assertAlmostEqual(
            result['first_health_gate_crossing']['aligned_position_error_m'], 0.15, places=8)

    def test_nonincreasing_source_stamps_are_rejected(self):
        capture, report = fixture(nonmonotonic=True)
        with self.assertRaises(ValueError):
            evaluate(capture, report)

    def test_quality_gate_report_shows_recovery_and_followup_spikes(self):
        capture, report = fixture()
        for step, cost, residuals, observations in (
                (13, 0.4, 1744, 396), (14, 1.2, 1812, 416),
                (15, 0.5, 1758, 400), (16, 1.4, 1824, 420)):
            sample = capture['telemetry'][step - 1]
            sample['residual_components'] = residuals
            sample['visual_observations'] = observations
            sample['final_cost'] = cost ** 2 * residuals / 2.0

        dynamics = evaluate(capture, report)['quality_gate_dynamics']
        self.assertEqual(dynamics['crossing']['stamp_ns'], 14_000_000_000)
        self.assertEqual(dynamics['change_from_previous']['residual_components'], 68)
        self.assertEqual(dynamics['change_from_previous']['visual_observations'], 20)
        self.assertAlmostEqual(
            dynamics['first_recovery_at_or_below_threshold']['delay_s'], 1.0)
        self.assertEqual(dynamics['followup_samples_above_threshold'], 1)
        self.assertEqual(dynamics['peak_within_followup']['stamp_ns'], 16_000_000_000)


if __name__ == '__main__':
    unittest.main()
