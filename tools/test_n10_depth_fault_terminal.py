#!/usr/bin/env python3
"""Unit checks for the offline N10 depth-fault-to-terminal evaluator."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from debug_truth.evaluate_n10_depth_fault_terminal import (
    evaluate_records, native_planner_log_path)


class N10DepthFaultTerminalTest(unittest.TestCase):
    def setUp(self):
        self.fault = {
            'kind': 'depth',
            'scope': 'Explicit sensor-fault relay with source-stamp scheduled drop window',
            'finalized': True,
            'status': 'finalized',
            'fault_drop_observed': True,
            'goal_trigger': {
                'goal_id': 'goal-1', 'epoch': 'epoch-1',
                'goal_source_stamp_ns': 100_000_000_000,
                'drop_window_start_ns': 102_000_000_000,
                'drop_window_end_ns': 105_000_000_000,
            },
            'topics': {'depth': {'forwarded_before': 800, 'dropped': 90,
                                 'forwarded_after': 20}},
        }
        self.flight = {
            'goal_id': 'goal-1', 'localization_epoch': 'epoch-1',
            'action_goal_sent': True, 'action_success': False,
            'action_result': {'outcome': 'aborted',
                              'reason': 'bridge_planner_fault:depth_odom_timeout'},
        }
        self.bridge_rows = [
            {'phase': 'ACTIVE', 'stamp_ns': 101_900_000_000,
             'reason': 'takeoff_complete_waiting_for_trajectory', 'armed': True},
            {'phase': 'LANDING', 'stamp_ns': 102_400_000_000,
             'reason': 'planner_fault:depth_odom_timeout', 'armed': True},
            {'phase': 'LANDED', 'stamp_ns': 110_000_000_000,
             'reason': 'planner_fault:depth_odom_timeout', 'landed': True,
             'armed': False},
        ]
        self.capture = {
            'source_stamp_regressions': {
                'stereo_left_image': 0, 'stereo_right_image': 0, 'camera_imu': 0},
            'errors': [],
        }
        self.receipts = [
            {'stream': 'stereo_left_image', 'sim_stamp_ns_at_receipt': 103_000_000_000},
            {'stream': 'stereo_right_image', 'sim_stamp_ns_at_receipt': 103_100_000_000},
            {'stream': 'camera_imu', 'sim_stamp_ns_at_receipt': 103_200_000_000},
        ]
        self.safe = {
            'safe_to_stop_project_container': True,
            'native_terminal_evidence_complete': True,
            'emergency_disarm_used': False,
        }
        self.readback = {
            'latest': {
                'bridge': {'phase': 'LANDED', 'landed': True, 'armed': False,
                           'control_enabled': False},
                'px4_status': {'arming_state': 1},
                'land_detected': {'landed': True},
            },
            'zero_control_after_terminal': True,
            'no_old_epoch_goal_or_trajectory': True,
            'stable_terminal_window_wall_s': 15.0,
            'terminal_state_violation_count': 0,
        }

    def evaluate(self):
        return evaluate_records(
            self.fault, self.flight,
            'Depth Lost! aborting active navigation task depth_odom_timeout',
            self.bridge_rows, self.capture, self.receipts,
            self.safe, self.readback)

    def test_depth_fault_reaches_native_landed_terminal_with_other_streams_live(self):
        report = self.evaluate()
        self.assertEqual(report['status'], 'PASS')
        self.assertTrue(all(report['checks'].values()))
        self.assertEqual(report['terminal']['trigger_to_landing_sim_s'], 0.4)

    def test_operator_disable_does_not_count_as_fault_landing(self):
        self.bridge_rows[1]['reason'] = 'operator_disable'
        report = self.evaluate()
        self.assertEqual(report['status'], 'INSUFFICIENT')
        self.assertFalse(report['checks']['bridge_entered_fault_landing'])

    def test_goal_epoch_mismatch_does_not_count_as_fault_coverage(self):
        self.fault['goal_trigger']['epoch'] = 'old-epoch'
        report = self.evaluate()
        self.assertEqual(report['status'], 'INSUFFICIENT')
        self.assertFalse(report['checks']['fault_bound_to_active_goal_epoch'])

    def test_native_planner_diagnostic_uses_ros_launch_log(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = root / 'run'
            run.mkdir()
            (run / 'planner.log').write_text('read-only ROS planner observer')
            (run / 'vio.log').write_text('Depth Lost! depth_odom_timeout')
            self.assertEqual(native_planner_log_path(run), run / 'vio.log')

    def test_native_planner_log_can_be_read_from_stack_archive(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = root / 'run'
            run.mkdir()
            stack_log = root / 'run-stack' / 'vio.log'
            stack_log.parent.mkdir()
            stack_log.write_text('Depth Lost! depth_odom_timeout')
            self.assertEqual(native_planner_log_path(run), stack_log)


if __name__ == '__main__':
    unittest.main()
