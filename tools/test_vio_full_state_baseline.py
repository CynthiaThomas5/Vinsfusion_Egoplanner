"""Deterministic checks for the read-only raw VINS full-state evaluator."""
import math
import sys
from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent / 'debug_truth'))
from evaluate_vio_full_state import evaluate, _pose_at


def _quat_from_euler(roll, pitch, yaw):
    cr, sr = math.cos(roll / 2), math.sin(roll / 2)
    cp, sp = math.cos(pitch / 2), math.sin(pitch / 2)
    cy, sy = math.cos(yaw / 2), math.sin(yaw / 2)
    return [sr * cp * cy - cr * sp * sy,
            cr * sp * cy + sr * cp * sy,
            cr * cp * sy - sr * sp * cy,
            cr * cp * cy + sr * sp * sy]


def _rotation(q):
    x, y, z, w = q
    return np.array([[1 - 2*(y*y + z*z), 2*(x*y - z*w), 2*(x*z + y*w)],
                     [2*(x*y + z*w), 1 - 2*(x*x + z*z), 2*(y*z - x*w)],
                     [2*(x*z - y*w), 2*(y*z + x*w), 1 - 2*(x*x + y*y)]])


def _quat_from_rotation(matrix):
    m = matrix
    trace = float(np.trace(m))
    if trace > 0:
        s = math.sqrt(trace + 1.0) * 2
        return [(m[2, 1]-m[1, 2])/s, (m[0, 2]-m[2, 0])/s,
                (m[1, 0]-m[0, 1])/s, 0.25*s]
    index = int(np.argmax(np.diag(m)))
    if index == 0:
        s = math.sqrt(1 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        return [0.25*s, (m[0, 1]+m[1, 0])/s, (m[0, 2]+m[2, 0])/s, (m[2, 1]-m[1, 2])/s]
    if index == 1:
        s = math.sqrt(1 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        return [(m[0, 1]+m[1, 0])/s, 0.25*s, (m[1, 2]+m[2, 1])/s, (m[0, 2]-m[2, 0])/s]
    s = math.sqrt(1 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
    return [(m[0, 2]+m[2, 0])/s, (m[1, 2]+m[2, 1])/s, 0.25*s, (m[1, 0]-m[0, 1])/s]


def fixture():
    epoch = 'a' * 32
    sensor_lever = np.array([0.12, 0.0, 0.08])
    align_r = _rotation(_quat_from_euler(0.0, 0.0, 0.35))
    align_t = np.array([2.0, -1.0, 0.7])
    truth = []
    for index in range(6251):
        t = index * 0.004
        moving = max(0.0, t - 3.0)
        roll = 0.012 * math.sin(0.4 * moving)
        pitch = 0.02 * math.sin(0.25 * moving)
        yaw = 0.05 * moving
        q = _quat_from_euler(roll, pitch, yaw)
        r = _rotation(q)
        p_base = np.array([0.08 * moving, 0.0, 0.6 + 0.01 * math.sin(0.2 * moving)])
        p_imu = p_base + r @ sensor_lever
        truth.append({'stamp_ns': int(round(t * 1e9)), 'xyz': p_imu.tolist(), 'q_xyzw': q})
    raw = []
    for index in range(16, 249):
        t = index * 0.1
        moving = max(0.0, t - 3.0)
        q_truth = _quat_from_euler(0.012 * math.sin(0.4 * moving),
                                   0.02 * math.sin(0.25 * moving), 0.05 * moving)
        r_truth = _rotation(q_truth)
        p_base = np.array([0.08 * moving, 0.0, 0.6 + 0.01 * math.sin(0.2 * moving)])
        p_imu = p_base + r_truth @ sensor_lever
        tdot = 0.08 if t > 3.0 else 0.0
        if t > 3.0:
            tdot += 0.002 * math.cos(0.2 * moving)
        omega_z = 0.05 if t > 3.0 else 0.0
        omega_x = 0.0048 * math.cos(0.4 * moving) if t > 3.0 else 0.0
        omega_y = 0.005 * math.cos(0.25 * moving) if t > 3.0 else 0.0
        omega = np.array([omega_x, omega_y, omega_z])
        v_base = np.array([tdot, 0.0, 0.002 * math.cos(0.2 * moving) if t > 3.0 else 0.0])
        v_imu = v_base + np.cross(omega, r_truth @ sensor_lever)
        p_raw = align_r.T @ (p_imu - align_t)
        r_raw = align_r.T @ r_truth
        v_raw = align_r.T @ v_imu
        source_ns = int(round(t * 1e9))
        raw.append({'kind': 'raw', 'source_ns': source_ns,
                    'receive_sim_ns': source_ns + 5_000_000,
                    'receive_monotonic_ns': 10_000_000_000 + index * 100_000_000,
                    'frame': f'vins_{epoch}_world', 'child_frame': f'vins_{epoch}_imu',
                    'xyz': p_raw.tolist(), 'q_xyzw': _quat_from_rotation(r_raw),
                    'velocity_xyz': v_raw.tolist()})
    trace = [{'sim_s': 1.0, 'target': [0.0, 0.0, 0.0, 0.0], 'epoch': epoch}]
    stages = [{'label': 'return', 'cycle': cycle} for cycle in (1, 2, 3)]
    fixture_result = {'epoch': epoch, 'profile': 'drift', 'outcome': 'unarmed_support_drift_completed'}
    protocol = {
        'schema_version': 1, 'profile': 'drift',
        'alignment': {'anchor_after_first_stationary_trace_sim_s': 1.0,
                      'method': 'single stationary pose'},
        'truth': {'maximum_truth_interpolation_gap_sim_s': 0.04,
                  'velocity_half_window_sim_s': 0.1},
        'support': {'maximum_raw_pose_interpolation_gap_sim_s': 0.2,
                    'rpe_windows_sim_s': [1, 5, 10],
                    'expected_stage_count': 23}}
    runtime = {'sha256': 'synthetic-runtime-contract'}
    return raw, truth, trace, stages, fixture_result, protocol, runtime


class VioFullStateBaselineTests(unittest.TestCase):
    def test_all_state_metrics_use_one_initial_alignment_and_independent_velocity(self):
        args = fixture()
        report, rows, rpe = evaluate(*args)
        self.assertLess(report['position_ate_m']['rmse'], 2e-5)
        self.assertLess(report['attitude_geodesic_error_deg']['rmse'], 1e-5)
        self.assertLess(report['velocity_error_m_s']['rmse'], 5e-3)
        self.assertEqual(report['alignment']['scale'], 1)
        self.assertFalse(report['alignment']['per_return_realignment'])
        self.assertEqual(len(report['rpe']), 3)
        self.assertEqual(report['coverage']['velocity_truth_pairs'], len(rows))
        self.assertGreater(len(rpe), 0)
        self.assertLess(report['lever_arm_velocity_audit']['maximum_reconstruction_error_m_s'], 2e-4)

        args = fixture()
        for row in args[0]:
            row['velocity_xyz'][0] += 0.2
        changed, _, _ = evaluate(*args)
        self.assertGreater(changed['velocity_error_m_s']['rmse'], 0.19)

    def test_missing_velocity_or_receipt_fields_are_not_inferred_from_vins_pose(self):
        args = fixture()
        del args[0][20]['velocity_xyz']
        with self.assertRaisesRegex(ValueError, 'velocity and receive-clock'):
            evaluate(*args)
        args = fixture()
        del args[0][20]['receive_monotonic_ns']
        with self.assertRaisesRegex(ValueError, 'velocity and receive-clock'):
            evaluate(*args)

    def test_epoch_frame_and_time_rewinds_are_rejected(self):
        args = fixture()
        args[0][20]['child_frame'] = 'vins_' + 'b' * 32 + '_imu'
        with self.assertRaisesRegex(ValueError, 'frame/epoch'):
            evaluate(*args)
        args = fixture()
        args[0][20]['source_ns'] = args[0][19]['source_ns']
        with self.assertRaisesRegex(ValueError, 'strictly increasing'):
            evaluate(*args)

    def test_nanosecond_source_stamp_rounding_does_not_fail_a_200ms_support_gap(self):
        stamps = np.array([0, 200_000_001], dtype=np.int64)
        positions = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
        quaternions = np.array([[0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0, 1.0]])
        position, _, gap = _pose_at(stamps, positions, quaternions, 100_000_000, 200_000_000)
        self.assertEqual(gap, 200_000_001)
        self.assertAlmostEqual(position[0], 100_000_000 / 200_000_001)


if __name__ == '__main__':
    unittest.main()
