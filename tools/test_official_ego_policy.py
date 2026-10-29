"""Regress official unknown-space admission and independent takeoff checks."""
import copy
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src/own/uav_navigation'))
from uav_navigation.admission import query_rejection
from check_takeoff_admission import official_takeoff_checks


class OfficialPolicyTests(unittest.TestCase):
    def setUp(self):
        self.request = NS(expected_epoch='e', expected_map_id='m', frame_id='odom_e',
                          center=NS(x=0., y=0., z=1.), radius_m=0.)
        stamp = NS(sec=10, nanosec=0)
        self.response = NS(accepted=True, free=True, reason='unobserved_not_occupied',
                           epoch='e', map_id='m', header=NS(frame_id='odom_e', stamp=stamp),
                           last_depth_source_stamp=stamp, last_fusion_stamp=stamp,
                           center=NS(x=0., y=0., z=1.), radius_m=0.,
                           unknown_count=1, occupied_count=0, free_count=0)

    def check(self):
        return query_rejection(self.response, self.request, 'official_ego')

    def test_unknown_is_traversable_only_for_official_point_query(self):
        self.assertEqual(self.check(), '')
        self.assertEqual(self.response.unknown_count, 1)
        self.assertTrue(query_rejection(self.response, self.request))
        self.request.radius_m = self.response.radius_m = .1
        self.assertTrue(self.check())

    def test_occupied_outside_and_missing_map_are_rejected(self):
        for reason in ('occupied', 'outside_map', 'no_active_map', 'epoch_mismatch'):
            self.response.reason = reason
            self.response.free = False
            self.assertEqual(self.check(), 'map_query_'+reason)

    def test_optimistic_query_still_checks_identity_and_counts_but_not_age(self):
        original = copy.deepcopy(self.response)
        self.response.map_id = 'old'
        self.assertEqual(self.check(), 'map_query_identity_mismatch')
        self.response = copy.deepcopy(original)
        self.response.last_fusion_stamp = NS(sec=9, nanosec=0)
        self.assertEqual(self.check(), '')
        self.response = original
        self.response.occupied_count = 1
        self.assertEqual(self.check(), 'map_query_inconsistent_counts')

    @staticmethod
    def preflight():
        return {'passed': True, 'last': {
            'bridge': {'phase': 'DISABLED', 'landed': True, 'armed': False, 'control_enabled': False},
            'odom': {'twist': {'twist': {'linear': {'x': 0.01, 'y': 0., 'z': 0.}}}},
        }}

    def test_takeoff_needs_native_state_without_map_or_speed_threshold(self):
        report = official_takeoff_checks(self.preflight())
        self.assertTrue(report['passed'])
        self.assertFalse(report['entry_map_known_free_claimed'])
        self.assertFalse(report['n05_raw_volume_gate_required'])
        self.assertEqual(report['speed_metric_effect'],
                         'diagnostic_only_no_takeoff_refusal')
        for field, value in [('armed', True), ('landed', False), ('control_enabled', True)]:
            preflight = self.preflight()
            preflight['last']['bridge'][field] = value
            self.assertFalse(official_takeoff_checks(preflight)['passed'])

    def test_takeoff_speed_is_observational_when_high_missing_or_nonfinite(self):
        for speed in (0.101, 1.0, float('nan')):
            preflight = self.preflight()
            preflight['last']['odom']['twist']['twist']['linear']['x'] = speed
            report = official_takeoff_checks(preflight)
            self.assertTrue(report['passed'])
            self.assertEqual(report['speed_metric_effect'],
                             'diagnostic_only_no_takeoff_refusal')
            if speed == speed:
                self.assertAlmostEqual(report['observed_odom_speed_m_s'], abs(speed))
            else:
                self.assertIsNone(report['observed_odom_speed_m_s'])
        preflight = self.preflight()
        del preflight['last']['odom']
        report = official_takeoff_checks(preflight)
        self.assertTrue(report['passed'])
        self.assertIsNone(report['observed_odom_speed_m_s'])
