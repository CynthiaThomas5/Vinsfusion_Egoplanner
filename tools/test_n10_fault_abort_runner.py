#!/usr/bin/env python3
"""Unit checks for the opt-in native fault-abort closeout path."""
import unittest

from run_vio_ego_flight import expected_fault_abort_matches


class ExpectedFaultAbortTests(unittest.TestCase):
    def test_matching_native_abort_is_recognized(self):
        self.assertTrue(expected_fault_abort_matches(
            {'outcome': 'aborted', 'reason': 'depth_odom_timeout'},
            'depth_odom_timeout'))

    def test_non_abort_or_wrong_reason_is_not_recognized(self):
        self.assertFalse(expected_fault_abort_matches(
            {'outcome': 'succeeded', 'reason': 'depth_odom_timeout'},
            'depth_odom_timeout'))
        self.assertFalse(expected_fault_abort_matches(
            {'outcome': 'aborted', 'reason': 'planner_process_exit'},
            'depth_odom_timeout'))

    def test_no_expected_reason_preserves_normal_action_handling(self):
        self.assertFalse(expected_fault_abort_matches(
            {'outcome': 'aborted', 'reason': 'depth_odom_timeout'}, None))


if __name__ == '__main__':
    unittest.main()
