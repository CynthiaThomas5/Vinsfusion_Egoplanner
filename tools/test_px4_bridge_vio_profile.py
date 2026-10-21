#!/usr/bin/env python3
"""Check VINS-only PX4 bridge profile isolation and shared ENU conversions."""

from pathlib import Path
import json
import sys
import unittest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/own/uav_px4_bridge'))

from uav_px4_bridge.control_state import OffboardSupervisor, readiness_failure  # noqa: E402
from uav_px4_bridge.trajectory import (  # noqa: E402
    position_command_to_ned,
    validate_debug_truth_profile,
    validate_px4_runtime_profile,
)
from uav_px4_bridge.vision_odometry import odometry_to_px4_values  # noqa: E402


PROFILE = json.loads((ROOT / 'config/profiles/vio_closed_loop.json').read_text())
BRIDGE = json.loads((ROOT / 'config/components/px4_bridge/vio_closed_loop.json').read_text())
SHARED = json.loads((ROOT / 'config/components/px4_bridge/debug_truth.json').read_text())
FRAME = json.loads((ROOT / 'config/components/px4_bridge/frames_vio_closed_loop.json').read_text())
EPOCH = '0123456789abcdef0123456789abcdef'


def ready_snapshot():
    return {
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


def odometry():
    return SimpleNamespace(
        header=SimpleNamespace(frame_id='odom_' + EPOCH,
                               stamp=SimpleNamespace(sec=12, nanosec=345_000_000)),
        child_frame_id='d435i_imu_' + EPOCH,
        pose=SimpleNamespace(pose=SimpleNamespace(
            position=SimpleNamespace(x=1.0, y=2.0, z=3.0),
            orientation=SimpleNamespace(x=0.0, y=0.0, z=0.0, w=1.0))),
        twist=SimpleNamespace(twist=SimpleNamespace(
            linear=SimpleNamespace(x=4.0, y=5.0, z=6.0),
            angular=SimpleNamespace(x=0.1, y=0.2, z=0.3))),
    )


def command():
    return SimpleNamespace(
        TRAJECTORY_STATUS_READY=1,
        trajectory_flag=1,
        header=SimpleNamespace(frame_id='odom_' + EPOCH),
        position=SimpleNamespace(x=1.0, y=2.0, z=3.0),
        velocity=SimpleNamespace(x=4.0, y=5.0, z=6.0),
        acceleration=SimpleNamespace(x=7.0, y=8.0, z=9.0),
        yaw=0.0,
        yaw_dot=0.25,
        trajectory_id=4,
        goal_id='goal-1',
        epoch=EPOCH,
    )


class VioProfileTests(unittest.TestCase):
    def test_profile_and_frame_contract_are_vins_only(self):
        validate_px4_runtime_profile(PROFILE, FRAME)
        self.assertFalse(PROFILE['ground_truth_online_allowed'])
        self.assertFalse(PROFILE['px4_debug_position_allowed'])
        self.assertEqual(PROFILE['mapping_localization'], 'vins')
        self.assertEqual(PROFILE['planner_localization'], 'vins')
        self.assertFalse(FRAME['ground_truth_online_allowed'])
        self.assertFalse(FRAME['gps_position_aiding_allowed'])

    def test_bridge_inputs_use_canonical_vins_topics_without_truth_topics(self):
        self.assertEqual(BRIDGE['profile'], 'vio_closed_loop')
        self.assertEqual(BRIDGE['localization_status_topic'], '/localization/status')
        self.assertEqual(BRIDGE['optimized_odometry_topic'],
                         '/localization/optimized_imu_odom')
        self.assertEqual(BRIDGE['clock_topic'], '/clock')
        self.assertEqual(BRIDGE['shared_control_config'], 'debug_truth.json')
        self.assertFalse(any('debug_truth' in key for key in BRIDGE))
        for shared_key in ('control_rate_hz', 'prestream_wall_s',
                           'vehicle_odometry_topic', 'system_id',
                           'clock_mapping_min_samples'):
            self.assertNotIn(shared_key, BRIDGE)

    def test_px4_telemetry_future_allowance_is_scoped_to_vio_profile(self):
        self.assertEqual(BRIDGE['px4_source_timestamp_max_future_sim_s'], 0.065)
        self.assertEqual(SHARED['px4_source_timestamp_max_future_sim_s'], 0.02)

    def test_vision_odometry_and_ego_trajectory_use_shared_enu_ned_conversion(self):
        values = odometry_to_px4_values(
            odometry(), PROFILE, FRAME, 50_000,
            BRIDGE['position_variance_m2'],
            BRIDGE['orientation_variance_rad2'],
            BRIDGE['velocity_variance_m2_s2'], SHARED['source_quality'],
            expected_epoch=EPOCH, timestamp_sample_us=49_800)
        self.assertEqual(values.position_ned, (2.0, 1.0, -3.0))
        self.assertEqual(values.velocity_body_frd, (4.0, -5.0, -6.0))
        self.assertEqual(values.epoch, EPOCH)
        result = position_command_to_ned(command(), PROFILE, FRAME,
                                         expected_epoch=EPOCH)
        self.assertEqual(result.position, (2.0, 1.0, -3.0))
        self.assertEqual(result.goal_id, 'goal-1')

    def test_offboard_state_machine_accepts_only_fully_ready_ev_without_gnss(self):
        snapshot = ready_snapshot()
        self.assertEqual(readiness_failure(snapshot, PROFILE, FRAME), '')
        machine = OffboardSupervisor(
            PROFILE, FRAME, prestream_wall_s=1.0, takeoff_altitude_m=1.0,
            position_tolerance_m=0.15, velocity_tolerance_m_s=0.2,
            takeoff_dwell_wall_s=1.0, command_retry_wall_s=1.0,
            command_retry_limit=3)
        self.assertEqual(machine.enable(snapshot, 1.0),
                         (True, 'prestreaming_offboard_setpoints'))
        for field in ('gnss_position_aiding', 'gnss_velocity_aiding',
                      'gnss_height_aiding', 'gnss_yaw_aiding'):
            self.assertEqual(readiness_failure(
                ready_snapshot() | {field: True}, PROFILE, FRAME),
                'gnss_aiding_active')

    def test_truth_or_mismatched_contract_cannot_enter_vio_profile(self):
        for bad_profile in (
                PROFILE | {'ground_truth_online_allowed': True},
                PROFILE | {'px4_debug_position_allowed': True},
                PROFILE | {'px4_position_source': 'debug_position'}):
            with self.assertRaises(ValueError):
                validate_px4_runtime_profile(bad_profile, FRAME)
        with self.assertRaises(ValueError):
            validate_px4_runtime_profile(
                PROFILE, FRAME | {'ground_truth_online_allowed': True})
        with self.assertRaises(ValueError):
            validate_debug_truth_profile(PROFILE, FRAME)
        with self.assertRaises(ValueError):
            validate_px4_runtime_profile(PROFILE | {'name': 'other'}, FRAME)

    def test_invalid_gnss_and_fusion_flags_fail_closed(self):
        snapshot = ready_snapshot()
        snapshot['ev_position_fused'] = False
        self.assertEqual(readiness_failure(snapshot, PROFILE, FRAME),
                         'ev_position_not_fused')
        snapshot = ready_snapshot()
        snapshot['ev_yaw_fused'] = False
        self.assertEqual(readiness_failure(snapshot, PROFILE, FRAME),
                         'ev_yaw_not_fused')
        snapshot = ready_snapshot()
        snapshot['gnss_height_aiding'] = True
        machine = OffboardSupervisor(
            PROFILE, FRAME, 1.0, 1.0, 0.15, 0.2, 1.0, 1.0, 3)
        self.assertEqual(machine.enable(snapshot, 1.0),
                         (False, 'gnss_aiding_active'))


if __name__ == '__main__':
    unittest.main()
