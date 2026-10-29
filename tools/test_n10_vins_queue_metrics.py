#!/usr/bin/env python3
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from n10_vins_queue_metrics import summarize_queue_samples


def sample(epoch, stamp, acc, gyr, feature):
    return {
        'epoch': epoch,
        'source_stamp_ns': stamp,
        'queue_metrics': {
            'scope': 'estimator_process_lifetime',
            'acc_current_before_feature_dequeue': acc[0],
            'acc_high_water': acc[1],
            'gyr_current_before_feature_dequeue': gyr[0],
            'gyr_high_water': gyr[1],
            'feature_current_before_feature_dequeue': feature[0],
            'feature_high_water': feature[1],
        },
    }


class N10VinsQueueMetricsTest(unittest.TestCase):
    def test_reports_observed_maxima_without_turning_them_into_limits(self):
        report = summarize_queue_samples([
            sample('e1', 10, (20, 22), (20, 22), (1, 2)),
            sample('e1', 20, (19, 24), (19, 24), (0, 3)),
        ])
        self.assertEqual(report['status'], 'OBSERVED')
        self.assertEqual(report['aggregate_queues']['acc']['max_reported_high_water'], 24)
        self.assertEqual(report['aggregate_queues']['feature']['max_current_before_feature_dequeue'], 1)
        self.assertFalse(report['queue_capacity_or_runtime_limit_inferred'])

    def test_missing_or_malformed_rows_are_insufficient_not_zero(self):
        report = summarize_queue_samples([{'epoch': 'e1'}])
        self.assertEqual(report['status'], 'INSUFFICIENT')
        self.assertIsNone(report['aggregate_queues']['acc']['max_reported_high_water'])
        self.assertIn('sample_0_missing_queue_metrics', report['errors'])

    def test_decreasing_process_lifetime_high_water_is_reported(self):
        rows = [sample('e1', 10, (2, 8), (2, 8), (0, 1)),
                sample('e1', 20, (2, 7), (2, 8), (0, 1))]
        report = summarize_queue_samples(rows)
        self.assertEqual(report['status'], 'INSUFFICIENT')
        self.assertIn('epoch_e1_acc_high_water_decreased', report['errors'])

    def test_epochs_are_kept_separate(self):
        report = summarize_queue_samples([
            sample('e1', 10, (1, 3), (1, 3), (0, 1)),
            sample('e2', 20, (1, 2), (1, 2), (0, 1)),
        ])
        self.assertEqual(set(report['epochs']), {'e1', 'e2'})
        self.assertEqual(report['aggregate_queues']['acc']['max_reported_high_water'], 3)


if __name__ == '__main__':
    unittest.main()
