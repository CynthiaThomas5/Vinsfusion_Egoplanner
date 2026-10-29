#!/usr/bin/env python3
"""Decode a single identity-bound raw/inflated snapshot against an injected box.

All world-frame reconciliation happens offline. Truth is not consumed by the
mapper or the online point-query collector.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from truth_reference import model_to_imu_contract, require_same_truth_reference

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from n10_map_query_contract import response_capture_error


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def point_to_cell(point_odom, origin, resolution, shape):
    index = np.floor((np.asarray(point_odom, dtype=float) - origin) / resolution).astype(int)
    if np.any(index < 0) or np.any(index >= np.asarray(shape, dtype=int)):
        return None
    return tuple(int(value) for value in index)


def voxel_centers(indices, origin, resolution):
    indices = np.asarray(indices, dtype=float)
    origin = np.asarray(origin, dtype=float)
    if indices.size == 0:
        return np.empty((0, 3), dtype=float)
    return origin[None, :] + (indices + 0.5) * resolution


def voxel_cells_fully_inside_box(indices, origin, resolution,
                                 rotation_world_from_odom,
                                 translation_world_from_odom,
                                 center_world, size_xyz, yaw_rad):
    """Return which center-selected voxels have all eight corners in a box.

    This distinguishes a center that falls just inside a surface from a voxel
    whose represented volume is wholly inside the obstacle. It says nothing
    about sensor visibility or whether the cell was occluded.
    """
    indices = np.asarray(indices, dtype=float)
    if indices.size == 0:
        return np.zeros(0, dtype=bool)
    centers_odom = voxel_centers(indices, origin, resolution)
    signs = np.asarray([
        [sx, sy, sz]
        for sx in (-1.0, 1.0)
        for sy in (-1.0, 1.0)
        for sz in (-1.0, 1.0)
    ])
    corner_offsets = signs * (float(resolution) / 2.0)
    corners_odom = centers_odom[:, None, :] + corner_offsets[None, :, :]
    corners_world = (corners_odom @ np.asarray(rotation_world_from_odom).T
                     + np.asarray(translation_world_from_odom)[None, None, :])
    corners_local = box_local(corners_world.reshape(-1, 3), center_world, yaw_rad)
    corners_local = corners_local.reshape(len(indices), 8, 3)
    half = np.asarray(size_xyz, dtype=float) / 2.0
    return np.all(np.abs(corners_local) <= half[None, None, :] + 1e-9,
                  axis=(1, 2))


def box_local(points_world, center_world, yaw_rad):
    points = np.asarray(points_world, dtype=float)
    center = np.asarray(center_world, dtype=float)
    c, s = math.cos(yaw_rad), math.sin(yaw_rad)
    world_to_box = np.asarray([[c, s, 0.0], [-s, c, 0.0], [0.0, 0.0, 1.0]])
    return (points - center) @ world_to_box.T


def signed_box_surface_distance(local_points, size_xyz):
    local = np.asarray(local_points, dtype=float)
    half = np.asarray(size_xyz, dtype=float) / 2.0
    excess = np.abs(local) - half
    outside = np.linalg.norm(np.maximum(excess, 0.0), axis=1)
    inside = np.all(excess <= 0.0, axis=1)
    inside_distance = np.min(half - np.abs(local), axis=1)
    return np.where(inside, inside_distance, outside)


def point_classification(point_world, rotation_world_from_odom, translation_world_from_odom,
                         origin, resolution, occupancy, inflated):
    rotation_world_from_odom = np.asarray(rotation_world_from_odom, dtype=float)
    translation_world_from_odom = np.asarray(translation_world_from_odom, dtype=float)
    origin = np.asarray(origin, dtype=float)
    point_odom = rotation_world_from_odom.T @ (
        np.asarray(point_world, dtype=float) - translation_world_from_odom)
    index = point_to_cell(point_odom, origin, resolution, occupancy.shape)
    if index is None:
        return {"inside_map": False, "xyz_odom_m": point_odom.tolist(), "cell_index_xyz": None,
                "raw_code": None, "inflated": None}
    return {"inside_map": True, "xyz_odom_m": point_odom.tolist(),
            "cell_index_xyz": list(index), "raw_code": int(occupancy[index]),
            "inflated": bool(inflated[index])}


def _load(path):
    return json.loads(Path(path).read_text())


def evaluate(run, output_path=None):
    run = Path(run).resolve()
    snapshot_dir = run / "n10-map-snapshot"
    metadata_path = snapshot_dir / "metadata.json"
    archive_path = snapshot_dir / "occupancy_snapshot.npz"
    observation_path = run / "n10-live-obstacle-observation.json"
    arrival_path = run / "arrival-evaluation-simtime-v2.json"
    point_query_path = run / "n10-map-point-queries.json"
    required = (metadata_path, archive_path, observation_path, arrival_path)
    if not all(path.is_file() for path in required):
        missing = [str(path) for path in required if not path.is_file()]
        raise FileNotFoundError("missing snapshot analysis inputs: " + ", ".join(missing))
    metadata = _load(metadata_path)
    observation = _load(observation_path)
    alignment = _load(arrival_path)
    truth_contract = model_to_imu_contract(run)
    require_same_truth_reference(alignment, truth_contract)
    if metadata.get("schema") != "plan-env-voxel-snapshot/v1":
        raise ValueError("unsupported map snapshot schema")
    if metadata.get("archive", {}).get("sha256") != sha256(archive_path):
        raise ValueError("snapshot archive hash does not match metadata")

    with np.load(archive_path, allow_pickle=False) as archive:
        occupancy = np.asarray(archive["occupancy"], dtype=np.int8)
        inflated = np.asarray(archive["inflated"], dtype=np.uint8)
    shape = tuple(int(value) for value in metadata["dimensions_xyz"])
    if occupancy.shape != shape or inflated.shape != shape:
        raise ValueError("snapshot shapes do not match metadata")
    if metadata.get("data_order") != "x_major_y_mid_z_fastest":
        raise ValueError("unsupported voxel data order")
    if not np.all(np.isin(occupancy, (-1, 0, 100))) or not np.all(np.isin(inflated, (0, 1))):
        raise ValueError("snapshot has invalid occupancy or inflation codes")

    identity = {key: metadata.get(key) for key in ("epoch", "map_id", "frame_id")}
    observation_identity = {
        "epoch": observation.get("epoch"),
        "map_id": observation.get("map_id_at_goal"),
        "frame_id": f"odom_{observation.get('epoch')}" if observation.get("epoch") else None,
    }
    identity_matches_observer = all(identity[key] == observation_identity[key] for key in identity)
    box = observation["obstacle"]
    center_world = np.asarray(box["pose_world_xyz_m"], dtype=float)
    size = np.asarray(box["size_xyz_m"], dtype=float)
    yaw = float(box.get("yaw_rad", 0.0))
    rotation = np.asarray(alignment["ground_rotation"], dtype=float)
    translation = np.asarray(alignment["ground_translation"], dtype=float)
    if rotation.shape != (3, 3) or translation.shape != (3,) or not np.isfinite(rotation).all():
        raise ValueError("invalid fixed alignment transform")
    if identity["frame_id"] != f"odom_{identity['epoch']}":
        raise ValueError("snapshot frame does not match its map epoch")

    origin = np.asarray(metadata["origin_m"], dtype=float)
    resolution = float(metadata["resolution_m"])
    if not math.isfinite(resolution) or resolution <= 0.0:
        raise ValueError("invalid map resolution")
    occupied_indices = np.argwhere(occupancy == 100)
    occupied_odom = voxel_centers(occupied_indices, origin, resolution)
    occupied_world = occupied_odom @ rotation.T + translation
    occupied_local = box_local(occupied_world, center_world, yaw)
    occupied_surface_distance = signed_box_surface_distance(occupied_local, size)
    occupied_inside = np.all(np.abs(occupied_local) <= size[None, :] / 2.0, axis=1)
    roi_band_m = max(0.30, 2.0 * resolution)
    near_box = occupied_surface_distance <= roi_band_m
    occupied_indices_roi = occupied_indices[near_box]
    occupied_odom_roi = occupied_odom[near_box]
    occupied_world_roi = occupied_world[near_box]
    occupied_local_roi = occupied_local[near_box]
    distances_roi = occupied_surface_distance[near_box]
    inside_roi = occupied_inside[near_box]
    inflated_roi = inflated[tuple(occupied_indices_roi.T)] if len(occupied_indices_roi) else np.empty(0)

    # Transform the world box test points back into the snapshot frame, then
    # read exact cells from this same raw/inflated snapshot.
    test_points = [{"label": "interior_center", "xyz_world_m": center_world}]
    half = size / 2.0
    face_axes = (("x", 0), ("y", 1), ("z", 2))
    for axis_name, axis in face_axes:
        for sign, side in ((-1.0, "negative"), (1.0, "positive")):
            local = np.zeros(3)
            local[axis] = sign * half[axis]
            c, s = math.cos(yaw), math.sin(yaw)
            box_to_world = np.asarray([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
            surface_world = center_world + box_to_world @ local
            outside_world = center_world + box_to_world @ (local + np.eye(3)[axis] * sign * 0.20)
            test_points.append({"label": f"{axis_name}_{side}_surface", "xyz_world_m": surface_world})
            test_points.append({"label": f"{axis_name}_{side}_outside_0p20m", "xyz_world_m": outside_world})
    test_point_rows = []
    for point in test_points:
        point_world = np.asarray(point["xyz_world_m"], dtype=float)
        test_point_rows.append({
            "label": point["label"],
            "xyz_world_m": point_world.tolist(),
            "snapshot_cell": point_classification(
                point_world, rotation, translation, origin, resolution, occupancy, inflated),
        })

    point_queries = _load(point_query_path) if point_query_path.is_file() else None
    point_query_identity_matches = None
    required_services_present = False
    point_query_capture_complete = False
    point_query_capture_errors = []
    query_by_label = {}
    if point_queries is not None:
        expected_labels = {'interior_center'} | {
            f'{axis}_{side}_{suffix}'
            for axis in ('x', 'y', 'z')
            for side in ('negative', 'positive')
            for suffix in ('surface', 'outside_0p20m')
        }
        query_labels = {row.get('label') for row in point_queries.get('queries', [])}
        query_services = {row.get('service') for row in point_queries.get('queries', [])}
        required_services_present = (
            query_labels == expected_labels
            and query_services == {
                '/mapping/query_occupancy_sphere',
                '/mapping/query_planning_occupancy',
            }
            and len(point_queries.get('queries', [])) == 2 * len(expected_labels)
        )
        point_query_identity_matches = (
            point_queries.get("identity", {}).get("epoch") == identity["epoch"]
            and point_queries.get("identity", {}).get("map_id") == identity["map_id"]
            and point_queries.get("identity", {}).get("frame_id") == identity["frame_id"]
            and point_queries.get('map_identity_stable') is True
            and all(row.get("identity_matches_request") for row in point_queries.get("queries", [])))
        point_query_capture_errors = [
            {"label": row.get("label"), "service": row.get("service"),
             "reason": response_capture_error(row)}
            for row in point_queries.get("queries", [])
            if response_capture_error(row)
        ]
        point_query_capture_complete = bool(
            required_services_present and point_query_identity_matches
            and len(point_queries.get("queries", [])) == 26
            and not point_query_capture_errors)
        for row in point_queries.get("queries", []):
            query_by_label.setdefault(row.get("label"), {})[row.get("service")] = row
    for row in test_point_rows:
        row["service_queries"] = query_by_label.get(row["label"], {})

    face_reports = {}
    surface_band = math.sqrt(3.0) * resolution / 2.0 + 1e-9
    surface_error_band = 1.5 * resolution
    for axis_name, axis in face_axes:
        for sign, side in ((-1.0, "negative"), (1.0, "positive")):
            face_mask = (sign * occupied_local[:, axis] >= half[axis] - surface_band)
            face_mask &= (sign * occupied_local[:, axis] <= half[axis] + surface_band)
            for other_axis in range(3):
                if other_axis == axis:
                    continue
                face_mask &= np.abs(occupied_local[:, other_axis]) <= half[other_axis] + surface_band
            selected = occupied_indices[face_mask]
            face_error = np.abs(sign * occupied_local[face_mask, axis] - half[axis])
            supported_surface = face_error <= surface_error_band
            face_reports[f"{axis_name}_{side}"] = {
                "surface_band_halfwidth_m": surface_band,
                "raw_occupied_center_count": int(len(selected)),
                "inflated_count": int(np.count_nonzero(inflated[tuple(selected.T)])) if len(selected) else 0,
                "surface_error_band_m": surface_error_band,
                "surface_center_error_sample_count": int(np.count_nonzero(supported_surface)),
                "surface_center_error_p95_m": float(np.percentile(face_error[supported_surface], 95))
                    if np.any(supported_surface) else None,
                "surface_center_error_max_m": float(np.max(face_error[supported_surface]))
                    if np.any(supported_surface) else None,
            }

    points_path = snapshot_dir / "box_roi_raw_occupied_points.jsonl"
    if not points_path.is_file():
        with points_path.open("w") as stream:
            for index, odom, world, local, distance, is_inside, is_inflated in zip(
                    occupied_indices_roi, occupied_odom_roi, occupied_world_roi,
                    occupied_local_roi, distances_roi, inside_roi, inflated_roi):
                stream.write(json.dumps({
                    "cell_index_xyz": [int(v) for v in index],
                    "xyz_odom_m": [float(v) for v in odom],
                    "xyz_world_m": [float(v) for v in world],
                    "xyz_box_local_m": [float(v) for v in local],
                    "distance_to_box_surface_m": float(distance),
                    "inside_box": bool(is_inside),
                    "inflated": bool(is_inflated),
                }, allow_nan=False) + "\n")

    codes = {"unknown": -1, "known_free": 0, "raw_occupied": 100}
    # Restrict the dense center classification to the box's transformed AABB;
    # a full-map meshgrid can require hundreds of megabytes for large maps.
    box_corners_local = np.asarray([
        [sx * half[0], sy * half[1], sz * half[2]]
        for sx in (-1.0, 1.0) for sy in (-1.0, 1.0) for sz in (-1.0, 1.0)
    ])
    c, s = math.cos(yaw), math.sin(yaw)
    box_to_world = np.asarray([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    corners_world = box_corners_local @ box_to_world.T + center_world
    corners_odom = (corners_world - translation) @ rotation
    index_min = np.floor((corners_odom.min(axis=0) - origin) / resolution).astype(int) - 1
    index_max = np.ceil((corners_odom.max(axis=0) - origin) / resolution).astype(int) + 1
    index_min = np.maximum(index_min, 0)
    index_max = np.minimum(index_max, np.asarray(shape, dtype=int) - 1)
    axis_indices = [np.arange(index_min[i], index_max[i] + 1) for i in range(3)]
    if any(len(values) == 0 for values in axis_indices):
        dense_shape = (0, 0, 0)
        all_indices = np.empty((0, 3), dtype=int)
    else:
        dense_shape = tuple(len(values) for values in axis_indices)
        all_indices = np.stack(np.meshgrid(*axis_indices, indexing="ij"), axis=-1).reshape(-1, 3)
    all_odom = voxel_centers(all_indices, origin, resolution)
    all_world = all_odom @ rotation.T + translation
    all_local = box_local(all_world, center_world, yaw)
    all_inside = np.all(np.abs(all_local) <= half[None, :], axis=1).reshape(dense_shape)
    if all_indices.size:
        dense_codes = occupancy[
            all_indices[:, 0], all_indices[:, 1], all_indices[:, 2]
        ].reshape(dense_shape)
    else:
        dense_codes = np.empty(dense_shape, dtype=np.int8)
    counts_inside = {name: 0 for name in codes}
    for name, code in codes.items():
        counts_inside[name] = int(np.count_nonzero(all_inside & (dense_codes == code)))
    center_inside_indices = all_indices[all_inside.reshape(-1)]
    center_inside_codes = dense_codes.reshape(-1)[all_inside.reshape(-1)]
    full_cell_inside = voxel_cells_fully_inside_box(
        center_inside_indices, origin, resolution, rotation, translation,
        center_world, size, yaw)
    fully_contained_counts = {name: 0 for name in codes}
    for name, code in codes.items():
        fully_contained_counts[name] = int(np.count_nonzero(
            full_cell_inside & (center_inside_codes == code)))
    center_inside_not_fully_contained_counts = {
        name: counts_inside[name] - fully_contained_counts[name]
        for name in codes
    }
    report = {
        "schema": "n10-box-map-snapshot-analysis/v1",
        "truth_reference_contract": truth_contract,
        "run_id": run.name,
        "classification": "offline single-snapshot geometry reconciliation; diagnostic only",
        "truth_used_online": False,
        "map_identity": identity,
        "snapshot_matches_live_observer_epoch_map_frame": bool(identity_matches_observer),
        "snapshot_source_stamp_ns": metadata["last_fused_depth_source_stamp_ns"],
        "snapshot_fusion_stamp_ns": metadata["last_fusion_stamp_ns"],
        "snapshot_header_stamp_ns": metadata["snapshot_stamp_ns"],
        "snapshot_source_coverage": metadata.get("snapshot_source_coverage"),
        "box": {"model_name": box.get("model_name"), "center_world_m": center_world.tolist(),
                "size_xyz_m": size.tolist(), "yaw_rad": yaw},
        "transform": {"source": arrival_path.name, "world_from_odom_rotation": rotation.tolist(),
                      "world_from_odom_translation_m": translation.tolist(),
                      "method": "one fixed prestream truth/VINS SE(3); no map-point fit"},
        "snapshot_roi": {
            "inside_box_voxel_counts_by_raw_class": counts_inside,
            "voxel_cell_geometry": {
                "method": "test all eight transformed voxel corners against the convex truth box, for cells whose centers lie inside",
                "all_corners_inside_box_counts_by_raw_class": fully_contained_counts,
                "center_inside_but_cell_not_fully_contained_counts_by_raw_class": (
                    center_inside_not_fully_contained_counts),
                "qualification": "all-corners-inside cells are geometrically inside the solid truth box and cannot be directly visible from outside; this does not classify free cells outside the obstacle by camera visibility",
            },
            "near_surface_raw_occupied_point_count": int(np.count_nonzero(near_box)),
            "near_surface_raw_occupied_inflated_count": int(np.count_nonzero(inflated_roi)),
            "near_surface_band_m": roi_band_m,
            "surface_face_samples": face_reports,
            "points": test_point_rows,
            "raw_occupied_point_archive": points_path.name,
            "raw_occupied_point_archive_sha256": sha256(points_path),
            "raw_occupied_point_archive_count": int(len(occupied_indices_roi)),
        },
        "point_query_archive": {
            "present": point_queries is not None,
            "same_map_identity": point_query_identity_matches,
            "query_count": len(point_queries.get("queries", [])) if point_queries else 0,
            "required_services_present": required_services_present,
            "capture_complete": point_query_capture_complete,
            "capture_error_count": len(point_query_capture_errors),
            "capture_errors": point_query_capture_errors,
            "snapshot_and_query_timestamp_equality_required": False,
        },
        "inputs_sha256": {path.name: sha256(path) for path in
                           (metadata_path, archive_path, observation_path, arrival_path)
                           + ((point_query_path,) if point_query_path.is_file() else ())},
        "qualification": "not map coverage, clearance, planner behavior, or N10 acceptance; missing/unknown remains distinct from raw free",
    }
    output = Path(output_path) if output_path else run / "n10-box-map-snapshot-analysis.json"
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    return report, output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--output", type=Path,
                        help="write report to a new path instead of replacing the default")
    args = parser.parse_args()
    report, _ = evaluate(args.run, args.output)
    print(json.dumps({
        "run_id": report["run_id"],
        "snapshot_matches_live_observer_epoch_map_frame": report[
            "snapshot_matches_live_observer_epoch_map_frame"],
        "point_query_same_map_identity": report["point_query_archive"]["same_map_identity"],
        "near_surface_raw_occupied_point_count": report["snapshot_roi"][
            "near_surface_raw_occupied_point_count"],
    }))


if __name__ == "__main__":
    main()
