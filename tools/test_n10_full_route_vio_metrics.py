import unittest

from tools.debug_truth.evaluate_n10_full_route_vio_metrics import (
    summarize_arrival_report,
)


class N10FullRouteVioMetricsTest(unittest.TestCase):
    def test_arrival_summary_uses_canonical_simulation_time_status(self):
        report = summarize_arrival_report({
            'time_domain': 'gazebo_sim_source_stamp',
            'position_tolerance_m': 0.3,
            'yaw_tolerance_deg': 15.0,
            'required_contiguous_dwell_sim_s': 3.0,
            'max_truth_sample_gap_sim_s': 0.02,
            'longest_joint_tolerance_window': {'duration_sim_s': 2.34,
                                               'duration_wall_s': 3.05},
            'independent_goal_dwell_status': 'FAIL',
            'independent_goal_dwell_passed': False,
            'native_action_success': True,
            'truth_is_offline_only': True,
        })
        self.assertEqual(report['independent_goal_dwell_status'], 'FAIL')
        self.assertFalse(report['independent_goal_dwell_passed'])
        self.assertEqual(report['longest_joint_tolerance_window']['duration_sim_s'], 2.34)
        self.assertEqual(report['time_domain'], 'gazebo_sim_source_stamp')


if __name__ == '__main__':
    unittest.main()
