#!/usr/bin/env python3
"""Checks for localization stream integrity without project quality gates."""
import json
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/own/uav_localization'))
from uav_localization.health import (Health, PublisherEndpointNotReady, body_velocity,
                                     publisher_endpoint_identity,
                                     publisher_endpoint_identity_changed)


POLICY = json.loads((ROOT / 'config/components/localization/health.json').read_text())


def metrics(stamp):
    return {'schema': 1, 'stamp_ns': stamp, 'initialized': False,
            'input_features': 0, 'stereo_features': 0, 'long_tracks': 0,
            'residual_components': 1000, 'final_cost': 5000.0,
            'accel_bias_norm': 10.0, 'gyro_bias_norm': 10.0,
            'solve_seconds': 10.0, 'state_finite': False,
            'solve_current': False, 'solver_usable': False}


class LocalizationIntegrityTests(unittest.TestCase):
    def test_quality_and_age_values_are_observations_not_gates(self):
        health = Health(POLICY, 0.0)
        health.clock(1_000_000_000, 1.0)
        health.sample('left', 1, 1.0)
        health.sample('optimized', 1_000_000_000, 1.0)
        self.assertTrue(health.telemetry(metrics(1_000_000_000), 1.0))
        self.assertTrue(health.paired(1.0))
        self.assertTrue(health.tick(1000.0))
        self.assertEqual(health.state, 'TRACKING')
        self.assertFalse(health.locked)
        self.assertAlmostEqual(health.normalized_cost, math.sqrt(10.0))

    def test_telemetry_and_optimized_odometry_are_correlated(self):
        health = Health(POLICY, 0.0)
        self.assertFalse(health.paired(1.0))
        health.telemetry(metrics(1_000_000_000), 1.0)
        health.sample('optimized', 1_000_002_000, 1.0)
        self.assertFalse(health.paired(1.0))
        health.telemetry(metrics(1_000_002_000), 1.1)
        self.assertTrue(health.paired(1.1))
        self.assertEqual(health.good_pairs, 1)
        self.assertFalse(health.paired(1.2))

    def test_clock_regression_and_nonincreasing_stream_stamp_lock(self):
        health = Health(POLICY, 0.0)
        self.assertTrue(health.clock(100, 0.1))
        self.assertFalse(health.clock(99, 0.2))
        self.assertEqual(health.reason, 'clock_regression')
        self.assertFalse(health.tick(0.3))
        self.assertEqual(health.state, 'LOCKED')

        sample = Health(POLICY, 0.0)
        self.assertTrue(sample.sample('left', 100, 0.1))
        self.assertFalse(sample.sample('left', 100, 0.2))
        self.assertEqual(sample.reason, 'left_stamp_not_increasing')

    def test_malformed_telemetry_remains_an_integrity_fault(self):
        health = Health(POLICY, 0.0)
        self.assertFalse(health.telemetry([], 0.1))
        self.assertEqual(health.reason, 'malformed_telemetry')
        self.assertTrue(health.locked)

    def test_integrity_snapshot_retains_cost_and_source_stamps(self):
        health = Health(POLICY, 0.0)
        sample = metrics(1_234_000_000)
        self.assertTrue(health.telemetry(sample, 1.25))
        self.assertTrue(health.sample('optimized', 1_234_000_000, 1.26))
        health.paired(1.26)
        snapshot = health.diagnostic_snapshot()
        self.assertEqual(snapshot['metrics']['stamp_ns'], 1_234_000_000)
        self.assertEqual(snapshot['samples']['telemetry']['source_stamp_ns'], 1_234_000_000)
        self.assertAlmostEqual(snapshot['normalized_cost'], math.sqrt(10.0))
        json.dumps(snapshot)

    def test_world_velocity_is_rotated_into_child_body_frame(self):
        root_half = 2**-0.5
        result = body_velocity([0.0, 0.0, root_half, root_half], [1.0, 0.0, 0.0])
        for actual, expected in zip(result, [0.0, -1.0, 0.0]):
            self.assertAlmostEqual(actual, expected, places=12)
        with self.assertRaises(ValueError):
            body_velocity([0.0, 0.0, 0.0, 0.0], [1.0, 0.0, 0.0])

    def test_publisher_identity_tracks_endpoint_gid_and_ros_node(self):
        first = type('Endpoint', (), {'endpoint_gid': list(range(24)),
                                     'node_name': 'vins_estimator', 'node_namespace': '/vins'})()
        second = type('Endpoint', (), {'endpoint_gid': list(range(1, 25)),
                                      'node_name': 'vins_estimator', 'node_namespace': '/vins'})()
        self.assertEqual(publisher_endpoint_identity([first]), (bytes(first.endpoint_gid).hex(), 'vins_estimator', '/vins'))
        self.assertNotEqual(publisher_endpoint_identity([first])[0], publisher_endpoint_identity([second])[0])
        with self.assertRaises(ValueError):
            publisher_endpoint_identity([])
        with self.assertRaises(ValueError):
            publisher_endpoint_identity([first, second])
        unresolved = type('Endpoint', (), {'endpoint_gid': list(range(24)),
                                          'node_name': '_NODE_NAME_UNKNOWN_',
                                          'node_namespace': '_NODE_NAMESPACE_UNKNOWN_'})()
        with self.assertRaises(PublisherEndpointNotReady):
            publisher_endpoint_identity([unresolved])

    def test_publisher_identity_is_checked_after_stream_first_message(self):
        # An unbound stream can be advertised after another stream has put the
        # adapter into TRACKING; its first message binds the identity in bind().
        self.assertFalse(publisher_endpoint_identity_changed(
            None, ('vins_estimator', '/vins'), bytes(range(24)).hex(),
            'vins_estimator', '/vins'))
        gid = bytes(range(24)).hex()
        node = ('vins_estimator', '/vins')
        self.assertFalse(publisher_endpoint_identity_changed(
            gid, node, gid, *node))
        self.assertTrue(publisher_endpoint_identity_changed(
            gid, node, bytes(range(1, 25)).hex(), *node))
        self.assertTrue(publisher_endpoint_identity_changed(
            gid, node, gid, 'other_estimator', '/vins'))


if __name__ == '__main__':
    unittest.main()
