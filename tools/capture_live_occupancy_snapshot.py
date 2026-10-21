#!/usr/bin/env python3
"""Capture one fresh, identity-bound readback from plan_env."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

import numpy as np
import rclpy
from rclpy.node import Node
from uav_interfaces.srv import GetMapStatus, GetOccupancySnapshot


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stamp_ns(stamp):
    return int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)


def relative_path(path, root):
    try:
        return os.path.relpath(path.resolve(), root.resolve())
    except ValueError:
        return str(path.resolve())


def status_record(status):
    return {
        "header_frame_id": status.header.frame_id,
        "header_stamp_ns": stamp_ns(status.header.stamp),
        "epoch": status.epoch,
        "map_id": status.map_id,
        "reset_acknowledged": bool(status.reset_acknowledged),
        "input_ready": bool(status.input_ready),
        "reason": status.reason,
        "last_depth_source_stamp_ns": stamp_ns(status.last_depth_source_stamp),
        "last_occupancy_stamp_ns": stamp_ns(status.last_occupancy_stamp),
        "occupancy_cloud_received": bool(status.occupancy_cloud_received),
        "occupied_point_count": int(status.occupied_point_count),
        "forwarded_depth_count": int(status.forwarded_depth_count),
        "calibration_sha256": status.calibration_sha256,
        "input_config_sha256": status.input_config_sha256,
        "keyframe_count": int(status.keyframe_count),
        "keyframe_dropped_count": int(status.keyframe_dropped_count),
        "keyframe_max_rgbd_stamp_delta_s": float(status.keyframe_max_rgbd_stamp_delta_s),
    }


class SnapshotClient(Node):
    def __init__(self, status_service, snapshot_service):
        super().__init__("occupancy_snapshot_client")
        self.status_client = self.create_client(GetMapStatus, status_service)
        self.snapshot_client = self.create_client(GetOccupancySnapshot, snapshot_service)

    def request(self, client, request, timeout_s):
        if not client.wait_for_service(timeout_sec=timeout_s):
            raise TimeoutError(f"service unavailable: {client.srv_name}")
        future = client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=timeout_s)
        if not future.done():
            raise TimeoutError(f"service call timed out: {client.srv_name}")
        result = future.result()
        if result is None:
            raise RuntimeError(f"service call failed: {client.srv_name}")
        return result

    def read_status(self, expected_epoch, timeout_s):
        request = GetMapStatus.Request()
        request.expected_epoch = expected_epoch
        result = self.request(self.status_client, request, timeout_s)
        return result, status_record(result.status)

    @staticmethod
    def validate_ready_status(result, status, expected_epoch, min_forwarded_depth_count=0):
        if not result.accepted:
            raise RuntimeError(f"MapStatus rejected: {result.reason}")
        if status["epoch"] != expected_epoch:
            raise RuntimeError("MapStatus returned a different epoch")
        if not status["map_id"].startswith(expected_epoch + "-"):
            raise RuntimeError("MapStatus map_id does not belong to the requested epoch")
        if not status["reset_acknowledged"] or not status["input_ready"]:
            raise RuntimeError(f"MapStatus is not ready: {status['reason']}")
        if not status["occupancy_cloud_received"]:
            raise RuntimeError("MapStatus has not received an occupancy cloud")
        if status["forwarded_depth_count"] < min_forwarded_depth_count:
            raise RuntimeError(
                f"only {status['forwarded_depth_count']} depth inputs forwarded; "
                f"need {min_forwarded_depth_count}")
        return status

    def wait_ready_status(
            self, expected_epoch, ready_timeout_s, poll_interval_s, min_forwarded_depth_count):
        deadline = time.monotonic() + ready_timeout_s
        last_reason = "service_not_ready"
        while time.monotonic() < deadline:
            try:
                result, status = self.read_status(expected_epoch, min(2.0, ready_timeout_s))
                if result.accepted:
                    try:
                        return self.validate_ready_status(
                            result, status, expected_epoch, min_forwarded_depth_count)
                    except RuntimeError as error:
                        last_reason = str(error)
                else:
                    last_reason = result.reason
            except (RuntimeError, TimeoutError) as error:
                last_reason = str(error)
            time.sleep(poll_interval_s)
        raise TimeoutError(f"MapStatus did not become ready within {ready_timeout_s}s: {last_reason}")

    def get_ready_status(self, expected_epoch, timeout_s):
        result, status = self.read_status(expected_epoch, timeout_s)
        return self.validate_ready_status(result, status, expected_epoch)


def capture(args):
    root = args.project_root.resolve()
    model_hash = sha256(args.model)
    input_hash = sha256(args.input_config)
    if not args.runtime_params.read_text().strip():
        raise ValueError("runtime parameter dump is empty")

    rclpy.init()
    node = SnapshotClient(args.status_service, args.snapshot_service)
    capture_start = time.monotonic()
    try:
        before = node.wait_ready_status(
            args.expected_epoch, args.ready_timeout_s, args.status_poll_interval_s,
            args.min_forwarded_depth_count)
        if before["calibration_sha256"] != model_hash:
            raise ValueError("MapStatus calibration hash does not match the model file")
        if before["input_config_sha256"] != input_hash:
            raise ValueError("MapStatus input-config hash does not match the config file")

        request = GetOccupancySnapshot.Request()
        request.expected_epoch = before["epoch"]
        request.expected_map_id = before["map_id"]
        transient_rejections = {"no_fresh_fused_depth", "depth_source_stale", "occupancy_update_stale"}
        rejection_counts = {}
        snapshot_wait_start = time.monotonic()
        snapshot_deadline = snapshot_wait_start + args.snapshot_ready_timeout_s
        while True:
            service_start = time.monotonic()
            response = node.request(node.snapshot_client, request, args.timeout_s)
            service_duration_ms = (time.monotonic() - service_start) * 1000.0
            if response.accepted:
                break
            rejection_counts[response.reason] = rejection_counts.get(response.reason, 0) + 1
            if response.reason not in transient_rejections:
                raise RuntimeError(f"snapshot rejected: {response.reason}")
            if time.monotonic() >= snapshot_deadline:
                raise TimeoutError(
                    f"snapshot did not become fresh within {args.snapshot_ready_timeout_s}s: "
                    f"{rejection_counts}")
            time.sleep(args.status_poll_interval_s)
        snapshot_wait_elapsed_ms = (time.monotonic() - snapshot_wait_start) * 1000.0
        after = node.get_ready_status(args.expected_epoch, args.timeout_s)
        if after["epoch"] != before["epoch"] or after["map_id"] != before["map_id"]:
            raise RuntimeError("map identity changed during snapshot capture")
        if response.epoch != before["epoch"] or response.map_id != before["map_id"]:
            raise RuntimeError("snapshot response does not match the ready MapStatus")

        wrong_epoch = "f" * 32 if before["epoch"] != "f" * 32 else "e" * 32
        wrong_epoch_request = GetOccupancySnapshot.Request()
        wrong_epoch_request.expected_epoch = wrong_epoch
        wrong_epoch_request.expected_map_id = before["map_id"]
        wrong_epoch_response = node.request(
            node.snapshot_client, wrong_epoch_request, args.timeout_s)
        if wrong_epoch_response.accepted or wrong_epoch_response.reason != "epoch_mismatch":
            raise RuntimeError("snapshot service did not reject a mismatched epoch")

        wrong_map_request = GetOccupancySnapshot.Request()
        wrong_map_request.expected_epoch = before["epoch"]
        wrong_map_request.expected_map_id = before["map_id"] + "-stale"
        wrong_map_response = node.request(node.snapshot_client, wrong_map_request, args.timeout_s)
        if wrong_map_response.accepted or wrong_map_response.reason != "map_id_mismatch":
            raise RuntimeError("snapshot service did not reject a mismatched map_id")

        shape = (int(response.size_x), int(response.size_y), int(response.size_z))
        if any(size <= 0 for size in shape):
            raise ValueError(f"invalid map dimensions: {shape}")
        expected_count = int(np.prod(shape, dtype=np.int64))
        occupancy = np.asarray(response.occupancy_data, dtype=np.int8)
        inflated = np.asarray(response.inflated_data, dtype=np.uint8)
        if occupancy.size != expected_count or inflated.size != expected_count:
            raise ValueError("snapshot array lengths do not match dimensions")
        occupancy = occupancy.reshape(shape, order="C")
        inflated = inflated.reshape(shape, order="C")
        allowed_occupancy = np.isin(occupancy, (-1, 0, 100))
        if not bool(np.all(allowed_occupancy)):
            raise ValueError("snapshot contains an unknown occupancy code")
        if not bool(np.all(np.isin(inflated, (0, 1)))):
            raise ValueError("snapshot inflation array is not binary")

        counts = {
            "unknown": int(np.count_nonzero(occupancy == -1)),
            "free": int(np.count_nonzero(occupancy == 0)),
            "occupied": int(np.count_nonzero(occupancy == 100)),
            "inflated": int(np.count_nonzero(inflated == 1)),
        }
        reported = {
            "unknown": int(response.unknown_voxel_count),
            "free": int(response.free_voxel_count),
            "occupied": int(response.occupied_voxel_count),
            "inflated": int(response.inflated_voxel_count),
        }
        if counts != reported or sum(counts[name] for name in ("unknown", "free", "occupied")) != expected_count:
            raise ValueError(f"snapshot counts do not match arrays: {counts} != {reported}")
        known_count = counts["free"] + counts["occupied"]
        if known_count < args.min_known_voxels:
            raise ValueError(
                f"snapshot has only {known_count} known voxels; need {args.min_known_voxels}")
        if response.data_order != "x_major_y_mid_z_fastest":
            raise ValueError(f"unsupported data order: {response.data_order}")
        if response.header.frame_id != f"odom_{response.epoch}":
            raise ValueError("snapshot frame does not match its epoch")

        source_ns = stamp_ns(response.last_depth_source_stamp)
        fusion_ns = stamp_ns(response.last_fusion_stamp)
        snapshot_ns = stamp_ns(response.header.stamp)
        source_age_s = (snapshot_ns - source_ns) / 1e9
        if source_ns <= 0 or fusion_ns <= 0 or source_age_s < 0.0 or source_age_s > args.max_source_age_s:
            raise ValueError(f"snapshot source/fusion freshness failed: age={source_age_s:.6f}s")

        args.output_dir.mkdir(parents=True, exist_ok=True)
        archive_path = args.output_dir / "occupancy_snapshot.npz"
        np.savez_compressed(archive_path, occupancy=occupancy, inflated=inflated)
        with np.load(archive_path, allow_pickle=False) as archive:
            if not np.array_equal(archive["occupancy"], occupancy):
                raise ValueError("occupancy array changed during compressed archive readback")
            if not np.array_equal(archive["inflated"], inflated):
                raise ValueError("inflation array changed during compressed archive readback")

        metadata = {
            "schema": "plan-env-voxel-snapshot/v1",
            "qualification": "single fresh map readback and archive roundtrip; not map coverage, vehicle clearance, or navigation acceptance",
            "expected_epoch": args.expected_epoch,
            "epoch": response.epoch,
            "map_id": response.map_id,
            "frame_id": response.header.frame_id,
            "snapshot_stamp_ns": snapshot_ns,
            "last_fused_depth_source_stamp_ns": source_ns,
            "last_fusion_stamp_ns": fusion_ns,
            "source_age_at_response_s": source_age_s,
            "snapshot_service_duration_ms": service_duration_ms,
            "snapshot_freshness_wait_ms": snapshot_wait_elapsed_ms,
            "transient_snapshot_rejection_count": sum(rejection_counts.values()),
            "transient_snapshot_rejection_reasons": rejection_counts,
            "capture_elapsed_ms": (time.monotonic() - capture_start) * 1000.0,
            "origin_m": [float(response.origin.x), float(response.origin.y), float(response.origin.z)],
            "map_size_m": [float(response.map_size.x), float(response.map_size.y), float(response.map_size.z)],
            "resolution_m": float(response.resolution),
            "dimensions_xyz": list(shape),
            "data_order": response.data_order,
            "occupancy_codes": {"unknown": -1, "known_nonoccupied": 0, "raw_occupied": 100},
            "inflated_mask_semantics": "plan_env obstacle inflation or virtual ceiling; separate from raw occupancy and unknown-space policy",
            "voxel_counts": counts,
            "map_status_before": before,
            "map_status_after": after,
            "minimum_forwarded_depth_count": args.min_forwarded_depth_count,
            "minimum_known_voxel_count": args.min_known_voxels,
            "identity_rejection_checks": {
                "mismatched_epoch_rejected": True,
                "mismatched_epoch_reason": wrong_epoch_response.reason,
                "mismatched_map_id_rejected": True,
                "mismatched_map_id_reason": wrong_map_response.reason,
            },
            "configuration": {
                "calibration_sha256": model_hash,
                "input_config_sha256": input_hash,
                "planner_config_sha256": sha256(args.planner_config),
                "runtime_parameters_sha256": sha256(args.runtime_params),
            },
            "source_files": {
                "model": {"path": relative_path(args.model, root), "sha256": model_hash},
                "input_config": {"path": relative_path(args.input_config, root), "sha256": input_hash},
                "planner_config": {"path": relative_path(args.planner_config, root), "sha256": sha256(args.planner_config)},
                "runtime_parameters": {"path": relative_path(args.runtime_params, root), "sha256": sha256(args.runtime_params)},
                "source_manifest": {"path": relative_path(args.source_manifest, root), "sha256": sha256(args.source_manifest)},
            },
            "archive": {
                "file": archive_path.name,
                "sha256": sha256(archive_path),
                "compressed_bytes": archive_path.stat().st_size,
                "readback_exact": True,
                "readback_arrays": ["occupancy", "inflated"],
            },
        }
        metadata_path = args.output_dir / "metadata.json"
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
        return metadata
    finally:
        node.destroy_node()
        rclpy.shutdown()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-epoch", required=True)
    parser.add_argument("--status-service", default="/mapping/get_map_status")
    parser.add_argument("--snapshot-service", default="/mapping/get_occupancy_snapshot")
    parser.add_argument("--timeout-s", type=float, default=60.0)
    parser.add_argument("--ready-timeout-s", type=float, default=120.0)
    parser.add_argument("--snapshot-ready-timeout-s", type=float, default=120.0)
    parser.add_argument("--status-poll-interval-s", type=float, default=0.25)
    parser.add_argument("--min-forwarded-depth-count", type=int, default=20)
    parser.add_argument("--min-known-voxels", type=int, default=1)
    parser.add_argument("--max-source-age-s", type=float, default=0.4)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--input-config", type=Path, required=True)
    parser.add_argument("--planner-config", type=Path, required=True)
    parser.add_argument("--runtime-params", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(capture(args), indent=2))


if __name__ == "__main__":
    main()
