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
                                     interpolate_angular_velocity,
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

    def test_stream_observation_tracks_periods_gaps_and_source_age(self):
        health = Health(POLICY, 0.0)
        health.clock(1_000_000_000, 1.0)
        health.sample('left', 990_000_000, 1.0)
        health.clock(1_100_000_000, 1.1)
        health.sample('left', 1_090_000_000, 1.1)
        summary = health.stream_summary()['left']
        self.assertEqual(summary['count'], 2)
        self.assertAlmostEqual(summary['max_source_interval_s'], 0.1)
        self.assertAlmostEqual(summary['max_receipt_interval_s'], 0.1)
        self.assertAlmostEqual(summary['max_source_age_s'], 0.01)
        self.assertAlmostEqual(summary['source_frequency_hz'], 10.0)

    def test_world_velocity_is_rotated_into_child_body_frame(self):
        root_half = 2**-0.5
        result = body_velocity([0.0, 0.0, root_half, root_half], [1.0, 0.0, 0.0])
        for actual, expected in zip(result, [0.0, -1.0, 0.0]):
            self.assertAlmostEqual(actual, expected, places=12)
        with self.assertRaises(ValueError):
            body_velocity([0.0, 0.0, 0.0, 0.0], [1.0, 0.0, 0.0])

    def test_imu_angular_velocity_uses_nearest_same_axis_bracket(self):
        samples = [(1_000_000, [0.0, 2.0, 4.0]),
                   (3_000_000, [2.0, 4.0, 8.0]),
                   (5_000_000, [4.0, 6.0, 12.0])]
        self.assertEqual(interpolate_angular_velocity(samples, 3_000_000),
                         [2.0, 4.0, 8.0])
        self.assertEqual(interpolate_angular_velocity(samples, 2_000_000),
                         [1.0, 3.0, 6.0])
        self.assertIsNone(interpolate_angular_velocity(samples, 500_000))

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

    def test_hardware_gate_requires_usable_vins_and_measured_age_budgets(self):
        stream_names = ('left', 'right', 'imu', 'telemetry', 'optimized', 'propagated')
        policy = {
            'status_period_wall_s': 0.05,
            'freshness': {
                'mode': 'gate',
                'streams': {name: {'source_age_budget_s': 0.2,
                                   'receipt_age_budget_s': 0.2}
                            for name in stream_names},
            },
        }
        health = Health(policy, 0.0)
        health.clock(1_000_000_000, 1.0)
        for name in stream_names:
            health.sample(name, 1_000_000_000, 1.0)
        usable = metrics(1_000_000_000)
        usable.update(initialized=True, state_finite=True,
                      solve_current=True, solver_usable=True)
        health.metrics = usable
        self.assertTrue(health.paired(1.0, require_solver_usable=True))
        self.assertTrue(health.enforce_freshness(1_050_000_000, 1.05))
        self.assertFalse(health.enforce_freshness(1_250_000_000, 1.05))
        self.assertEqual(health.reason, 'left_source_stale')

        waiting = Health(policy, 0.0)
        waiting.telemetry(metrics(1_000_000_000), 1.0)
        waiting.sample('optimized', 1_000_000_000, 1.0)
        self.assertFalse(waiting.paired(1.0, require_solver_usable=True))
        self.assertEqual(waiting.state, 'INITIALIZING')
        self.assertEqual(waiting.reason, 'waiting_for_usable_vins_solution')

        startup = Health(policy, 0.0)
        startup.clock(1_000_000_000, 1.0)
        for name in ('left', 'telemetry', 'optimized'):
            startup.sample(name, 1_000_000_000, 1.0)
        startup.metrics = usable
        self.assertFalse(startup.paired(1.0, require_solver_usable=True))
        self.assertFalse(startup.locked)
        self.assertEqual(startup.reason, 'waiting_for_freshness_inputs')
        for name in ('right', 'imu', 'propagated'):
            startup.sample(name, 1_000_000_000, 1.0)
        self.assertTrue(startup.paired(1.1, require_solver_usable=True))

    def test_hardware_gate_waits_for_fresh_startup_samples_then_locks_if_stale(self):
        names = ('left', 'right', 'imu', 'telemetry', 'optimized', 'propagated')
        policy = {
            'status_period_wall_s': 0.05,
            'freshness': {
                'mode': 'gate',
                'streams': {name: {'source_age_budget_s': 0.2,
                                   'receipt_age_budget_s': 0.2}
                            for name in names},
            },
        }
        usable = metrics(1_000_000_000)
        usable.update(initialized=True, state_finite=True,
                      solve_current=True, solver_usable=True)
        health = Health(policy, 0.0)
        health.clock(1_000_000_000, 1.0)
        health.telemetry(usable, 1.0)
        for name in ('left', 'right', 'imu', 'optimized', 'propagated'):
            health.sample(name, 1_000_000_000, 1.0)

        health.clock(1_300_000_000, 1.3)
        self.assertFalse(health.paired(1.3, require_solver_usable=True))
        self.assertEqual(health.state, 'INITIALIZING')
        self.assertEqual(health.reason, 'waiting_for_freshness_inputs')
        self.assertFalse(health.locked)

        health.clock(1_400_000_000, 1.4)
        fresh_stamp = 1_390_000_000
        usable = metrics(fresh_stamp)
        usable.update(initialized=True, state_finite=True,
                      solve_current=True, solver_usable=True)
        health.telemetry(usable, 1.39)
        for name in ('left', 'right', 'imu', 'optimized', 'propagated'):
            health.sample(name, fresh_stamp, 1.39)
        self.assertTrue(health.paired(1.4, require_solver_usable=True))
        self.assertTrue(health.enforce_freshness(1_400_000_000, 1.4))
        self.assertFalse(health.enforce_freshness(1_650_000_000, 1.65))
        self.assertEqual(health.reason, 'left_source_stale')

        future = Health(policy, 0.0)
        future.clock(2_000_000_000, 2.0)
        future_metrics = metrics(2_100_000_000)
        future_metrics.update(initialized=True, state_finite=True,
                              solve_current=True, solver_usable=True)
        future.telemetry(future_metrics, 2.0)
        for name in ('left', 'right', 'imu', 'optimized', 'propagated'):
            future.sample(name, 2_100_000_000, 2.0)
        self.assertFalse(future.paired(2.0, require_solver_usable=True))
        self.assertTrue(future.locked)
        self.assertEqual(future.reason, 'left_future_source_stamp')


    def test_startup_fresh_window_restarts_after_gap_and_preserves_tracking_lock(self):
        policy = {'status_period_wall_s': 0.05, 'startup_fresh_window_s': 0.5,
                  'freshness': {'mode': 'gate', 'streams': {
                      name: {'source_age_budget_s': 0.2, 'receipt_age_budget_s': 0.2}
                      for name in ('telemetry', 'optimized')}}}
        health = Health(policy, 0.0)

        def pair(wall):
            stamp = int(wall * 1e9)
            health.clock(stamp, wall)
            data = metrics(stamp)
            data.update(initialized=True, state_finite=True, solve_current=True, solver_usable=True)
            health.telemetry(data, wall)
            health.sample('optimized', stamp, wall)
            return health.paired(wall, require_solver_usable=True)

        self.assertFalse(pair(1.0))
        self.assertFalse(pair(1.1))
        health.clock(1_400_000_000, 1.4)
        self.assertFalse(health.paired(1.4, require_solver_usable=True))
        self.assertFalse(pair(1.5))
        self.assertFalse(pair(1.65))
        self.assertFalse(pair(1.8))
        self.assertFalse(pair(1.95))
        self.assertTrue(pair(2.01))
        # A newly paired solution with an old receipt must not reopen startup.
        health.clock(2_400_000_000, 2.4)
        data = metrics(2_020_000_000)
        data.update(initialized=True, state_finite=True, solve_current=True, solver_usable=True)
        health.telemetry(data, 2.02)
        health.sample('optimized', 2_020_000_000, 2.02)
        self.assertFalse(health.paired(2.4, require_solver_usable=True))
        self.assertEqual(health.state, 'TRACKING')
        self.assertFalse(health.enforce_freshness(2_400_000_000, 2.4))
        self.assertTrue(health.locked)


class HardwareFutureToleranceTests(unittest.TestCase):
 def health(self,lead,tolerance=None):
  streams={x:{'source_age_budget_s':.2,'receipt_age_budget_s':.2} for x in ('left','right','imu','telemetry','optimized','propagated')}
  if tolerance is not None:streams['imu']['future_source_tolerance_s']=tolerance
  h=Health({'status_period_wall_s':.05,'freshness':{'mode':'gate','streams':streams}},0.)
  h.clock(1_000_000_000,1.)
  for name in streams:
   if name!='telemetry':h.sample(name,1_000_000_000+(int(lead*1e9) if name=='imu' else 0),1.)
  data=metrics(1_000_000_000);data.update(initialized=True,state_finite=True,solve_current=True,solver_usable=True);h.telemetry(data,1.)
  return h
 def test_default_zero_preserved(self):
  h=self.health(.0006);self.assertFalse(h.paired(1.,require_solver_usable=True));self.assertEqual(h.reason,'imu_future_source_stamp')
 def test_measured_lead_within_proposed_budget(self):
  h=self.health(.000845744,.001);self.assertTrue(h.paired(1.,require_solver_usable=True));self.assertTrue(h.enforce_freshness(1_000_000_000,1.));self.assertLess(h.last_age_metrics['imu']['source_age_s'],0)
 def test_over_one_ms_still_locks(self):
  h=self.health(.001001,.001);self.assertFalse(h.paired(1.,require_solver_usable=True));self.assertEqual(h.reason,'imu_future_source_stamp')
 def test_source_and_receipt_limits_unchanged(self):
  for now,wall,reason in ((1_250_000_000,1.05,'left_source_stale'),(1_100_000_000,1.25,'left_receipt_stale')):
   h=self.health(.0006,.001);self.assertTrue(h.paired(1.,require_solver_usable=True));self.assertFalse(h.enforce_freshness(now,wall));self.assertEqual(h.reason,reason)
 def test_rollback_still_locks(self):
  h=self.health(.0006,.001);self.assertTrue(h.paired(1.,require_solver_usable=True));self.assertFalse(h.clock(999_999_999,1.));self.assertEqual(h.reason,'clock_regression')

if __name__ == '__main__':
    unittest.main()
