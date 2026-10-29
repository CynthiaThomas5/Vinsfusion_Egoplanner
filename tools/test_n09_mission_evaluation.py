"""Freshness evidence must use the recorder's real schema and retain limits."""
import unittest
from evaluate_n09_mission import localization_receipt_freshness


class N09FreshnessEvidenceTests(unittest.TestCase):
    @staticmethod
    def timeline(status=.15, odom=.25):
        return {'stream_summary': {
            'localization_status': {'max_receipt_gap_wall_s': status},
            'adapter_optimized': {'max_receipt_gap_wall_s': odom},
        }}

    def test_recorder_stream_summary_schema(self):
        report = localization_receipt_freshness(self.timeline())
        self.assertTrue(report['passed'])
        self.assertEqual(report['max_optimized_odometry_receipt_gap_wall_s'], .25)

    def test_absent_or_wrong_schema_fails(self):
        self.assertFalse(localization_receipt_freshness({})['passed'])
        self.assertFalse(localization_receipt_freshness({'streams': self.timeline()['stream_summary']})['passed'])

    def test_stale_negative_nan_and_missing_receipts_fail(self):
        for status, odom in [(.501,.25), (.15,.301), (-.1,.25), (.15,float('nan')), (None,.25)]:
            self.assertFalse(localization_receipt_freshness(self.timeline(status,odom))['passed'])
