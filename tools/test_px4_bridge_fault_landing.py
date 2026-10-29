#!/usr/bin/env python3
"""Run with the ROS environment sourced; exercise the actual bridge timer."""
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/own/uav_px4_bridge'))
sys.path.insert(0, str(ROOT / 'tools'))

from uav_px4_bridge.px4_bridge_node import Px4BridgeNode
from test_px4_bridge_control import ready_snapshot, supervisor
from uav_px4_bridge.control_state import OffboardSupervisor
from uav_px4_bridge.process_watch import ProcessIdentity
from uav_interfaces.msg import TrajectoryCancel
from px4_msgs.msg import VehicleCommand, VehicleCommandAck


class FaultLandingTests(unittest.TestCase):
    def test_navigation_goal_binds_current_epoch_and_planner_process_identity(self):
        identity = ProcessIdentity(123, 456)
        node = SimpleNamespace(
            profile={'name': 'vio_closed_loop'}, epoch='epoch-a',
            active_navigation_goal_id='', active_navigation_epoch='',
            planner_process_identity=None, last_planner_process_check_ns=99,
            config={'planner_process_executable': 'ego_planner_node'})
        goal = SimpleNamespace(goal_id='goal-a', epoch='epoch-a')
        with mock.patch(
                'uav_px4_bridge.px4_bridge_node.find_process_identities',
                return_value=(identity,)):
            Px4BridgeNode._on_navigation_goal(node, goal)
        self.assertEqual(node.active_navigation_goal_id, 'goal-a')
        self.assertEqual(node.active_navigation_epoch, 'epoch-a')
        self.assertEqual(node.planner_process_identity, identity)
        self.assertEqual(node.last_planner_process_check_ns, 0)

        stale = SimpleNamespace(goal_id='goal-old', epoch='epoch-old')
        with mock.patch(
                'uav_px4_bridge.px4_bridge_node.find_process_identities') as lookup:
            Px4BridgeNode._on_navigation_goal(node, stale)
        lookup.assert_not_called()
        self.assertEqual(node.active_navigation_goal_id, 'goal-a')

    def test_matching_planner_abort_latches_fault_but_stale_fault_is_ignored(self):
        node = SimpleNamespace(
            supervisor=supervisor(), active_navigation_goal_id='goal-current',
            active_navigation_epoch='epoch-current', bridge_fault='',
            last_navigation_fault_identity=None)
        node.supervisor.phase = OffboardSupervisor.ACTIVE
        published = []
        node.planner_fault_pub = SimpleNamespace(publish=published.append)
        node._publish_navigation_fault = (
            lambda reason, source: Px4BridgeNode._publish_navigation_fault(
                node, reason, source))

        stale = SimpleNamespace(mode=TrajectoryCancel.MODE_ABORT,
                                goal_id='goal-old', epoch='epoch-current',
                                reason='depth_timeout')
        Px4BridgeNode._on_planner_fault(node, stale)
        self.assertEqual(node.bridge_fault, '')

        matching = SimpleNamespace(mode=TrajectoryCancel.MODE_ABORT,
                                    goal_id='goal-current', epoch='epoch-current',
                                    reason='full_curve_depth_odom_timeout')
        Px4BridgeNode._on_planner_fault(node, matching)
        self.assertEqual(node.bridge_fault,
                         'planner_fault:full_curve_depth_odom_timeout')
        commands = []
        snapshot = ready_snapshot(armed=True, landed=False)
        node.pending_command = ''
        node.last_reported_reason = ''
        node.last_status_publish_ns = 2_000_000_000
        node.config = {'status_period_wall_s': 1.0}
        node._now_ns = lambda: 2_000_000_000
        node._check_planner_process = lambda now: None
        node._snapshot = lambda now: snapshot
        node._publish_command = lambda command, now: commands.append(command)
        node._publish_control = lambda output, _snapshot, _now: None
        node.get_logger = lambda: SimpleNamespace(info=lambda message: None)
        Px4BridgeNode._on_control_tick(node)
        self.assertEqual(node.supervisor.phase, OffboardSupervisor.LANDING)
        self.assertEqual(commands, ['land'])
        snapshot.update(armed=False, landed=True)
        Px4BridgeNode._on_control_tick(node)
        self.assertEqual(node.supervisor.phase, OffboardSupervisor.LANDED)

    def test_native_readiness_landing_aborts_exact_navigation_goal_once(self):
        state = supervisor()
        state.phase = OffboardSupervisor.ACTIVE
        published = []
        commands = []
        snapshot = ready_snapshot(
            armed=True, landed=False, local_position_valid=False,
            nav_offboard=True)
        node = SimpleNamespace(
            supervisor=state,
            active_navigation_goal_id='goal-current',
            active_navigation_epoch='epoch-current',
            last_navigation_fault_identity=None,
            planner_fault_pub=SimpleNamespace(publish=published.append),
            bridge_fault='', alignment_fault='', pending_command='',
            last_reported_reason='', last_status_publish_ns=2_000_000_000,
            config={'status_period_wall_s': 1.0},
            _now_ns=lambda: 2_000_000_000,
            _check_planner_process=lambda now: None,
            _snapshot=lambda now: snapshot,
            _publish_command=lambda command, now: commands.append(command),
            _publish_control=lambda output, _snapshot, _now: None,
            get_logger=lambda: SimpleNamespace(info=lambda message: None),
        )
        node._publish_navigation_fault = (
            lambda reason, source: Px4BridgeNode._publish_navigation_fault(
                node, reason, source))

        Px4BridgeNode._on_control_tick(node)
        self.assertEqual(node.supervisor.phase, OffboardSupervisor.LANDING)
        self.assertEqual(commands, ['land'])
        self.assertEqual(len(published), 1)
        self.assertEqual(published[0].goal_id, 'goal-current')
        self.assertEqual(published[0].epoch, 'epoch-current')
        self.assertEqual(published[0].mode, TrajectoryCancel.MODE_ABORT)
        self.assertEqual(published[0].reason, 'bridge_px4_local_position_invalid')

        # Repeated landing supervision must not send another terminal event.
        Px4BridgeNode._on_control_tick(node)
        self.assertEqual(len(published), 1)
        snapshot.update(armed=False, landed=True)
        Px4BridgeNode._on_control_tick(node)
        self.assertEqual(node.supervisor.phase, OffboardSupervisor.LANDED)
        self.assertEqual(len(published), 1)

    def test_land_ack_must_match_latest_nav_land_command(self):
        node = SimpleNamespace(
            ack=None, ack_receipt_ns=None, last_command=VehicleCommand.VEHICLE_CMD_NAV_LAND,
            last_command_timestamp_us=1000, last_command_result=255,
            last_command_receipt_ns=9, uxrce_dds_time_sync_enabled=False,
            land_command_ack_result=None, _now_ns=lambda: 10,
        )
        stale = SimpleNamespace(
            command=VehicleCommand.VEHICLE_CMD_NAV_LAND,
            timestamp=999,
            result=VehicleCommandAck.VEHICLE_CMD_RESULT_ACCEPTED,
        )
        Px4BridgeNode._on_command_ack(node, stale)
        self.assertIsNone(node.land_command_ack_result)
        matching = SimpleNamespace(
            command=VehicleCommand.VEHICLE_CMD_NAV_LAND,
            timestamp=1001,
            result=VehicleCommandAck.VEHICLE_CMD_RESULT_ACCEPTED,
        )
        Px4BridgeNode._on_command_ack(node, matching)
        self.assertEqual(node.land_command_ack_result,
                         VehicleCommandAck.VEHICLE_CMD_RESULT_ACCEPTED)

    def test_synced_agent_timestamp_ack_uses_host_receipt_order(self):
        node = SimpleNamespace(
            ack=None, ack_receipt_ns=None,
            last_command=VehicleCommand.VEHICLE_CMD_NAV_LAND,
            last_command_timestamp_us=9_000_000_000_000,
            last_command_receipt_ns=10,
            last_command_result=255,
            uxrce_dds_time_sync_enabled=True,
            land_command_ack_result=None,
            _now_ns=lambda: 11,
        )
        ack = SimpleNamespace(
            command=VehicleCommand.VEHICLE_CMD_NAV_LAND,
            timestamp=42,
            result=VehicleCommandAck.VEHICLE_CMD_RESULT_ACCEPTED,
        )
        Px4BridgeNode._on_command_ack(node, ack)
        self.assertEqual(node.land_command_ack_result,
                         VehicleCommandAck.VEHICLE_CMD_RESULT_ACCEPTED)

    def test_process_exit_fault_is_checked_only_for_vio_active_goal(self):
        state = supervisor()
        state.phase = OffboardSupervisor.ACTIVE
        node = SimpleNamespace(
            profile={'name': 'vio_closed_loop'}, supervisor=state,
            active_navigation_goal_id='goal-a', active_navigation_epoch='epoch-a',
            planner_process_identity=None,
            last_planner_process_check_ns=0,
            config={'planner_process_check_period_wall_s': 0.1,
                    'planner_process_executable': 'ego_planner_node'},
            bridge_fault='')
        published = []
        node.planner_fault_pub = SimpleNamespace(publish=published.append)
        node.last_navigation_fault_identity = None
        node._publish_navigation_fault = (
            lambda reason, source: Px4BridgeNode._publish_navigation_fault(
                node, reason, source))
        node._latch_planner_process_fault = (
            lambda reason: Px4BridgeNode._latch_planner_process_fault(node, reason))
        with mock.patch(
                'uav_px4_bridge.px4_bridge_node.find_process_identities',
                return_value=()):
            Px4BridgeNode._check_planner_process(node, 1_000_000_000)
        self.assertEqual(node.bridge_fault,
                         'ego_planner_process_exited_during_active_goal')
        self.assertEqual(len(published), 1)
        self.assertEqual(published[0].goal_id, 'goal-a')
        self.assertEqual(published[0].epoch, 'epoch-a')
        self.assertEqual(published[0].mode, TrajectoryCancel.MODE_ABORT)
        self.assertEqual(node.last_navigation_fault_identity, ('goal-a', 'epoch-a'))

    def test_process_identity_disappearance_latches_fault(self):
        state = supervisor()
        state.phase = OffboardSupervisor.ACTIVE
        identity = object()
        node = SimpleNamespace(
            profile={'name': 'vio_closed_loop'}, supervisor=state,
            active_navigation_goal_id='goal-a', active_navigation_epoch='epoch-a',
            planner_process_identity=identity,
            last_planner_process_check_ns=0,
            config={'planner_process_check_period_wall_s': 0.1,
                    'planner_process_executable': 'ego_planner_node'},
            bridge_fault='')
        published = []
        node.planner_fault_pub = SimpleNamespace(publish=published.append)
        node.last_navigation_fault_identity = None
        node._publish_navigation_fault = (
            lambda reason, source: Px4BridgeNode._publish_navigation_fault(
                node, reason, source))
        node._latch_planner_process_fault = (
            lambda reason: Px4BridgeNode._latch_planner_process_fault(node, reason))
        with mock.patch(
                'uav_px4_bridge.px4_bridge_node.process_identity_is_running',
                return_value=False):
            Px4BridgeNode._check_planner_process(node, 1_000_000_000)
        self.assertEqual(node.bridge_fault,
                         'ego_planner_process_exited_during_active_goal')
        self.assertEqual(len(published), 1)
        self.assertEqual(published[0].epoch, 'epoch-a')
        self.assertEqual(published[0].reason,
                         'ego_planner_process_exited_during_active_goal')
        self.assertEqual(node.last_navigation_fault_identity, ('goal-a', 'epoch-a'))

    def test_degraded_localization_status_is_observational(self):
        status = SimpleNamespace(epoch='epoch-a', valid=False, state=2,
                                  reason='project_health_gate_removed')
        node = SimpleNamespace(
            epoch='epoch-a',
            _now_ns=lambda: 2_000_000_000,
            localization=None,
            localization_receipt_ns=None,
            trajectory_fault='',
            bridge_fault='',
            alignment=None,
            alignment_pair=None,
            position_command=None,
            cached_trajectory_body=None,
        )
        Px4BridgeNode._on_localization(node, status)
        self.assertIs(node.localization, status)
        self.assertEqual(node.trajectory_fault, '')
        self.assertEqual(node.bridge_fault, '')

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

    def test_alignment_disagreement_is_diagnostic_not_numeric_landing_gate(self):
        state = supervisor()
        state.phase = state.ACTIVE
        pair = {
            'odometry': object(),
            'attitude': SimpleNamespace(q=(1.0, 0.0, 0.0, 0.0)),
            'local_position': SimpleNamespace(
                x=0.0, y=0.0, z=0.0, heading=0.0),
        }
        node = SimpleNamespace(
            supervisor=state,
            alignment_fault='',
            alignment_pair=pair,
            alignment=SimpleNamespace(
                yaw_offset_ned=0.0, origin_offset_ned=(0.0, 0.0, 0.0)),
            alignment_drift_m=-1.0,
            alignment_yaw_error_rad=-1.0,
            sensor_leverarm_frd=(0.0, 0.0, 0.0),
            _update_alignment=lambda now: None,
            _alignment_pair_available=lambda now: True,
            _source_position_enu=lambda odom: (100.0, 0.0, 0.0),
            _source_yaw_enu=lambda odom: 0.0,
        )

        self.assertTrue(Px4BridgeNode._alignment_health(node, 1))
        self.assertGreater(node.alignment_drift_m, 0.15)
        self.assertGreater(node.alignment_yaw_error_rad, 0.15)
        self.assertEqual(node.alignment_fault, '')

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
                    active_navigation_goal_id='', active_navigation_epoch='',
                    last_navigation_fault_identity=None,
                    planner_fault_pub=SimpleNamespace(publish=lambda _msg: None),
                    last_status_publish_ns=2_000_000_000,
                    config={'status_period_wall_s': 1.0},
                    _now_ns=lambda: 2_000_000_000,
                    _check_planner_process=lambda now: None,
                    _snapshot=lambda now: snapshot,
                    _publish_command=lambda command, now: commands.append(command),
                    _publish_control=lambda output, snapshot, now: outputs.append(output),
                    get_logger=lambda: SimpleNamespace(info=lambda message: None),
                )
                node._publish_navigation_fault = (
                    lambda reason, source: Px4BridgeNode._publish_navigation_fault(
                        node, reason, source))
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
