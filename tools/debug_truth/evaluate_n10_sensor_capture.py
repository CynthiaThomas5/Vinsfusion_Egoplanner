#!/usr/bin/env python3
"""Offline coverage and identity checks for the N10 sensor payload recorder."""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from n10_run_identity import read_run_identity, sha256_file


REQUIRED_STREAMS = ("stereo_left_image", "stereo_right_image", "camera_imu")
IDENTITY_FIELDS = (
    "run_id", "runtime_contract_sha256", "declared_runtime_contract_sha256",
    "goal_id", "epoch", "map_id", "frame_id",
)


def message_key(topic, source_stamp_ns, frame_id):
    return str(topic), int(source_stamp_ns), str(frame_id)


def compare_receipts_to_bag(receipt_rows, bag_rows, topics):
    """Compare every receipt metadata key with deserialized MCAP message keys."""
    receipt = Counter(message_key(row["topic"], row["source_stamp_ns"], row["frame_id"])
                      for row in receipt_rows)
    bag = Counter(message_key(row["topic"], row["source_stamp_ns"], row["frame_id"])
                  for row in bag_rows)
    per_topic = {}
    for topic in topics.values():
        expected = sum(count for (name, _, _), count in receipt.items() if name == topic)
        observed = sum(count for (name, _, _), count in bag.items() if name == topic)
        receipt_topic = Counter({key: count for key, count in receipt.items()
                                 if key[0] == topic})
        bag_topic = Counter({key: count for key, count in bag.items()
                             if key[0] == topic})
        payload_without_receipt = sum((bag_topic - receipt_topic).values())
        receipt_without_payload = receipt_topic - bag_topic
        bag_stamps = [key[1] for key in bag_topic]
        if bag_stamps:
            minimum_stamp, maximum_stamp = min(bag_stamps), max(bag_stamps)
            boundary_receipts = sum(
                count for key, count in receipt_without_payload.items()
                if key[1] < minimum_stamp or key[1] > maximum_stamp)
            interior_receipts = sum(
                count for key, count in receipt_without_payload.items()
                if minimum_stamp <= key[1] <= maximum_stamp)
        else:
            boundary_receipts = 0
            interior_receipts = sum(receipt_without_payload.values())
        mismatch = payload_without_receipt + interior_receipts
        per_topic[topic] = {
            "receipt_count": expected,
            "bag_count": observed,
            "receipt_bag_key_mismatch_count": mismatch,
            "payload_without_receipt_count": payload_without_receipt,
            "receipt_without_payload_boundary_count": boundary_receipts,
            "receipt_without_payload_interior_count": interior_receipts,
            "keys_match": observed > 0 and payload_without_receipt == 0
            and interior_receipts == 0,
        }
    return per_topic


def summarize_stream_timing(receipt_rows, topics):
    report = {}
    for stream, topic in topics.items():
        rows = [row for row in receipt_rows if row.get("topic") == topic]
        source = [int(row["source_stamp_ns"]) for row in rows
                  if row.get("source_stamp_ns") is not None]
        receipt = [int(row["receipt_monotonic_ns"]) for row in rows
                   if row.get("receipt_monotonic_ns") is not None]
        source_gaps = [(right - left) / 1e9 for left, right in zip(source, source[1:])]
        receipt_gaps = [(right - left) / 1e9 for left, right in zip(receipt, receipt[1:])]
        source_sorted = sorted(source_gaps)
        receipt_sorted = sorted(receipt_gaps)
        percentile = lambda values, q: (
            values[min(len(values) - 1, int(q * len(values)))] if values else None)
        report[stream] = {
            "message_count": len(rows),
            "source_stamp_monotonic": all(b > a for a, b in zip(source, source[1:])),
            "receipt_monotonic": all(b > a for a, b in zip(receipt, receipt[1:])),
            "source_gap_max_s": max(source_gaps) if source_gaps else None,
            "source_gap_p99_s": percentile(source_sorted, 0.99),
            "receipt_gap_max_s": max(receipt_gaps) if receipt_gaps else None,
            "receipt_gap_p99_s": percentile(receipt_sorted, 0.99),
        }
    return report


def resolve_capture_identity(run_dir, capture):
    """Resolve active-run identity from the final live snapshot when available.

    The recorder starts before a goal exists, so its initial identity can be
    incomplete. Its final MapStatus/goal snapshot is cross-checked against all
    fields recoverable from the run files before it is used for receipt checks.
    """
    identity = read_run_identity(run_dir)
    end_identity = capture.get("run_identity_at_end")
    if not isinstance(end_identity, dict) or end_identity.get("complete") is not True:
        return identity, "run_files", []

    errors = []
    required_fields = (
        "run_id", "runtime_contract_sha256", "goal_id", "epoch", "map_id",
    )
    for field in required_fields:
        if not end_identity.get(field):
            errors.append(f"capture_end_identity_missing:{field}")
    if end_identity.get("missing_fields"):
        errors.append("capture_end_identity_reports_missing_fields")
    if end_identity.get("conflicts"):
        errors.append("capture_end_identity_reports_conflicts")

    for field in IDENTITY_FIELDS:
        recorded = end_identity.get(field)
        recovered = identity.get(field)
        if recorded and recovered and recorded != recovered:
            errors.append(f"capture_end_identity_conflicts_with_run_files:{field}")

    if errors:
        identity = dict(identity)
        identity["complete"] = False
        identity["conflicts"] = sorted(set(identity.get("conflicts", []) + errors))
        return identity, "run_files_with_conflicting_capture_end_identity", errors

    resolved = read_run_identity(
        run_dir,
        goal_id=end_identity.get("goal_id"),
        epoch=end_identity.get("epoch"),
        map_id=end_identity.get("map_id"),
        frame_id=end_identity.get("frame_id"),
    )
    if not resolved.get("complete"):
        errors.append("resolved_capture_end_identity_incomplete")
        return resolved, "capture_end_live_snapshot_incomplete", errors
    return resolved, "capture_end_live_snapshot_cross_checked_with_run_files", []


def assess_capture(capture, receipt_rows, bag_rows, topics, identity):
    errors = []
    if capture.get("schema") != "n10-sensor-capture/v1":
        errors.append("unsupported_or_missing_capture_report")
    if capture.get("metadata_write_ok") is not True:
        errors.append("receipt_metadata_write_incomplete")
    if capture.get("bag_exit_code") != 0:
        errors.append("bag_close_not_clean")
    if capture.get("errors"):
        errors.append("capture_report_has_errors")
    if capture.get("capture_window", {}).get("safe_session_terminal_observed") is not True:
        errors.append("safe_session_terminal_not_observed")
    if capture.get("capture_window", {}).get("stop_reason") != "safe_terminal_plus_closeout":
        errors.append("capture_did_not_reach_terminal_closeout_window")
    if capture.get("run_identity", {}).get("runtime_contract_sha256") != identity.get(
            "runtime_contract_sha256"):
        errors.append("runtime_contract_identity_mismatch")
    if not identity.get("complete"):
        errors.append("run_identity_incomplete")
    if set(capture.get("topics", {}).values()) != set(topics.values()):
        errors.append("resolved_topic_set_mismatch")

    active_rows = [row for row in receipt_rows
                   if (row.get("identity") or {}).get("goal_id")]
    active_ids = {
        tuple((row.get("identity") or {}).get(key, "")
              for key in ("run_id", "runtime_contract_sha256", "goal_id", "epoch", "map_id"))
        for row in active_rows
    }
    complete_active = all((row.get("identity") or {}).get("complete") is True
                          for row in active_rows)
    if not active_rows:
        errors.append("no_goal_bound_sensor_receipts")
    if not complete_active:
        errors.append("active_sensor_receipts_have_incomplete_identity")
    if len(active_ids) != 1:
        errors.append("active_sensor_receipts_span_multiple_identity_epochs_or_maps")
    if len(active_ids) == 1:
        expected_identity = tuple(identity.get(key, "") for key in (
            "run_id", "runtime_contract_sha256", "goal_id", "epoch", "map_id"))
        if next(iter(active_ids)) != expected_identity:
            errors.append("active_receipt_identity_differs_from_run_identity")

    bag_comparison = compare_receipts_to_bag(receipt_rows, bag_rows, topics)
    if len(receipt_rows) == 0:
        errors.append("no_sensor_receipts")
    if any(not row["keys_match"] for row in bag_comparison.values()):
        errors.append("compressed_payload_message_missing_receipt_metadata")
    reported_counts = capture.get("stream_counts", {})
    for stream in REQUIRED_STREAMS:
        actual = sum(1 for row in receipt_rows if row.get("stream") == stream)
        if int(reported_counts.get(stream, -1)) != actual or actual == 0:
            errors.append(f"stream_count_missing_or_mismatched:{stream}")

    return {
        "schema": "n10-sensor-capture-evaluation/v1",
        "classification": "offline recorder integrity only; not system acceptance",
        "status": "PASS" if not errors else "INSUFFICIENT",
        "run_identity": identity,
        "active_identity_tuple_count": len(active_ids),
        "active_receipt_count": len(active_rows),
        "receipt_count": len(receipt_rows),
        "bag_message_count": len(bag_rows),
        "receipt_to_payload": bag_comparison,
        "stream_timing": summarize_stream_timing(receipt_rows, topics),
        "errors": errors,
        "runtime_control_effect": False,
        "limits": [
            "A successful capture check establishes receipt-to-lossless-bag linkage, not visual localization quality.",
            "Missing or conflicting records are INSUFFICIENT and never trigger flight control.",
        ],
    }


def assess_zero_flight_capture(capture, receipt_rows, bag_rows, topics, run_identity,
                               flight_record_present=False):
    """Validate transport/payload coverage in a disarmed no-goal smoke run."""
    errors = []
    if capture.get("schema") != "n10-sensor-capture/v1":
        errors.append("unsupported_or_missing_capture_report")
    if capture.get("metadata_write_ok") is not True:
        errors.append("receipt_metadata_write_incomplete")
    if capture.get("bag_exit_code") != 0:
        errors.append("bag_close_not_clean")
    if capture.get("errors"):
        errors.append("capture_report_has_errors")
    if flight_record_present:
        errors.append("flight_record_present_in_zero_flight_check")
    if not all(run_identity.get(key) for key in (
            "run_id", "runtime_contract_sha256", "epoch", "map_id", "frame_id")):
        errors.append("zero_flight_run_epoch_map_identity_incomplete")
    if run_identity.get("goal_id"):
        errors.append("goal_identity_present_in_zero_flight_check")
    if not run_identity.get("map_id", "").startswith(
            str(run_identity.get("epoch", "")) + "-"):
        errors.append("map_id_epoch_mismatch")
    if capture.get("run_identity_at_end", {}).get("runtime_contract_sha256") != run_identity.get(
            "runtime_contract_sha256"):
        errors.append("zero_flight_capture_runtime_identity_mismatch")
    if set(capture.get("topics", {}).values()) != set(topics.values()):
        errors.append("resolved_topic_set_mismatch")
    comparison = compare_receipts_to_bag(receipt_rows, bag_rows, topics)
    if not receipt_rows:
        errors.append("no_sensor_receipts")
    reported_counts = capture.get("stream_counts", {})
    for stream in REQUIRED_STREAMS:
        actual = sum(1 for row in receipt_rows if row.get("stream") == stream)
        if int(reported_counts.get(stream, -1)) != actual or actual == 0:
            errors.append(f"stream_count_missing_or_mismatched:{stream}")
    expected_identity = tuple(run_identity.get(key, "") for key in (
        "run_id", "runtime_contract_sha256", "epoch", "map_id"))
    receipt_identities = {
        tuple((row.get("identity") or {}).get(key, "") for key in (
            "run_id", "runtime_contract_sha256", "epoch", "map_id"))
        for row in receipt_rows
    }
    if not receipt_identities or receipt_identities != {expected_identity}:
        errors.append("zero_flight_receipts_span_missing_or_multiple_identities")
    if any(not row["keys_match"] for row in comparison.values()):
        errors.append("compressed_payload_message_missing_receipt_metadata")
    return {
        "schema": "n10-sensor-capture-evaluation/v1",
        "classification": "zero-flight transport smoke only; not a task or acceptance result",
        "status": "PASS" if not errors else "INSUFFICIENT",
        "run_identity": run_identity,
        "receipt_count": len(receipt_rows),
        "bag_message_count": len(bag_rows),
        "receipt_to_payload": comparison,
        "stream_timing": summarize_stream_timing(receipt_rows, topics),
        "errors": errors,
        "runtime_control_effect": False,
    }


def _read_jsonl(path):
    rows = []
    with Path(path).open() as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except ValueError as exc:
                raise ValueError(f"invalid JSONL line {line_number}: {exc}") from exc
    return rows


def read_mcap_rows(bag_dir):
    """Read message identity keys through rosbag2's normal decompression path."""
    import rosbag2_py
    from rclpy.serialization import deserialize_message
    from rosidl_runtime_py.utilities import get_message

    reader = rosbag2_py.SequentialReader()
    reader.open(
        rosbag2_py.StorageOptions(uri=str(Path(bag_dir)), storage_id="mcap"),
        rosbag2_py.ConverterOptions(input_serialization_format="", output_serialization_format=""),
    )
    type_by_topic = {item.name: get_message(item.type)
                     for item in reader.get_all_topics_and_types()}
    rows = []
    while reader.has_next():
        topic, serialized, _ = reader.read_next()
        if topic not in type_by_topic:
            continue
        message = deserialize_message(serialized, type_by_topic[topic])
        header = message.header
        stamp = int(header.stamp.sec) * 1_000_000_000 + int(header.stamp.nanosec)
        rows.append({"topic": topic, "source_stamp_ns": stamp,
                     "frame_id": str(header.frame_id)})
    return rows


def evaluate(run_dir, zero_flight=False):
    run = Path(run_dir).resolve()
    capture_path = run / "n10-sensor-capture.json"
    receipt_path = run / "n10-sensor-receipts.jsonl"
    capture = json.loads(capture_path.read_text()) if capture_path.is_file() else {}
    topics = capture.get("topics", {})
    identity = read_run_identity(run)
    identity_source = "run_files"
    identity_errors = []
    if not zero_flight:
        identity, identity_source, identity_errors = resolve_capture_identity(run, capture)
    errors = []
    try:
        receipt_rows = _read_jsonl(receipt_path)
    except (OSError, ValueError) as exc:
        receipt_rows = []
        errors.append(f"receipt_read:{type(exc).__name__}:{exc}")
    try:
        bag_rows = read_mcap_rows(run / capture.get("bag_directory", "n10-sensor-payload"))
    except Exception as exc:
        bag_rows = []
        errors.append(f"bag_read:{type(exc).__name__}:{exc}")
    if receipt_path.is_file() and capture.get("receipt_sha256"):
        if sha256_file(receipt_path) != capture["receipt_sha256"]:
            errors.append("receipt_sha256_mismatch")
    if zero_flight:
        zero_identity = (capture.get("run_identity_at_end") or {})
        result = assess_zero_flight_capture(
            capture, receipt_rows, bag_rows, topics, zero_identity,
            flight_record_present=(run / "flight.json").is_file())
    else:
        result = assess_capture(capture, receipt_rows, bag_rows, topics, identity)
        result["errors"].extend(identity_errors)
        result["identity_source"] = identity_source
    result["errors"].extend(errors)
    if errors:
        result["status"] = "INSUFFICIENT"
    result["capture_report_sha256"] = (
        sha256_file(capture_path) if capture_path.is_file() else None)
    result["receipt_sha256"] = sha256_file(receipt_path) if receipt_path.is_file() else None
    (run / "n10-sensor-capture-evaluation.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--zero-flight", action="store_true",
                        help="verify only stream-to-payload integrity in a disarmed no-goal run")
    args = parser.parse_args()
    result = evaluate(args.run_dir, zero_flight=args.zero_flight)
    print(json.dumps({"status": result["status"], "errors": result["errors"]}))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
