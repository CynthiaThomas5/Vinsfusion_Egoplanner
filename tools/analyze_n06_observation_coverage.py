#!/usr/bin/env python3
"""Project N06 body/hold raw-unknown voxel centers into captured D435i views.

This is a geometric coverage diagnostic. It checks exact closed-cell sphere
queries against archived raw occupancy, then projects unknown cell centers
using recorded camera poses and intrinsics. It does not certify depth-ray
clearing, occlusion, occupancy classification, or navigation safety.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNS = (
    "n06-20261023-wall-r10",
    "n06-20261023-corridor-r10",
)
RADII_M = {
    "body": 0.7306179170842027,
    "terminal_hold": 0.9806179170842027,
}
NEAR_CLIP_M = 0.2


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def nearest(rows, stamp_ns):
    return min(rows, key=lambda row: abs(int(row["stamp_ns"]) - stamp_ns))


def rotate_inverse(vectors, quaternion_xyzw):
    """Rotate row-vector positions by the inverse ROS xyzw quaternion."""
    q = np.asarray(quaternion_xyzw, dtype=float)
    qv, qw = -q[:3], q[3]
    twice_cross = 2.0 * np.cross(qv, vectors)
    return vectors + qw * twice_cross + np.cross(qv, twice_cross)


def cell_indices_for_sphere(center, radius, origin, resolution, shape):
    lo = np.floor((center - radius - origin - 1e-9) / resolution).astype(int)
    hi = np.floor((center + radius - origin + 1e-9) / resolution).astype(int)
    if np.any(lo < 0) or np.any(hi >= np.asarray(shape)):
        raise ValueError("sphere extends outside archived map bounds")
    indices = np.stack(np.meshgrid(
        *(np.arange(lo[axis], hi[axis] + 1) for axis in range(3)),
        indexing="ij"), axis=-1).reshape(-1, 3)
    lower = origin + indices * resolution
    upper = lower + resolution
    offset = np.maximum(np.maximum(lower - center, 0.0), center - upper)
    intersects = np.sum(offset * offset, axis=1) <= (radius + 1e-9) ** 2
    return indices[intersects]


def projected_bins(points_odom, camera_pose, intrinsics):
    camera = rotate_inverse(
        points_odom - np.asarray(camera_pose["position"], dtype=float),
        camera_pose["quaternion"],
    )
    z = camera[:, 2]
    fx, fy, cx, cy = intrinsics
    safe_z = np.where(np.abs(z) > 1e-9, z, 1.0)
    u = fx * camera[:, 0] / safe_z + cx
    v = fy * camera[:, 1] / safe_z + cy
    front = z > 0.0
    beyond_near = z >= NEAR_CLIP_M
    horizontal = (u >= 0.0) & (u < 640.0)
    vertical = (v >= 0.0) & (v < 480.0)
    in_image = front & beyond_near & horizontal & vertical
    return {
        "behind_camera": ~front,
        "inside_near_clip": front & ~beyond_near,
        "horizontal_outside_image": front & beyond_near & ~horizontal,
        "vertical_outside_image": front & beyond_near & horizontal & ~vertical,
        "inside_geometric_image": in_image,
    }


def analyze_run(run_id):
    run_dir = ROOT / "artifacts" / "runs" / run_id
    input_path = run_dir / "inputs" / "mapping-inputs.json"
    snapshot_dir = run_dir / "snapshots" / "snapshot-03"
    metadata_path = snapshot_dir / "metadata.json"
    archive_path = snapshot_dir / "occupancy_snapshot.npz"
    inputs = json.loads(input_path.read_text())
    metadata = json.loads(metadata_path.read_text())
    snapshot_stamp = int(metadata["snapshot_stamp_ns"])
    source_stamp = int(metadata["last_fused_depth_source_stamp_ns"])
    body_pose = max(
        (row for row in inputs["optimized_odometry"]
         if int(row["stamp_ns"]) <= snapshot_stamp),
        key=lambda row: int(row["stamp_ns"]),
    )
    camera_pose = nearest(inputs["camera_poses"], source_stamp)
    camera_info = nearest(inputs["depth_camera_info"], source_stamp)
    if int(camera_pose["stamp_ns"]) != source_stamp:
        raise ValueError(f"{run_id}: no exact camera pose at fused depth source stamp")
    if int(camera_info["stamp_ns"]) != source_stamp:
        raise ValueError(f"{run_id}: no exact camera info at fused depth source stamp")
    intrinsics = [
        float(camera_info["k"][0]), float(camera_info["k"][4]),
        float(camera_info["k"][2]), float(camera_info["k"][5]),
    ]
    center = np.asarray(body_pose["position"], dtype=float)
    origin = np.asarray(metadata["origin_m"], dtype=float)
    resolution = float(metadata["resolution_m"])
    with np.load(archive_path) as archive:
        occupancy = np.asarray(archive["occupancy"], dtype=np.int8)

    projections = {}
    capture_poses = [
        pose for pose in inputs["camera_poses"]
        if int(pose["stamp_ns"]) <= source_stamp
    ]
    for label, radius in RADII_M.items():
        indices = cell_indices_for_sphere(
            center, radius, origin, resolution, occupancy.shape)
        values = occupancy[indices[:, 0], indices[:, 1], indices[:, 2]]
        counts = {
            "unknown": int(np.count_nonzero(values == -1)),
            "free": int(np.count_nonzero(values == 0)),
            "occupied": int(np.count_nonzero(values == 100)),
        }
        unknown_indices = indices[values == -1]
        points = origin + (unknown_indices + 0.5) * resolution
        bins = projected_bins(points, camera_pose, intrinsics)
        current_counts = {key: int(mask.sum()) for key, mask in bins.items()}
        ever_visible = np.zeros(len(points), dtype=bool)
        for pose in capture_poses:
            ever_visible |= projected_bins(points, pose, intrinsics)[
                "inside_geometric_image"]
        projection = {
            "unknown_cell_centers": int(len(points)),
            "source_pose_counts": current_counts,
            "ever_inside_geometric_image_during_capture": int(ever_visible.sum()),
            "never_inside_geometric_image_during_capture": int((~ever_visible).sum()),
            "classification_qualification": (
                "cell-center geometric projection only; depth values and ray "
                "occlusion/classification are not tested"
            ),
        }
        if sum(current_counts[key] for key in (
                "behind_camera", "inside_near_clip", "horizontal_outside_image",
                "vertical_outside_image", "inside_geometric_image")) != len(points):
            raise AssertionError(f"{run_id}/{label}: projection bins do not partition unknown centers")
        projections[label] = {"radius_m": radius, "raw_query_counts": counts,
                              "projection": projection}

    return {
        "run_id": run_id,
        "layout_id": json.loads((run_dir / "run-inputs.json").read_text())["layout_id"],
        "snapshot": "snapshot-03",
        "body_center_pose": {
            "stamp_ns": int(body_pose["stamp_ns"]),
            "frame_id": body_pose["frame_id"],
            "position_xyz_m": center.tolist(),
            "snapshot_minus_pose_s": (snapshot_stamp - int(body_pose["stamp_ns"])) / 1e9,
        },
        "camera_at_fused_depth_source": {
            "stamp_ns": source_stamp,
            "frame_id": camera_pose["frame_id"],
            "position_xyz_m": camera_pose["position"],
            "quaternion_xyzw": camera_pose["quaternion"],
            "intrinsics_fx_fy_cx_cy": intrinsics,
            "capture_pose_count_through_source_stamp": len(capture_poses),
        },
        "map_identity": {key: metadata[key] for key in (
            "epoch", "map_id", "frame_id", "snapshot_stamp_ns",
            "last_fused_depth_source_stamp_ns", "last_fusion_stamp_ns",
            "source_age_at_response_s")},
        "source_hashes": {
            "mapping_inputs": sha256(input_path),
            "snapshot_metadata": sha256(metadata_path),
            "raw_occupancy_archive": sha256(archive_path),
            "analyzer": sha256(Path(__file__)),
        },
        "queries": projections,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", action="append", dest="run_ids",
                        help="N06 run ID; may be repeated (defaults to wall/corridor r10)")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = {
        "schema": "n06-observation-coverage-diagnostic/v1",
        "qualification": (
            "Geometric cell-center visibility diagnostic only. It does not "
            "establish depth-ray clearing, map correctness, or safety approval."
        ),
        "near_clip_m": NEAR_CLIP_M,
        "layouts": [analyze_run(run_id) for run_id in (args.run_ids or DEFAULT_RUNS)],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({
        "output": str(args.output),
        "layouts": [{
            "run_id": row["run_id"],
            "queries": {
                key: {
                    "counts": value["raw_query_counts"],
                    "unknown_cell_centers": value["projection"]["unknown_cell_centers"],
                    "visible_during_capture": value[
                        "projection"]["ever_inside_geometric_image_during_capture"],
                } for key, value in row["queries"].items()
            },
        } for row in result["layouts"]],
    }, indent=2))


if __name__ == "__main__":
    main()
