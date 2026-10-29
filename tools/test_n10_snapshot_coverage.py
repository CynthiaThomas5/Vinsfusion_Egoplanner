import unittest

from tools.n10_snapshot_coverage import (
    assess_snapshot_source_coverage,
    latest_roi_cloud_watermark,
)


class N10SnapshotCoverageTests(unittest.TestCase):
    def test_watermark_uses_latest_positive_roi_source_stamp(self):
        rows = [
            {"header_stamp_ns": 100, "receipt_sim_ns": 110,
             "frame_id": "odom-a", "obstacle_roi_point_count": 0},
            {"header_stamp_ns": 300, "receipt_sim_ns": 305,
             "frame_id": "odom-a", "obstacle_roi_point_count": 4},
            {"header_stamp_ns": 250, "receipt_sim_ns": 310,
             "frame_id": "odom-a", "obstacle_roi_point_count": 2},
        ]
        watermark = latest_roi_cloud_watermark(rows)
        self.assertEqual(watermark["header_stamp_ns"], 300)
        self.assertEqual(watermark["row_index"], 1)
        self.assertEqual(watermark["frame_id"], "odom-a")

    def test_equal_source_stamp_covers_and_frame_must_match(self):
        watermark = {"header_stamp_ns": 300, "frame_id": "odom-a"}
        covered = assess_snapshot_source_coverage(
            300, watermark, "odom-a", attempt_count=1, max_attempts=5)
        self.assertEqual(covered["status"], "covered")
        self.assertTrue(covered["covered"])
        self.assertFalse(covered["should_retry"])
        mismatch = assess_snapshot_source_coverage(
            301, watermark, "odom-b", attempt_count=1, max_attempts=5)
        self.assertEqual(mismatch["status"], "frame_mismatch")
        self.assertFalse(mismatch["should_retry"])

    def test_lagging_source_is_retried_then_stays_insufficient(self):
        watermark = {"header_stamp_ns": 300, "frame_id": "odom-a"}
        waiting = assess_snapshot_source_coverage(
            299, watermark, "odom-a", attempt_count=2, max_attempts=5)
        self.assertEqual(waiting["status"], "waiting_for_fusion")
        self.assertTrue(waiting["should_retry"])
        exhausted = assess_snapshot_source_coverage(
            299, watermark, "odom-a", attempt_count=5, max_attempts=5)
        self.assertEqual(exhausted["status"], "insufficient_after_retry_limit")
        self.assertFalse(exhausted["covered"])
        self.assertFalse(exhausted["should_retry"])

    def test_missing_obstacle_cloud_never_claims_coverage(self):
        self.assertIsNone(latest_roi_cloud_watermark([
            {"header_stamp_ns": 100, "obstacle_roi_point_count": 0},
            {"header_stamp_ns": "bad", "obstacle_roi_point_count": 2},
        ]))
        result = assess_snapshot_source_coverage(500, None)
        self.assertEqual(result["status"], "no_roi_cloud_observed")
        self.assertIsNone(result["covered"])
        self.assertFalse(result["should_retry"])


if __name__ == "__main__":
    unittest.main()
