"""Unit tests for N08 derivative-hull speed certification."""
import sys
from pathlib import Path
import unittest
import hashlib
import json
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

from evaluate_n08_curve_certificate import certify_speed_bounds, resolve_trial_speed_profile  # noqa: E402


class N08CurveSpeedCertificateTests(unittest.TestCase):
    def test_trial_profile_requires_matching_recorded_bytes_and_launch_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            relative = 'config/components/mapping/n08_trial.json'
            path = root / relative
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({'max_velocity_m_s': 0.1,
                                       'max_acceleration_m_s2': 0.25,
                                       'n08_vector_speed_cap_m_s': 0.12}))
            launch = {'planner_config': relative,
                      'source_sha256': {relative: hashlib.sha256(path.read_bytes()).hexdigest()},
                      'ego_launch_arguments': {'max_vel': 0.1, 'max_acc': 0.25}}
            result = resolve_trial_speed_profile(launch, root)
            self.assertAlmostEqual(result['vector_speed_cap_m_s'], 0.12)
            launch['ego_launch_arguments']['max_vel'] = 0.15
            with self.assertRaisesRegex(ValueError, 'launch_speed'):
                resolve_trial_speed_profile(launch, root)
            launch['ego_launch_arguments']['max_vel'] = 0.1
            path.write_text(path.read_text()+'\n')
            with self.assertRaisesRegex(ValueError, 'hash_mismatch'):
                resolve_trial_speed_profile(launch, root)

    def test_axis_over_limit_fails_even_when_vector_cap_passes(self):
        result = certify_speed_bounds(np.asarray([[0.0, 0.08157, 0.0]]), 0.075)
        self.assertFalse(result['per_axis_pass'])
        self.assertTrue(result['vector_pass'])
        self.assertFalse(result['passed'])
        self.assertAlmostEqual(result['per_axis_limit_m_s'], 0.07885)

    def test_both_axis_and_vector_limits_pass(self):
        result = certify_speed_bounds(
            np.asarray([[0.04, 0.05, 0.03], [-0.02, 0.06, 0.0]]), 0.075)
        self.assertTrue(result['per_axis_pass'])
        self.assertTrue(result['vector_pass'])
        self.assertTrue(result['passed'])

    def test_vector_cap_is_still_checked_independently(self):
        result = certify_speed_bounds(np.asarray([[0.11, 0.11, 0.0]]), 0.15)
        self.assertTrue(result['per_axis_pass'])
        self.assertFalse(result['vector_pass'])
        self.assertFalse(result['passed'])

    def test_invalid_derivative_shape_fails_closed(self):
        with self.assertRaises(ValueError):
            certify_speed_bounds(np.asarray([[0.1, 0.2]]), 0.075)


if __name__ == '__main__':
    unittest.main()
