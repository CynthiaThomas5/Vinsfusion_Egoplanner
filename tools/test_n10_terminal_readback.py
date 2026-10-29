import unittest

from tools.n10_terminal_readback import summarize_terminal_readback


def _readback():
    return {
        'latest': {
            'bridge': {
                'phase': 'LANDED', 'landed': True, 'armed': False,
                'control_enabled': False,
            },
            'px4_status': {'arming_state': 1, 'nav_state': 14},
            'land_detected': {'landed': True},
        },
        'zero_control_after_terminal': True,
        'no_old_epoch_goal_or_trajectory': True,
        'stable_terminal_window_wall_s': 3.0,
        'terminal_state_violation_count': 0,
    }


class TerminalReadbackTests(unittest.TestCase):
    def test_complete_native_terminal_requires_independent_px4_and_planner_state(self):
        result = summarize_terminal_readback(_readback())
        self.assertTrue(result['native_terminal_evidence_complete'])
        self.assertEqual(result['missing_evidence'], [])

    def test_emergency_disarm_is_not_a_native_fault_terminal(self):
        result = summarize_terminal_readback(_readback(), {
            'classification': 'authorized emergency-disarm closeout',
            'command_count_requested': 1,
        })
        self.assertFalse(result['native_terminal_evidence_complete'])
        self.assertTrue(result['emergency_closeout_used'])

    def test_missing_post_terminal_evidence_is_insufficient_not_assumed_zero(self):
        readback = _readback()
        del readback['no_old_epoch_goal_or_trajectory']
        result = summarize_terminal_readback(readback)
        self.assertFalse(result['native_terminal_evidence_complete'])
        self.assertEqual(result['missing_evidence'], [
            'no_old_epoch_goal_or_trajectory'])

    def test_observed_control_after_terminal_is_explicit_failure(self):
        readback = _readback()
        readback['zero_control_after_terminal'] = False
        result = summarize_terminal_readback(readback)
        self.assertEqual(result['post_terminal_failures'], [
            'zero_control_after_terminal'])


if __name__ == '__main__':
    unittest.main()
