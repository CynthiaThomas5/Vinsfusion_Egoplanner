import json
from pathlib import Path
import tempfile
import unittest

from tools.debug_truth.evaluate_n10_sensor_capture import (
    assess_capture,
    assess_zero_flight_capture,
    resolve_capture_identity,
)
from tools.diagnostics.record_n10_sensor_streams import (
    load_capture_inputs,
    rosbag_command,
)
from tools.n10_run_identity import read_run_identity


ROOT = Path(__file__).resolve().parents[1]


class N10SensorCaptureTests(unittest.TestCase):
    def _identity(self):
        return {
            "run_id": "run-1", "runtime_contract_sha256": "contract-1",
            "goal_id": "goal-1", "epoch": "epoch-1", "map_id": "epoch-1-map-1",
            "frame_id": "odom_epoch-1", "complete": True, "missing_fields": [],
            "conflicts": [],
        }

    def _fixture(self):
        topics = {
            "stereo_left_image": "/cam/left", "stereo_right_image": "/cam/right",
            "camera_imu": "/cam/imu",
        }
        identity = self._identity()
        rows = []
        bag = []
        for stream, topic, frame, count in (
            ("stereo_left_image", topics["stereo_left_image"], "left_optical", 2),
            ("stereo_right_image", topics["stereo_right_image"], "right_optical", 2),
            ("camera_imu", topics["camera_imu"], "imu_link", 4),
        ):
            for i in range(count):
                stamp = 1_000_000_000 + i * 10_000_000
                rows.append({"stream": stream, "topic": topic,
                             "source_stamp_ns": stamp, "frame_id": frame,
                             "identity": identity})
                bag.append({"topic": topic, "source_stamp_ns": stamp,
                            "frame_id": frame})
        capture = {
            "schema": "n10-sensor-capture/v1", "metadata_write_ok": True,
            "bag_exit_code": 0, "run_identity": identity,
            "capture_window": {"safe_session_terminal_observed": True,
                               "stop_reason": "safe_terminal_plus_closeout"},
            "topics": topics,
            "stream_counts": {"stereo_left_image": 2,
                              "stereo_right_image": 2, "camera_imu": 4},
        }
        return capture, rows, bag, topics, identity

    def test_topics_are_resolved_from_the_single_vins_configuration(self):
        config, config_path, sensor_path, topics = load_capture_inputs(
            ROOT, "config/n10_capture.json")
        self.assertEqual(config["schema"], "uav-n10-capture/v1")
        self.assertEqual(sensor_path.relative_to(ROOT).as_posix(),
                         config["sensor_config"])
        self.assertEqual(topics, {
            "stereo_left_image": "/sensors/d435i/infra1/image_rect",
            "stereo_right_image": "/sensors/d435i/infra2/image_rect",
            "camera_imu": "/sensors/d435i/imu",
        })
        self.assertEqual(config["receipt_observer"]["sensor_subscription_depth"], 100)
        self.assertFalse(config["receipt_observer"]["runtime_effect"])
        self.assertEqual(config_path, ROOT / "config/n10_capture.json")

    def test_rosbag_command_is_lossless_compressed_and_read_only(self):
        _, _, _, topics = load_capture_inputs(ROOT, "config/n10_capture.json")
        command = rosbag_command(ROOT, ROOT / "run/bag", topics,
                                 self._identity(), "capture-config-hash")
        self.assertIn("mcap", command)
        self.assertIn("zstd_fast", command)
        self.assertIn("--use-sim-time", command)
        self.assertIn("--max-cache-size", command)
        self.assertIn("104857600", command)
        self.assertNotIn("--all", command)
        self.assertIn("run_id=run-1", command)
        self.assertIn("runtime_contract_sha256=contract-1", command)
        self.assertIn("capture_config_sha256=capture-config-hash", command)

    def test_identity_binds_runtime_goal_epoch_and_map_or_reports_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run = root / "run-1"
            run.mkdir()
            stack = root / "run-1-stack/session"
            stack.mkdir(parents=True)
            (run / "runtime-contract.json").write_text(json.dumps({"sha256": "contract-1"}))
            (run / "n10-run-manifest.json").write_text(json.dumps({
                "run_id": "run-1", "runtime_contract_sha256": "contract-1"}))
            (stack / "session.json").write_text(json.dumps({"epoch": "epoch-1"}))
            (run / "flight.json").write_text(json.dumps({"goal_id": "goal-1"}))
            (run / "n10-map-point-queries.json").write_text(json.dumps({
                "identity": {"epoch": "epoch-1", "map_id": "epoch-1-map-1",
                             "frame_id": "odom_epoch-1"}}))
            identity = read_run_identity(run)
            self.assertTrue(identity["complete"])
            self.assertEqual(identity["goal_id"], "goal-1")
            self.assertEqual(identity["map_id"], "epoch-1-map-1")
            (run / "n10-map-point-queries.json").unlink()
            incomplete = read_run_identity(run)
            self.assertFalse(incomplete["complete"])
            self.assertIn("map_id", incomplete["missing_fields"])

    def test_capture_launch_manifest_binds_runtime_before_a_goal_exists(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run = root / "run-1"
            run.mkdir()
            (run / "runtime-contract.json").write_text(json.dumps({"sha256": "contract-1"}))
            (run / "n10-capture-launch-manifest.json").write_text(json.dumps({
                "run_id": "run-1", "runtime_contract_sha256": "contract-1",
                "n10_capture": {"enabled": True},
            }))
            identity = read_run_identity(run)
            self.assertEqual(identity["run_id"], "run-1")
            self.assertEqual(identity["runtime_contract_sha256"], "contract-1")
            self.assertFalse(identity["complete"])
            self.assertIn("goal_id", identity["missing_fields"])
            self.assertIn("epoch", identity["missing_fields"])
            self.assertIn("map_id", identity["missing_fields"])

    def test_active_capture_uses_complete_end_identity_when_goal_begins_later(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / "run-1"
            run.mkdir()
            (run / "runtime-contract.json").write_text(json.dumps({
                "sha256": "contract-1"}))
            (run / "n10-capture-launch-manifest.json").write_text(json.dumps({
                "run_id": "run-1", "runtime_contract_sha256": "contract-1"}))
            (run / "flight.json").write_text(json.dumps({
                "goal_id": "goal-1", "localization_epoch": "epoch-1"}))

            capture, receipts, bag, topics, expected = self._fixture()
            capture["run_identity"] = {
                "run_id": "run-1", "runtime_contract_sha256": "contract-1",
                "goal_id": "", "epoch": "", "map_id": "", "complete": False,
            }
            capture["run_identity_at_end"] = {
                **expected,
                "declared_runtime_contract_sha256": "contract-1",
                "complete": True, "missing_fields": [], "conflicts": [],
            }

            identity, source, errors = resolve_capture_identity(run, capture)
            self.assertTrue(identity["complete"])
            self.assertEqual(identity["map_id"], "epoch-1-map-1")
            self.assertEqual(source,
                             "capture_end_live_snapshot_cross_checked_with_run_files")
            self.assertEqual(errors, [])
            result = assess_capture(capture, receipts, bag, topics, identity)
            self.assertEqual(result["status"], "PASS")

    def test_end_identity_conflicting_with_flight_record_stays_insufficient(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / "run-1"
            run.mkdir()
            (run / "runtime-contract.json").write_text(json.dumps({
                "sha256": "contract-1"}))
            (run / "n10-capture-launch-manifest.json").write_text(json.dumps({
                "run_id": "run-1", "runtime_contract_sha256": "contract-1"}))
            (run / "flight.json").write_text(json.dumps({
                "goal_id": "goal-1", "localization_epoch": "epoch-1"}))
            capture, _, _, _, expected = self._fixture()
            capture["run_identity_at_end"] = {
                **expected, "goal_id": "other-goal",
                "complete": True, "missing_fields": [], "conflicts": [],
            }

            identity, source, errors = resolve_capture_identity(run, capture)
            self.assertFalse(identity["complete"])
            self.assertEqual(source,
                             "run_files_with_conflicting_capture_end_identity")
            self.assertIn(
                "capture_end_identity_conflicts_with_run_files:goal_id", errors)

    def test_complete_capture_matches_each_payload_message_by_source_key(self):
        capture, receipts, bag, topics, identity = self._fixture()
        result = assess_capture(capture, receipts, bag, topics, identity)
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["runtime_control_effect"])
        self.assertTrue(all(row["keys_match"]
                            for row in result["receipt_to_payload"].values()))
        self.assertTrue(result["stream_timing"]["camera_imu"]["source_stamp_monotonic"])

    def test_missing_payload_or_identity_is_insufficient_not_a_runtime_action(self):
        capture, receipts, bag, topics, identity = self._fixture()
        incomplete_bag = bag.copy()
        incomplete_bag.remove(bag[6])
        result = assess_capture(capture, receipts, incomplete_bag, topics, identity)
        self.assertEqual(result["status"], "INSUFFICIENT")
        self.assertIn("compressed_payload_message_missing_receipt_metadata",
                      result["errors"])
        self.assertFalse(result["runtime_control_effect"])
        capture, receipts, bag, topics, identity = self._fixture()
        receipts[0]["identity"] = {**identity, "map_id": "other-epoch-map"}
        result = assess_capture(capture, receipts, bag, topics, identity)
        self.assertEqual(result["status"], "INSUFFICIENT")
        self.assertIn("active_sensor_receipts_span_multiple_identity_epochs_or_maps",
                      result["errors"])

    def test_receipt_boundary_outside_bag_window_is_reported_without_hiding_payload_gaps(self):
        capture, receipts, bag, topics, identity = self._fixture()
        receipts.append({"stream": "camera_imu", "topic": topics["camera_imu"],
                         "source_stamp_ns": 500_000_000, "frame_id": "imu_link",
                         "receipt_monotonic_ns": 1, "identity": identity})
        capture["stream_counts"]["camera_imu"] += 1
        result = assess_capture(capture, receipts, bag, topics, identity)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["receipt_to_payload"][topics["camera_imu"]][
            "receipt_without_payload_boundary_count"], 1)
        self.assertEqual(result["receipt_to_payload"][topics["camera_imu"]][
            "payload_without_receipt_count"], 0)

    def test_capture_report_close_errors_remain_insufficient(self):
        capture, receipts, bag, topics, identity = self._fixture()
        capture["errors"] = ["bag_close:TimeoutExpired"]
        result = assess_capture(capture, receipts, bag, topics, identity)
        self.assertEqual(result["status"], "INSUFFICIENT")
        self.assertIn("capture_report_has_errors", result["errors"])

    def test_zero_flight_smoke_can_pass_payload_integrity_without_a_goal(self):
        capture, receipts, bag, topics, identity = self._fixture()
        zero_identity = {**identity, "goal_id": "", "complete": False}
        capture["run_identity_at_end"] = zero_identity
        capture["capture_window"] = {
            "safe_session_terminal_observed": False,
            "stop_reason": "wall_timeout",
        }
        for row in receipts:
            row["identity"] = zero_identity
        result = assess_zero_flight_capture(
            capture, receipts, bag, topics, zero_identity,
            flight_record_present=False)
        self.assertEqual(result["status"], "PASS")
        self.assertIn("zero-flight", result["classification"])
        self.assertFalse(result["runtime_control_effect"])

    def test_zero_flight_rejects_incomplete_stream_counts_and_mixed_identity(self):
        capture, receipts, bag, topics, identity = self._fixture()
        zero_identity = {**identity, "goal_id": "", "complete": False}
        capture["run_identity_at_end"] = zero_identity
        capture["stream_counts"]["camera_imu"] -= 1
        receipts[0]["identity"] = {**zero_identity, "map_id": "other-epoch-map"}
        result = assess_zero_flight_capture(
            capture, receipts, bag, topics, zero_identity,
            flight_record_present=False)
        self.assertEqual(result["status"], "INSUFFICIENT")
        self.assertIn("stream_count_missing_or_mismatched:camera_imu", result["errors"])
        self.assertIn("zero_flight_receipts_span_missing_or_multiple_identities",
                      result["errors"])


if __name__ == "__main__":
    unittest.main()
