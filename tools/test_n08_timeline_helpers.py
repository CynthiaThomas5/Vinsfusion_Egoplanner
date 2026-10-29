"""Tests for the low-overhead N08 timing observer helpers."""
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

from n08_timeline_helpers import (bridge_timing_fields, clock_sample_due,
                                  health_metric_summary,
                                  stream_sample_due)  # noqa: E402


class N08TimelineHelperTests(unittest.TestCase):
    def test_clock_sampling_is_rate_limited(self):
        due, regression = clock_sample_due(1_000_000_000, 1_010_000_000,
                                           200_000_000, 150_000_000,
                                           100_000_000)
        self.assertFalse(due)
        self.assertFalse(regression)

    def test_clock_sampling_keeps_regressions_immediately(self):
        due, regression = clock_sample_due(1_010_000_000, 900_000_000,
                                           160_000_000, 150_000_000,
                                           100_000_000)
        self.assertTrue(due)
        self.assertTrue(regression)

    def test_source_sampling_is_decimated_between_changes(self):
        self.assertFalse(stream_sample_due(150_000_000, 100_000_000,
                                           100_000_000))
        self.assertTrue(stream_sample_due(150_000_000, 100_000_000,
                                          100_000_000,
                                          transition_changed=True))
        self.assertTrue(stream_sample_due(150_000_000, 100_000_000,
                                          100_000_000,
                                          source_regression=True))

    def test_bridge_timing_fields_include_clock_and_source_pair_gaps(self):
        detail = bridge_timing_fields(
            '{"px4_ros_clock_gap_sim_s":0.02,"alignment_pair_gap_sim_s":0.4,'
            '"alignment_pair_validated_age_wall_s":1.5,'
            '"odometry_time_error":"clock_mapping_not_converged",'
            '"timesync_age_sim_s":0.3,"secret":"ignore"}')
        self.assertEqual(detail['px4_ros_clock_gap_sim_s'], 0.02)
        self.assertEqual(detail['alignment_pair_gap_sim_s'], 0.4)
        self.assertEqual(detail['alignment_pair_validated_age_wall_s'], 1.5)
        self.assertEqual(detail['odometry_time_error'],
                         'clock_mapping_not_converged')
        self.assertEqual(detail['timesync_age_sim_s'], 0.3)
        self.assertNotIn('secret', detail)

    def test_malformed_bridge_detail_is_reported(self):
        self.assertIn('parse_error', bridge_timing_fields('{bad json'))

    def test_health_metric_summary_preserves_compact_cost_groups(self):
        metrics = {
            'stamp_ns': 123,
            'initialized': True,
            'solve_current': True,
            'solver_usable': True,
            'state_finite': True,
            'termination_type': 1,
            'solve_seconds': 0.02,
            'residual_components': 100,
            'iterations': 8,
            'input_features': 80,
            'stereo_features': 70,
            'continued_tracks': 40,
            'long_tracks': 30,
            'final_cost': 50,
            'cost_components': {
                'evaluation_ok': True,
                'evaluation_seconds': 0.001,
                'grouped_cost_sum': 50,
                'grouped_residual_components': 100,
                'grouped_cost_error': 0,
                'visual': {'cost': 20, 'residual_components': 60},
                'imu': {'cost': 5, 'residual_components': 20},
                'marginalization': {'cost': 25, 'residual_components': 20},
                'prior_details': {
                    'available': True,
                    'evaluation_ok': True,
                    'spectrum_ok': True,
                    'next_marginalization_branch': 'second_newest',
                    'information_rank': 4,
                    'retained_dimension': 4,
                    'current_squared_norm': 8,
                    'window_tracks': [[1, 0, 4, 4]],
                },
            },
        }
        record = health_metric_summary(metrics, 1.0)
        self.assertEqual(record['normalized_cost'], 1.0)
        self.assertFalse(record['cost_limit_exceeded'])
        self.assertEqual(record['cost_components']['groups']['marginalization'],
                         {'cost': 25, 'residual_components': 20})
        self.assertEqual(record['cost_components']['prior']['information_rank'], 4)
        self.assertNotIn('window_tracks', record['cost_components']['prior'])

    def test_health_cost_limit_crossings_are_explicit_in_samples(self):
        metrics = {'stamp_ns': 123, 'final_cost': 50.1,
                   'residual_components': 100}
        record = health_metric_summary(metrics, 1.0)
        self.assertTrue(record['cost_limit_exceeded'])
        self.assertGreater(record['normalized_cost'], 1.0)
        self.assertIsNone(record['cost_components'])


if __name__ == '__main__':
    unittest.main()
