"""Negative evidence and geometry checks for the actual N13 route evaluator."""
import tempfile
import unittest
from pathlib import Path
from tools.debug_truth.evaluate_n13_route import evaluate, direct_hit, plane_crossings


class N13RouteTests(unittest.TestCase):
    def setUp(self):
        self.cylinder = {'center_xyz_m': [0., .3, 1.5], 'radius_m': .5,
                         'z_min_m': 0., 'z_max_m': 3.}

    def test_direct_line_is_physically_blocked(self):
        self.assertIsNotNone(direct_hit([-6, 0, 1], [6, 0, 1], self.cylinder))

    def test_actual_bypass(self):
        rows = [{'source_stamp_ns': 1, 'p': [-1, -1, 1]},
                {'source_stamp_ns': 2, 'p': [1, -1, 1]}]
        self.assertFalse(plane_crossings(rows, 'p', self.cylinder)[0]['inside_solid'])

    def test_path_through_solid_is_detected(self):
        rows = [{'source_stamp_ns': 1, 'p': [-1, 0, 1]},
                {'source_stamp_ns': 2, 'p': [1, 0, 1]}]
        self.assertTrue(plane_crossings(rows, 'p', self.cylinder)[0]['inside_solid'])

    def test_missing_archive_never_passes(self):
        with tempfile.TemporaryDirectory() as path:
            result = evaluate(Path(path), Path('config/acceptance_n13.json'))
            self.assertEqual(result['status'], 'INSUFFICIENT')
            self.assertEqual(len(result['obstacles']), 3)

    def test_time_regression_rejected(self):
        with self.assertRaises(ValueError):
            plane_crossings([{'source_stamp_ns': 2, 'p': [-1, -1, 1]},
                             {'source_stamp_ns': 1, 'p': [1, -1, 1]}], 'p', self.cylinder)

    def test_duplicate_sample_does_not_invent_elapsed_time(self):
        rows=[{'source_stamp_ns':1,'p':[-1,-1,1]},
              {'source_stamp_ns':1,'p':[-1,-1,1]},
              {'source_stamp_ns':2,'p':[1,-1,1]}]
        crossings=plane_crossings(rows,'p',self.cylinder)
        self.assertEqual(len(crossings),1)
        self.assertEqual(crossings[0]['bracket_source_gap_sim_s'],1e-9)

    def test_same_stamp_command_change_across_plane_is_insufficient(self):
        with self.assertRaisesRegex(ValueError,'ambiguous_same_stamp'):
            plane_crossings([{'source_stamp_ns':1,'p':[-1,-1,1]},
                             {'source_stamp_ns':1,'p':[1,-1,1]}],'p',self.cylinder)
