#!/usr/bin/env python3
"""Recompute comparable N10 VIO, tracking and timing metrics from run archives.

This is an offline, read-only evaluator. It never joins samples across runs,
changes a runtime gate, or overwrites a source run archive.
"""
import argparse
import bisect
import csv
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
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools/debug_truth'))
sys.path.insert(0, str(ROOT / 'src/own/uav_sim'))

from evaluate_arrival import evaluate_run as evaluate_arrival
from evaluate_n10_vins_velocity import evaluate as evaluate_velocity
from evaluate_vio_full_state import _rpe, _stats
from evaluate_vio_quality_alignment import _unit_quaternion
from evaluate_vins_motion import rotation

TRUTH_BRACKET_MAX_NS = 40_000_000
RPE_RAW_GAP_MAX_NS = 200_000_000
RPE_TRUTH_GAP_MAX_NS = 40_000_000


def _load(path):
    return json.loads(Path(path).read_text())


def _jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()
            if line.strip()]


def _quat_slerp(q0, q1, fraction):
    q0 = np.asarray(q0, dtype=float)
    q1 = np.asarray(q1, dtype=float)
    q0 /= np.linalg.norm(q0)
    q1 /= np.linalg.norm(q1)
    dot = float(np.dot(q0, q1))
    if dot < 0.0:
        q1 = -q1
        dot = -dot
    dot = min(1.0, max(-1.0, dot))
    if dot > 0.9995:
        result = q0 + fraction * (q1 - q0)
        return result / np.linalg.norm(result)
    angle = math.acos(dot)
    scale = math.sin(angle)
    return (math.sin((1.0 - fraction) * angle) / scale * q0
            + math.sin(fraction * angle) / scale * q1)


def _truth_pose_at(stamps, positions, quaternions, stamp_ns):
    index = bisect.bisect_left(stamps, int(stamp_ns))
    if index == 0 or index == len(stamps):
        raise ValueError('truth interpolation would extrapolate')
    left_ns, right_ns = int(stamps[index - 1]), int(stamps[index])
    gap_ns = right_ns - left_ns
    if gap_ns <= 0 or gap_ns > TRUTH_BRACKET_MAX_NS:
        raise ValueError('truth bracket gap is invalid or exceeds 0.04 simulated seconds')
    fraction = (int(stamp_ns) - left_ns) / gap_ns
    position = positions[index - 1] * (1.0 - fraction) + positions[index] * fraction
    quaternion = _quat_slerp(quaternions[index - 1], quaternions[index], fraction)
    return position, quaternion, gap_ns


def _summary(values):
    return _stats([float(value) for value in values]) if values else None


def _max_gap_seconds(stamps):
    return float(np.diff(stamps).max() / 1e9) if len(stamps) > 1 else None


def _tracking_samples(flight, truth, arrival):
    stamps = [int(row['stamp_ns']) for row in truth]
    if len(stamps) < 3 or any(b <= a for a, b in zip(stamps, stamps[1:])):
        raise ValueError('truth source timestamps must be strictly increasing')
    positions = [np.asarray(row['xyz'], dtype=float) for row in truth]
    quaternions = [_unit_quaternion(row['q_xyzw']) for row in truth]
    align_r = np.asarray(arrival['ground_rotation'], dtype=float)
    align_t = np.asarray(arrival['ground_translation'], dtype=float)
    goal_id = flight.get('goal_id')
    epoch = flight.get('localization_epoch')
    candidates = [row for row in flight.get('position_command_history', [])
                  if row.get('goal_id') == goal_id and row.get('epoch') == epoch
                  and int(row.get('flag', -1)) == 1]
    paired, rejected = [], []
    for command in candidates:
        stamp_ns = int(command['source_stamp_ns'])
        try:
            position, quaternion, gap_ns = _truth_pose_at(
                stamps, positions, quaternions, stamp_ns)
        except ValueError as exc:
            rejected.append({'source_stamp_ns': stamp_ns, 'reason': str(exc)})
            continue
        command_world = align_r @ np.asarray(command['position_enu'], dtype=float) + align_t
        paired.append({
            'source_stamp_ns': stamp_ns,
            'position_error_m': float(np.linalg.norm(command_world - position)),
            'truth_bracket_gap_sim_s': gap_ns / 1e9,
        })
    return candidates, paired, rejected


def _age_summary(rows, start_ns, end_ns):
    selected = [row for row in rows
                if isinstance(row.get('clock_ns_at_receipt'), int)
                and not isinstance(row.get('clock_ns_at_receipt'), bool)
                and start_ns <= row['clock_ns_at_receipt'] <= end_ns
                and isinstance(row.get('source_stamp_ns'), int)
                and not isinstance(row.get('source_stamp_ns'), bool)
                and isinstance(row.get('last_occupancy_stamp_ns'), int)
                and not isinstance(row.get('last_occupancy_stamp_ns'), bool)]
    source_age = [(int(row['clock_ns_at_receipt']) - int(row['source_stamp_ns'])) / 1e9
                  for row in selected]
    occupancy_age = [(int(row['clock_ns_at_receipt'])
                      - int(row['last_occupancy_stamp_ns'])) / 1e9 for row in selected]
    return {
        'map_status_samples': len(selected),
        'source_age_sim_s': _summary(source_age),
        'occupancy_update_age_sim_s': _summary(occupancy_age),
        'sampling_note': 'Map status is sampled by the archived source-timeline recorder; this is not an exact per-callback latency bound.',
    }


def _identity(run_a, run_b):
    contracts = [_load(run / 'runtime-contract.json') for run in (run_a, run_b)]
    files_a, files_b = contracts[0]['files'], contracts[1]['files']
    only_a = sorted(set(files_a) - set(files_b))
    only_b = sorted(set(files_b) - set(files_a))
    changed = sorted(path for path in set(files_a) & set(files_b)
                     if files_a[path] != files_b[path])
    runtime_delta = [{'path': path, 'run_a_sha256': files_a.get(path),
                      'run_b_sha256': files_b.get(path)}
                     for path in sorted(set(only_a + only_b + changed))]

    run_manifests = [_load(run / 'n10-run-manifest.json') for run in (run_a, run_b)]
    contact = [_load(run / 'n09-contact-model-manifest.json') for run in (run_a, run_b)]
    contact_normalized = []
    for manifest in contact:
        normalized = dict(manifest)
        normalized.pop('overlay_root', None)
        contact_normalized.append(normalized)
    launches = [manifest['launch_manifest'] for manifest in run_manifests]
    tool_freezes = [_load(run / 'n10-tool-freeze-used.json') for run in (run_a, run_b)]
    px4_params = [_load(run / 'px4-params.json') for run in (run_a, run_b)]
    session = [launch['session'] for launch in launches]
    install_paths = sorted(path for path in set(files_a) | set(files_b)
                           if path.startswith('install/'))
    installed_same = all(files_a.get(path) == files_b.get(path) for path in install_paths)
    px4_binary_paths = sorted(path for path in set(files_a) | set(files_b)
                              if path.endswith('/bin/px4'))
    px4_binary_same = bool(px4_binary_paths) and all(
        files_a.get(path) == files_b.get(path) for path in px4_binary_paths)

    return {
        'run_ids': [run_a.name, run_b.name],
        'runtime_contracts': {
            'sha256': [contracts[0].get('sha256'), contracts[1].get('sha256')],
            'file_count': [len(files_a), len(files_b)],
            'source_and_tool_differences': runtime_delta,
            'all_installed_runtime_files_identical': installed_same,
            'installed_runtime_file_count': len(install_paths),
            'px4_binary_identical': px4_binary_same,
            'px4_binary_paths': px4_binary_paths,
        },
        'task_and_epoch_differences': {
            'goal_profiles': [manifest.get('goal_profile') for manifest in run_manifests],
            'goal_profile_sha256': [manifest.get('goal_profile_sha256') for manifest in run_manifests],
            'native_dwell_s': [
                _load(ROOT / manifest['goal_profile']).get('dwell_s')
                for manifest in run_manifests],
            'localization_epochs': [session_item.get('epoch') for session_item in session],
            'epoch_generated_vins_yaml_sha256': [
                session_item.get('files_sha256', {}).get('vins.yaml') for session_item in session],
            'vins_settings_sha256': [session_item.get('settings_sha256') for session_item in session],
            'vins_model_sha256': [session_item.get('model_sha256') for session_item in session],
            'camera_calibration_yaml_sha256': [
                {key: session_item.get('files_sha256', {}).get(key)
                 for key in ('left.yaml', 'right.yaml')} for session_item in session],
            'vins_generated_yaml_note': 'The VINS generator embeds each fresh epoch in world/body/camera frame IDs and namespace; distinct generated vins.yaml hashes are expected. Source settings, camera YAMLs, model, generator and installed VINS binary are compared separately.',
        },
        'flight_configuration': {
            'effective_ego_launch_arguments_identical': launches[0].get('ego_launch_arguments')
                == launches[1].get('ego_launch_arguments'),
            'effective_ego_launch_arguments': launches[0].get('ego_launch_arguments'),
            'px4_configured_values_identical': px4_params[0].get('parameters')
                == px4_params[1].get('parameters'),
            'px4_mount_model_sha256': [item.get('mount_model_sha256') for item in px4_params],
            'ego_binary_sha256': [item.get('ego_binary_sha256') for item in tool_freezes],
            'bridge_module_sha256': [item.get('bridge_module_sha256') for item in tool_freezes],
            'source_patch_0054_sha256': [item.get('source_patch_0054_sha256') for item in tool_freezes],
        },
        'physical_model': {
            'contact_model_sha256_run_manifest': [
                manifest.get('contact_model_sha256') for manifest in run_manifests],
            'run_local_contact_manifest_diff_only_overlay_root': contact_normalized[0]
                == contact_normalized[1],
            'source_model_sha256': [manifest.get('source_sha256') for manifest in contact],
            'generated_x500_and_d435i_sdf_sha256': [
                manifest.get('generated_model_sha256') for manifest in contact],
            'project_world_sha256': [
                _load(run / 'world.json').get('output_sha256') for run in (run_a, run_b)],
        },
        'reuse_decision': {
            'comparable_as_two_independent_calibration_records': bool(
                installed_same and px4_binary_same
                and launches[0].get('ego_launch_arguments') == launches[1].get('ego_launch_arguments')
                and px4_params[0].get('parameters') == px4_params[1].get('parameters')
                and contact[0].get('generated_model_sha256') == contact[1].get('generated_model_sha256')
                and session[0].get('settings_sha256') == session[1].get('settings_sha256')
                and session[0].get('model_sha256') == session[1].get('model_sha256')),
            'not_same_exact_task_profile': True,
            'do_not_stitch_epochs_or_pool_samples_as_one_run': True,
            'scope': 'Per-run distributions may be compared under a common evaluator. #385 changes only the native goal dwell in the task profile; epochs remain independent. These are not repeated identical-profile qualifications and neither counts toward frozen N15/N16 runs.',
        },
    }


def _incomplete_run_report(run, flight):
    """Preserve failed/partial archives without inventing arrival or hold boundaries."""
    action_result = flight.get('action_result') or {}
    native_success = bool(
        flight.get('action_success') is True
        and action_result.get('success') is True
        and action_result.get('outcome') == 'succeeded'
    )
    reason = action_result.get('reason') or flight.get('failure') or 'native_action_incomplete'
    arrival_path = next((run / name for name in (
        'arrival-evaluation-simtime-v2.json', 'arrival-evaluation.json'
    ) if (run / name).is_file()), None)
    arrival_source = _load(arrival_path) if arrival_path else {}
    runtime_path = run / 'runtime-contract.json'
    runtime_contract = _load(runtime_path) if runtime_path.is_file() else {}
    contact_path = run / 'vehicle-contact-evaluation.json'
    contact = _load(contact_path) if contact_path.is_file() else {}
    source_input_names = [
        'alignment-observation.json', 'debug-truth-evaluation.json',
        'odometry-evaluation.json', 'odometry-errors.csv', 'flight.json',
        'preflight.json', 'planner-observation.json', 'bridge-alignment-timeline.jsonl',
        'n08-localization-source-timeline.json', 'runtime-contract.json',
        'n10-run-manifest.json', 'n10-tool-freeze-used.json', 'n09-contact-model-manifest.json',
        'n09-runtime-contract-current.json', 'world.json', 'px4-params.json',
    ]
    input_hashes = {
        name: hashlib.sha256((run / name).read_bytes()).hexdigest()
        for name in source_input_names if (run / name).is_file()
    }
    missing_input_files = [name for name in source_input_names if not (run / name).is_file()]
    prohibited_contacts = contact.get('prohibited_contact_event_count')
    direct_failure = not native_success or (
        isinstance(prohibited_contacts, int) and prohibited_contacts > 0
    )
    arrival_status = (
        'FAIL' if not native_success
        else arrival_source.get('independent_goal_dwell_status', 'INSUFFICIENT')
    )
    return {
        'schema': 'n10-cross-run-calibration/v1',
        'run_id': run.name,
        'status': 'FAIL' if direct_failure else 'INSUFFICIENT',
        'classification': 'partial archive; no cross-run arrival/hold segmentation was inferred',
        'runtime_contract_sha256': runtime_contract.get('sha256'),
        'epoch': flight.get('localization_epoch'),
        'native_action': {
            'goal_sent': flight.get('action_goal_sent'),
            'action_success': native_success,
            'outcome': action_result.get('outcome'),
            'reason': reason,
            'goal_completed_source_ns': flight.get('goal_completed_source_ns'),
            'post_goal_hold_completed': (flight.get('post_goal_hold') or {}).get('completed'),
        },
        'arrival': {
            'independent_goal_dwell_status': arrival_status,
            'independent_goal_dwell_passed': arrival_source.get('independent_goal_dwell_passed'),
            'required_contiguous_dwell_sim_s': arrival_source.get('required_contiguous_dwell_sim_s'),
            'longest_joint_tolerance_window': arrival_source.get('longest_joint_tolerance_window'),
            'max_truth_sample_gap_sim_s': arrival_source.get('max_truth_sample_gap_sim_s'),
            'native_action_success': native_success,
            'failure': reason,
            'method': 'Existing source-time offline arrival report; incomplete native task remains FAIL or INSUFFICIENT and no endpoint is synthesized.',
        },
        'segments': {},
        'contact_evaluation': {
            'passed': contact.get('passed'),
            'sensor_topics_ready': contact.get('sensor_topics_ready'),
            'prohibited_contact_event_count': prohibited_contacts,
            'first_prohibited_contact': contact.get('first_prohibited_contact'),
        },
        'coverage': {
            'status': 'INSUFFICIENT',
            'reason': 'native arrival and completed active hold are required for the requested cross-run segments',
            'missing_input_files': missing_input_files,
        },
        'input_sha256': input_hashes,
        'limitations': [
            'No goal-completion or hold-end timestamp is synthesized for an aborted task.',
            'Per-segment cross-run comparisons are unavailable for this archive.',
            'Any native action failure or observed prohibited contact is preserved as FAIL.',
        ],
    }


def evaluate_run(run):
    run = Path(run).resolve()
    flight = _load(run / 'flight.json')
    action_result = flight.get('action_result') or {}
    hold = flight.get('post_goal_hold') or {}
    landed = [row for row in _jsonl(run / 'bridge-alignment-timeline.jsonl')
              if row.get('phase') == 'LANDED']
    if (flight.get('action_success') is not True
            or action_result.get('success') is not True
            or action_result.get('outcome') != 'succeeded'
            or not isinstance(flight.get('goal_completed_source_ns'), int)
            or not hold.get('completed')
            or not landed):
        return _incomplete_run_report(run, flight)
    observation = _load(run / 'alignment-observation.json')
    truth_report = _load(run / 'debug-truth-evaluation.json')
    odometry = _load(run / 'odometry-evaluation.json')
    phases = _jsonl(run / 'bridge-alignment-timeline.jsonl')
    source_timeline = _load(run / 'n08-localization-source-timeline.json')
    truth, truth_contract = imu_truth_samples(run, truth_report)
    require_same_truth_reference(odometry, truth_contract)
    truth_t = np.asarray([int(row['stamp_ns']) for row in truth], dtype=np.int64)
    truth_p = np.asarray([row['xyz'] for row in truth], dtype=float)
    truth_q = np.asarray([_unit_quaternion(row['q_xyzw']) for row in truth])
    if len(truth_t) < 3 or np.any(np.diff(truth_t) <= 0):
        raise ValueError(f'{run.name}: truth source stamps are not strictly monotonic')

    prestream_ns = int(odometry['interval']['start_source_ns'])
    landed = [row for row in phases if row.get('phase') == 'LANDED']
    if not landed:
        raise ValueError(f'{run.name}: no LANDED bridge phase')
    landed_ns = int(landed[-1]['stamp_ns'])
    goal_start_ns = int(flight['goal']['source_ns'])
    goal_end_ns = int(flight['goal_completed_source_ns'])
    hold = flight.get('post_goal_hold') or {}
    if not hold.get('completed'):
        raise ValueError(f'{run.name}: post-goal active hold is not complete')
    hold_duration_ns = int(round(float(hold['requested_sim_s']) * 1e9))
    hold_end_ns = goal_end_ns + hold_duration_ns
    if not prestream_ns <= goal_start_ns <= goal_end_ns < hold_end_ns <= landed_ns:
        raise ValueError(f'{run.name}: inconsistent prestream/goal/hold/landed timestamps')

    raw = [row for row in observation.get('samples', [])
           if row.get('kind') == 'raw_odom'
           and prestream_ns <= int(row.get('source_ns', -1)) <= landed_ns]
    raw_t = np.asarray([int(row['source_ns']) for row in raw], dtype=np.int64)
    raw_p = np.asarray([row['xyz'] for row in raw], dtype=float)
    raw_q = np.asarray([_unit_quaternion(row['q_xyzw']) for row in raw])
    if len(raw_t) < 3 or np.any(np.diff(raw_t) <= 0):
        raise ValueError(f'{run.name}: raw VINS pose stamps are not strictly monotonic')
    alignment_r = np.asarray(odometry['alignment']['rotation'], dtype=float)
    if alignment_r.shape != (3, 3) or odometry['alignment'].get('scale') != 1:
        raise ValueError(f'{run.name}: scale-one prestream alignment is missing')

    with (run / 'odometry-errors.csv').open(newline='') as stream:
        pose_errors = list(csv.DictReader(stream))
    velocity_report, velocity_samples = evaluate_velocity(run)
    # The shared arrival evaluator writes a companion report by default. Keep
    # source archives immutable by directing that derived report to a temp dir.
    with tempfile.TemporaryDirectory(prefix='n10-arrival-recompute-') as temp_dir:
        arrival_report, _ = evaluate_arrival(
            run, output_name=str(Path(temp_dir) / 'arrival-recomputed.json'))
    goal_target_world = np.asarray(arrival_report['world_imu_goal_xyz'], dtype=float)
    goal_yaw_world = (float(flight['goal']['yaw_enu'])
                      + float(arrival_report['ground_yaw_offset_rad']))
    goal_config = _load(ROOT / flight['goal_config'])
    hold_truth = []
    for row in truth:
        stamp_ns = int(row['stamp_ns'])
        if not goal_end_ns <= stamp_ns <= hold_end_ns:
            continue
        rotation_world = rotation(_unit_quaternion(row['q_xyzw']))
        sensor_position = np.asarray(row['xyz'], dtype=float)
        yaw_world = math.atan2(rotation_world[1, 0], rotation_world[0, 0])
        yaw_error = abs(math.atan2(math.sin(yaw_world - goal_yaw_world),
                                   math.cos(yaw_world - goal_yaw_world)))
        hold_truth.append({
            'source_ns': stamp_ns,
            'position_error_m': float(np.linalg.norm(sensor_position - goal_target_world)),
            'yaw_error_deg': math.degrees(yaw_error),
        })
    hold_position_errors = [row['position_error_m'] for row in hold_truth]
    hold_yaw_errors = [row['yaw_error_deg'] for row in hold_truth]
    first_hold_exit = next((row for row in hold_truth
                            if row['position_error_m'] > float(
                                goal_config.get('verification_position_tolerance_m', 0.3))), None)
    target_hold_summary = {
        'truth_samples': len(hold_truth),
        'position_error_to_goal_m': _summary(hold_position_errors),
        'absolute_yaw_error_to_goal_deg': _summary(hold_yaw_errors),
        'first_position_exit_from_goal_s': ({
            'elapsed_from_goal_completion_sim_s':
                (first_hold_exit['source_ns'] - goal_end_ns) / 1e9,
            'position_error_m': first_hold_exit['position_error_m'],
        } if first_hold_exit else None),
        'note': 'Diagnostic target-relative truth drift; distinct from raw VINS absolute alignment error and not a ten-minute acceptance limit.',
    }
    track_candidates, tracking_samples, tracking_rejected = _tracking_samples(
        flight, truth, arrival_report)
    tracking_by_stamp = {row['source_stamp_ns']: row for row in tracking_samples}

    intervals = {
        'goal_motion_and_arrival_dwell': (goal_start_ns, goal_end_ns),
        'requested_active_hold': (goal_end_ns, hold_end_ns),
        'hold_end_to_landed': (hold_end_ns, landed_ns),
        'goal_start_to_landed': (goal_start_ns, landed_ns),
        'prestream_to_landed': (prestream_ns, landed_ns),
    }
    rpe_rows, rpe_detail = _rpe(
        raw_t, raw_p, raw_q, truth_t, truth_p, truth_q, alignment_r,
        (1.0, 5.0, 10.0), RPE_RAW_GAP_MAX_NS, RPE_TRUTH_GAP_MAX_NS)

    def pose_summary(start_ns, end_ns):
        selected = [row for row in pose_errors
                    if start_ns <= int(row['source_ns']) <= end_ns]
        return {
            'sample_count': len(selected),
            'supported': len(selected) >= 3,
            'position_error_m': _summary([float(row['position_error_m']) for row in selected]),
            'absolute_yaw_error_deg': _summary([abs(float(row['yaw_error_deg'])) for row in selected]),
            'max_source_gap_sim_s': _max_gap_seconds(
                np.asarray([int(row['source_ns']) for row in selected], dtype=np.int64)),
            'reference': 'One fixed prestream SE(3), scale=1; source-stamp pairing; no segment refit.',
        }

    def velocity_summary(start_ns, end_ns):
        selected = [row for row in velocity_samples
                    if start_ns <= int(row['source_ns']) <= end_ns]
        return {
            'sample_count': len(selected),
            'supported': len(selected) >= 3,
            'velocity_error_norm_m_s': _summary(
                [float(row['velocity_error_norm_m_s']) for row in selected]),
            'truth_speed_imu_m_s': _summary(
                [float(row['truth_speed_imu_m_s']) for row in selected]),
            'max_source_gap_sim_s': _max_gap_seconds(
                np.asarray([int(row['source_ns']) for row in selected], dtype=np.int64)),
            'method': velocity_report['truth_velocity_method'],
        }

    def rpe_summary(start_ns, end_ns):
        result = {}
        for aggregate in rpe_rows:
            horizon = float(aggregate['target_window_s'])
            candidate = [int(stamp) for stamp in raw_t
                         if start_ns <= int(stamp)
                         and int(stamp) + int(round(horizon * 1e9)) <= end_ns]
            selected = [row for row in rpe_detail
                        if float(row['window_s']) == horizon
                        and start_ns <= int(row['start_source_ns'])
                        and int(row['end_source_ns']) <= end_ns]
            result[f'{horizon:g}s'] = {
                'candidate_pairs': len(candidate),
                'supported_pairs': len(selected),
                'rejected_pairs': len(candidate) - len(selected),
                'supported': bool(selected),
                'translation_error_m': _summary(
                    [float(row['translation_error_m']) for row in selected]),
                'rotation_error_deg': _summary(
                    [float(row['rotation_error_deg']) for row in selected]),
            }
        return result

    def tracking_summary(start_ns, end_ns):
        selected = [row for stamp, row in tracking_by_stamp.items()
                    if start_ns <= stamp <= end_ns]
        return {
            'ready_command_candidates': sum(
                start_ns <= int(row['source_stamp_ns']) <= end_ns
                for row in track_candidates),
            'truth_paired_commands': len(selected),
            'rejected_commands': sum(
                start_ns <= int(row['source_stamp_ns']) <= end_ns
                for row in tracking_rejected),
            'supported': len(selected) >= 3,
            'position_error_m': _summary([row['position_error_m'] for row in selected]),
            'max_truth_bracket_gap_sim_s': max(
                (row['truth_bracket_gap_sim_s'] for row in selected), default=None),
            'reference': 'Matching READY PositionCommand transformed with one fixed preflight ground SE(3), compared with interpolated Gazebo D435i IMU truth; no truth feedback.',
        }

    map_rows = [row for row in source_timeline.get('events', [])
                if row.get('stream') == 'map_status']
    segments = {}
    for name, (start_ns, end_ns) in intervals.items():
        raw_selected = raw_t[(raw_t >= start_ns) & (raw_t <= end_ns)]
        truth_selected = truth_t[(truth_t >= start_ns) & (truth_t <= end_ns)]
        velocity_selected = [row for row in velocity_samples
                             if start_ns <= int(row['source_ns']) <= end_ns]
        segments[name] = {
            'start_source_ns': start_ns,
            'end_source_ns': end_ns,
            'duration_sim_s': (end_ns - start_ns) / 1e9,
            'raw_vins_pose_samples': len(raw_selected),
            'raw_vins_max_source_gap_sim_s': _max_gap_seconds(raw_selected),
            'truth_pose_samples': len(truth_selected),
            'truth_max_source_gap_sim_s': _max_gap_seconds(truth_selected),
            'absolute_position_yaw_error': pose_summary(start_ns, end_ns),
            'relative_pose_error': rpe_summary(start_ns, end_ns),
            'raw_velocity_error': velocity_summary(start_ns, end_ns),
            'ego_tracking_error': tracking_summary(start_ns, end_ns),
            'map_and_source_timing': _age_summary(map_rows, start_ns, end_ns),
            'raw_velocity_supported_pairs': len(velocity_selected),
        }

    source_input_names = [
        'alignment-observation.json', 'debug-truth-evaluation.json',
        'odometry-evaluation.json', 'odometry-errors.csv', 'flight.json',
        'preflight.json', 'planner-observation.json', 'bridge-alignment-timeline.jsonl',
        'n08-localization-source-timeline.json', 'runtime-contract.json',
        'n10-run-manifest.json', 'n10-tool-freeze-used.json', 'n09-contact-model-manifest.json',
        'n09-runtime-contract-current.json', 'world.json', 'px4-params.json',
    ]
    input_hashes = {name: hashlib.sha256((run / name).read_bytes()).hexdigest()
                    for name in source_input_names}
    tool_paths = [
        Path(__file__).resolve(),
        ROOT / 'tools/debug_truth/evaluate_n10_vins_velocity.py',
        ROOT / 'tools/debug_truth/evaluate_arrival.py',
        ROOT / 'tools/debug_truth/evaluate_vio_full_state.py',
        ROOT / 'tools/generate_vins_config.py',
        ROOT / 'simulation/models/x500_d435i/model.sdf',
        ROOT / 'simulation/models/d435i/model.sdf',
    ]
    tool_hashes = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in tool_paths}
    return {
        'schema': 'n10-cross-run-calibration/v1',
        'truth_reference_contract': truth_contract,
        'run_id': run.name,
        'status': 'COMPLETE',
        'classification': 'offline archive re-evaluation; no new flight and no new runtime gate',
        'runtime_contract_sha256': _load(run / 'runtime-contract.json')['sha256'],
        'epoch': flight.get('localization_epoch'),
        'time_domain': 'simulated source stamps for segmentation and RPE; wall time is diagnostic only',
        'segmentation': {
            'goal_start_source_ns': goal_start_ns,
            'goal_completion_source_ns': goal_end_ns,
            'requested_hold_sim_s': float(hold['requested_sim_s']),
            'hold_end_source_ns': hold_end_ns,
            'landed_source_ns': landed_ns,
            'hold_boundary_basis': 'goal completion source stamp plus the runner recorded completed requested duration; exact hold-loop entry/exit source stamps were not persisted.',
        },
        'arrival': {
            'independent_goal_dwell_status': arrival_report.get('independent_goal_dwell_status'),
            'independent_goal_dwell_passed': arrival_report.get('independent_goal_dwell_passed'),
            'required_contiguous_dwell_sim_s': arrival_report.get('required_contiguous_dwell_sim_s'),
            'longest_joint_tolerance_window': arrival_report.get('longest_joint_tolerance_window'),
            'max_truth_sample_gap_sim_s': arrival_report.get('max_truth_sample_gap_sim_s'),
            'native_action_success': arrival_report.get('native_action_success'),
            'method': 'Current read-only evaluate_arrival.py; fixed preflight SE(3), D435i IMU reference, joint position/yaw tolerance, contiguous simulation-time source stamps, and explicit maximum truth gap.',
        },
        'target_relative_truth_during_hold': target_hold_summary,
        'segments': segments,
        'coverage': {
            'raw_vins_pose_samples': len(raw_t),
            'raw_vins_max_source_gap_sim_s': _max_gap_seconds(raw_t),
            'truth_pose_samples': len(truth_t),
            'truth_max_source_gap_sim_s': _max_gap_seconds(truth_t),
            'raw_vins_velocity_coverage': velocity_report['coverage'],
            'tracking_ready_command_candidates': len(track_candidates),
            'tracking_truth_paired_commands': len(tracking_samples),
            'tracking_unpaired_commands': len(tracking_rejected),
            'source_timeline_wall_duration_s': source_timeline.get('duration_wall_s'),
            'source_timeline_stop_reason': source_timeline.get('stop_reason'),
            'source_timeline_clock_regression_events': source_timeline.get('clock_regression_event_count'),
        },
        'methods': {
            'absolute_position_yaw': 'N01 odometry-evaluation samples under one fixed prestream rigid alignment, scale=1; segment boundaries use source stamps.',
            'rpe': 'N01 evaluate_vio_full_state._rpe implementation; exact 1/5/10 simulated-second increments; raw bracket <=0.2 s and truth bracket <=0.04 s; no segment refit.',
            'velocity': 'evaluate_n10_vins_velocity.py: raw VINS WORLD_FRAME_ID twist.linear against centered 0.2 simulated-second finite-difference D435i IMU truth; no extrapolation.',
            'tracking': 'Matching READY PositionCommand at its source stamp compared to interpolated IMU truth converted from frozen model-origin geometry; one preflight sensor-point SE(3), truth bracket <=0.04 s. The model-origin lever is applied once by the common reader.',
            'timing': 'Per-segment source/receipt-derived map age and occupancy update age; recorder is decimated and does not establish callback latency.',
            'thresholds': 'No new candidate threshold or runtime refusal is applied by this evaluator.',
        },
        'wall_time_diagnostics': {
            'goal_elapsed_wall_s': flight.get('goal_timing', {}).get('wall_elapsed_s'),
            'goal_elapsed_sim_s': flight.get('goal_timing', {}).get('sim_elapsed_s'),
            'hold_elapsed_wall_s': hold.get('wall_elapsed_s'),
            'hold_elapsed_sim_s': hold.get('observed_sim_s'),
            'hold_rtf_sim_over_wall': hold.get('realtime_factor_sim_over_wall'),
        },
        'input_sha256': input_hashes,
        'evaluator_and_geometry_sha256': tool_hashes,
    }


def evaluate_pair(run_a, run_b):
    run_a, run_b = Path(run_a).resolve(), Path(run_b).resolve()
    identity = _identity(run_a, run_b)
    runs = [evaluate_run(run_a), evaluate_run(run_b)]
    pair_complete = (
        all(row.get('status') == 'COMPLETE' for row in runs)
        and identity['reuse_decision']['comparable_as_two_independent_calibration_records']
    )
    return {
        'schema': 'n10-cross-run-calibration-pair/v1',
        'status': 'COMPLETE' if pair_complete else 'INSUFFICIENT',
        'classification': 'two independent archives evaluated separately under one source-time evaluator; no raw sample stitching or threshold pooling',
        'identity_comparison': identity,
        'runs': runs,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_a', type=Path)
    parser.add_argument('run_b', type=Path)
    parser.add_argument('--output', type=Path, required=True,
                        help='new JSON path; source archives are never overwritten')
    args = parser.parse_args()
    report = evaluate_pair(args.run_a, args.run_b)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
