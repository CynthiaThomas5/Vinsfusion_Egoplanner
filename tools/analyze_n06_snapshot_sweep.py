#!/usr/bin/env python3
"""Replay the production raw-sphere and continuous-sweep rules on live N04 maps.

This is an offline map certificate helper. It never publishes ROS messages and
does not claim that the candidate line is an EGO-generated or flown trajectory.
The sphere and sweep arithmetic mirrors plan_env/sphere_query.h and
plan_env/swept_curve.h, while map bytes and identity come from live plan_env
snapshot archives.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np
from scipy.ndimage import distance_transform_edt

from n05_entry import ROOT, load_policy


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def query_sphere(snapshot, center, radius):
    """Mirror plan_env::querySphere over archived raw occupancy cells."""
    center = np.asarray(center, dtype=float)
    origin = np.asarray(snapshot['origin_m'], dtype=float)
    occupancy = snapshot['occupancy']
    resolution = float(snapshot['resolution_m'])
    extent = np.asarray(occupancy.shape, dtype=float) * resolution
    epsilon = 1e-9
    if (center.shape != (3,) or not np.isfinite(center).all()
            or not math.isfinite(radius) or radius <= 0 or radius > 2
            or not math.isfinite(resolution) or resolution <= 0):
        return {'accepted': False, 'reason': 'invalid_query',
                'unknown': 0, 'free': 0, 'occupied': 0}
    lower, upper = center - radius, center + radius
    if np.any(lower <= origin) or np.any(upper >= origin + extent):
        return {'accepted': False, 'reason': 'outside_map',
                'unknown': 0, 'free': 0, 'occupied': 0}
    size = np.asarray(occupancy.shape, dtype=int)
    lo = np.maximum(0, np.floor((lower - origin - epsilon) / resolution).astype(int))
    hi = np.minimum(size - 1,
                    np.floor((upper - origin + epsilon) / resolution).astype(int))
    if np.any(hi < lo):
        return {'accepted': False, 'reason': 'invalid_map_geometry',
                'unknown': 0, 'free': 0, 'occupied': 0}
    if int(np.prod(hi - lo + 1, dtype=np.int64)) > 100000:
        return {'accepted': False, 'reason': 'query_too_large',
                'unknown': 0, 'free': 0, 'occupied': 0}
    axes = [np.arange(lo[axis], hi[axis] + 1) for axis in range(3)]
    xx, yy, zz = np.meshgrid(*axes, indexing='ij')
    indices = (xx, yy, zz)
    distance_squared = np.zeros(xx.shape, dtype=float)
    for axis, index in enumerate(indices):
        cell_lower = origin[axis] + index * resolution
        cell_upper = cell_lower + resolution
        distance = np.maximum(np.maximum(cell_lower - center[axis], 0.0),
                              center[axis] - cell_upper)
        distance_squared += distance * distance
    local = occupancy[lo[0]:hi[0] + 1, lo[1]:hi[1] + 1, lo[2]:hi[2] + 1]
    cells = local[distance_squared <= (radius + epsilon) ** 2]
    unknown = int(np.count_nonzero(cells == -1))
    occupied = int(np.count_nonzero(cells == 100))
    free = int(np.count_nonzero(cells == 0))
    reason = ('occupied' if occupied else 'unknown' if unknown else
              'free' if free else 'empty_query')
    return {'accepted': True, 'reason': reason,
            'unknown': unknown, 'free': free, 'occupied': occupied}


def certify_line(snapshot, start, end, body_radius, hold_radius, speed_bound,
                 include_hold=True):
    start, end = np.asarray(start, dtype=float), np.asarray(end, dtype=float)
    length = float(np.linalg.norm(end - start))
    duration = length / speed_bound if speed_bound > 0 else 0.0
    resolution = float(snapshot['resolution_m'])
    count = max(1, math.ceil(speed_bound * duration / (resolution / 4.0)))
    if count > 10000:
        return {'free': False, 'reason': 'sweep_too_large', 'queries': 0,
                'wall_ms': 0.0, 'length_m': length}
    dt = duration / count
    cover_radius = body_radius + speed_bound * dt / 2.0
    started = time.perf_counter()
    failures = []
    for index in range(count):
        mid = (index + 0.5) * dt
        fraction = 0.5 if duration == 0 else mid / duration
        center = start + (end - start) * fraction
        result = query_sphere(snapshot, center, cover_radius)
        if not result['accepted'] or result['reason'] != 'free':
            failures.append({'sample_index': index, 'time_s': mid,
                             'center_xyz_m': center.tolist(), **result})
            break
    terminal = None
    if not failures and include_hold:
        terminal = query_sphere(snapshot, end, body_radius + hold_radius)
        if not terminal['accepted'] or terminal['reason'] != 'free':
            failures.append({'sample_index': count, 'time_s': duration,
                             'center_xyz_m': end.tolist(), **terminal,
                             'phase': 'terminal_hold_neighborhood'})
    return {'free': not failures,
            'reason': 'free' if not failures else failures[0]['reason'],
            'queries': count + int(terminal is not None),
            'wall_ms': (time.perf_counter() - started) * 1000.0,
            'length_m': length, 'duration_s': duration,
            'speed_bound_m_s': speed_bound,
            'body_radius_m': body_radius,
            'continuous_cover_radius_m': cover_radius,
            'terminal_hold_radius_m': body_radius + hold_radius if include_hold else None,
            'terminal_hold': terminal,
            'first_failure': failures[0] if failures else None}


def find_candidates(snapshot, body_radius, hold_radius, speed_bound):
    occupancy = snapshot['occupancy']
    resolution = float(snapshot['resolution_m'])
    origin = np.asarray(snapshot['origin_m'], dtype=float)
    terminal_radius = body_radius + hold_radius
    # Any continuous clear center is within half a voxel diagonal of a sampled
    # cell center. This is only a candidate bound; every candidate is checked
    # below by the exact closed-cell sphere predicate.
    cell_half_diagonal = math.sqrt(3.0) * resolution / 2.0
    clearance = distance_transform_edt(occupancy == 0, sampling=resolution)
    indices = np.argwhere(clearance > terminal_radius - cell_half_diagonal)
    offsets = np.linspace(-resolution / 2.0, resolution / 2.0,
                          int(round(resolution / 0.025)) + 1)
    points = {}
    candidates_checked = 0
    for index in indices:
        cell_center = origin + (index + 0.5) * resolution
        for dx in offsets:
            for dy in offsets:
                for dz in offsets:
                    point = cell_center + np.asarray([dx, dy, dz])
                    candidates_checked += 1
                    query = query_sphere(snapshot, point, terminal_radius)
                    if query['accepted'] and query['reason'] == 'free':
                        points[tuple(np.round(point, 6))] = point
    return (list(points.values()), candidates_checked,
            float(clearance.max()), int(np.count_nonzero(clearance > terminal_radius)))


def find_chain(snapshot, points, body_radius, hold_radius, speed_bound):
    # Find two spatially continuous candidate curves sharing an exactly
    # identical terminal/start hold point and the same map snapshot identity.
    max_length = 1.0
    certified = []
    failures = {}
    for i, start in enumerate(points):
        for j, middle in enumerate(points):
            if i == j:
                continue
            length = float(np.linalg.norm(middle - start))
            if length < 0.05 or length > max_length:
                continue
            first = certify_line(snapshot, start, middle, body_radius,
                                 hold_radius, speed_bound)
            if not first['free']:
                failures[first['reason']] = failures.get(first['reason'], 0) + 1
                continue
            for k, end in enumerate(points):
                if k in (i, j):
                    continue
                next_length = float(np.linalg.norm(end - middle))
                if next_length < 0.05 or next_length > max_length:
                    continue
                second = certify_line(snapshot, middle, end, body_radius,
                                      hold_radius, speed_bound)
                if second['free']:
                    certified.append((length + next_length, start, middle, end,
                                      first, second))
                else:
                    failures[second['reason']] = failures.get(second['reason'], 0) + 1
    if not certified:
        return None, failures
    certified.sort(key=lambda item: item[0], reverse=True)
    total, start, middle, end, first, second = certified[0]
    emergency = certify_line(snapshot, start, middle, body_radius + hold_radius,
                             0.0, speed_bound, include_hold=False)
    return ({'start_xyz_m': start.tolist(), 'handoff_xyz_m': middle.tolist(),
             'end_xyz_m': end.tolist(), 'total_length_m': total,
             'same_handoff_pose': True, 'first_curve': first,
             'second_curve': second,
             'emergency_hold_envelope_over_first_curve': emergency}, failures)


def analyze_run(run_id, snapshot_name, policy, planner_config):
    run_dir = ROOT / 'artifacts/runs' / run_id
    snap_dir = run_dir / 'snapshots' / snapshot_name
    metadata_path = snap_dir / 'metadata.json'
    archive_path = snap_dir / 'occupancy_snapshot.npz'
    metadata = json.loads(metadata_path.read_text())
    archive_hash = sha256(archive_path)
    archive = np.load(archive_path)
    occupancy = np.asarray(archive['occupancy'], dtype=np.int8)
    expected = tuple(metadata['dimensions_xyz'])
    identity = {
        'epoch': metadata['epoch'], 'map_id': metadata['map_id'],
        'frame_id': metadata['frame_id'],
        'epoch_match': metadata['epoch'] == metadata['expected_epoch'],
        'map_id_matches_epoch': metadata['map_id'].startswith(metadata['epoch'] + '-'),
        'frame_matches_epoch': metadata['frame_id'] == 'odom_' + metadata['epoch'],
        'status_before_matches': metadata['map_status_before']['map_id'] == metadata['map_id'],
        'status_after_matches': metadata['map_status_after']['map_id'] == metadata['map_id'],
        'reset_acknowledged': metadata['map_status_after']['reset_acknowledged'],
        'input_ready': metadata['map_status_after']['input_ready'],
    }
    freshness = {
        'source_age_at_response_s': metadata['source_age_at_response_s'],
        'fusion_age_at_response_s': (metadata['snapshot_stamp_ns']
                                     - metadata['last_fusion_stamp_ns']) / 1e9,
        'max_sim_age_s': 0.4,
    }
    configuration = metadata['configuration']
    source_valid = bool(
        identity['epoch_match'] and identity['map_id_matches_epoch']
        and identity['frame_matches_epoch'] and identity['status_before_matches']
        and identity['status_after_matches'] and identity['reset_acknowledged']
        and identity['input_ready'] and occupancy.shape == expected
        and np.isin(occupancy, (-1, 0, 100)).all()
        and freshness['source_age_at_response_s'] <= 0.4
        and freshness['fusion_age_at_response_s'] <= 0.4
        and configuration['planner_config_sha256'] == sha256(
            ROOT / 'config/components/mapping/ego_planner.json')
    )
    snapshot = {'occupancy': occupancy, 'origin_m': metadata['origin_m'],
                'resolution_m': metadata['resolution_m'],
                'dimensions_xyz': metadata['dimensions_xyz']}
    actual_pose_result = None
    inputs_path = run_dir / 'inputs/mapping-inputs.json'
    if inputs_path.is_file():
        inputs = json.loads(inputs_path.read_text())
        odometry = inputs.get('optimized_odometry', [])
        before = [item for item in odometry
                  if item['stamp_ns'] <= metadata['snapshot_stamp_ns']]
        if before:
            nearest = max(before, key=lambda item: item['stamp_ns'])
            position = nearest['position']
            actual_pose_result = {
                'stamp_ns': nearest['stamp_ns'],
                'frame_id': nearest['frame_id'],
                'position_xyz_m': position,
                'snapshot_minus_pose_s': (metadata['snapshot_stamp_ns']
                                          - nearest['stamp_ns']) / 1e9,
                'body_sphere_query': query_sphere(
                    snapshot, position, policy['spatial_budget']['body_reference_clearance_radius_m']),
                'terminal_hold_query': query_sphere(
                    snapshot, position,
                    policy['spatial_budget']['body_reference_clearance_radius_m']
                    + policy['map_policy']['terminal_hold_neighborhood_radius_m']),
            }
    search_started = time.perf_counter()
    points, candidate_checks, clearance_max, terminal_center_count = find_candidates(
        snapshot, policy['spatial_budget']['body_reference_clearance_radius_m'],
        policy['map_policy']['terminal_hold_neighborhood_radius_m'],
        float(planner_config['max_velocity_m_s'])) if source_valid else ([], 0, 0.0, 0)
    chain, handoff_failures = find_chain(
        snapshot, points,
        policy['spatial_budget']['body_reference_clearance_radius_m'],
        policy['map_policy']['terminal_hold_neighborhood_radius_m'],
        float(planner_config['max_velocity_m_s'])) if source_valid else (None, {})
    return {
        'run_id': run_id, 'layout_id': json.loads((run_dir / 'world-manifest.json').read_text())['layout_id'],
        'snapshot': snapshot_name, 'archive': {
            'path': str(archive_path.relative_to(ROOT)), 'sha256': archive_hash,
            'schema': metadata['schema'], 'data_order': metadata['data_order'],
            'raw_codes': metadata['occupancy_codes']},
        'identity': identity, 'freshness': freshness,
        'source_valid_for_replay': source_valid,
        'configuration': {
            'policy_sha256': sha256(ROOT / 'config/components/navigation/vehicle_envelope.json'),
            'planner_sha256': configuration['planner_config_sha256'],
            'body_radius_m': policy['spatial_budget']['body_reference_clearance_radius_m'],
            'planner_radius_m': planner_config['obstacles_inflation_m'],
            'terminal_hold_neighborhood_radius_m': policy['map_policy']['terminal_hold_neighborhood_radius_m'],
            'raw_query_radius_matches_n05': abs(
                planner_config['obstacles_inflation_m']
                - policy['spatial_budget']['body_reference_clearance_radius_m']) <= 1e-9},
        'actual_vins_pose_at_or_before_snapshot': actual_pose_result,
        'candidate_search': {
            'method': 'voxel-distance-transform bound followed by exact closed-cell raw sphere queries; 0.025 m subvoxel candidate grid',
            'max_free_cell_center_distance_m': clearance_max,
            'centers_above_terminal_radius': terminal_center_count,
            'exact_candidate_query_count': candidate_checks,
            'exact_terminal_hold_centers': len(points),
            'search_wall_ms': (time.perf_counter() - search_started) * 1000.0},
        'offline_curve_chain': chain,
        'handoff_rejections': handoff_failures,
        'qualification': 'offline replay of actual raw map snapshot using production sphere/sweep arithmetic; no EGO-generated trajectory, simulated control, flight, or braking dynamics.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', action='append', required=True)
    parser.add_argument('--snapshot', default='snapshot-03')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    policy = load_policy()
    planner_config = json.loads((ROOT / 'config/components/mapping/ego_planner.json').read_text())
    radius = policy['spatial_budget']['body_reference_clearance_radius_m']
    if abs(planner_config['obstacles_inflation_m'] - radius) > 1e-9:
        raise SystemExit('planner sphere does not match the N05 body reference radius')
    if not 0 <= policy['map_policy']['terminal_hold_neighborhood_radius_m'] <= 1.0:
        raise SystemExit('invalid N05 terminal hold neighborhood radius')
    result = {
        'schema': 'n06-actual-map-sweep-replay/v1',
        'scope': 'N06 offline certificate search on actual Gazebo+VINS+plan_env raw occupancy snapshots; not a live EGO trajectory or movement qualification.',
        'source_files': {
            'vehicle_envelope_sha256': sha256(ROOT / 'config/components/navigation/vehicle_envelope.json'),
            'planner_config_sha256': sha256(ROOT / 'config/components/mapping/ego_planner.json'),
            'sphere_query_header_sha256': sha256(ROOT / 'src/vendor/ego_planner/planner/plan_env/include/plan_env/sphere_query.h'),
            'swept_curve_header_sha256': sha256(ROOT / 'src/vendor/ego_planner/planner/plan_env/include/plan_env/swept_curve.h'),
        },
        'speed_bound_m_s': planner_config['max_velocity_m_s'],
        'layouts': [analyze_run(run_id, args.snapshot, policy, planner_config)
                    for run_id in args.run_id],
    }
    result['all_snapshots_valid'] = all(x['source_valid_for_replay'] for x in result['layouts'])
    result['two_layout_certificates'] = (len({x['layout_id'] for x in result['layouts']
                                             if x['offline_curve_chain']}) >= 2)
    result['n06_positive_exit_supported'] = bool(
        result['all_snapshots_valid'] and result['two_layout_certificates'])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
