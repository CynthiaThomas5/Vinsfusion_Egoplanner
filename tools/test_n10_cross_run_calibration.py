import json
import tempfile
import unittest
from pathlib import Path

from tools.debug_truth.evaluate_n10_cross_run_calibration import _age_summary, evaluate_run


class N10IncompleteCrossRunArchiveTests(unittest.TestCase):
    def test_map_age_summary_skips_null_or_invalid_timestamps_as_missing(self):
        report = _age_summary([
            {'clock_ns_at_receipt': None, 'source_stamp_ns': 10,
             'last_occupancy_stamp_ns': 10},
            {'clock_ns_at_receipt': 100, 'source_stamp_ns': 90,
             'last_occupancy_stamp_ns': 80},
            {'clock_ns_at_receipt': True, 'source_stamp_ns': 90,
             'last_occupancy_stamp_ns': 80},
        ], 0, 200)

        self.assertEqual(report['map_status_samples'], 1)
        self.assertEqual(report['source_age_sim_s']['median'], 1e-8)
        self.assertEqual(report['occupancy_update_age_sim_s']['median'], 2e-8)

    def test_aborted_native_action_is_reported_without_synthesizing_hold(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory) / 'n10-aborted'
            run.mkdir()
            (run / 'flight.json').write_text(json.dumps({
                'action_goal_sent': True,
                'action_success': False,
                'goal_completed_source_ns': None,
                'post_goal_hold': None,
                'failure': 'navigation_action_not_successful:bridge_ev_position_not_fused',
                'action_result': {
                    'outcome': 'aborted',
                    'success': False,
                    'reason': 'bridge_ev_position_not_fused',
                },
            }))
            (run / 'runtime-contract.json').write_text(json.dumps({'sha256': 'runtime-id'}))
            (run / 'bridge-alignment-timeline.jsonl').write_text('')
            (run / 'arrival-evaluation-simtime-v2.json').write_text(json.dumps({
                'independent_goal_dwell_status': 'FAIL',
                'independent_goal_dwell_passed': False,
                'longest_joint_tolerance_window': None,
            }))

            report = evaluate_run(run)

        self.assertEqual(report['status'], 'FAIL')
        self.assertEqual(report['native_action']['reason'], 'bridge_ev_position_not_fused')
        self.assertEqual(report['arrival']['independent_goal_dwell_status'], 'FAIL')
        self.assertEqual(report['segments'], {})
        self.assertIn('timestamp is synthesized', report['limitations'][0])


if __name__ == '__main__':
    unittest.main()
