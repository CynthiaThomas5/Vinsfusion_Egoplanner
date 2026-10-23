"""Synthetic checks for fixed-initial-pose drift measurement, not SITL evidence."""
import copy
import math
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent/'debug_truth'))
from evaluate_odometry import evaluate


def quaternion(yaw):
    return [0, 0, math.sin(yaw/2), math.cos(yaw/2)]


def fixture(drift=False):
    epoch = 'a'*32
    truth = [{'stamp_ns': k*20_000_000, 'xyz': [k*.02, 0, 0],
              'q_xyzw': [0, 0, 0, 1]} for k in range(251)]
    rows = []
    for k in range(51):
        t = k*.1
        offset = max(0, t-2) if drift else 0
        p = {'source_ns': k*100_000_000, 'xyz': [t+.2*offset, 0, 0],
             'q_xyzw': quaternion(.1*offset)}
        rows.extend([dict(p, kind='raw_odom', frame_id=f'vins_{epoch}_world',
                          child_frame_id=f'vins_{epoch}_imu'),
                     dict(p, kind='odom', frame_id=f'odom_{epoch}', child_frame_id=f'd435i_imu_{epoch}')])
    observation = {'epoch': epoch, 'raw_topic': f'/vins_raw/s_{epoch}/odometry', 'samples': rows}
    phases = [{'phase': 'PRESTREAM', 'stamp_ns': 2_000_000_000},
              {'phase': 'LANDED', 'stamp_ns': 4_000_000_000}]
    return [observation, truth, phases, {'clock_samples': [{'sim_ns': 2_000_000_000}]},
            {'localization_quality_history': [], 'landed_and_disarmed': True}, [0, 0, 0]]


class OdometryEvaluationTest(unittest.TestCase):
    def test_known_drift_is_not_fitted_away(self):
        report, curve = evaluate(*fixture(drift=True))
        self.assertAlmostEqual(report['endpoint']['position_error_m'], .4)
        self.assertAlmostEqual(report['endpoint']['yaw_error_deg'], math.degrees(.2))
        self.assertAlmostEqual(report['position_error_m']['rmse'], np.sqrt(np.mean(np.linspace(0, .4, 21)**2)))
        self.assertEqual(report['alignment']['reference_source_ns'], 1_000_000_000)
        self.assertEqual(report['alignment']['scale'], 1)
        self.assertEqual(report['coverage']['truth_grid_support_fraction'], 1)
        self.assertEqual(report['coverage']['bounded_time_support_fraction'], 1)
        self.assertEqual(len(curve), 21)

    def test_initial_frame_and_rotating_lever_arm(self):
        args = fixture()
        lever = np.array([.12, 0, .08])
        angle = .6
        a = np.array([[math.cos(angle), -math.sin(angle), 0],
                      [math.sin(angle), math.cos(angle), 0], [0, 0, 1]])
        translation = np.array([3, -2, 1])
        for row in args[1]:
            row['q_xyzw'] = quaternion(row['stamp_ns']/1e9*.3)
        for row in args[0]['samples']:
            yaw = row['source_ns']/1e9*.3
            r = np.array([[math.cos(yaw), -math.sin(yaw), 0],
                          [math.sin(yaw), math.cos(yaw), 0], [0, 0, 1]])
            imu = np.array([row['source_ns']/1e9, 0, 0])+r@lever
            row['xyz'] = (a.T@(imu-translation)).tolist()
            row['q_xyzw'] = quaternion(yaw-angle)
        args[-1] = lever
        report, _ = evaluate(*args)
        self.assertLess(report['position_error_m']['max'], 1e-12)
        self.assertLess(report['absolute_yaw_error_deg']['max'], 1e-10)

    def test_missing_odometry_is_visible_in_time_coverage(self):
        args = fixture()
        args[0]['samples'] = [p for p in args[0]['samples'] if not 2_500_000_000 < p['source_ns'] < 3_300_000_000]
        report, _ = evaluate(*args)
        self.assertEqual(report['coverage']['paired_raw_fraction'], 1)
        self.assertLess(report['coverage']['truth_grid_support_fraction'], .7)
        self.assertAlmostEqual(report['coverage']['raw_max_gap_sim_s'], .8)

    def test_missing_truth_not_interpolated_across_large_gap(self):
        args = fixture()
        args[1] = [p for p in args[1] if not 2_900_000_000 < p['stamp_ns'] < 3_100_000_000]
        report, _ = evaluate(*args)
        self.assertEqual(report['coverage']['rejected_samples'][0]['source_ns'], 3_000_000_000)
        self.assertLess(report['coverage']['paired_raw_fraction'], 1)

    def test_time_rewind_and_epoch_change_are_rejected(self):
        args = fixture()
        args[0]['samples'][12]['source_ns'] = 100_000_000
        with self.assertRaisesRegex(ValueError, 'strictly increasing'):
            evaluate(*args)
        args = fixture()
        args[0]['samples'][-2]['frame_id'] = 'different_epoch'
        with self.assertRaisesRegex(ValueError, 'epoch changed'):
            evaluate(*args)

    def test_endpoint_age_and_adapter_mismatch_reported(self):
        args = fixture()
        args[0]['samples'] = [copy.deepcopy(p) for p in args[0]['samples'] if p['source_ns'] < 3_900_000_000]
        args[0]['samples'][-1]['xyz'][0] += 1
        report, _ = evaluate(*args)
        self.assertAlmostEqual(report['endpoint']['age_before_landed_sim_s'], .2)
        self.assertEqual(report['raw_adapter_pose_check']['mismatched_pose_pairs'], 1)
        self.assertLess(report['coverage']['bounded_time_support_fraction'], 1)

    def test_bad_reference_or_invalid_quaternion_fails(self):
        args = fixture()
        args[3]['clock_samples'][-1]['sim_ns'] = 4_000_000_000
        with self.assertRaisesRegex(ValueError, 'pre-enable'):
            evaluate(*args)
        args = fixture()
        args[1][100]['q_xyzw'] = [0, 0, 0, 0]
        with self.assertRaisesRegex(ValueError, 'quaternion'):
            evaluate(*args)


if __name__ == '__main__':
    unittest.main()
