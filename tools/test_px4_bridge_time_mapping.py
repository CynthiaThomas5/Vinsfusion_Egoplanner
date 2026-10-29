#!/usr/bin/env python3
"""Regression tests for explicit ROS simulation to PX4 timestamp mapping."""

from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/own/uav_px4_bridge'))

from uav_px4_bridge.time_mapping import (  # noqa: E402
    RosClockMapper, TimeMappingError, fallback_agent_timestamp_us,
    px4_clock_age_sim_s,
    px4_ros_source_gap_sim_s,
    px4_timesync_age_sim_s)


class Px4TimeMappingTests(unittest.TestCase):
    def mapper(self, **kwargs):
        settings = dict(min_samples=4, max_samples=8,
                        max_future_s=0.02,
                        min_rate=0.1, max_rate=10.0)
        settings.update(kwargs)
        result = RosClockMapper(**settings)
        for index in range(5):
            result.add_clock(1_000_000_000 + index * 100_000_000,
                             10_000_000_000 + index * 150_000_000)
        return result

    def to_px4(self, mapper, **overrides):
        values = dict(
            source_ros_ns=1_300_000_000,
            receipt_monotonic_ns=10_700_000_000,
            receipt_system_ns=50_000_000_000,
            estimated_offset_us=-49_000_000,
            timesync_rtt_us=500,
            timesync_receipt_monotonic_ns=10_650_000_000,
            max_timesync_age_s=0.5,
            max_timesync_rtt_us=10_000,
            max_fit_residual_s=0.03,
            px4_ros_clock_offset_us=-400_000,
            max_timesync_future_s=0.02,
        )
        values.update(overrides)
        return mapper.to_px4(**values)

    def test_inverse_maps_ros_sample_into_px4_dds_clock_domain(self):
        result = self.to_px4(self.mapper())
        self.assertEqual(result.now_us, 50_000_000)
        self.assertEqual(result.sample_us, 49_900_000)
        # PX4's XRCE deserializer adds the estimated offset, recovering the
        # ROS sample time after the configured PX4-to-ROS clock alignment.
        self.assertEqual(result.sample_us - 49_000_000, 900_000)
        self.assertAlmostEqual(result.sample_age_wall_s, 0.25)

    def test_mapper_fallback_uses_current_agent_time_only_when_synced(self):
        current_agent_time_ns = 50_000_000_000
        stale_timesync_timestamp_us = 44_000_000
        result = fallback_agent_timestamp_us(current_agent_time_ns, True)
        self.assertEqual(result, current_agent_time_ns // 1000)
        self.assertNotEqual(result, stale_timesync_timestamp_us)
        self.assertEqual(
            fallback_agent_timestamp_us(current_agent_time_ns, False), 0)

    def test_mapper_fallback_rejects_nonpositive_agent_time(self):
        with self.assertRaisesRegex(TimeMappingError, 'positive'):
            fallback_agent_timestamp_us(0, True)

    def test_timesync_freshness_uses_supplied_px4_clock_age(self):
        mapper = self.mapper()
        result = self.to_px4(
            mapper, timesync_receipt_monotonic_ns=9_000_000_000,
            timesync_age_s=0.4)
        self.assertEqual(result.sample_us, 49_900_000)
        with self.assertRaisesRegex(TimeMappingError, 'timesync_stale'):
            self.to_px4(mapper, timesync_age_s=2.0)

    def test_direct_lockstep_mapping_uses_sim_time_without_timesync(self):
        mapper = self.mapper(lockstep=True)
        result = self.to_px4(
            mapper, estimated_offset_us=0, timesync_rtt_us=0,
            timesync_receipt_monotonic_ns=0, timesync_age_s=None,
            px4_ros_clock_offset_us=0, timestamp_sync_enabled=False)
        self.assertEqual(result.now_us, 1_400_000)
        self.assertEqual(result.sample_us, 1_300_000)
        self.assertAlmostEqual(result.sample_age_wall_s, 0.25)

    def test_direct_timestamps_require_lockstep_clock(self):
        with self.assertRaisesRegex(TimeMappingError, 'requires_lockstep'):
            self.to_px4(
                self.mapper(), estimated_offset_us=0, timesync_rtt_us=0,
                timesync_receipt_monotonic_ns=0, timesync_age_s=None,
                px4_ros_clock_offset_us=0, timestamp_sync_enabled=False)
        with self.assertRaisesRegex(TimeMappingError, 'requires_lockstep'):
            self.mapper().current_lockstep_px4_time_us(10_700_000_000)

    def test_lockstep_source_age_is_reported_without_a_stale_cutoff(self):
        mapper = RosClockMapper(4, 8, .02, .1, 10., lockstep=True)
        for index, offset in enumerate((0, 150_000_000, 300_000_000,
                                        300_100_000, 600_000_000)):
            mapper.add_clock(1_000_000_000 + index * 100_000_000,
                             10_000_000_000 + offset)
        result = self.to_px4(mapper, receipt_monotonic_ns=10_650_000_000,
                             timestamp_sync_enabled=False,
                             px4_ros_clock_offset_us=0)
        self.assertEqual(result.sample_us, 1_300_000)
        self.assertAlmostEqual(result.sample_age_wall_s, .3499)
        delayed = self.to_px4(mapper, receipt_monotonic_ns=10_650_200_000,
                              timestamp_sync_enabled=False, px4_ros_clock_offset_us=0)
        self.assertGreater(delayed.sample_age_wall_s, result.sample_age_wall_s)

    def test_lockstep_interpolation_rejects_nonincreasing_receipt_times(self):
        for offset in (300_000_000, 290_000_000):
            with self.subTest(offset=offset):
                mapper = RosClockMapper(4, 8, .02, .1, 10., lockstep=True)
                for index, ns in enumerate((0, 150_000_000, 300_000_000,
                                            offset, 600_000_000)):
                    mapper.add_clock(1_000_000_000 + index * 100_000_000,
                                     10_000_000_000 + ns)
                with self.assertRaisesRegex(TimeMappingError, 'clock_receipt_not_increasing'):
                    self.to_px4(mapper, timestamp_sync_enabled=False,
                                px4_ros_clock_offset_us=0)


    def test_current_lockstep_timestamp_uses_clock_without_wall_rate_fit(self):
        mapper = RosClockMapper(4, 8, 0.02, 0.1, 10.0, lockstep=True)
        for index in range(5):
            mapper.add_clock(1_000_000_000 + index * 4_000_000,
                             10_000_000_000 + index * 50_000_000)

        with self.assertRaisesRegex(TimeMappingError, 'rate_out_of_bounds'):
            self.to_px4(mapper, source_ros_ns=1_016_000_000,
                        receipt_monotonic_ns=10_210_000_000,
                        estimated_offset_us=0, timesync_rtt_us=0,
                        timesync_receipt_monotonic_ns=0, timesync_age_s=None,
                        px4_ros_clock_offset_us=0, timestamp_sync_enabled=False)
        self.assertEqual(
            mapper.current_lockstep_px4_time_us(10_210_000_000), 1_016_000)

    def test_current_lockstep_timestamp_does_not_reject_by_wall_age_but_latches_rollback(self):
        mapper = self.mapper(lockstep=True)
        self.assertEqual(mapper.current_lockstep_px4_time_us(11_200_000_000),
                         1_400_000)
        with self.assertRaisesRegex(TimeMappingError, 'regression'):
            mapper.add_clock(1_200_000_000, 10_700_000_000)
        with self.assertRaisesRegex(TimeMappingError, 'regression'):
            mapper.current_lockstep_px4_time_us(10_700_000_000)

    def test_recovers_lockstep_time_from_shifted_timesync_status(self):
        age = px4_timesync_age_sim_s(
            ros_clock_ns=40_500_000_000,
            timesync_timestamp_us=1_000_000_000,
            estimated_offset_us=-960_000_000)
        self.assertAlmostEqual(age, 0.5)

    def test_recovers_lockstep_time_from_shifted_px4_telemetry_stamp(self):
        age = px4_clock_age_sim_s(
            ros_clock_ns=40_500_000_000,
            agent_timestamp_us=41_000_000,
            estimated_offset_us=-1_000_000)
        self.assertAlmostEqual(age, 0.5)

    def test_telemetry_age_uses_offset_from_message_receipt_after_timesync_reset(self):
        ros_clock_ns = 50_359_983_000
        agent_timestamp_us = 1_792_390_149_209_470
        offset_at_message_receipt_us = -1_792_390_099_745_470
        offset_after_timesync_reset_us = -1_792_390_103_981_570

        age_with_captured_offset = px4_clock_age_sim_s(
            ros_clock_ns, agent_timestamp_us, offset_at_message_receipt_us)
        age_recomputed_with_new_offset = px4_clock_age_sim_s(
            ros_clock_ns, agent_timestamp_us, offset_after_timesync_reset_us)

        self.assertAlmostEqual(age_with_captured_offset, 0.895983)
        self.assertAlmostEqual(age_recomputed_with_new_offset, 5.132083)

    def test_compares_ros_and_px4_stamps_in_lockstep_sim_time(self):
        gap = px4_ros_source_gap_sim_s(
            ros_stamp_ns=40_500_000_000,
            px4_agent_stamp_us=41_000_000,
            estimated_offset_us=-1_000_000)
        self.assertAlmostEqual(gap, 0.5)

    def test_requires_converged_clock_and_fresh_dds_timesync(self):
        with self.assertRaisesRegex(TimeMappingError, 'not_converged'):
            RosClockMapper(5, 64, 0.02, 0.1, 10.0).to_px4(
                1, 1, 1, 0, 0, 1, 0.5, 10_000, 0.03)
        mapper = self.mapper()
        with self.assertRaisesRegex(TimeMappingError, 'timesync_stale'):
            self.to_px4(mapper, timesync_receipt_monotonic_ns=9_000_000_000)
        with self.assertRaisesRegex(TimeMappingError, 'rtt_high'):
            self.to_px4(mapper, timesync_rtt_us=10_001)

    def test_maps_old_source_samples_without_receipt_age_cutoff(self):
        mapper = self.mapper(lockstep=True)
        self.assertEqual(self.to_px4(
            mapper, timestamp_sync_enabled=False,
            px4_ros_clock_offset_us=0).sample_us, 1_300_000)
        delayed = self.to_px4(
            mapper, receipt_monotonic_ns=11_200_000_000,
            timestamp_sync_enabled=False, px4_ros_clock_offset_us=0)
        self.assertEqual(delayed.sample_us, 1_300_000)

    def test_rejects_samples_outside_observed_clock_range(self):
        mapper = self.mapper()
        old_sample = self.to_px4(mapper, source_ros_ns=900_000_000)
        self.assertEqual(old_sample.sample_us, 49_500_000)
        with self.assertRaisesRegex(TimeMappingError, 'outside_clock_history'):
            self.to_px4(mapper, source_ros_ns=1_500_000_000)

    def test_debug_profile_history_covers_allowed_late_vio_sample(self):
        bridge = json.loads((ROOT / 'config/components/px4_bridge/debug_truth.json').read_text())
        max_samples = bridge['clock_mapping_max_samples']
        self.assertEqual(max_samples, 128)

        def make_mapper(sample_limit):
            mapper = RosClockMapper(
                min_samples=bridge['clock_mapping_min_samples'],
                max_samples=sample_limit,
                max_future_s=bridge['clock_mapping_max_future_wall_s'],
                min_rate=bridge['clock_mapping_min_sim_rate'],
                max_rate=bridge['clock_mapping_max_sim_rate'],
                lockstep=True)
            for index in range(160):
                mapper.add_clock(
                    100_000_000_000 + index * 4_000_000,
                    200_000_000_000 + round(index * 4_000_000 / 0.88))
            return mapper

        source_stamp_ns = 100_000_000_000 + (159 * 4_000_000) - 296_000_000
        receipt_monotonic_ns = 200_000_000_000 + round(159 * 4_000_000 / 0.88)
        short_history = make_mapper(64)
        late_in_short_history = short_history.to_px4(
            source_stamp_ns, receipt_monotonic_ns, 300_000_000_000,
            0, 0, 0, 0.5, 10_000, 0.03,
            px4_ros_clock_offset_us=0, timestamp_sync_enabled=False)
        self.assertEqual(late_in_short_history.sample_us, source_stamp_ns // 1000)

        mapper = make_mapper(max_samples)
        mapped = mapper.to_px4(
            source_stamp_ns, receipt_monotonic_ns, 300_000_000_000,
            0, 0, 0, 0.5, 10_000, 0.03,
            px4_ros_clock_offset_us=0, timestamp_sync_enabled=False)
        self.assertEqual(mapped.sample_us, source_stamp_ns // 1000)
        self.assertGreater(mapped.sample_age_wall_s, 0.2)
        older = mapper.to_px4(
            source_stamp_ns - 20_000_000, receipt_monotonic_ns,
            300_000_000_000, 0, 0, 0, 0.5, 10_000, 0.03,
            px4_ros_clock_offset_us=0, timestamp_sync_enabled=False)
        self.assertEqual(older.sample_us, (source_stamp_ns - 20_000_000) // 1000)

    def test_projects_sim_time_to_current_receipt_instant(self):
        mapper = self.mapper()
        now_ros_ns = mapper.ros_time_at_monotonic(10_750_000_000, 0.03)
        self.assertEqual(now_ros_ns, 1_500_000_000)
        # A PX4 sample can be newer than the last delivered /clock callback
        # while still being older than current simulation time.
        age = px4_clock_age_sim_s(now_ros_ns, 1_480_000, 0)
        latest_clock_age = px4_clock_age_sim_s(1_400_000_000, 1_480_000, 0)
        self.assertAlmostEqual(age, 0.02)
        self.assertAlmostEqual(latest_clock_age, -0.08)

    def test_current_sim_time_projection_does_not_reject_by_receipt_age(self):
        mapper = self.mapper()
        self.assertEqual(mapper.ros_time_at_monotonic(11_200_000_000, 0.03),
                         1_800_000_000)
        with self.assertRaisesRegex(TimeMappingError, 'clock_receipt_in_future'):
            mapper.ros_time_at_monotonic(10_500_000_000, 0.03)

    def test_lockstep_uses_observed_clock_when_wall_fit_residual_is_high(self):
        settings = dict(min_samples=4, max_samples=8,
                        max_future_s=0.02,
                        min_rate=0.1, max_rate=10.0)
        samples = (
            (1_000_000_000, 10_000_000_000),
            (1_100_000_000, 10_150_000_000),
            (1_200_000_000, 10_360_000_000),
            (1_300_000_000, 10_450_000_000),
            (1_400_000_000, 10_660_000_000),
        )
        strict_mapper = RosClockMapper(**settings)
        lockstep_mapper = RosClockMapper(**settings, lockstep=True)
        for ros_ns, monotonic_ns in samples:
            strict_mapper.add_clock(ros_ns, monotonic_ns)
            lockstep_mapper.add_clock(ros_ns, monotonic_ns)

        residual_s = lockstep_mapper._fit()[3] / 1e9
        self.assertGreater(residual_s, 0.03)
        with self.assertRaisesRegex(TimeMappingError, 'residual_high'):
            self.to_px4(strict_mapper)

        result = self.to_px4(lockstep_mapper)
        self.assertEqual(result.sample_us, 49_900_000)
        self.assertAlmostEqual(result.sample_age_wall_s, 0.25)
        # The most recently received /clock stamp is authoritative in
        # lockstep; a wall-time fit must not extrapolate it.
        self.assertEqual(
            lockstep_mapper.ros_time_at_monotonic(10_750_000_000, 0.03),
            1_400_000_000)
        self.assertEqual(lockstep_mapper.ros_time_at_monotonic(
            11_200_000_000, 0.03), 1_400_000_000)

    def test_clock_rollback_latches_mapper(self):
        mapper = self.mapper()
        with self.assertRaisesRegex(TimeMappingError, 'regression'):
            mapper.add_clock(1_200_000_000, 10_700_000_000)
        self.assertTrue(mapper.locked)
        with self.assertRaisesRegex(TimeMappingError, 'regression'):
            self.to_px4(mapper)

    def test_rejects_clock_rate_outside_configured_bounds(self):
        mapper = RosClockMapper(4, 64, 0.02, 0.8, 1.2)
        for index in range(5):
            mapper.add_clock(1_000_000_000 + index * 100_000_000,
                             10_000_000_000 + index * 150_000_000)
        with self.assertRaisesRegex(TimeMappingError, 'rate_out_of_bounds'):
            self.to_px4(mapper)


if __name__ == '__main__':
    unittest.main()
