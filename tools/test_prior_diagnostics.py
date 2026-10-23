import copy
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent / 'debug_truth'))
from evaluate_prior_diagnostics import validate


class PriorDiagnosticTests(unittest.TestCase):
    def sample(self):
        return {'stamp_ns': 1, 'final_cost': 13, 'residual_components': 21,
                'input_features': 1, 'stereo_features': 1, 'continued_tracks': 1, 'long_tracks': 1,
                'cost_components': {'evaluation_ok': True, 'evaluation_seconds': .001,
                    'visual': {'cost': 2, 'residual_components': 14},
                    'imu': {'cost': 3, 'residual_components': 5},
                    'marginalization': {'cost': 8, 'residual_components': 2},
                    'prior_details': {'next_marginalization_branch': 'oldest', 'available': True,
                        'evaluation_ok': True, 'spectrum_ok': True, 'retained_dimension': 2,
                        'r0_squared_norm': 4, 'Jdx_squared_norm': 4, 'twice_r0_dot_Jdx': 8,
                        'current_squared_norm': 16, 'information_rank': 1,
                        'information_min_positive': 2, 'information_max': 2,
                        'window_tracks': [[1, 0, 4, 4]], 'window_tracks_truncated': False}}}

    def test_consistent_vector_identity_and_stereo_factors(self):
        validate(self.sample())

    def test_rejects_inconsistent_norm_rank_and_spectrum(self):
        for key, value in [('current_squared_norm', 17), ('twice_r0_dot_Jdx', 9),
                           ('information_rank', 3), ('spectrum_ok', False),
                           ('information_max', float('nan')),
                           ('window_tracks', [[1, 0, 4, 3]]),
                           ('window_tracks', [[1, 0, 4, 4], [1, 1, 3, 3]])]:
            metric = copy.deepcopy(self.sample())
            metric['cost_components']['prior_details'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate(metric)

    def test_truncation_only_checks_visual_count_lower_bound(self):
        metric = self.sample()
        details = metric['cost_components']['prior_details']
        details['window_tracks_truncated'] = True
        details['window_tracks'] = [[1, 0, 4, 3]]
        validate(metric)
        details['window_tracks'] = [[1, 0, 5, 5]]
        with self.assertRaises(ValueError):
            validate(metric)


if __name__ == '__main__':
    unittest.main()
