#!/usr/bin/env python3
"""Exercise production main teardown with mocked ROS entrypoints; no ROS nodes."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uav_px4_bridge import px4_bridge_node as bridge


class BridgeShutdownTest(unittest.TestCase):
    def shutdown(self, mode, phase=None, error=None, ros_ok=True):
        events = []
        node = SimpleNamespace(runtime_mode=mode,
            destroy_node=Mock(side_effect=lambda: events.append('destroy')))
        if mode == 'control':
            node.supervisor = SimpleNamespace(phase=phase,
                disable=Mock(side_effect=lambda state: events.append(('disable', state))))
        with patch.object(bridge.rclpy, 'init') as init, \
                patch.object(bridge, 'Px4BridgeNode', return_value=node), \
                patch.object(bridge.rclpy, 'spin', side_effect=error or KeyboardInterrupt), \
                patch.object(bridge.rclpy, 'ok', return_value=ros_ok), \
                patch.object(bridge.rclpy, 'shutdown', side_effect=lambda: events.append('shutdown')):
            bridge.main()
        init.assert_called_once_with(args=None)
        return node, events

    def test_ev_only_has_no_supervisor(self):
        node, events = self.shutdown('ev_only')
        self.assertFalse(hasattr(node, 'supervisor'))
        self.assertEqual(events, ['destroy', 'shutdown'])

    def test_compute_only_has_no_supervisor(self):
        node, events = self.shutdown('compute_only')
        self.assertFalse(hasattr(node, 'supervisor'))
        self.assertEqual(events, ['destroy', 'shutdown'])

    def test_active_control_disabled_before_destroy(self):
        node, events = self.shutdown('control', bridge.OffboardSupervisor.ACTIVE)
        node.supervisor.disable.assert_called_once_with({})
        self.assertEqual(events, [('disable', {}), 'destroy', 'shutdown'])

    def test_terminal_control_not_disabled_again(self):
        for phase in (bridge.OffboardSupervisor.DISABLED,
                      bridge.OffboardSupervisor.LANDED,
                      bridge.OffboardSupervisor.LOCKED):
            with self.subTest(phase=phase):
                node, events = self.shutdown('control', phase)
                node.supervisor.disable.assert_not_called()
                self.assertEqual(events, ['destroy', 'shutdown'])

    def test_external_shutdown_does_not_shutdown_context_twice(self):
        _, events = self.shutdown('ev_only', error=bridge.ExternalShutdownException(), ros_ok=False)
        self.assertEqual(events, ['destroy'])


if __name__ == '__main__':
    unittest.main()
