#!/usr/bin/env python3
"""Enumerate N05 raw unknown voxels intersecting selected entry volumes."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from n05_entry import (ROOT, _candidate_index_range, _rotation,
                       _voxel_is_below_ground, check_pose,
                       collision_primitives, load_policy, make_entry_schedule)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _classify_cells(snapshot, pose, phase, plane, policy, primitives):
    occupancy = np.asarray(snapshot['occupancy'])
    origin = np.asarray(snapshot['origin_m'], dtype=float)
    resolution = float(snapshot['resolution_m'])
    center = np.asarray(pose['center_xyz_m'], dtype=float)
    yaw = float(pose['yaw_rad'])
    body_rotation = np.asarray([
        [np.cos(yaw), -np.sin(yaw), 0.0],
        [np.sin(yaw), np.cos(yaw), 0.0],
        [0.0, 0.0, 1.0],
    ])
    margin = float(policy['spatial_budget']['combined_uncertainty_margin_m'])
    unknown = {}
    subground = set()

    for primitive in primitives:
        world_center = center + body_rotation @ np.asarray(
            primitive['center_imu_m'], dtype=float)
        if primitive['kind'] == 'box':
            world_rotation = body_rotation @ _rotation(primitive['rpy_rad'])
            half = np.asarray(primitive['size_m'], dtype=float) / 2.0
            world_half = np.abs(world_rotation) @ half + margin
            ranges = [
                _candidate_index_range(
                    world_center[i] - world_half[i],
                    world_center[i] + world_half[i],
                    origin[i], resolution, occupancy.shape[i])
                for i in range(3)
            ]
            if any(item is None for item in ranges):
                continue
            slices = tuple(slice(item[0], item[1] + 1) for item in ranges)
            starts = np.asarray([item.start for item in slices])
            indices = np.indices(
                tuple(item.stop - item.start for item in slices), dtype=float)
            indices += starts.reshape(3, 1, 1, 1)
            centers = np.asarray([
                origin[i] + (indices[i] + 0.5) * resolution
                for i in range(3)
            ])
            delta = centers - world_center.reshape(3, 1, 1, 1)
            local = np.einsum('i...,ij->j...', delta, world_rotation)
            excess = np.maximum(np.abs(local) - half.reshape(3, 1, 1, 1), 0.0)
            intersects = np.sqrt(np.sum(excess * excess, axis=0)) <= margin + 1e-12
        elif primitive['kind'] == 'rotor_disk':
            radius = float(primitive['radius_m'])
            half_height = float(primitive['half_height_m'])
            world_half = np.asarray([
                radius + margin, radius + margin, half_height + margin])
            ranges = [
                _candidate_index_range(
                    world_center[i] - world_half[i],
                    world_center[i] + world_half[i],
                    origin[i], resolution, occupancy.shape[i])
                for i in range(3)
            ]
            if any(item is None for item in ranges):
                continue
            slices = tuple(slice(item[0], item[1] + 1) for item in ranges)
            starts = np.asarray([item.start for item in slices])
            indices = np.indices(
                tuple(item.stop - item.start for item in slices), dtype=float)
            indices += starts.reshape(3, 1, 1, 1)
            centers = np.asarray([
                origin[i] + (indices[i] + 0.5) * resolution
                for i in range(3)
            ])
            delta = centers - world_center.reshape(3, 1, 1, 1)
            local = np.einsum('i...,ij->j...', delta, body_rotation)
            radial = np.hypot(local[0], local[1])
            excess_r = np.maximum(radial - radius, 0.0)
            excess_z = np.maximum(np.abs(local[2]) - half_height, 0.0)
            intersects = np.hypot(excess_r, excess_z) <= margin + 1e-12
        else:
            raise ValueError(f"unsupported vehicle primitive: {primitive['kind']}")

        values = occupancy[slices][intersects]
        intersected = np.argwhere(intersects) + starts
        voxel_centers = origin + (intersected + 0.5) * resolution
        for value, index, point in zip(values.tolist(), intersected, voxel_centers):
            key = tuple(int(component) for component in index)
            if _voxel_is_below_ground(
                    point, resolution, plane, phase, True, policy):
                subground.add(key)
            elif value == -1:
                unknown[key] = point

    checked = check_pose(snapshot, pose, phase, policy, primitives, plane, True)
    counts = checked.get('counts', {})
    if (len(unknown) != counts.get('unknown_cells')
            or len(subground) != counts.get('subground_excluded_cells')):
        raise RuntimeError(
            f"cell enumeration differs from N05 check_pose for {phase}: "
            f"unknown={len(unknown)}/{counts.get('unknown_cells')}, "
            f"subground={len(subground)}/{counts.get('subground_excluded_cells')}")

    points = np.asarray(list(unknown.values()), dtype=float)
    if points.size:
        x_hist = {}
        z_hist = {}
        for value in points[:, 0]:
            key = round(float(value), 1)
            x_hist[key] = x_hist.get(key, 0) + 1
        for value in points[:, 2]:
            key = round(float(value), 1)
            z_hist[key] = z_hist.get(key, 0) + 1
        extents = {
            'minimum_xyz_m': points.min(axis=0).tolist(),
            'maximum_xyz_m': points.max(axis=0).tolist(),
            'x_center_histogram_m': dict(sorted(x_hist.items())),
            'z_center_histogram_m': dict(sorted(z_hist.items())),
            'x_negative_count': int(np.count_nonzero(points[:, 0] < 0.0)),
            'x_nonnegative_count': int(np.count_nonzero(points[:, 0] >= 0.0)),
            'centers_odom_m': points.tolist(),
        }
    else:
        extents = {
            'minimum_xyz_m': None, 'maximum_xyz_m': None,
            'x_center_histogram_m': {}, 'z_center_histogram_m': {},
            'x_negative_count': 0, 'x_nonnegative_count': 0,
            'centers_odom_m': [],
        }
    return {
        'phase': phase,
        'check_pose_counts': counts,
        'unknown_count_unique': len(unknown),
        'subground_excluded_unique': len(subground),
        **extents,
    }


def audit(live_report_path, output_path):
    live_report_path = Path(live_report_path).resolve()
    report = json.loads(live_report_path.read_text())
    policy = load_policy(ROOT)
    archive = live_report_path.parent / report['snapshot']['archive']
    if (not archive.is_file()
            or sha256(archive) != report['snapshot']['archive_sha256']):
        raise ValueError('raw occupancy archive is missing or its hash differs')
    with np.load(archive, allow_pickle=False) as arrays:
        occupancy = arrays['occupancy']
    if tuple(occupancy.shape) != tuple(report['snapshot']['dimensions_xyz']):
        raise ValueError('raw occupancy shape differs from live report')

    identity = report['identity']
    state = report['state']
    admission = report['online_admission']
    snapshot = {
        'occupancy': occupancy,
        'origin_m': report['snapshot']['origin_m'],
        'resolution_m': report['snapshot']['resolution_m'],
        'dimensions_xyz': report['snapshot']['dimensions_xyz'],
        'frame_id': identity['frame_id'],
        'epoch': identity['epoch'],
        'map_id': identity['map_id'],
    }
    if (not identity.get('epoch')
            or not identity.get('map_id', '').startswith(identity['epoch'] + '-')
            or identity.get('frame_id') != 'odom_' + identity['epoch']):
        raise ValueError('live report epoch, map id, and frame do not match')
    ground_confirmed = bool(
        state['landed'] and not state['armed'] and not state['control_enabled'])
    if not ground_confirmed:
        raise ValueError('unknown-volume audit requires fresh landed and disarmed state')
    plane = admission['ground_plane']
    if not plane.get('valid'):
        raise ValueError('unknown-volume audit requires a valid raw-ground plane')

    schedule = make_entry_schedule(
        state['body_pose_imu_m'], admission['hold_height_m'],
        admission['sample_step_m'])
    poses = {
        phase: pose for phase, pose in schedule
        if phase in ('TAKEOFF_CONTACT', 'HOLD')
    }
    phases = [
        _classify_cells(snapshot, poses[phase], phase, plane,
                        policy, collision_primitives(ROOT))
        for phase in ('TAKEOFF_CONTACT', 'HOLD')
    ]
    hold = next(item for item in phases if item['phase'] == 'HOLD')
    output = {
        'schema': 'n07-n05-unknown-volume-audit/v1',
        'source_live_report': str(live_report_path.relative_to(ROOT)),
        'source_live_report_sha256': sha256(live_report_path),
        'source_snapshot_sha256': sha256(archive),
        'epoch': identity['epoch'], 'map_id': identity['map_id'],
        'scope': 'read-only enumeration of raw unknown cells intersecting N05 entry volumes; no controller input',
        'ground_plane_z_m': plane['z_at_center_m'],
        'hold_height_m': admission['hold_height_m'],
        'combined_uncertainty_margin_m': policy['spatial_budget']['combined_uncertainty_margin_m'],
        'hold_unknown_center_count': hold['unknown_count_unique'],
        'hold_unknown_center_count_below_ground_plane': sum(
            point[2] < plane['z_at_center_m'] for point in hold['centers_odom_m']),
        'phases': phases,
        'debug_truth_used': False,
    }
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live-report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.live_report, args.output)
    print(json.dumps({
        'output': str(args.output),
        'hold_unknown_count': result['hold_unknown_center_count'],
        'hold_unknown_below_ground': result['hold_unknown_center_count_below_ground_plane'],
        'ground_plane_z_m': result['ground_plane_z_m'],
        'hold_unknown_min_xyz_m': result['phases'][1]['minimum_xyz_m'],
        'hold_unknown_max_xyz_m': result['phases'][1]['maximum_xyz_m'],
        'hold_unknown_x_negative_count': result['phases'][1]['x_negative_count'],
    }, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
