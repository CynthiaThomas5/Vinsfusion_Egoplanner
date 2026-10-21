#!/usr/bin/env python3
"""Pure-Python checks for the fail-closed localization health state machine."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/own/uav_localization'))
from uav_localization.health import (Health, PublisherEndpointNotReady, body_velocity,
                                     publisher_endpoint_identity)


POLICY = json.loads((ROOT / 'config/components/localization/health.json').read_text())
STREAMS = ('left', 'right', 'imu', 'telemetry', 'optimized', 'propagated')


def metrics(stamp):
    return {'schema': 1, 'stamp_ns': stamp, 'initialized': True,
            'input_features': 36, 'stereo_features': 36, 'long_tracks': 36,
            'residual_components': 1000, 'final_cost': 0.01,
            'accel_bias_norm': 0.001, 'gyro_bias_norm': 0.001,
            'solve_seconds': 0.01, 'state_finite': True,
            'solve_current': True, 'solver_usable': True}


def feed_pair(health, stamp, wall):
    health.clock(stamp, wall)
    for name, offset in [('left', 10_000_000), ('right', 9_000_000), ('imu', 1_000_000),
                         ('propagated', 500_000), ('optimized', 0)]:
        health.sample(name, stamp-offset, wall)
    health.telemetry(metrics(stamp), wall)
    return health.paired(wall)


class HealthTests(unittest.TestCase):
    def tracked(self, policy=None):
        h = Health(copy.deepcopy(policy or POLICY), 0.0)
        for i in range(10):
            feed_pair(h, 1_000_000_000+i*50_000_000, 1.0+i*0.05)
        self.assertEqual(h.state, 'TRACKING')
        self.assertTrue(h.tick(1.5))
        return h

    def test_requires_ten_distinct_fresh_optimized_telemetry_pairs(self):
        h = Health(copy.deepcopy(POLICY), 0.0)
        for i in range(9):
            self.assertFalse(feed_pair(h, 1_000_000_000+i*50_000_000, 1.0+i*0.05))
        self.assertEqual(h.good_pairs, 9)
        self.assertTrue(feed_pair(h, 1_450_000_000, 1.45))
        self.assertEqual(h.good_pairs, 10)

    def test_each_stale_stream_latches_loss(self):
        for stale in STREAMS:
            with self.subTest(stale=stale):
                h = self.tracked()
                now = h.clock_ns + int((POLICY['max_source_age_s'][stale]+0.01)*1e9)
                wall = 1.51
                h.clock(now, wall)
                for name in STREAMS:
                    if name == stale:
                        continue
                    if name == 'telemetry':
                        h.telemetry(metrics(now), wall)
                    else:
                        h.sample(name, now, wall)
                self.assertFalse(h.tick(wall))
                self.assertEqual(h.state, 'LOST')
                self.assertEqual(h.reason, stale+'_stale')

    def test_bad_telemetry_and_clock_regression_lock_without_recovery(self):
        h = Health(copy.deepcopy(POLICY), 0.0)
        self.assertFalse(h.telemetry([], 0.1))
        self.assertEqual(h.reason, 'malformed_telemetry')
        self.assertFalse(h.clock(1, 0.2))
        self.assertFalse(h.tick(0.3))
        self.assertEqual(h.state, 'LOCKED')

        h = self.tracked()
        self.assertFalse(h.clock(h.clock_ns-1, 1.6))
        self.assertEqual(h.reason, 'clock_regression')
        self.assertFalse(h.sample('left', h.clock_ns+1, 1.7))
        self.assertFalse(h.tick(1.8))
        self.assertEqual(h.state, 'LOCKED')

    def test_initialization_timeout_fails_closed(self):
        h = Health(copy.deepcopy(POLICY), 2.0)
        self.assertFalse(h.tick(22.01))
        self.assertFalse(h.locked)
        h.clock(0, 30.0)
        self.assertFalse(h.tick(50.01))
        self.assertEqual(h.reason, 'initialization_timeout')
        self.assertEqual(h.state, 'LOST')

    def test_paused_clock_is_detected_by_steady_timer(self):
        h = self.tracked()
        self.assertFalse(h.tick(2.0))
        self.assertEqual(h.reason, 'clock_stalled')

    def test_short_lockstep_pause_does_not_extrapolate_receipt_age(self):
        h = Health(copy.deepcopy(POLICY), 0.0)
        for i in range(10):
            feed_pair(h, 1_000_000_000+i*39_000_000, 1.0+i*0.05)
        self.assertEqual(h.state, 'TRACKING')
        self.assertAlmostEqual(h.clock_rate, 0.78, places=12)
        paused_clock = h.clock_ns
        # A 0.34 s wall pause projects to 0.265 s at this RTF, above the 0.2 s
        # IMU receipt limit, but remains below the 0.5 s clock-stall watchdog.
        # With lockstep stopped, the last sensor samples remain fresh in sim time.
        self.assertTrue(h.tick(1.79))
        self.assertEqual(h.state, 'TRACKING')
        self.assertEqual(h.clock_ns, paused_clock)

        # Resume with advancing simulation time and fresh samples; tracking continues.
        self.assertTrue(feed_pair(h, paused_clock + 39_000_000, 1.80))
        self.assertTrue(h.tick(1.81))
        self.assertEqual(h.state, 'TRACKING')

    def test_receipt_age_tracks_simulation_rate_during_slow_replay(self):
        h = Health(copy.deepcopy(POLICY), 0.0)
        for i in range(10):
            stamp = 1_000_000_000+i*50_000_000
            wall = 5.0+i*0.5
            feed_pair(h, stamp, wall)
        self.assertEqual(h.state, 'TRACKING')
        self.assertAlmostEqual(h.clock_rate, 0.1, places=12)
        h.clock(1_480_000_000, 10.0)
        self.assertTrue(h.tick(10.1))
        self.assertEqual(h.state, 'TRACKING')

    def test_source_age_limit_uses_exact_integer_nanoseconds(self):
        for age_ns, expected in ((300_000_000, ''),
                                 (300_000_001, 'optimized_stale')):
            with self.subTest(age_ns=age_ns):
                h = self.tracked()
                now_ns = h.clock_ns + 1_000_000_000
                wall = 1.6
                h.clock(now_ns, wall)
                for name in STREAMS:
                    stamp_ns = now_ns - age_ns if name == 'optimized' else now_ns
                    if name == 'telemetry':
                        h.telemetry(metrics(stamp_ns), wall)
                    else:
                        h.sample(name, stamp_ns, wall)
                self.assertEqual(h.freshness(wall), expected)

    def test_future_stamp_context_uses_adapter_clock_at_health_evaluation(self):
        h = self.tracked()
        now_ns = h.clock_ns + 50_000_000
        wall = 1.6
        h.clock(now_ns, wall)
        for name in STREAMS:
            stamp_ns = now_ns
            if name == 'telemetry':
                h.telemetry(metrics(stamp_ns), wall)
            else:
                h.sample(name, stamp_ns, wall)

        future_tolerance_ns = round(POLICY['future_tolerance_s'] * 1e9)
        future_stamp_ns = now_ns + future_tolerance_ns + 1
        h.sample('propagated', future_stamp_ns, wall + 0.01)
        self.assertEqual(h.freshness(wall + 0.02), 'propagated_from_future')
        self.assertEqual(h.future_observation, {
            'stream': 'propagated',
            'source_stamp_ns': future_stamp_ns,
            'clock_stamp_ns': now_ns,
            'source_age_ns': -future_tolerance_ns - 1,
            'future_tolerance_ns': future_tolerance_ns,
            'receipt_clock_ns': now_ns,
            'evaluated_wall_s': wall + 0.02,
        })

    def test_quality_guards_reject_unusable_solve_and_weak_tracks(self):
        h = Health(copy.deepcopy(POLICY), 0.0)
        bad = metrics(1_000_000_000)
        bad['solver_usable'] = False
        h.telemetry(bad, 1.0)
        self.assertEqual(h.quality(), 'solver_invalid')
        bad = metrics(1_000_000_001)
        bad['input_features'] = 1
        h.telemetry(bad, 1.1)
        self.assertEqual(h.quality(), 'input_features_insufficient')

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


if __name__ == '__main__':
    unittest.main()
