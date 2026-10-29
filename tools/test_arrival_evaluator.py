import math
import json
import tempfile
import unittest
from pathlib import Path

from tools.debug_truth.evaluate_arrival import (
    MAX_TRUTH_SAMPLE_GAP_SIM_S,
    fixed_sensor_reference_alignment,
    load_arrival_contract,
    longest_joint_window,
    wrap_abs_angle,
)


def rows_at(times, inside=None, wall_scale=1.0):
    inside = inside or [True] * len(times)
    return [
        {
            'sim_s': t,
            'wall_s': t * wall_scale,
            'position_error_m': 0.1 if ok else 0.31,
            'yaw_error_rad': 0.05,
            'inside': ok,
        }
        for t, ok in zip(times, inside)
    ]


class ArrivalEvaluatorSimulationTimeTest(unittest.TestCase):
    def test_alignment_maps_coincident_vins_and_truth_imu_points(self):
        align, translation = fixed_sensor_reference_alignment(
            [1.0, 2.0, 3.0], [0.0, 0.0, 0.0, 1.0],
            [-4.0, 5.0, 1.5], [0.0, 0.0, 0.0, 1.0])
        mapped = align @ [1.0, 2.0, 3.0] + translation
        self.assertAlmostEqual(mapped[0], -4.0)
        self.assertAlmostEqual(mapped[1], 5.0)
        self.assertAlmostEqual(mapped[2], 1.5)

    def test_wall_duration_does_not_extend_sim_duration(self):
        times = [i * 0.02 for i in range(118)]
        window = longest_joint_window(rows_at(times, wall_scale=1.306))
        self.assertAlmostEqual(window['duration_sim_s'], 2.34, places=8)
        self.assertAlmostEqual(window['duration_wall_s'], 2.34 * 1.306, places=6)
        self.assertLess(window['duration_sim_s'], 3.0)

    def test_three_sim_seconds_pass_with_supported_samples(self):
        times = [i * 0.02 for i in range(151)]
        window = longest_joint_window(rows_at(times))
        self.assertIsNotNone(window)
        self.assertAlmostEqual(window['duration_sim_s'], 3.0, places=8)
        self.assertEqual(window['sample_count'], 151)

    def test_truth_gap_breaks_contiguous_dwell(self):
        times = [0.0, 0.02, 0.04, 0.081, 0.101, 0.121]
        window = longest_joint_window(rows_at(times))
        self.assertIsNotNone(window)
        self.assertAlmostEqual(window['duration_sim_s'], 0.04, places=8)
        self.assertGreater(0.081 - 0.04, MAX_TRUTH_SAMPLE_GAP_SIM_S)

    def test_out_of_tolerance_sample_breaks_joint_window(self):
        times = [i * 0.02 for i in range(151)]
        inside = [True] * len(times)
        inside[75] = False
        window = longest_joint_window(rows_at(times, inside=inside))
        self.assertAlmostEqual(window['duration_sim_s'], 1.48, places=8)

    def test_yaw_wrap_uses_shortest_angular_difference(self):
        error = wrap_abs_angle(math.radians(179.0), math.radians(-179.0))
        self.assertAlmostEqual(math.degrees(error), 2.0, places=8)

    def test_duplicate_or_backwards_stamp_breaks_continuity(self):
        window = longest_joint_window(rows_at([0.0, 0.02, 0.02, 0.04, 0.06]))
        self.assertAlmostEqual(window['duration_sim_s'], 0.04, places=8)

    def test_arrival_contract_comes_from_shared_acceptance_config(self):
        with tempfile.TemporaryDirectory() as temp:
            config_path = Path(temp) / 'acceptance.json'
            config_path.write_text(json.dumps({
                'metrics': {'arrival_position_yaw_dwell': {'thresholds': {
                    'position_error_max_m': 0.28,
                    'absolute_yaw_error_max_deg': 14.0,
                    'continuous_dwell_min_sim_s': 3.2,
                    'maximum_truth_source_gap_sim_s': 0.03,
                }}}
            }))
            goal_profile = {
                'position_tolerance_m': 0.2,
                'verification_position_tolerance_m': 0.25,
                'yaw_tolerance_rad': math.radians(10),
                'dwell_s': 4.0,
                'verification_dwell_sim_s': 4.0,
            }
            contract = load_arrival_contract(config_path, goal_profile)
            self.assertEqual(contract['position_tolerance_m'], 0.28)
            self.assertAlmostEqual(math.degrees(contract['yaw_tolerance_rad']), 14.0)
            self.assertEqual(contract['required_dwell_sim_s'], 3.2)
            self.assertEqual(contract['maximum_truth_gap_sim_s'], 0.03)
            self.assertTrue(contract['sha256'])


if __name__ == '__main__':
    unittest.main()
