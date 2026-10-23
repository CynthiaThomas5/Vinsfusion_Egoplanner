from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/debug_truth'))

from evaluate_health_timing import (associate_telemetry, latest_input_stamps,
                                     normalized_cost)


class HealthTimingAnalysisTest(unittest.TestCase):
    def test_normalized_cost_matches_adapter_formula(self):
        self.assertAlmostEqual(
            normalized_cost({'final_cost': 954.2694015367708,
                             'residual_components': 4661}),
            0.6398982841078671,
        )
        self.assertIsNone(normalized_cost({'final_cost': 1.0,
                                           'residual_components': 0}))

    def test_association_uses_latest_telemetry_received_before_status(self):
        telemetry = [
            {'source_stamp_ns': 1, 'receive_monotonic_ns': 100},
            {'source_stamp_ns': 2, 'receive_monotonic_ns': 200},
        ]
        status = {'receive_monotonic_ns': 250}
        sample, method = associate_telemetry(status, telemetry)
        self.assertEqual(sample['source_stamp_ns'], 2)
        self.assertEqual(method, 'last_telemetry_received_before_status')

    def test_association_prefers_explicit_status_callback_context(self):
        telemetry = [
            {'source_stamp_ns': 1, 'receive_monotonic_ns': 100},
            {'source_stamp_ns': 2, 'receive_monotonic_ns': 200},
        ]
        status = {
            'receive_monotonic_ns': 250,
            'latest_telemetry_at_callback': {
                'source_stamp_ns': 1,
                'receive_monotonic_ns': 100,
            },
        }
        sample, method = associate_telemetry(status, telemetry)
        self.assertEqual(sample['source_stamp_ns'], 1)
        self.assertEqual(method, 'status_callback_context')

    def test_missing_preceding_or_context_telemetry_is_explicit(self):
        sample, method = associate_telemetry({'receive_monotonic_ns': 10}, [
            {'source_stamp_ns': 1, 'receive_monotonic_ns': 20},
        ])
        self.assertIsNone(sample)
        self.assertEqual(method, 'unmatched')

    def test_latest_input_stamps_accepts_compact_and_legacy_event_shapes(self):
        compact = {'latest_input_stamps': {'/camera/image': {'source_stamp_ns': 20}}}
        legacy = {'recent_input_stamps': {'/camera/image': [
            {'source_stamp_ns': 10}, {'source_stamp_ns': 20}]}}
        self.assertEqual(latest_input_stamps(compact), {
            '/camera/image': {'source_stamp_ns': 20}})
        self.assertEqual(latest_input_stamps(legacy), {
            '/camera/image': {'source_stamp_ns': 20}})


if __name__ == '__main__':
    unittest.main()
