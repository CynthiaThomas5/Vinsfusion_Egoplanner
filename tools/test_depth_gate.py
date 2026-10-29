#!/usr/bin/env python3
"""Unit checks for depth layout validation and session lockout."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/own/uav_mapping'))
from uav_mapping.depth_gate import DepthFreshnessGate


POLICY = {
    'expected_frame': 'depth_optical_frame', 'expected_encoding': '32FC1',
    'width': 2, 'height': 2,
    'startup_timeout_wall_s': 1.0, 'status_period_wall_s': 0.05,
}


def image(stamp, **changes):
    msg = SimpleNamespace(
        header=SimpleNamespace(frame_id='depth_optical_frame', stamp=SimpleNamespace(sec=0, nanosec=stamp)),
        encoding='32FC1', width=2, height=2, step=8, data=bytes(32))
    for key, value in changes.items():
        setattr(msg, key, value)
    return msg


class DepthGateTests(unittest.TestCase):
    def test_wait_for_first_frame_then_remain_ready_without_age_gate(self):
        gate = DepthFreshnessGate(POLICY, 0.0)
        self.assertEqual(gate.tick(1.0), 'STALE')
        self.assertTrue(gate.observe(image(1), 1.1))
        self.assertEqual(gate.tick(100.0), 'READY')
        self.assertEqual(gate.reason, 'structurally_valid_depth')

    def test_invalid_layout_fails_closed_then_valid_frame_recovers(self):
        gate = DepthFreshnessGate(POLICY, 0.0)
        self.assertFalse(gate.observe(image(1, step=4), 0.1))
        self.assertEqual(gate.reason, 'depth_layout_invalid')
        self.assertTrue(gate.observe(image(2), 0.2))
        self.assertEqual(gate.state, 'READY')

    def test_source_stamp_regression_locks_until_monitor_restart(self):
        gate = DepthFreshnessGate(POLICY, 0.0)
        self.assertTrue(gate.observe(image(2), 0.1))
        self.assertFalse(gate.observe(image(1), 0.2))
        self.assertEqual(gate.tick(0.3), 'LOCKED')
        self.assertFalse(gate.observe(image(3), 0.4))


if __name__ == '__main__':
    unittest.main()
