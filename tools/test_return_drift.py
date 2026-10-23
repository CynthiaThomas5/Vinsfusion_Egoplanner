import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent/'debug_truth'))
from evaluate_return_drift import score_windows


class ReturnDriftTests(unittest.TestCase):
    def samples(self):
        stages = [{'label': 'reference' if i == 0 else 'return', 'cycle': i,
                   'end_sim_s': 10+i*100} for i in range(4)]
        rows = []
        for i, stage in enumerate(stages):
            for j in range(51):
                rows.append({'source_ns': round((stage['end_sim_s']-5+j*.1)*1e9),
                             'truth_x_m': 0, 'truth_y_m': 0, 'truth_z_m': 1,
                             'truth_yaw_deg': 0, 'dx_m': i*.02, 'dy_m': 0, 'dz_m': 0,
                             'yaw_error_deg': i*.5})
        protocol = {'stationary_tail_sim_s': 5, 'return_position_tolerance_m': .02,
                    'return_yaw_tolerance_deg': 1, 'required_returns': 3, 'minimum_duration_sim_s': 300}
        return rows, stages, protocol

    def test_does_not_realign_away_return_drift(self):
        report = score_windows(*self.samples())
        self.assertTrue(report['measurement_completed'])
        self.assertAlmostEqual(report['checkpoints'][-1]['drift_since_reference_m'], .06)
        self.assertAlmostEqual(report['checkpoints'][-1]['yaw_drift_since_reference_deg'], 1.5)
        self.assertAlmostEqual(report['descriptive_trend']['return_drift_norm_slope_m_per_min'], .012)

    def test_actual_pose_mismatch_does_not_pass_return_count(self):
        rows, stages, protocol = self.samples()
        rows[-1]['truth_x_m'] = .1
        self.assertFalse(score_windows(rows, stages, protocol)['measurement_completed'])

    def test_missing_return_and_nonmonotonic_time(self):
        rows, stages, protocol = self.samples()
        self.assertFalse(score_windows(rows, stages[:-1], protocol)['measurement_completed'])
        with self.assertRaises(ValueError):score_windows(rows[::-1], stages, protocol)


if __name__ == '__main__':
    unittest.main()
