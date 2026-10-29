#!/usr/bin/env python3
"""Summarize N10 injected-obstacle observations and all published splines.

The evaluator is read-only and post-run. It separates raw-cloud observations,
one identity-bound raw/inflated map snapshot, spline centerline geometry, and
actual full-body truth/SDF clearance. None is a runtime gate or formal
dynamic-replanning qualification.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from evaluate_n08_curve_certificate import bspline_eval
from truth_reference import model_to_imu_contract, require_same_truth_reference


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def int_or(value, fallback=-1):
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return fallback


def sample_centerline_to_box(spline, center, size, alignment_rotation=None,
                             alignment_translation=None, box_yaw_rad=0.0,
                             body_radius_m=None, required_body_clearance_m=0.0):
    message = spline.get('message', {})
    order = int(message.get('order', 0))
    control = np.asarray([[float(point['x']), float(point['y']), float(point['z'])]
                          for point in message.get('pos_pts', [])], dtype=float)
    knots = np.asarray(message.get('knots', []), dtype=float)
    if (control.ndim != 2 or control.shape[1] != 3
            or knots.size != control.shape[0] + order + 1
            or order < 1 or not np.isfinite(control).all()
            or not np.isfinite(knots).all()):
        return {'valid': False, 'reason': 'invalid_bspline'}
    begin, end = float(knots[order]), float(knots[control.shape[0]])
    if not math.isfinite(begin + end) or end <= begin:
        return {'valid': False, 'reason': 'invalid_bspline_duration'}
    count = max(501, int((end - begin) * 100) + 1)
    points = np.asarray([bspline_eval(knots, control, order, t)
                         for t in np.linspace(begin, end, count)])
    points_odom = points.copy()
    if alignment_rotation is not None:
        points = points @ np.asarray(alignment_rotation).T + np.asarray(alignment_translation)
    c, s = math.cos(box_yaw_rad), math.sin(box_yaw_rad)
    world_to_box = np.asarray([[c, s, 0.0], [-s, c, 0.0], [0.0, 0.0, 1.0]])
    local = (points - center) @ world_to_box.T
    outside = np.maximum(np.abs(local) - size / 2.0, 0.0)
    distance = np.linalg.norm(outside, axis=1)
    index = int(np.argmin(distance))
    first_margin_crossing = None
    if body_radius_m is not None:
        required_centerline_distance = (
            float(body_radius_m) + float(required_body_clearance_m))
        crossing = np.flatnonzero(distance <= required_centerline_distance)
        if crossing.size:
            first_margin_crossing = float(
                np.linspace(begin, end, count)[int(crossing[0])] - begin)
    return {
        'valid': True,
        'sample_count': int(count),
        'min_centerline_to_box_m': float(distance[index]),
        'minimum_centerline_body_margin_m': (
            float(distance[index] - float(body_radius_m))
            if body_radius_m is not None else None),
        'required_body_clearance_m': (
            float(required_body_clearance_m) if body_radius_m is not None else None),
        'first_required_clearance_crossing_offset_sim_s': first_margin_crossing,
        'sample_time_resolution_max_s': float((end - begin) / max(1, count - 1)),
        'closest_centerline_point_odom_m': points_odom[index].tolist(),
        'closest_centerline_point_world_m': points[index].tolist(),
        'method': ('dense sampled B-spline centerline distance to axis-aligned box; '
                   'body margin subtracts the yaw-invariant vehicle horizontal swept radius; '
                   'not a continuous-time vehicle clearance certificate'),
    }


def replan_clearance_policy(acceptance_config=None):
    if acceptance_config is None:
        return 0.10, 0.10  # Unchanged historical replay policy.
    config = json.loads(Path(acceptance_config).read_text())
    minimum = config['metrics']['dynamic_replanning']['acceptance_thresholds'].get(
        'minimum_planner_centerline_body_margin_m')
    return minimum, minimum if minimum is not None else 0.0


def evaluate(run, output=None, acceptance_config=None):
    run = Path(run).resolve()
    required_clearance, additional_deadline_margin = replan_clearance_policy(acceptance_config)
    paths = {
        'observation': run / 'n10-live-obstacle-observation.json',
        'planner': run / 'planner-observation.json',
        'flight': run / 'flight.json',
        'runtime': run / 'runtime-contract.json',
        'snapshot_metadata': run / 'n10-map-snapshot' / 'metadata.json',
        'snapshot_analysis': run / 'n10-box-map-snapshot-analysis.json',
        'body_clearance': run / 'n10-clearance-evaluation.json',
        'alignment': run / 'arrival-evaluation-simtime-v2.json',
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError('required obstacle diagnostic inputs missing: ' + ', '.join(missing))
    observation = json.loads(paths['observation'].read_text())
    runtime = json.loads(paths['runtime'].read_text())
    flight = json.loads(paths['flight'].read_text())
    metadata = json.loads(paths['snapshot_metadata'].read_text())
    snapshot = json.loads(paths['snapshot_analysis'].read_text())
    query_path = run / 'n10-map-point-queries.json'
    queries = json.loads(query_path.read_text()) if query_path.is_file() else {}
    if query_path.is_file():
        paths['map_queries'] = query_path
    box_clearance = json.loads(paths['body_clearance'].read_text())
    alignment = json.loads(paths['alignment'].read_text())
    contract = model_to_imu_contract(run)
    require_same_truth_reference(alignment, contract)
    require_same_truth_reference(box_clearance, contract)
    planner_rows = observation.get('matching_goal_splines', [])
    trigger_ns = int(observation['actual_injection_request_sim_ns'])
    center = np.asarray(observation['obstacle']['pose_world_xyz_m'], dtype=float)
    size = np.asarray(observation['obstacle']['size_xyz_m'], dtype=float)
    envelope_path = run.parent.parent.parent.parent / 'config' / 'components' / 'navigation' / 'vehicle_envelope.json'
    if not envelope_path.is_file():
        envelope_path = Path(__file__).resolve().parents[2] / 'config' / 'components' / 'navigation' / 'vehicle_envelope.json'
    envelope = json.loads(envelope_path.read_text())['geometry']
    paths['vehicle_envelope'] = envelope_path
    paths['injected_obstacle_sdf'] = run / observation['obstacle']['sdf_file']
    if not paths['injected_obstacle_sdf'].is_file():
        raise FileNotFoundError('injected obstacle SDF is missing from the run archive')
    body_radius = float(envelope['orientation_invariant_rotor_sweep_radius_m'])

    spline_rows = []
    for row in planner_rows:
        receipt_ns = row.get('receipt_sim_ns')
        if receipt_ns is None or int(receipt_ns) <= trigger_ns:
            continue
        geometry = sample_centerline_to_box(
            row, center, size, alignment['ground_rotation'],
            alignment['ground_translation'], observation['obstacle'].get('yaw_rad', 0.0),
            body_radius_m=body_radius, required_body_clearance_m=additional_deadline_margin)
        spline_start_ns = (
            int(row['message']['start_time']['sec']) * 1_000_000_000
            + int(row['message']['start_time']['nanosec']))
        crossing_offset = geometry.get(
            'first_required_clearance_crossing_offset_sim_s')
        spline_rows.append({
            'receipt_sim_ns': int(receipt_ns),
            'relative_receipt_sim_s': (int(receipt_ns) - trigger_ns) / 1e9,
            'traj_id': int(row['traj_id']),
            'spline_start_sim_ns': spline_start_ns,
            'first_required_clearance_crossing_sim_ns': (
                int(round(spline_start_ns + crossing_offset * 1e9))
                if crossing_offset is not None else None),
            **geometry,
        })
    cloud_rows = [{
        'relative_to_injection_sim_s': row.get('relative_to_injection_sim_s'),
        'stamp_ns': row.get('receipt_sim_ns'),
        'obstacle_roi_point_count': row.get('obstacle_roi_point_count'),
        'nearest_point_to_box_center_m': row.get('nearest_point_to_expected_obstacle_center_m'),
    } for row in observation.get('occupied_cloud_roi_observations', [])]
    first_cloud = next((row for row in cloud_rows
                        if isinstance(row['obstacle_roi_point_count'], int)
                        and row['obstacle_roi_point_count'] > 0), None)
    after_cloud = ([row for row in spline_rows
                    if first_cloud is not None
                    and row['relative_receipt_sim_s'] >= first_cloud['relative_to_injection_sim_s']]
                   if first_cloud else [])
    first_positive_after_cloud = next((row for row in after_cloud
                                       if row.get('min_centerline_to_box_m', 0.0) > 0.0), None)
    first_body_radius_after_cloud = next((row for row in after_cloud
                                          if row.get('min_centerline_to_box_m', 0.0) > body_radius), None)
    first_margin_safe_after_cloud = next((row for row in after_cloud
                                          if row.get('minimum_centerline_body_margin_m') is not None
                                          and (required_clearance is None or row['minimum_centerline_body_margin_m'] >= required_clearance)), None)
    prior_to_cloud = ([row for row in spline_rows
                       if first_cloud is not None
                       and row['receipt_sim_ns'] < int(first_cloud['stamp_ns'])]
                      if first_cloud else [])
    latest_pre_cloud_spline = prior_to_cloud[-1] if prior_to_cloud else None
    pre_cloud_commands = ([row for row in flight.get('position_command_history', [])
                           if row.get('goal_id') == observation.get('goal_id')
                           and row.get('epoch') == observation.get('epoch')
                           and int_or(row.get('flag')) == 1
                           and first_cloud is not None
                           and int_or(row.get('source_stamp_ns'))
                           < int(first_cloud['stamp_ns'])]
                          if first_cloud else [])
    latest_pre_cloud_command = pre_cloud_commands[-1] if pre_cloud_commands else None
    reference_trajectory_was_active = bool(
        latest_pre_cloud_spline is not None
        and latest_pre_cloud_command is not None
        and int_or(latest_pre_cloud_command.get('trajectory_id'))
        == int_or(latest_pre_cloud_spline.get('traj_id'), -2))
    if required_clearance is None:
        first_margin_safe_after_cloud = next((row for row in after_cloud
            if latest_pre_cloud_spline is not None
            and row['traj_id'] > latest_pre_cloud_spline['traj_id']), None)
    predicted_boundary_ns = ((latest_pre_cloud_spline or {}).get(
        'first_required_clearance_crossing_sim_ns'))
    safe_spline_receipt_ns = (first_margin_safe_after_cloud or {}).get('receipt_sim_ns')
    replanning_deadline = {
        'basis': ('latest planner spline received strictly before the first positive '
                  'EGO occupied-cloud ROI; first predicted entry into the vehicle swept '
                  'radius plus the configured additional clearance margin'),
        'additional_body_clearance_m': additional_deadline_margin,
        'first_positive_cloud_stamp_ns': (
            int(first_cloud['stamp_ns']) if first_cloud else None),
        'reference_trajectory_id': (latest_pre_cloud_spline or {}).get('traj_id'),
        'reference_trajectory_receipt_sim_ns': (latest_pre_cloud_spline or {}).get(
            'receipt_sim_ns'),
        'latest_strictly_pre_cloud_ready_command': latest_pre_cloud_command,
        'reference_trajectory_matches_latest_pre_cloud_ready_command': (
            reference_trajectory_was_active),
        'predicted_clearance_boundary_stamp_ns': predicted_boundary_ns,
        'available_time_to_clearance_boundary_sim_s': (
            (int(predicted_boundary_ns) - int(first_cloud['stamp_ns'])) / 1e9
            if predicted_boundary_ns is not None and first_cloud else None),
        'first_margin_qualified_replacement_trajectory_id': (
            (first_margin_safe_after_cloud or {}).get('traj_id')),
        'replacement_trajectory_receipt_sim_ns': safe_spline_receipt_ns,
        'replacement_delay_after_first_positive_cloud_sim_s': (
            (int(safe_spline_receipt_ns) - int(first_cloud['stamp_ns'])) / 1e9
            if safe_spline_receipt_ns is not None and first_cloud else None),
        'deadline_slack_after_replacement_sim_s': (
            (int(predicted_boundary_ns) - int(safe_spline_receipt_ns)) / 1e9
            if predicted_boundary_ns is not None and safe_spline_receipt_ns is not None
            else None),
        'minimum_clearance_sampling_resolution_sim_s': min(
            (row['sample_time_resolution_max_s'] for row in spline_rows), default=None),
        'dense_curve_crossing_is_diagnostic_not_a_continuous_certificate': True,
    }

    roi = snapshot.get('snapshot_roi', {})
    box_map = {
        'snapshot_identity_matches_live_observer': snapshot.get(
            'snapshot_matches_live_observer_epoch_map_frame'),
        'snapshot_source_stamp_ns': metadata.get('last_fused_depth_source_stamp_ns'),
        'snapshot_stamp_ns': metadata.get('snapshot_stamp_ns'),
        'snapshot_trigger_source': metadata.get('snapshot_trigger_source'),
        'snapshot_trigger_sim_ns': metadata.get('snapshot_trigger_sim_ns'),
        'snapshot_relative_to_injection_sim_s': (
            (int(metadata['snapshot_stamp_ns']) - trigger_ns) / 1e9
            if metadata.get('snapshot_stamp_ns') is not None else None),
        'snapshot_roi_inside_box_voxel_counts_by_raw_class': roi.get(
            'inside_box_voxel_counts_by_raw_class'),
        'snapshot_roi_near_surface_raw_occupied_count': roi.get(
            'near_surface_raw_occupied_point_count'),
        'snapshot_roi_near_surface_inflated_count': roi.get(
            'near_surface_raw_occupied_inflated_count'),
        'point_query_capture_complete': snapshot.get('point_query_archive', {}).get(
            'capture_complete'),
        'point_query_archive_present': query_path.is_file(),
        'point_queries_required': False,
        'point_query_error': queries.get('error'),
        'point_query_service_query_count': len(queries.get('queries', [])),
    }
    result = {
        'schema': 'n10-obstacle-replan-geometry/v3',
        'truth_reference_contract': contract,
        'run_id': run.name,
        'classification': 'offline single-run diagnostic; no formal replanning or clearance qualification',
        'read_only': True,
        'control_published': False,
        'identity': {
            'runtime_contract_sha256': runtime.get('sha256'),
            'goal_id': observation.get('goal_id'),
            'epoch': observation.get('epoch'),
            'map_id': observation.get('map_id_at_goal'),
        },
        'injection': {
            'trigger_sim_ns': trigger_ns,
            'obstacle': observation.get('obstacle'),
            'gazebo_create_acknowledged': (observation.get('gazebo_create') or {}).get('acknowledged'),
        },
        'raw_occupancy_cloud_observations': {
            'samples': cloud_rows,
            'first_sample_with_points': first_cloud,
        },
        'identity_bound_raw_inflated_snapshot': box_map,
        'planner_centerline_geometry': {
            'sample_count': len(spline_rows),
            'vehicle_horizontal_swept_radius_m': body_radius,
            'first_post_injection_spline': spline_rows[0] if spline_rows else None,
            'first_trajectory_with_positive_box_distance_after_cloud': first_positive_after_cloud,
            'first_trajectory_beyond_body_radius_after_cloud': first_body_radius_after_cloud,
            'first_trajectory_with_required_body_clearance_after_cloud': (
                first_margin_safe_after_cloud),
            'required_full_body_clearance_m': required_clearance,
            'clearance_numeric_limit_enabled': required_clearance is not None,
            'replacement_selection': ('configured margin-qualified spline' if required_clearance is not None else 'first new post-observation spline, no clearance-margin filter'),
            'replanning_deadline': replanning_deadline,
            'post_margin_qualified_spline_geometry': {
                'trajectory_count': sum(
                    first_margin_safe_after_cloud is not None
                    and row['traj_id'] >= first_margin_safe_after_cloud['traj_id']
                    for row in spline_rows),
                'minimum_centerline_body_margin_m': min(
                    (row['minimum_centerline_body_margin_m'] for row in spline_rows
                     if first_margin_safe_after_cloud is not None
                     and row['traj_id'] >= first_margin_safe_after_cloud['traj_id']),
                    default=None),
                'below_required_body_clearance_count': sum(
                    row['minimum_centerline_body_margin_m'] < (required_clearance if required_clearance is not None else 0.0)
                    for row in spline_rows
                    if first_margin_safe_after_cloud is not None
                    and row['traj_id'] >= first_margin_safe_after_cloud['traj_id']),
            },
            'relative_time_bins_s': [
                {
                    'start_s': start, 'end_s': end,
                    'count': len(rows),
                    'minimum_centerline_to_box_m': min(
                        (row['min_centerline_to_box_m'] for row in rows
                         if row.get('min_centerline_to_box_m') is not None),
                        default=None),
                    'maximum_centerline_to_box_m': max(
                        (row['min_centerline_to_box_m'] for row in rows
                         if row.get('min_centerline_to_box_m') is not None),
                        default=None),
                }
                for start, end in ((0, 1), (1, 2), (2, 4), (4, 8),
                                   (8, 15), (15, 30), (30, 60))
                for rows in [[row for row in spline_rows
                              if start <= row['relative_receipt_sim_s'] < end]]
                if rows
            ],
            'all_spline_rows': spline_rows,
            'qualification_limit': 'Centerline distance does not include the full body envelope, map uncertainty, or a continuous-time bound.',
        },
        'actual_body_clearance': {
            'scope': 'all scene colliders; independently measured complete task clearance, not a box-only claim',
            'classification': box_clearance.get('classification'),
            'sampled_minimum': box_clearance.get('sampled_minimum'),
            'maximum_observed_inter_sample_envelope_motion_m': box_clearance.get(
                'maximum_observed_inter_sample_envelope_motion_m'),
        },
        'inputs_sha256': {key: sha256(path) for key, path in paths.items()},
        'tool_sha256': sha256(Path(__file__)),
        'limitations': [
            'A replacement traj_id may be ordinary receding-horizon replanning; geometric distance and map observations are reported separately.',
            'Mapping support comes from the identity-bound raw/inflated snapshot and its reported observed ROI; point queries are optional diagnostics.',
            'Raw point cloud evidence and raw/inflated snapshot evidence are different timestamps and are not combined into one map state.',
            'The event-specific deadline is a dense sampled look-ahead on the last spline strictly before first positive cloud; the independent 4 ms full-body interval report is still required for executed motion.',
            'One diagnostic run does not establish general performance for other obstacle positions, geometry, velocity, or mapping load.',
        ],
    }
    output = Path(output) if output else run / 'n10-obstacle-replan-timing-analysis.json'
    if not output.is_absolute():
        output = run / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--acceptance-config', type=Path, help='Explicit current policy; omitted keeps legacy0.10m')
    args = parser.parse_args()
    report = evaluate(args.run, args.output, args.acceptance_config)
    print(json.dumps({
        'run_id': report['run_id'],
        'first_cloud_points_s': (report['raw_occupancy_cloud_observations'][
            'first_sample_with_points'] or {}).get('relative_to_injection_sim_s'),
        'first_post_cloud_body_radius_clear_spline': report['planner_centerline_geometry'][
            'first_trajectory_beyond_body_radius_after_cloud'],
        'snapshot_inside_box_classes': report['identity_bound_raw_inflated_snapshot'][
            'snapshot_roi_inside_box_voxel_counts_by_raw_class'],
    }, allow_nan=False))


if __name__ == '__main__':
    main()
