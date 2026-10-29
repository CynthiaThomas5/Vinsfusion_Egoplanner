#!/usr/bin/env python3
"""Record named raw and official-EGO point queries for one active map identity.

The input points are supplied in ``odom_<epoch>``. This tool only calls
read-only map services; it does not subscribe to truth or publish control.
"""
import argparse
import json
import math
from pathlib import Path
import sys
import time

import rclpy
from uav_interfaces.srv import GetMapStatus, QueryOccupancySphere
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from n10_map_query_contract import (
    PLANNING_OCCUPANCY_SERVICE,
    RAW_OCCUPANCY_SERVICE,
    radius_for_service,
    resolve_point_query_identity,
    response_capture_error,
    response_query_geometry,
)
from n10_run_identity import sha256_file


def stamp_ns(stamp):
    return int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)


def read_status(node, client, epoch, timeout_s):
    if not client.wait_for_service(timeout_sec=timeout_s):
        raise TimeoutError(f"service unavailable: {client.srv_name}")
    request = GetMapStatus.Request()
    request.expected_epoch = epoch
    future = client.call_async(request)
    rclpy.spin_until_future_complete(node, future, timeout_sec=timeout_s)
    if not future.done() or future.result() is None:
        raise TimeoutError("GetMapStatus did not complete")
    result = future.result()
    status = result.status
    record = {
        "accepted": bool(result.accepted),
        "reason": result.reason,
        "epoch": status.epoch,
        "map_id": status.map_id,
        "frame_id": status.header.frame_id,
        "input_ready": bool(status.input_ready),
        "reset_acknowledged": bool(status.reset_acknowledged),
        "last_depth_source_stamp_ns": stamp_ns(status.last_depth_source_stamp),
        "last_occupancy_stamp_ns": stamp_ns(status.last_occupancy_stamp),
    }
    if (not record["accepted"] or record["epoch"] != epoch
            or record["frame_id"] != f"odom_{epoch}"
            or not record["input_ready"] or not record["reset_acknowledged"]):
        raise RuntimeError(f"active map identity is not ready: {record}")
    return record


def query(node, client, point, identity, raw_query_radius_m, timeout_s,
          run_identity=None):
    if not client.wait_for_service(timeout_sec=timeout_s):
        raise TimeoutError(f"service unavailable: {client.srv_name}")
    request = QueryOccupancySphere.Request()
    request.expected_epoch = identity["epoch"]
    request.expected_map_id = identity["map_id"]
    request.frame_id = identity["frame_id"]
    request.center.x, request.center.y, request.center.z = map(float, point["xyz_odom_m"])
    request.radius_m = radius_for_service(client.srv_name, raw_query_radius_m)
    requested_steady_ns = time.monotonic_ns()
    future = client.call_async(request)
    rclpy.spin_until_future_complete(node, future, timeout_sec=timeout_s)
    responded_steady_ns = time.monotonic_ns()
    if not future.done() or future.result() is None:
        raise TimeoutError(f"query timed out: {client.srv_name} ({point['label']})")
    response = future.result()
    response_geometry = response_query_geometry(response)
    return {
        "service": client.srv_name,
        "label": point["label"],
        "run_identity": run_identity,
        "request": {
            "expected_epoch": request.expected_epoch,
            "expected_map_id": request.expected_map_id,
            "frame_id": request.frame_id,
            "xyz_odom_m": [float(request.center.x), float(request.center.y),
                            float(request.center.z)],
            "radius_m": float(request.radius_m),
            "steady_monotonic_ns": requested_steady_ns,
        },
        "response": {
            "accepted": bool(response.accepted),
            "free": bool(response.free),
            "reason": response.reason,
            "header_frame_id": response.header.frame_id,
            "service_stamp_ns": stamp_ns(response.header.stamp),
            "epoch": response.epoch,
            "map_id": response.map_id,
            "last_depth_source_stamp_ns": stamp_ns(response.last_depth_source_stamp),
            "last_fusion_stamp_ns": stamp_ns(response.last_fusion_stamp),
            "unknown_count": int(response.unknown_count),
            "free_count": int(response.free_count),
            "occupied_count": int(response.occupied_count),
            **response_geometry,
        },
        "response_steady_monotonic_ns": responded_steady_ns,
        "service_round_trip_steady_s": (responded_steady_ns - requested_steady_ns) / 1e9,
        "identity_matches_request": bool(
            response.epoch == identity["epoch"]
            and response.map_id == identity["map_id"]
            and response.header.frame_id == identity["frame_id"]),
    }


def capture(input_path, output_path, timeout_s):
    spec = json.loads(input_path.read_text())
    if spec.get("schema") != "n10-map-point-queries/v2":
        raise ValueError("unsupported point-query specification schema")
    raw_query_radius_m = float(spec.get("raw_query_radius_m", float("nan")))
    radius_for_service(RAW_OCCUPANCY_SERVICE, raw_query_radius_m)
    epoch = str(spec.get("epoch", ""))
    map_id = str(spec.get("map_id", ""))
    frame_id = str(spec.get("frame_id", ""))
    points = spec.get("points")
    if (not epoch or not map_id.startswith(epoch + "-")
            or frame_id != f"odom_{epoch}" or not isinstance(points, list) or not points):
        raise ValueError("point-query spec needs one exact epoch/map/frame and non-empty points")
    run_identity, identity_conflicts = resolve_point_query_identity(
        output_path.parent, spec)
    labels = set()
    for point in points:
        xyz = point.get("xyz_odom_m")
        if (not point.get("label") or point["label"] in labels
                or not isinstance(xyz, list) or len(xyz) != 3
                or not all(math.isfinite(float(v)) for v in xyz)):
            raise ValueError("point labels must be unique and coordinates finite xyz")
        labels.add(point["label"])

    rclpy.init()
    node = rclpy.create_node("n10_readonly_map_point_queries", parameter_overrides=[
        rclpy.parameter.Parameter("use_sim_time", value=True)])
    status_client = node.create_client(GetMapStatus, "/mapping/get_map_status")
    raw_client = node.create_client(QueryOccupancySphere, RAW_OCCUPANCY_SERVICE)
    planning_client = node.create_client(QueryOccupancySphere, PLANNING_OCCUPANCY_SERVICE)
    try:
        identity = {"epoch": epoch, "map_id": map_id, "frame_id": frame_id}
        before = read_status(node, status_client, epoch, timeout_s)
        if before["map_id"] != map_id:
            raise RuntimeError("active map_id differs from point-query specification")
        records = []
        for point in points:
            for client in (raw_client, planning_client):
                try:
                    row = query(node, client, point, identity, raw_query_radius_m,
                                timeout_s, run_identity)
                    row["capture_error"] = response_capture_error(row)
                    row["capture_valid"] = not row["capture_error"]
                    records.append(row)
                except Exception as exc:
                    records.append({
                        "service": client.srv_name,
                        "label": point["label"],
                        "identity_matches_request": False,
                        "capture_valid": False,
                        "capture_error": f"{type(exc).__name__}: {exc}",
                        "error": f"{type(exc).__name__}: {exc}",
                    })
        after = read_status(node, status_client, epoch, timeout_s)
        identities_match = before["map_id"] == after["map_id"] == map_id
        queries_valid = all(row.get("capture_valid") is True for row in records)
        row_identities_match = all(row.get("identity_matches_request") is True
                                   for row in records)
        report = {
            "schema": "n10-map-point-query-results/v2",
            "classification": "read-only service-capture validity only; free is the service verdict; not map coverage, clearance, or a control decision",
            "read_only": True,
            "truth_subscribed": False,
            "control_published": False,
            "snapshot_time_equality_required": False,
            "identity": identity,
            "run_identity": run_identity,
            "declared_identity_conflicts": identity_conflicts,
            "declared_identity_matches": not identity_conflicts,
            "input_spec_sha256": sha256_file(input_path),
            "runtime_identity_complete": bool(run_identity.get("complete"))
            and not identity_conflicts,
            "map_status_before": before,
            "map_status_after": after,
            "map_identity_stable": identities_match,
            "all_query_responses_match_identity": row_identities_match,
            "all_query_responses_accepted_and_echoed": queries_valid,
            "raw_query_radius_m": raw_query_radius_m,
            "planning_query_radius_m": 0.0,
            "queries": records,
            "passed": bool(identities_match and queries_valid and row_identities_match
                           and run_identity.get("complete") is True
                           and not identity_conflicts),
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        return report
    finally:
        node.destroy_node()
        rclpy.shutdown()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True,
                        help="JSON schema n10-map-point-queries/v1")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-s", type=float, default=3.0)
    parser.add_argument("--wait-input-timeout-s", type=float, default=0.0,
                        help="wait for an observer to write the input specification")
    args = parser.parse_args()
    if args.wait_input_timeout_s < 0.0:
        parser.error("wait-input-timeout-s must be non-negative")
    deadline = time.monotonic() + args.wait_input_timeout_s
    while not args.input.is_file() and time.monotonic() < deadline:
        time.sleep(0.1)
    if not args.input.is_file():
        parser.error(f"point-query input was not created: {args.input}")
    try:
        report = capture(args.input, args.output, args.timeout_s)
    except Exception as exc:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "schema": "n10-map-point-query-results/v2",
            "classification": "read-only diagnostic; incomplete service capture",
            "read_only": True,
            "truth_subscribed": False,
            "control_published": False,
            "passed": False,
            "queries": [],
            "error": f"{type(exc).__name__}: {exc}",
        }
        args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"passed": report["passed"], "query_count": len(report["queries"])}))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
