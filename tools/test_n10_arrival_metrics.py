import unittest

from n10_arrival_metrics import longest_contiguous_window, wrapped_angle_error_rad


class N10ArrivalMetricsTest(unittest.TestCase):
    def test_joint_window_reports_both_clock_domains(self):
        rows = [
            {'sim_s': 1.0, 'wall_s': 2.0, 'position_error_m': 0.1,
             'yaw_error_deg': 2.0, 'within_tolerance': True},
            {'sim_s': 2.0, 'wall_s': 2.05, 'position_error_m': 0.2,
             'yaw_error_deg': 4.0, 'within_tolerance': True},
            {'sim_s': 3.0, 'wall_s': 2.10, 'position_error_m': 0.31,
             'yaw_error_deg': 1.0, 'within_tolerance': False},
        ]
        result = longest_contiguous_window(rows, max_sim_gap_s=1.1)
        self.assertEqual(result['sample_count'], 2)
        self.assertEqual(result['sim_duration_s'], 1.0)
        self.assertAlmostEqual(result['wall_duration_s'], 0.05)
        self.assertEqual(result['max_position_error_m'], 0.2)

    def test_gap_breaks_the_window(self):
        rows = [
            {'sim_s': 1.0, 'wall_s': 1.0, 'position_error_m': 0.1,
             'yaw_error_deg': 2.0, 'within_tolerance': True},
            {'sim_s': 1.1, 'wall_s': 1.1, 'position_error_m': 0.1,
             'yaw_error_deg': 2.0, 'within_tolerance': True},
            {'sim_s': 2.0, 'wall_s': 2.0, 'position_error_m': 0.1,
             'yaw_error_deg': 2.0, 'within_tolerance': True},
            {'sim_s': 2.1, 'wall_s': 2.1, 'position_error_m': 0.1,
             'yaw_error_deg': 2.0, 'within_tolerance': True},
        ]
        result = longest_contiguous_window(rows, max_sim_gap_s=0.2)
        self.assertEqual(result['sample_count'], 2)
        self.assertAlmostEqual(result['sim_duration_s'], 0.1)

    def test_timestamp_regression_is_rejected(self):
        rows = [
            {'sim_s': 2.0, 'wall_s': 2.0, 'within_tolerance': True},
            {'sim_s': 1.0, 'wall_s': 3.0, 'within_tolerance': True},
        ]
        with self.assertRaisesRegex(ValueError, 'increase'):
            longest_contiguous_window(rows)

    def test_yaw_wrap_uses_shortest_angle(self):
        self.assertAlmostEqual(
            wrapped_angle_error_rad(3.13, -3.13), 0.023185307179586445)


if __name__ == '__main__':
    unittest.main()
