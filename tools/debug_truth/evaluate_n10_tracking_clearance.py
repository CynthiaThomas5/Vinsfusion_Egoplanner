#!/usr/bin/env python3
"""Relate EGO command-tracking residuals to observed route obstacle margins.

This offline comparison uses one fixed prestream transform and the same
full-body envelope for the commanded and truth positions at each source stamp.
It is diagnostic; it creates no runtime gate and no collision guarantee.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from truth_reference import imu_truth_samples, require_same_truth_reference

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/debug_truth'))
from evaluate_n10_clearance import (distance_to_obstacle, parse_obstacles,
                                    vehicle_vertical_cylinder)
from evaluate_n10_interval_clearance_bound import (
    _collision_component_spheres,
    quaternion_rotation,
)
from evaluate_n10_cross_run_calibration import _truth_pose_at
from evaluate_arrival import evaluate_run as evaluate_arrival


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def stats(values):
    if not values:
        return {'count': 0, 'p50': None, 'p95': None, 'p99': None, 'max': None}
    array = np.asarray(values, dtype=float)
    return {
        'count': int(array.size),
        'p50': float(np.percentile(array, 50)),
        'p95': float(np.percentile(array, 95)),
        'p99': float(np.percentile(array, 99)),
        'max': float(np.max(array)),
    }


def translation_only_clearance_lower_bound(command_clearance_m, position_error_m):
    """Pointwise distance lower bound for translation with fixed geometry.

    Distance between a fixed obstacle and a translated, unchanged body envelope
    is 1-Lipschitz in position. This does not bound attitude/shape changes,
    obstacle motion between timestamps, map/model error, or motion between
    samples; a negative result means this bound cannot establish positive
    clearance, not that a collision occurred.
    """
    command_clearance_m = float(command_clearance_m)
    position_error_m = float(position_error_m)
    if not math.isfinite(command_clearance_m) or not math.isfinite(position_error_m):
        raise ValueError('clearance and position error must be finite')
    if position_error_m < 0.0:
        raise ValueError('position error must be non-negative')
    return command_clearance_m - position_error_m


def component_tracking_clearances(rows, components, obstacles, imu_model_offset,
                                  dynamic_model=None, injection_ns=None):
    """Compare actual and command positions with SDF collision-component spheres.

    Both poses use each sample's observed attitude, isolating translation only.
    Dynamic obstacles are included only at/after their recorded insertion stamp.
    """
    if not rows or not components or not obstacles:
        raise ValueError('component_tracking_geometry_inputs_empty')
    actual = np.asarray([row['truth_xyz_world_m'] for row in rows], dtype=float)
    command = np.asarray([row['command_xyz_world_m'] for row in rows], dtype=float)
    rotations = np.asarray([quaternion_rotation(row['q_xyzw']) for row in rows])
    stamps = np.asarray([int(row['source_stamp_ns']) for row in rows], dtype=np.int64)
    imu_offset = np.asarray(imu_model_offset, dtype=float)
    if imu_offset.shape != (3,) or not np.isfinite(imu_offset).all():
        raise ValueError('invalid_model_origin_to_imu_offset')
    local_centers = np.asarray(
        [item['center_model_origin_m'] for item in components], dtype=float
    ) - imu_offset
    radii = np.asarray(
        [item['enclosing_sphere_radius_m'] for item in components], dtype=float
    )
    actual_centers = actual[:, None, :] + np.einsum(
        'nij,kj->nki', rotations, local_centers)
    command_centers = command[:, None, :] + np.einsum(
        'nij,kj->nki', rotations, local_centers)
    count = len(rows)
    actual_clearance = np.full(count, np.inf, dtype=float)
    command_clearance = np.full(count, np.inf, dtype=float)
    command_clearance_to_actual_nearest = np.full(count, np.inf, dtype=float)
    actual_component = np.full(count, -1, dtype=int)
    actual_obstacle = np.full(count, -1, dtype=int)

    for obstacle_index, obstacle in enumerate(obstacles):
        active = np.ones(count, dtype=bool)
        if (dynamic_model and obstacle['name'].split('/')[0] == dynamic_model):
            active = (injection_ns is not None) & (stamps >= int(injection_ns))
            if not np.any(active):
                continue
        actual_delta = actual_centers - np.asarray(obstacle['center_xyz_m'], dtype=float)
        command_delta = command_centers - np.asarray(obstacle['center_xyz_m'], dtype=float)
        if obstacle['kind'] == 'vertical_cylinder':
            actual_horizontal = np.maximum(
                0.0,
                np.linalg.norm(actual_delta[:, :, :2], axis=2)
                - float(obstacle['radius_m']),
            )
            command_horizontal = np.maximum(
                0.0,
                np.linalg.norm(command_delta[:, :, :2], axis=2)
                - float(obstacle['radius_m']),
            )
        else:
            yaw = float(obstacle['yaw_rad'])
            cosine, sine = math.cos(yaw), math.sin(yaw)
            half = np.asarray(obstacle['size_xyz_m'][:2], dtype=float) / 2.0
            actual_x = cosine * actual_delta[:, :, 0] + sine * actual_delta[:, :, 1]
            actual_y = -sine * actual_delta[:, :, 0] + cosine * actual_delta[:, :, 1]
            command_x = cosine * command_delta[:, :, 0] + sine * command_delta[:, :, 1]
            command_y = -sine * command_delta[:, :, 0] + cosine * command_delta[:, :, 1]
            actual_horizontal = np.linalg.norm(np.stack((
                np.maximum(np.abs(actual_x) - half[0], 0.0),
                np.maximum(np.abs(actual_y) - half[1], 0.0),
            ), axis=2), axis=2)
            command_horizontal = np.linalg.norm(np.stack((
                np.maximum(np.abs(command_x) - half[0], 0.0),
                np.maximum(np.abs(command_y) - half[1], 0.0),
            ), axis=2), axis=2)
        actual_vertical = np.maximum(
            0.0,
            np.maximum(
                float(obstacle['z_min_m']) - actual_centers[:, :, 2],
                actual_centers[:, :, 2] - float(obstacle['z_max_m']),
            ),
        )
        command_vertical = np.maximum(
            0.0,
            np.maximum(
                float(obstacle['z_min_m']) - command_centers[:, :, 2],
                command_centers[:, :, 2] - float(obstacle['z_max_m']),
            ),
        )
        actual_gap = np.maximum(
            0.0, np.hypot(actual_horizontal, actual_vertical) - radii[None, :]
        )
        command_gap = np.maximum(
            0.0, np.hypot(command_horizontal, command_vertical) - radii[None, :]
        )
        actual_gap[~active, :] = np.inf
        command_gap[~active, :] = np.inf
        best_component = np.argmin(actual_gap, axis=1)
        best_actual = actual_gap[np.arange(count), best_component]
        changed = best_actual < actual_clearance
        actual_clearance[changed] = best_actual[changed]
        actual_component[changed] = best_component[changed]
        actual_obstacle[changed] = obstacle_index
        command_clearance_to_actual_nearest[changed] = command_gap[
            np.arange(count)[changed], best_component[changed]
        ]
        command_clearance = np.minimum(
            command_clearance, np.min(command_gap, axis=1)
        )

    result = []
    for index, row in enumerate(rows):
        if actual_component[index] < 0 or actual_obstacle[index] < 0:
            raise ValueError(f'no_active_obstacle_for_tracking_sample:{int(stamps[index])}')
        result.append({
            'source_stamp_ns': int(stamps[index]),
            'actual_component_clearance_m': float(actual_clearance[index]),
            'command_clearance_to_actual_nearest_component_obstacle_m': float(
                command_clearance_to_actual_nearest[index]),
            'minimum_command_component_clearance_any_obstacle_m': float(
                command_clearance[index]),
            'nearest_actual_component': components[int(actual_component[index])]['name'],
            'nearest_actual_obstacle': obstacles[int(actual_obstacle[index])]['name'],
        })
    return result


def evaluate(run, output):
    run = Path(run).resolve()
    output = Path(output).resolve()
    names = {
        'flight': run / 'flight.json',
        'truth': run / 'debug-truth-evaluation.json',
        'runtime_contract': run / 'runtime-contract.json',
        'envelope': ROOT / 'config/components/navigation/vehicle_envelope.json',
        'world': run / 'n10-dynamic-clearance-world.sdf',
        'observation': run / 'n10-live-obstacle-observation.json',
        'contact_model_manifest': run / 'n09-contact-model-manifest.json',
        'base_collision_model': run / 'n09-contact-models/x500_base/model.sdf',
        'vehicle_collision_model': run / 'n09-contact-models/x500_d435i/model.sdf',
        'camera_collision_model': run / 'n09-contact-models/d435i/model.sdf',
    }
    required_capture_names = (
        'flight', 'truth', 'runtime_contract', 'envelope', 'world', 'observation')
    missing = [str(names[name]) for name in required_capture_names
               if not names[name].is_file()]
    if missing:
        raise FileNotFoundError('missing tracking/clearance inputs: ' + ', '.join(missing))
    flight = json.loads(names['flight'].read_text())
    runtime_contract = json.loads(names['runtime_contract'].read_text())
    action_result = flight.get('action_result') or {}
    native_success = bool(
        flight.get('action_success') is True
        and action_result.get('success') is True
        and action_result.get('outcome') == 'succeeded'
    )
    if (not native_success
            or not isinstance(flight.get('goal_completed_source_ns'), int)):
        observation = json.loads(names['observation'].read_text())
        identity = {
            'run_directory_matches_selected_run': (
                run.name == (flight.get('run_id') or run.name)),
            'runtime_contract_identity_sha256': runtime_contract.get('sha256'),
            'goal_id': flight.get('goal_id'),
            'epoch': flight.get('localization_epoch'),
            'map_id': observation.get('map_id_at_goal'),
            'goal_map_identity_matches': bool(
                flight.get('goal_id')
                and flight.get('localization_epoch')
                and observation.get('run_id') == run.name
                and observation.get('goal_id') == flight.get('goal_id')
                and observation.get('epoch') == flight.get('localization_epoch')
                and str(observation.get('map_id_at_goal') or '').startswith(
                    flight.get('localization_epoch', '') + '-')),
        }
        input_paths = {
            'flight': names['flight'],
            'truth': names['truth'],
            'runtime_contract': names['runtime_contract'],
            'envelope': names['envelope'],
            'world': names['world'],
            'observation': names['observation'],
            'contact_model_manifest': names['contact_model_manifest'],
            'base_collision_model': names['base_collision_model'],
            'vehicle_collision_model': names['vehicle_collision_model'],
            'camera_collision_model': names['camera_collision_model'],
        }
        reason = (action_result.get('reason') or flight.get('failure')
                  or 'native_action_or_goal_completion_missing')
        report = {
            'schema': 'n10-tracking-clearance-relation/v3',
            'run_id': run.name,
            'status': 'FAIL' if not native_success else 'INSUFFICIENT',
            'classification': 'partial archive; no command/truth endpoint was synthesized',
            'identity': identity,
            'native_action': {
                'action_success': native_success,
                'outcome': action_result.get('outcome'),
                'reason': reason,
                'goal_completed_source_ns': flight.get('goal_completed_source_ns'),
            },
            'interval': {
                'goal_start_source_ns': (flight.get('goal') or {}).get('source_ns'),
                'goal_completion_source_ns': None,
                'matching_ready_commands': 0,
                'paired_truth_commands': 0,
                'rejected_commands': [],
                'unavailable_reason': 'the native action did not complete; no route endpoint is inferred',
            },
            'tracking_error_m': stats([]),
            'clearance_margin_consumed_actual_vs_command_m': stats([]),
            'translation_only_clearance_budget': {
                'pointwise_lower_bound_m': stats([]),
                'negative_sample_count': 0,
                'negative_sample_fraction': None,
                'minimum_sample': None,
                'classification': 'INSUFFICIENT: task endpoint missing; no pointwise pairs were synthesized',
            },
            'minimum_actual_body_clearance': None,
            'maximum_sampled_clearance_consumption': None,
            'obstacles': [],
            'skipped_sdf_geometry': [],
            'per_sample': [],
            'input_sha256': {key: sha256(path) for key, path in input_paths.items()
                             if path.is_file()},
            'tracking_clearance_evaluator_sha256': sha256(Path(__file__).resolve()),
            'limitations': [
                'An aborted action has no native goal-completion timestamp; no route interval is inferred.',
                'Missing pointwise samples are INSUFFICIENT, not zero tracking error or positive clearance.',
                'This report is offline diagnostic evidence and does not affect runtime or acceptance gates.',
            ],
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
        return report
    truth, truth_contract = imu_truth_samples(run, json.loads(names['truth'].read_text()))
    # Use the current point-reference implementation. Older archived arrival
    # JSON may have been produced before the IMU-reference correction.
    with tempfile.TemporaryDirectory(prefix='n10-tracking-alignment-') as temp_dir:
        arrival, _ = evaluate_arrival(
            run, output_name=str(Path(temp_dir) / 'arrival-current.json'))
    missing_collision_models = [str(names[name]) for name in (
        'contact_model_manifest', 'base_collision_model',
        'vehicle_collision_model', 'camera_collision_model')
        if not names[name].is_file()]
    if missing_collision_models:
        raise FileNotFoundError(
            'run collision geometry identity is missing: '
            + ', '.join(missing_collision_models))
    envelope = json.loads(names['envelope'].read_text())['geometry']
    observation = json.loads(names['observation'].read_text())
    contact_manifest = json.loads(names['contact_model_manifest'].read_text())
    generated = contact_manifest.get('generated_model_sha256') or {}
    model_source_checks = {
        'x500_base/model.sdf': generated.get('x500_base/model.sdf') == sha256(
            names['base_collision_model']),
        'x500_d435i/model.sdf': generated.get('x500_d435i/model.sdf') == sha256(
            names['vehicle_collision_model']),
        'd435i/model.sdf': generated.get('d435i/model.sdf') == sha256(
            names['camera_collision_model']),
    }
    if not all(model_source_checks.values()):
        raise ValueError('run_collision_model_identity_mismatch')
    components = _collision_component_spheres(
        names['base_collision_model'], names['vehicle_collision_model'],
        names['camera_collision_model'])
    identity = {
        'run_directory_matches_selected_run': run.name == (flight.get('run_id') or run.name),
        'runtime_contract_identity_sha256': runtime_contract.get('sha256'),
        'goal_id': flight.get('goal_id'),
        'epoch': flight.get('localization_epoch'),
        'map_id': observation.get('map_id_at_goal'),
        'goal_map_identity_matches': bool(
            flight.get('goal_id')
            and flight.get('localization_epoch')
            and observation.get('run_id') == run.name
            and observation.get('goal_id') == flight.get('goal_id')
            and observation.get('epoch') == flight.get('localization_epoch')
            and str(observation.get('map_id_at_goal') or '').startswith(
                flight.get('localization_epoch', '') + '-')),
    }
    truth_stamps = [int(row['stamp_ns']) for row in truth]
    truth_positions = [np.asarray(row['xyz'], dtype=float) for row in truth]
    truth_quaternions = [row['q_xyzw'] for row in truth]
    if len(truth_stamps) < 3 or any(b <= a for a, b in zip(truth_stamps, truth_stamps[1:])):
        raise ValueError('truth samples must have strictly increasing source timestamps')

    goal = flight.get('goal') or {}
    goal_start_ns = int(goal['source_ns'])
    goal_end_ns = int(flight['goal_completed_source_ns'])
    goal_id = flight.get('goal_id')
    epoch = flight.get('localization_epoch')
    rotation = np.asarray(arrival['ground_rotation'], dtype=float)
    translation = np.asarray(arrival['ground_translation'], dtype=float)
    if rotation.shape != (3, 3) or translation.shape != (3,) or not np.isfinite(rotation).all():
        raise ValueError('arrival evaluator lacks a valid fixed prestream transform')

    bounds = envelope['collision_bounds_xyz_m']
    z_min_local, z_max_local = min(bounds[2]), max(bounds[2])
    body_radius = float(envelope['orientation_invariant_rotor_sweep_radius_m'])
    obstacles, skipped = parse_obstacles(names['world'])
    dynamic_model = observation.get('obstacle', {}).get('model_name')
    injection_ns = observation.get('actual_injection_request_sim_ns')
    commands = [row for row in flight.get('position_command_history', [])
                if row.get('goal_id') == goal_id and row.get('epoch') == epoch
                and int(row.get('flag', -1)) == 1
                and goal_start_ns <= int(row['source_stamp_ns']) <= goal_end_ns]
    paired, rejected = [], []
    for command in commands:
        stamp = int(command['source_stamp_ns'])
        try:
            actual_position, quaternion, truth_gap_ns = _truth_pose_at(
                truth_stamps, truth_positions, truth_quaternions, stamp)
        except ValueError as exc:
            rejected.append({'source_stamp_ns': stamp, 'reason': str(exc)})
            continue
        commanded_position = (rotation @ np.asarray(command['position_enu'], dtype=float)
                              + translation)
        commanded_yaw = (float(command['yaw_enu'])
                         + math.atan2(rotation[1, 0], rotation[0, 0]))
        _ = commanded_yaw  # The envelope is yaw invariant; record that command yaw is retained.
        vehicle_radius, z_min, z_max, sin_tilt = vehicle_vertical_cylinder(
            actual_position, quaternion, body_radius, z_min_local, z_max_local)
        active_obstacles = [obstacle for obstacle in obstacles
                            if obstacle['name'].split('/')[0] != dynamic_model
                            or (injection_ns is not None and stamp >= int(injection_ns))]
        if not active_obstacles:
            rejected.append({'source_stamp_ns': stamp, 'reason': 'no_active_sdf_obstacles'})
            continue
        rows = []
        for obstacle in active_obstacles:
            actual_clearance = distance_to_obstacle(
                actual_position, vehicle_radius, z_min, z_max, obstacle)
            command_clearance = distance_to_obstacle(
                commanded_position, vehicle_radius, z_min, z_max, obstacle)
            rows.append((actual_clearance, command_clearance, obstacle['name']))
        actual_clearance, command_clearance_same_obstacle, nearest_name = min(
            rows, key=lambda item: item[0])
        nearest_command_clearance = min(row[1] for row in rows)
        tracking = float(np.linalg.norm(commanded_position - actual_position))
        translation_bound = translation_only_clearance_lower_bound(
            nearest_command_clearance, tracking)
        paired.append({
            'source_stamp_ns': stamp,
            'trajectory_id': int(command['trajectory_id'])
            if command.get('trajectory_id') is not None else None,
            'truth_bracket_gap_sim_s': truth_gap_ns / 1e9,
            'truth_xyz_world_m': actual_position.tolist(),
            'command_xyz_world_m': commanded_position.tolist(),
            'q_xyzw': quaternion.tolist(),
            'position_tracking_error_m': tracking,
            'legacy_whole_vehicle_cylinder_nearest_obstacle': nearest_name,
            'legacy_whole_vehicle_cylinder_actual_clearance_m': actual_clearance,
            'legacy_whole_vehicle_cylinder_command_clearance_m': command_clearance_same_obstacle,
            'legacy_whole_vehicle_cylinder_clearance_consumed_m':
                command_clearance_same_obstacle - actual_clearance,
            'legacy_whole_vehicle_cylinder_minimum_command_clearance_m': nearest_command_clearance,
            'legacy_whole_vehicle_cylinder_translation_lower_bound_m': translation_bound,
            'body_envelope_radius_m': vehicle_radius,
            'body_tilt_sin': sin_tilt,
            'dynamic_box_active': bool(injection_ns is not None and stamp >= int(injection_ns)),
        })

    component_rows = component_tracking_clearances(
        paired, components, obstacles,
        truth_contract['model_origin_to_imu_m'], dynamic_model, injection_ns,
    )
    for row, geometry in zip(paired, component_rows):
        row['nearest_actual_component'] = geometry['nearest_actual_component']
        row['nearest_actual_obstacle'] = geometry['nearest_actual_obstacle']
        row['actual_body_clearance_to_nearest_obstacle_m'] = geometry[
            'actual_component_clearance_m']
        row['command_body_clearance_to_same_obstacle_m'] = geometry[
            'command_clearance_to_actual_nearest_component_obstacle_m']
        row['minimum_command_body_clearance_any_obstacle_m'] = geometry[
            'minimum_command_component_clearance_any_obstacle_m']
        row['clearance_margin_consumed_actual_vs_command_m'] = (
            row['command_body_clearance_to_same_obstacle_m']
            - row['actual_body_clearance_to_nearest_obstacle_m'])
        row['translation_only_clearance_lower_bound_m'] = translation_only_clearance_lower_bound(
            row['minimum_command_body_clearance_any_obstacle_m'],
            row['position_tracking_error_m'])
        row.pop('q_xyzw', None)

    margins = [row['clearance_margin_consumed_actual_vs_command_m'] for row in paired]
    translation_bounds = [row['translation_only_clearance_lower_bound_m']
                          for row in paired]
    minimum = min(paired, key=lambda row: row['actual_body_clearance_to_nearest_obstacle_m'],
                  default=None)
    maximum_consumed = max(paired, key=lambda row: row['clearance_margin_consumed_actual_vs_command_m'],
                           default=None)
    report = {
        'schema': 'n10-tracking-clearance-relation/v3',
        'truth_reference_contract': truth_contract,
        'run_id': run.name,
        'classification': 'offline per-sample route geometry diagnostic using run-identity-bound SDF collision-component spheres; not a runtime gate',
        'identity': identity,
        'reference': {
            'truth_point': 'Gazebo D435i IMU / d435i_link point',
            'command_point': 'EGO PositionCommand point transformed by one fixed scale-one prestream SE(3)',
            'full_body_envelope': str(names['envelope'].relative_to(ROOT)),
            'geometry': {
                'orientation_invariant_rotor_sweep_radius_m': body_radius,
                'collision_bounds_xyz_m': bounds,
                'local_vertical_bounds_m': [z_min_local, z_max_local],
            },
            'command_orientation_note': 'Command yaw is retained; the configured rotationally invariant swept envelope makes the translational clearance comparison yaw invariant. Actual tilt is taken from truth.',
        },
        'collision_component_sphere_geometry': {
            'schema': 'n10-sdf-collision-component-spheres/v1',
            'component_count': len(components),
            'components': components,
            'model_source_checks': model_source_checks,
            'source_sha256': {
                key: sha256(names[name]) for key, name in (
                    ('contact_model_manifest', 'contact_model_manifest'),
                    ('x500_base/model.sdf', 'base_collision_model'),
                    ('x500_d435i/model.sdf', 'vehicle_collision_model'),
                    ('d435i/model.sdf', 'camera_collision_model'),
                )
            },
            'reference_point': 'Gazebo model origin; component centers shifted to the D435i IMU point before pairing with IMU truth/command positions',
            'command_attitude': 'same observed truth attitude for command and actual poses; isolates translation and does not qualify attitude tracking',
        },
        'interval': {
            'goal_start_source_ns': goal_start_ns,
            'goal_completion_source_ns': goal_end_ns,
            'duration_sim_s': (goal_end_ns - goal_start_ns) / 1e9,
            'matching_ready_commands': len(commands),
            'paired_truth_commands': len(paired),
            'rejected_commands': rejected,
            'maximum_truth_bracket_gap_sim_s': max(
                (row['truth_bracket_gap_sim_s'] for row in paired), default=None),
        },
        'tracking_error_m': stats([row['position_tracking_error_m'] for row in paired]),
        'clearance_margin_consumed_actual_vs_command_m': stats(margins),
        'translation_only_clearance_budget': {
            'formula': 'minimum_command_component_clearance_any_obstacle_m - position_tracking_error_m',
            'pointwise_lower_bound_m': stats(translation_bounds),
            'negative_sample_count': sum(value < 0.0 for value in translation_bounds),
            'negative_sample_fraction': (
                sum(value < 0.0 for value in translation_bounds) / len(translation_bounds)
                if translation_bounds else None),
            'minimum_sample': min(
                paired, key=lambda row: row['translation_only_clearance_lower_bound_m'],
                default=None),
            'classification': (
                'offline pointwise translation-only Lipschitz bound using the same '
                'actual-attitude SDF component-sphere geometry at command and truth positions; '
                'not a collision result, interval certificate, acceptance threshold, '
                'or runtime gate'),
        },
        'minimum_actual_body_clearance': minimum,
        'maximum_sampled_clearance_consumption': maximum_consumed,
        'obstacles': [item['name'] for item in obstacles],
        'skipped_sdf_geometry': skipped,
        'per_sample': paired,
        'input_sha256': {key: sha256(path) for key, path in names.items()},
        'tracking_clearance_evaluator_sha256': sha256(Path(__file__).resolve()),
        'current_arrival_evaluator_sha256': sha256(ROOT / 'tools/debug_truth/evaluate_arrival.py'),
        'limitations': [
            'Per-sample command-to-truth residual and SDF clearance are paired diagnostics; this is not a prediction for another route or a continuous-time clearance certificate.',
            'Each collision box is replaced by a circumscribed sphere, and both command and truth positions use the same observed truth attitude to isolate translational tracking; attitude tracking requires separate analysis.',
            'The pointwise translation-only lower bound assumes unchanged obstacle geometry and unchanged body envelope at that source stamp; it does not bound orientation mismatch, inter-sample motion, map/model error, or later obstacle motion.',
            'A positive actual clearance describes this simulated route only and does not make a global scalar tracking threshold collision-safe.',
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--output', type=Path, required=True,
                        help='new diagnostic JSON path; source run files are not overwritten')
    args = parser.parse_args()
    report = evaluate(args.run, args.output)
    print(json.dumps({
        'run_id': report['run_id'],
        'tracking_p95_m': report['tracking_error_m']['p95'],
        'actual_clearance_min_m': report['minimum_actual_body_clearance'][
            'actual_body_clearance_to_nearest_obstacle_m'] if report['minimum_actual_body_clearance'] else None,
        'margin_consumed_at_min_clearance_m': report['minimum_actual_body_clearance'][
            'clearance_margin_consumed_actual_vs_command_m'] if report['minimum_actual_body_clearance'] else None,
        'translation_only_bound_min_m': (
            report['translation_only_clearance_budget']['minimum_sample'][
                'translation_only_clearance_lower_bound_m']
            if report['translation_only_clearance_budget']['minimum_sample'] else None),
        'translation_only_bound_negative_fraction': report[
            'translation_only_clearance_budget']['negative_sample_fraction'],
    }))


if __name__ == '__main__':
    main()
