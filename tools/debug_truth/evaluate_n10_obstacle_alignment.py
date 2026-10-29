#!/usr/bin/env python3
"""Offline fixed-SE(3) reconciliation for one N10 injected-box diagnostic."""
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from evaluate_n08_curve_certificate import bspline_eval


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def distance_to_world_box(points, center, size, yaw):
    c, s = math.cos(yaw), math.sin(yaw)
    rotation_z = np.asarray([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    local = (np.asarray(points) - center) @ rotation_z
    outside = np.maximum(np.abs(local) - size / 2.0, 0.0)
    return np.linalg.norm(outside, axis=1)


def sample_spline(spline, rotation, translation):
    message = spline['message']
    order = int(message['order'])
    control = np.asarray([[float(p['x']), float(p['y']), float(p['z'])]
                          for p in message.get('pos_pts', [])], dtype=float)
    knots = np.asarray(message.get('knots', []), dtype=float)
    if (control.ndim != 2 or control.shape[1] != 3
            or knots.size != control.shape[0] + order + 1
            or order < 1 or not np.isfinite(control).all()
            or not np.isfinite(knots).all()):
        return {'valid': False, 'reason': 'invalid_bspline'}
    start, end = float(knots[order]), float(knots[control.shape[0]])
    if not math.isfinite(start + end) or end <= start:
        return {'valid': False, 'reason': 'invalid_bspline_duration'}
    values = np.linspace(start, end, max(501, int((end - start) * 100) + 1))
    odom_points = np.asarray([bspline_eval(knots, control, order, value)
                              for value in values])
    world_points = odom_points @ rotation.T + translation
    return {'valid': True, 'sample_count': int(len(values)),
            'odom_min_xyz_m': odom_points.min(axis=0).tolist(),
            'odom_max_xyz_m': odom_points.max(axis=0).tolist(),
            'world_min_xyz_m': world_points.min(axis=0).tolist(),
            'world_max_xyz_m': world_points.max(axis=0).tolist(),
            'world_points': world_points}


def summarize_distance(points, center, size, yaw):
    distances = distance_to_world_box(points, center, size, yaw)
    index = int(np.argmin(distances))
    return {'sampled_centerline_min_distance_to_box_m': float(distances[index]),
            'closest_world_point_m': np.asarray(points[index]).tolist(),
            'sample_count': int(len(points))}


def evaluate(run):
    run = Path(run).resolve()
    observation_path = run / 'n10-live-obstacle-observation.json'
    arrival_path = run / 'arrival-evaluation-simtime-v2.json'
    flight_path = run / 'flight.json'
    if not all(p.is_file() for p in (observation_path, arrival_path, flight_path)):
        raise FileNotFoundError('observation, fixed-SE(3) arrival report and flight report are required')
    observation = json.loads(observation_path.read_text())
    arrival = json.loads(arrival_path.read_text())
    flight = json.loads(flight_path.read_text())
    align_rotation = np.asarray(arrival['ground_rotation'], dtype=float)
    align_translation = np.asarray(arrival['ground_translation'], dtype=float)
    if (align_rotation.shape != (3, 3) or align_translation.shape != (3,)
            or not np.isfinite(align_rotation).all()
            or not np.isfinite(align_translation).all()):
        raise ValueError('invalid fixed SE(3) alignment')

    box = observation['obstacle']
    box_center_world = np.asarray(box['pose_world_xyz_m'], dtype=float)
    box_size = np.asarray(box['size_xyz_m'], dtype=float)
    box_yaw = float(box.get('yaw_rad', 0.0))
    box_center_exact_odom = align_rotation.T @ (box_center_world - align_translation)
    box_center_assumed_odom = np.asarray(box['expected_center_odom_xyz_m'], dtype=float)
    assumed_center_world = align_rotation @ box_center_assumed_odom + align_translation

    trigger = observation.get('actual_injection_request_sim_ns')
    splines = observation.get('matching_goal_splines', [])
    before = [item for item in splines
              if trigger is not None and item.get('receipt_sim_ns') is not None
              and int(item['receipt_sim_ns']) <= int(trigger)]
    after = [item for item in splines
             if trigger is not None and item.get('receipt_sim_ns') is not None
             and int(item['receipt_sim_ns']) > int(trigger)]
    prior = before[-1] if before else None
    replacements = [item for item in after if prior is not None
                    and int(item['traj_id']) != int(prior['traj_id'])]
    first_replacement = replacements[0] if replacements else None
    spline_reports = {}
    for name, spline in [('immediately_pre_injection', prior),
                         ('first_post_injection', after[0] if after else None),
                         ('first_different_trajectory_id', first_replacement)]:
        sampled = sample_spline(spline, align_rotation, align_translation) if spline else None
        if sampled and sampled['valid']:
            points = sampled.pop('world_points')
            sampled['geometry'] = summarize_distance(points, box_center_world,
                                                     box_size, box_yaw)
        spline_reports[name] = sampled

    position_commands = [row for row in flight.get('position_command_history', [])
                         if row.get('goal_id') == flight.get('goal_id')
                         and row.get('epoch') == flight.get('localization_epoch')
                         and int(row.get('flag', -1)) == 1]
    command_world = []
    for row in position_commands:
        point = align_rotation @ np.asarray(row['position_enu'], dtype=float) + align_translation
        command_world.append({'world_xyz_m': point,
                              'traj_id': int(row['trajectory_id']),
                              'source_stamp_ns': int(row['source_stamp_ns'])})
    command_world.sort(key=lambda row: row['source_stamp_ns'])
    command_points = np.asarray([row['world_xyz_m'] for row in command_world])
    command_distances = distance_to_world_box(command_points, box_center_world,
                                              box_size, box_yaw)
    closest_index = int(np.argmin(command_distances))
    post_commands = [i for i, row in enumerate(command_world)
                     if trigger is not None and row['source_stamp_ns'] >= int(trigger)]
    post_distances = command_distances[post_commands] if post_commands else np.asarray([])
    per_trajectory = {}
    for traj_id in sorted({row['traj_id'] for row in command_world}):
        indices = [i for i, row in enumerate(command_world) if row['traj_id'] == traj_id]
        distances = command_distances[indices]
        per_trajectory[str(traj_id)] = {
            'sample_count': len(indices),
            'minimum_command_center_distance_to_box_m': float(np.min(distances)),
            'source_stamp_start_ns': min(command_world[i]['source_stamp_ns'] for i in indices),
            'source_stamp_end_ns': max(command_world[i]['source_stamp_ns'] for i in indices),
        }

    query_reports = []
    for row in observation.get('map_raw_observations', []):
        response = row.get('response') or {}
        request_center = row.get('request', {}).get('center') or {}
        request_odom = np.asarray([request_center.get(k, 0.0) for k in ('x', 'y', 'z')], dtype=float)
        request_world = align_rotation @ request_odom + align_translation
        query_reports.append({
            'label': row.get('label'),
            'request_sim_ns': row.get('request_sim_ns'),
            'response_sim_ns': row.get('response_sim_ns'),
            'request_center_odom_xyz_m': request_odom.tolist(),
            'request_center_world_xyz_m': request_world.tolist(),
            'request_center_inside_spawned_box': bool(np.all(
                np.abs(request_world - box_center_world) <= box_size / 2.0)),
            'radius_m': row.get('request', {}).get('radius_m'),
            'accepted': response.get('accepted'),
            'free': response.get('free'),
            'reason': response.get('reason'),
            'unknown_count': response.get('unknown_count'),
            'free_count': response.get('free_count'),
            'occupied_count': response.get('occupied_count'),
            'map_id': response.get('map_id'),
        })

    body_clearance_path = run / 'n10-live-obstacle-box-clearance.json'
    body_clearance = json.loads(body_clearance_path.read_text()) if body_clearance_path.is_file() else None
    report = {
        'schema': 'n10-obstacle-alignment-forensics/v1',
        'run_id': run.name,
        'classification': 'offline forensic reconciliation; one diagnostic run; not formal qualification',
        'fixed_alignment': {
            'source': arrival_path.name,
            'rotation': align_rotation.tolist(),
            'translation_m': align_translation.tolist(),
        },
        'obstacle_frame_reconciliation': {
            'sdf_world_center_m': box_center_world.tolist(),
            'expected_odom_center_m_from_protocol': box_center_assumed_odom.tolist(),
            'expected_odom_center_m_transformed_to_world': assumed_center_world.tolist(),
            'transformed_expected_center_minus_sdf_center_m':
                (assumed_center_world - box_center_world).tolist(),
            'exact_odom_center_from_sdf_and_fixed_alignment_m': box_center_exact_odom.tolist(),
            'assumed_minus_exact_odom_center_m':
                (box_center_assumed_odom - box_center_exact_odom).tolist(),
            'expected_odom_center_offset_norm_m': float(np.linalg.norm(
                assumed_center_world - box_center_world)),
            'box_size_m': box_size.tolist(),
            'box_yaw_rad': box_yaw,
        },
        'trajectory_geometry': {
            'injection_request_sim_ns': trigger,
            'pre_injection_traj_id': prior.get('traj_id') if prior else None,
            'first_different_traj_id_after_injection':
                first_replacement.get('traj_id') if first_replacement else None,
            'whole_spline_geometry_sampled_against_exact_world_box': spline_reports,
            'interpretation': 'A whole spline geometric sample is not an executed-command trace; compare with the time-stamped PositionCommand stream.',
        },
        'executed_reference_command_geometry': {
            'matching_ready_position_commands': len(command_world),
            'post_injection_command_count': len(post_commands),
            'minimum_all_command_center_distance_to_box_m': float(command_distances[closest_index]),
            'closest_command': {
                'traj_id': command_world[closest_index]['traj_id'],
                'source_stamp_ns': command_world[closest_index]['source_stamp_ns'],
                'world_xyz_m': command_world[closest_index]['world_xyz_m'].tolist(),
            },
            'minimum_post_injection_command_center_distance_to_box_m':
                float(np.min(post_distances)) if len(post_distances) else None,
            'trajectory_id_minimums': per_trajectory,
            'limitation': 'PositionCommand points do not replace a continuous executed-body envelope proof; the truth-based sampled body envelope report is retained separately.',
        },
        'truth_body_clearance': body_clearance,
        'raw_map_query_observations': query_reports,
        'camera_and_occupied_roi': {
            'depth_color_frame_count': len(observation.get('depth_and_color_frames', [])),
            'occupied_cloud_roi_observation_count': len(observation.get('occupied_cloud_roi_observations', [])),
            'occupied_cloud_roi_point_counts': [int(row.get('obstacle_roi_point_count', 0))
                                                for row in observation.get('occupied_cloud_roi_observations', [])],
            'limitation': 'The archive stores ROI counts and depth/color snapshots, but not the occupied point coordinates needed to bind each ROI point to the injected SDF box.',
        },
        'input_sha256': {name: sha256(run / name) for name in (
            'n10-live-obstacle-observation.json', 'arrival-evaluation-simtime-v2.json',
            'flight.json', 'n10-live-obstacle-analysis.json',
            'n10-live-obstacle-box-clearance.json') if (run / name).is_file()},
    }
    report.pop('truth_body_clearance')
    if body_clearance is not None:
        report['truth_body_clearance'] = {
            'sampled_minimum_clearance_m': body_clearance['sampled_minimum']['clearance_m'],
            'sampled_clearance_minus_max_observed_motion_m':
                body_clearance['sampled_clearance_minus_max_observed_motion_m'],
            'positive_sampled_lower_bound_supported':
                body_clearance['positive_sampled_lower_bound_supported'],
            'classification': body_clearance['classification'],
        }
    output = run / 'n10-obstacle-alignment-forensics.json'
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return report, output


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: evaluate_n10_obstacle_alignment.py RUN_DIR')
    result, output = evaluate(sys.argv[1])
    print(json.dumps({'output': str(output),
                      'classification': result['classification'],
                      'expected_odom_center_offset_norm_m': result['obstacle_frame_reconciliation']['expected_odom_center_offset_norm_m'],
                      'minimum_post_injection_command_center_distance_to_box_m': result['executed_reference_command_geometry']['minimum_post_injection_command_center_distance_to_box_m'],
                      'truth_body_sampled_clearance_lower_bound_m': result['truth_body_clearance']['sampled_clearance_minus_max_observed_motion_m'] if result.get('truth_body_clearance') else None,
                      'raw_map_queries': [{'label': row['label'], 'free': row['free'], 'occupied_count': row['occupied_count'], 'request_center_inside_spawned_box': row['request_center_inside_spawned_box']} for row in result['raw_map_query_observations']]}, indent=2))
