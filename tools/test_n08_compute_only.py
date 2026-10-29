"""Unit checks for the independent N08 compute-only record evaluator."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

from evaluate_n08_compute_only import CONTROL_TOPICS, evaluate  # noqa: E402
from n08_compute_only_record import summarize_navigation_action_result  # noqa: E402


class N08ComputeOnlyEvaluatorTests(unittest.TestCase):
    def fixture(self):
        return {
            'result': 'PASS',
            'mode': 'compute_only',
            'launch_mode_record': {'mode': 'compute_only'},
            'compute_only_graph': {
                'bridge_subscribed_to_position_cmd': False,
                'bridge_subscribed_to_isolated_input': True,
            },
            'goal_id': 'fixture-goal',
            'epoch': 'fixture-epoch',
            'ready_position_command_samples': [
                {'goal_id': 'fixture-goal', 'epoch': 'fixture-epoch'}],
            'cancel_accepted': True,
            'action_cancel_confirmed': True,
            'bridge_hold_confirmed_after_cancel': True,
            'hold_after_cancel_sim_s': 2.0,
            'clock_regressions': 0,
            'landed_and_disarmed': True,
            'n05_current_area': {'accepted': True, 'online_offline_identical': True},
            'publisher_counts': {topic: 1 for topic in CONTROL_TOPICS},
            'debug_truth_used_for_control': False,
        }

    def test_complete_compute_only_cancel_hold_and_land_record_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'fixture.json'
            path.write_text(json.dumps(self.fixture()))
            self.assertTrue(evaluate(path)['passed'])

    def test_action_cancel_and_hold_are_required(self):
        data = self.fixture()
        data['action_cancel_confirmed'] = False
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'fixture.json'
            path.write_text(json.dumps(data))
            result = evaluate(path)
            self.assertFalse(result['passed'])
            self.assertFalse(result['checks']['action_cancel_confirmed'])

    def test_terminal_action_reason_is_preserved_for_failed_diagnostic(self):
        wrapped = SimpleNamespace(
            status=6,
            result=SimpleNamespace(success=False, outcome='rejected', reason='map_query_unknown'))
        terminal = summarize_navigation_action_result(wrapped)
        self.assertEqual(terminal, {
            'status': 6, 'success': False,
            'outcome': 'rejected', 'reason': 'map_query_unknown'})
        data = self.fixture()
        data['result'] = 'FAIL'
        data['failure'] = 'navigation_action_terminal_before_ready:rejected:map_query_unknown'
        data['action_terminal_result_before_ready'] = terminal
        data['trajectory_ready_seen'] = False
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'fixture.json'
            path.write_text(json.dumps(data))
            result = evaluate(path)
            self.assertFalse(result['passed'])
            self.assertEqual(result['source_failure'], data['failure'])
            self.assertEqual(result['action_terminal_result'], terminal)


if __name__ == '__main__':
    unittest.main()
