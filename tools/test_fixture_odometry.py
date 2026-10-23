import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent / 'debug_truth'))
from evaluate_fixture_odometry import compare


class FixtureOdometryTests(unittest.TestCase):
    def sample(self):
        raw = [{'source_ns': i * 10_000_000, 'xyz': [i*.01 + 2, 0, 0], 'q_xyzw': [0, 0, 0, 1]}
               for i in range(5)]
        truth = [{'stamp_ns': i * 10_000_000, 'xyz': [i*.01, 0, 0], 'q_xyzw': [0, 0, 0, 1]}
                 for i in range(5)]
        return raw, truth

    def test_fixed_alignment_does_not_fit_away_later_error(self):
        raw, truth = self.sample()
        raw[-1]['xyz'][0] += .1
        report, rows = compare(raw, truth, 0, [0, 0, .02])
        self.assertAlmostEqual(rows[0]['position_error_m'], 0)
        self.assertAlmostEqual(report['position_last_m'], .1)

    def test_rejects_session_time_repair_and_stale_anchor(self):
        raw, truth = self.sample()
        with self.assertRaises(ValueError):
            compare(raw[::-1], truth, 0, [0, 0, 0])
        with self.assertRaises(ValueError):
            compare(raw, truth, 1_000_000_000, [0, 0, 0])


if __name__ == '__main__':
    unittest.main()
