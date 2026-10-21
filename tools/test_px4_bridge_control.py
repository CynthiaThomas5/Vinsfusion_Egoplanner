#!/usr/bin/env python3
"""Safety-gate and transition tests for the P3 Offboard supervisor."""
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/own/uav_px4_bridge'))

from uav_px4_bridge.control_state import (  # noqa: E402
    OffboardSupervisor,
    receipt_limits_fresh,
    readiness_failure,
)


PROFILE = json.loads((ROOT / 'config/profiles/debug_truth.json').read_text())
FRAME_CONTRACT = json.loads((ROOT / 'config/components/px4_bridge/frames.json').read_text())
VIO_PROFILE = json.loads((ROOT / 'config/profiles/vio_closed_loop.json').read_text())
VIO_FRAME_CONTRACT = json.loads((ROOT / 'config/components/px4_bridge/frames_vio_closed_loop.json').read_text())


def ready_snapshot(**overrides):
    values = {
        'localization_tracking': True,
        'odometry_fresh': True,
        'clock_fresh': True,
        'px4_time_domain_valid': True,
        'px4_telemetry_fresh': True,
        'local_position_valid': True,
        'ev_position_fused': True,
        'ev_yaw_fused': True,
        'alignment_valid': True,
        'preflight_passed': True,
        'gnss_position_aiding': False,
        'gnss_velocity_aiding': False,
        'gnss_height_aiding': False,
        'gnss_yaw_aiding': False,
        'landed': True,
        'armed': False,
        'nav_offboard': False,
        'position_ned': (0.0, 0.0, 0.0),
        'velocity_ned': (0.0, 0.0, 0.0),
        'heading_ned': 0.0,
        'trajectory_ready': False,
        'trajectory_fault': False,
    }
    values.update(overrides)
    return values


def supervisor(retry_limit=3):
    return OffboardSupervisor(
        PROFILE, FRAME_CONTRACT, prestream_wall_s=1.0,
        takeoff_altitude_m=1.0, position_tolerance_m=0.15,
        velocity_tolerance_m_s=0.2, takeoff_dwell_wall_s=1.0,
        command_retry_wall_s=1.0, command_retry_limit=retry_limit)


class Px4BridgeControlTests(unittest.TestCase):
    def test_per_topic_receipt_limits_expire_fast_and_slow_telemetry_separately(self):
        now_ns = 2_000_000_000
        self.assertTrue(receipt_limits_fresh(now_ns, (
            (1_500_000_000, 0.5),
            (1_000_000_000, 1.5),
        )))
        self.assertFalse(receipt_limits_fresh(now_ns, (
            (1_499_000_000, 0.5),
            (1_000_000_000, 1.5),
        )))
        self.assertFalse(receipt_limits_fresh(now_ns, ((None, 1.5),)))

    def test_enable_gate_requires_ev_fusion_and_rejects_each_gnss_aiding(self):
        self.assertEqual(readiness_failure(ready_snapshot(ev_position_fused=False),
                                           PROFILE, FRAME_CONTRACT),
                         'ev_position_not_fused')
        for key in ('gnss_position_aiding', 'gnss_velocity_aiding',
                    'gnss_height_aiding', 'gnss_yaw_aiding'):
            self.assertEqual(readiness_failure(ready_snapshot(**{key: True}),
                                               PROFILE, FRAME_CONTRACT),
                             'gnss_aiding_active')

    def test_missing_health_input_fails_and_vio_profile_is_supported(self):
        missing = ready_snapshot()
        del missing['px4_time_domain_valid']
        self.assertEqual(readiness_failure(missing, PROFILE, FRAME_CONTRACT),
                         'missing_px4_time_domain_valid')
        self.assertEqual(readiness_failure(ready_snapshot(), VIO_PROFILE,
                                           VIO_FRAME_CONTRACT), '')

    def test_service_is_required_and_enable_requires_landed_disarmed_vehicle(self):
        machine = supervisor()
        self.assertEqual(machine.step(ready_snapshot(), 0.0).phase, machine.DISABLED)
        self.assertEqual(machine.enable(ready_snapshot(landed=False), 1.0),
                         (False, 'vehicle_not_landed'))
        self.assertEqual(machine.enable(ready_snapshot(armed=True), 1.0),
                         (False, 'vehicle_already_armed'))
        accepted, reason = machine.enable(ready_snapshot(), 2.0)
        self.assertTrue(accepted)
        self.assertEqual(reason, 'prestreaming_offboard_setpoints')
        self.assertEqual(machine.phase, machine.PRESTREAM)

    def test_prestream_precedes_mode_then_arm_requests(self):
        machine = supervisor()
        self.assertTrue(machine.enable(ready_snapshot(), 10.0)[0])
        before = machine.step(ready_snapshot(), 10.99)
        self.assertTrue(before.publish_offboard)
        self.assertEqual(before.setpoint_kind, 'hold')
        self.assertEqual(before.command, '')
        mode = machine.step(ready_snapshot(), 11.0)
        self.assertEqual(mode.command, 'offboard')
        arm = machine.step(ready_snapshot(nav_offboard=True), 11.1)
        self.assertEqual(arm.command, 'arm')
        self.assertEqual(arm.phase, machine.REQUEST_ARM)
        takeoff = machine.step(ready_snapshot(nav_offboard=True, armed=True,
                                              landed=False), 11.2)
        self.assertEqual(takeoff.phase, machine.TAKEOFF)
        self.assertEqual(takeoff.setpoint_kind, 'takeoff')

    def test_offboard_prestream_can_resolve_mode_specific_preflight_but_never_arms_early(self):
        machine = supervisor()
        self.assertTrue(machine.enable(ready_snapshot(preflight_passed=False), 10.0)[0])
        machine.step(ready_snapshot(preflight_passed=False), 10.99)
        mode = machine.step(ready_snapshot(preflight_passed=False), 11.0)
        self.assertEqual(mode.command, 'offboard')
        waiting = machine.step(ready_snapshot(nav_offboard=True,
                                              preflight_passed=False), 11.1)
        self.assertEqual(waiting.phase, machine.REQUEST_OFFBOARD)
        self.assertEqual(waiting.command, '')
        self.assertTrue(waiting.publish_offboard)
        arm = machine.step(ready_snapshot(nav_offboard=True,
                                          preflight_passed=True), 11.2)
        self.assertEqual(arm.command, 'arm')

    def test_offboard_preflight_timeout_locks_disarmed_without_arm_request(self):
        machine = supervisor()
        self.assertTrue(machine.enable(ready_snapshot(preflight_passed=False), 0.0)[0])
        machine.step(ready_snapshot(preflight_passed=False), 1.0)
        machine.step(ready_snapshot(preflight_passed=False), 1.01)
        machine.step(ready_snapshot(nav_offboard=True,
                                    preflight_passed=False), 1.1)
        expired = machine.step(ready_snapshot(nav_offboard=True,
                                               preflight_passed=False), 4.0)
        self.assertEqual(expired.phase, machine.LOCKED)
        self.assertEqual(expired.command, '')
        self.assertFalse(expired.publish_offboard)
        self.assertEqual(expired.reason, 'offboard_preflight_timeout')

    def test_prestream_health_loss_returns_to_closed_state_without_arming(self):
        machine = supervisor()
        self.assertTrue(machine.enable(ready_snapshot(), 1.0)[0])
        result = machine.step(ready_snapshot(odometry_fresh=False), 1.2)
        self.assertEqual(result.phase, machine.DISABLED)
        self.assertFalse(result.publish_offboard)
        self.assertEqual(result.reason, 'external_odometry_stale')

    def test_offboard_command_retry_limit_locks_without_arm(self):
        machine = supervisor(retry_limit=2)
        self.assertTrue(machine.enable(ready_snapshot(), 1.0)[0])
        self.assertEqual(machine.step(ready_snapshot(), 2.0).command, 'offboard')
        self.assertEqual(machine.step(ready_snapshot(), 2.9).command, '')
        self.assertEqual(machine.step(ready_snapshot(), 3.0).command, 'offboard')
        expired = machine.step(ready_snapshot(), 4.0)
        self.assertEqual(expired.phase, machine.LOCKED)
        self.assertEqual(expired.reason, 'offboard_command_timeout')

    def test_takeoff_needs_position_velocity_dwell_then_lands_on_health_loss(self):
        machine = supervisor()
        self.assertTrue(machine.enable(ready_snapshot(), 0.0)[0])
        machine.step(ready_snapshot(), 1.0)
        machine.step(ready_snapshot(nav_offboard=True), 1.1)
        machine.step(ready_snapshot(nav_offboard=True, armed=True, landed=False), 1.2)
        target = ready_snapshot(nav_offboard=True, armed=True, landed=False,
                                position_ned=(0.0, 0.0, -1.0),
                                velocity_ned=(0.0, 0.0, 0.0))
        self.assertEqual(machine.step(target, 1.3).phase, machine.TAKEOFF)
        self.assertEqual(machine.step(target, 2.29).phase, machine.TAKEOFF)
        active = machine.step(target, 2.31)
        self.assertEqual(active.phase, machine.ACTIVE)
        self.assertEqual(active.setpoint_kind, 'hold')
        fault = machine.step(ready_snapshot(nav_offboard=True, armed=True,
                                             landed=False,
                                             px4_time_domain_valid=False), 2.4)
        self.assertEqual((fault.phase, fault.command), (machine.LANDING, 'land'))
        landed = machine.step(ready_snapshot(nav_offboard=False, armed=False,
                                              landed=True), 3.0)
        self.assertEqual(landed.phase, machine.LANDED)

    def test_active_trajectory_loss_lands_instead_of_reusing_old_setpoint(self):
        machine = supervisor()
        self.assertTrue(machine.enable(ready_snapshot(), 0.0)[0])
        machine.step(ready_snapshot(), 1.0)
        machine.step(ready_snapshot(nav_offboard=True), 1.1)
        machine.step(ready_snapshot(nav_offboard=True, armed=True, landed=False), 1.2)
        target = ready_snapshot(nav_offboard=True, armed=True, landed=False,
                                position_ned=(0.0, 0.0, -1.0),
                                trajectory_ready=True)
        machine.step(target, 1.3)
        machine.step(target, 2.31)
        lost = machine.step(ready_snapshot(nav_offboard=True, armed=True,
                                            landed=False, trajectory_ready=False), 2.4)
        self.assertEqual((lost.phase, lost.command), (machine.LANDING, 'land'))
        self.assertFalse(lost.publish_offboard)


if __name__ == '__main__':
    unittest.main()
