import unittest

import numpy as np

from tools.debug_truth.evaluate_n10_px4_tracking_lag import common_support_lag_sweep


class CommonSupportLagSweepTests(unittest.TestCase):
    def test_all_lags_use_same_samples_and_recover_known_lookback(self):
        setpoint_stamps = np.arange(0, 5_000_001, 20_000, dtype=np.int64)
        setpoint_positions = np.asarray(
            [[stamp / 1e6, 0.0, 0.0] for stamp in setpoint_stamps])
        local_stamps = np.arange(3_000_000, 5_000_001, 20_000, dtype=np.int64)
        local_positions = np.asarray(
            [[(stamp - 1_000_000) / 1e6, 0.0, 0.0]
             for stamp in local_stamps])

        result = common_support_lag_sweep(
            local_stamps, local_positions, setpoint_stamps,
            setpoint_positions, [0.0, 0.5, 1.0, 1.5, 2.0, 3.0], 40_000)

        self.assertEqual(result['sample_count'], len(local_stamps))
        self.assertEqual(len({row['count'] for row in result['candidates']}), 1)
        best = min(result['candidates'], key=lambda row: row['rms'])
        self.assertEqual(best['setpoint_lookback_s'], 1.0)
        self.assertAlmostEqual(best['rms'], 0.0)

    def test_gap_over_limit_excludes_a_local_state_from_all_lags(self):
        setpoint_stamps = np.asarray([0, 20_000, 120_000, 140_000], dtype=np.int64)
        setpoint_positions = np.asarray(
            [[stamp / 1e6, 0.0, 0.0] for stamp in setpoint_stamps])
        local_stamps = np.asarray([20_000, 120_000], dtype=np.int64)
        local_positions = np.asarray(
            [[stamp / 1e6, 0.0, 0.0] for stamp in local_stamps])

        result = common_support_lag_sweep(
            local_stamps, local_positions, setpoint_stamps,
            setpoint_positions, [0.0, 0.02], 40_000)

        self.assertEqual(result['sample_count'], 1)
        self.assertEqual(result['local_source_interval_us'], [20_000, 20_000])
        self.assertEqual([row['count'] for row in result['candidates']], [1, 1])


if __name__ == '__main__':
    unittest.main()
