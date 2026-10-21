#!/usr/bin/env python3
"""Run with the ROS environment sourced; exercise the actual bridge timer."""
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/own/uav_px4_bridge'))
sys.path.insert(0, str(ROOT / 'tools'))

from uav_px4_bridge.px4_bridge_node import Px4BridgeNode
from test_px4_bridge_control import ready_snapshot, supervisor


class FaultLandingTests(unittest.TestCase):
    def test_ground_alignment_refresh_stops_at_enable_and_preserves_faults(self):
        for phase, armed, landed, fault, refresh in (
                ('DISABLED', False, True, '', True),
                ('DISABLED', True, True, '', False),
                ('DISABLED', False, False, '', False),
                ('PRESTREAM', False, True, '', False),
                ('ACTIVE', True, False, '', False),
                ('LANDED', False, True, '', False),
                ('DISABLED', False, True, 'latched_fault', False)):
            with self.subTest(phase=phase, armed=armed, landed=landed, fault=fault):
                state = supervisor()
                state.phase = phase
                previous = object()
                captured = []
                node = SimpleNamespace(
                    supervisor=state, alignment_fault=fault, alignment=previous,
                    vehicle_status=SimpleNamespace(arming_state=2 if armed else 1),
                    land_detected=SimpleNamespace(landed=landed),
                    alignment_pair=None,
                    _update_alignment=lambda now: captured.append(node.alignment),
                )
                self.assertFalse(Px4BridgeNode._alignment_health(node, 1))
                self.assertEqual(captured, [None if refresh else previous])
                self.assertEqual(node.alignment_fault, fault)

    def test_enable_refreshes_alignment_only_after_disarmed_readiness_acceptance(self):
        for armed, fault, refresh_valid in ((False, '', True), (True, '', True),
                                             (False, 'latched_fault', True),
                                             (False, '', False)):
            with self.subTest(armed=armed, fault=fault, refresh_valid=refresh_valid):
                state = supervisor()
                previous = object()
                refreshed = object()
                captures = []
                snapshot = ready_snapshot(armed=armed)
                node = SimpleNamespace(
                    supervisor=state, bridge_fault='', alignment_fault=fault,
                    alignment=previous, _now_ns=lambda: 2_000_000_000,
                    _snapshot=lambda now: snapshot,
                    _alignment_health=lambda now: refresh_valid,
                )
                def capture(now):
                    self.assertEqual(state.phase, state.PRESTREAM)
                    self.assertIsNone(node.alignment)
                    captures.append(now)
                    node.alignment = refreshed if refresh_valid else None
                node._update_alignment = capture
                response = SimpleNamespace()
                Px4BridgeNode._on_enable(node, SimpleNamespace(enable=True), response)
                if armed or fault:
                    self.assertFalse(response.accepted)
                    self.assertEqual(captures, [])
                    self.assertIs(node.alignment, previous)
                else:
                    self.assertEqual(captures, [2_000_000_000])
                    self.assertEqual(response.accepted, refresh_valid)
                    self.assertEqual(state.phase, state.PRESTREAM if refresh_valid else state.DISABLED)

    def test_latched_fault_allows_landing_completion_without_resuming_control(self):
        for fault in ('bridge_fault', 'alignment_fault'):
            with self.subTest(fault=fault):
                state = supervisor()
                state.phase = state.ACTIVE
                snapshot = ready_snapshot(armed=True, landed=False)
                commands, outputs = [], []
                node = SimpleNamespace(
                    supervisor=state, bridge_fault='', alignment_fault='',
                    pending_command='', last_reported_reason='',
                    last_status_publish_ns=2_000_000_000,
                    config={'status_period_wall_s': 1.0},
                    _now_ns=lambda: 2_000_000_000,
                    _snapshot=lambda now: snapshot,
                    _publish_command=lambda command, now: commands.append(command),
                    _publish_control=lambda output, snapshot, now: outputs.append(output),
                    get_logger=lambda: SimpleNamespace(info=lambda message: None),
                )
                setattr(node, fault, 'latched_test_fault')
                Px4BridgeNode._on_control_tick(node)
                self.assertEqual(state.phase, state.LANDING)
                Px4BridgeNode._on_control_tick(node)
                self.assertEqual(state.phase, state.LANDING)
                snapshot.update(armed=False, landed=True)
                Px4BridgeNode._on_control_tick(node)
                self.assertEqual(state.phase, state.LANDED)
                Px4BridgeNode._on_control_tick(node)
                self.assertEqual(state.phase, state.LANDED)
                self.assertEqual(commands, ['land'])
                self.assertTrue(all(not output.publish_offboard for output in outputs))
                self.assertEqual(getattr(node, fault), 'latched_test_fault')


if __name__ == '__main__':
    unittest.main()
