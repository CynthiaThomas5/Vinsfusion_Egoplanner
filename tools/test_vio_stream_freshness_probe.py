import io
import json
from collections import deque
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest

from probe_vio_stream_freshness import (
    StreamProbe,
    _observation_stop_state,
    _spin_timeout,
)


class ObservationStopStateTest(unittest.TestCase):
    def test_end_marker_starts_bounded_tail_then_stops(self):
        with tempfile.TemporaryDirectory() as temporary:
            marker = Path(temporary) / 'fixture-result.json'
            marker_seen, reason = _observation_stop_state(
                10.0, 100.0, marker, None, 2.0)
            self.assertIsNone(marker_seen)
            self.assertIsNone(reason)

            marker.touch()
            marker_seen, reason = _observation_stop_state(
                11.0, 100.0, marker, marker_seen, 2.0)
            self.assertEqual(marker_seen, 11.0)
            self.assertIsNone(reason)

            marker_seen, reason = _observation_stop_state(
                12.99, 100.0, marker, marker_seen, 2.0)
            self.assertIsNone(reason)
            marker_seen, reason = _observation_stop_state(
                13.0, 100.0, marker, marker_seen, 2.0)
            self.assertEqual(reason, 'end_marker_tail_complete')

    def test_hard_deadline_reports_missing_marker(self):
        with tempfile.TemporaryDirectory() as temporary:
            marker = Path(temporary) / 'fixture-result.json'
            seen, reason = _observation_stop_state(
                5.0, 5.0, marker, None, 2.0)
        self.assertIsNone(seen)
        self.assertEqual(reason, 'max_duration_end_marker_missing')

    def test_fixed_duration_mode_keeps_existing_stop_reason(self):
        seen, reason = _observation_stop_state(5.0, 5.0, None, None, 2.0)
        self.assertIsNone(seen)
        self.assertEqual(reason, 'max_duration')

    def test_spin_timeout_respects_marker_tail_and_hard_deadline(self):
        self.assertAlmostEqual(_spin_timeout(10.0, 100.0, 9.99, 2.0), 0.02)
        self.assertAlmostEqual(_spin_timeout(10.0, 100.0, 9.99, 0.015), 0.005)
        self.assertAlmostEqual(_spin_timeout(10.0, 100.0, 9.999, 0.002), 0.001)
        self.assertEqual(_spin_timeout(5.0, 5.0, None, 2.0), 0.0)


class EventRecordTest(unittest.TestCase):
    def test_telemetry_event_carries_compact_latest_sensor_stamps(self):
        probe = StreamProbe.__new__(StreamProbe)
        probe.started = time.monotonic()
        probe.clock_ns = 10_000_000_000
        probe.stats = {}
        probe.recent_sources = {}
        probe.event_topics = {'/vins/estimator_telemetry'}
        probe.events = io.StringIO()
        probe.event_count = 0

        image_topic = '/sensors/d435i/infra1/image_rect'
        imu_topic = '/sensors/d435i/imu'
        probe.record(image_topic, 9_980_000_000, {'frame_id': 'infra1'})
        probe.record(imu_topic, 9_990_000_000, {'frame_id': 'imu'})
        telemetry = {
            'stamp_ns': 10_000_000_000,
            'input_features': 180,
            'final_cost': 600.0,
            'residual_components': 1100,
            'cost_components': {'visual': 280.0, 'imu': 2.0},
        }
        probe.record('/vins/estimator_telemetry', 10_000_000_000,
                     {'telemetry': telemetry})

        event = json.loads(probe.events.getvalue().splitlines()[0])
        self.assertEqual(event['source_stamp_ns'], 10_000_000_000)
        self.assertEqual(event['telemetry']['cost_components']['visual'], 280.0)
        self.assertEqual(event['clock_stamp_ns_at_receipt'], 10_000_000_000)
        self.assertEqual(
            event['latest_input_stamps'][image_topic]['source_stamp_ns'],
            9_980_000_000)
        self.assertEqual(
            event['latest_input_stamps'][imu_topic]['source_stamp_ns'],
            9_990_000_000)
        self.assertIn('receive_monotonic_ns',
                      event['latest_input_stamps'][image_topic])
        self.assertNotIsInstance(event['latest_input_stamps'][image_topic], list)
        self.assertEqual(probe.event_count, 1)

    def test_status_event_separates_header_propagated_and_health_telemetry_stamps(self):
        probe = StreamProbe.__new__(StreamProbe)
        probe.started = time.monotonic()
        probe.clock_ns = 20_050_000_000
        probe.stats = {}
        probe.recent_sources = {
            '/vins/estimator_telemetry': deque([{
                'source_stamp_ns': 20_000_000_000,
                'receive_monotonic_ns': 123456789,
                'clock_stamp_ns_at_receipt': 20_004_000_000,
            }], maxlen=16)
        }
        probe.telemetry_topic = '/vins/estimator_telemetry'
        probe.event_topics = {'/localization/status'}
        probe.events = io.StringIO()
        probe.event_count = 0
        probe.transitions = []
        probe.last_localization = None
        msg = SimpleNamespace(
            header=SimpleNamespace(stamp=SimpleNamespace(sec=20, nanosec=50_000_000)),
            source_stamp=SimpleNamespace(sec=20, nanosec=48_000_000),
            epoch='e' * 32,
            state=1,
            valid=True,
            reason='fresh_inputs_and_usable_solver',
            good_pairs=500,
            normalized_cost=0.64,
            accepted_optimized=100,
            accepted_propagated=20000,
        )

        probe.on_localization('/localization/status', msg)

        event = json.loads(probe.events.getvalue().splitlines()[0])
        self.assertEqual(event['source_stamp_ns'], 20_050_000_000)
        self.assertEqual(event['status_header_stamp_ns'], 20_050_000_000)
        self.assertEqual(event['propagated_source_stamp_ns'], 20_048_000_000)
        self.assertEqual(
            event['latest_telemetry_at_callback']['source_stamp_ns'],
            20_000_000_000)
        self.assertEqual(event['normalized_cost'], 0.64)


if __name__ == '__main__':
    unittest.main()
