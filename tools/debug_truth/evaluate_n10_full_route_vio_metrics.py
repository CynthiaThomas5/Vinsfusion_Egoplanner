#!/usr/bin/env python3
"""Recompute N10 long-route raw VIO metrics with explicit action/hold/landing windows."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
import tempfile

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from truth_reference import imu_truth_samples, require_same_truth_reference

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/debug_truth'))
sys.path.insert(0, str(ROOT / 'tools'))
from evaluate_n10_vins_velocity import evaluate as evaluate_velocity
from evaluate_arrival import evaluate_run as evaluate_arrival
from evaluate_vio_full_state import _rpe, _stats
from evaluate_vio_quality_alignment import _unit_quaternion
from evaluate_vins_motion import rotation


def _load(path):
    return json.loads(Path(path).read_text())


def summarize_arrival_report(report):
    """Expose the canonical simulation-time arrival evaluator without rejudging it."""
    return {
        'time_domain': report.get('time_domain'),
        'position_tolerance_m': report.get('position_tolerance_m'),
        'yaw_tolerance_deg': report.get('yaw_tolerance_deg'),
        'required_contiguous_dwell_sim_s': report.get('required_contiguous_dwell_sim_s'),
        'truth_max_source_gap_sim_s': report.get('max_truth_sample_gap_sim_s'),
        'longest_joint_tolerance_window': report.get('longest_joint_tolerance_window'),
        'independent_goal_dwell_status': report.get('independent_goal_dwell_status'),
        'independent_goal_dwell_passed': report.get('independent_goal_dwell_passed'),
        'native_action_success': report.get('native_action_success'),
        'truth_is_offline_only': report.get('truth_is_offline_only') is True,
    }


def evaluate(run):
    run = Path(run).resolve()
    observation = _load(run / 'alignment-observation.json')
    truth_report = _load(run / 'debug-truth-evaluation.json')
    odometry = _load(run / 'odometry-evaluation.json')
    flight = _load(run / 'flight.json')
    phases = [json.loads(line) for line in (run / 'bridge-alignment-timeline.jsonl').read_text().splitlines()
              if line.strip()]

    goal_start_ns = int(flight['goal']['source_ns'])
    goal_end_ns = int(flight['goal_completed_source_ns'])
    hold = flight['post_goal_hold']
    requested_hold_s = float(hold['requested_sim_s'])
    if not hold.get('completed') or requested_hold_s <= 0:
        raise ValueError('a completed positive-duration post-goal hold is required')
    hold_end_ns = goal_end_ns + int(round(requested_hold_s * 1e9))
    landed_rows = [row for row in phases if row.get('phase') == 'LANDED']
    if not landed_rows:
        raise ValueError('bridge timeline has no LANDED phase')
    landed_ns = int(landed_rows[-1]['stamp_ns'])
    prestream_ns = int(odometry['interval']['start_source_ns'])
    if not prestream_ns <= goal_start_ns <= goal_end_ns < hold_end_ns <= landed_ns:
        raise ValueError('the flight, hold and landed timestamps are inconsistent')

    raw = [row for row in observation.get('samples', [])
           if row.get('kind') == 'raw_odom'
           and prestream_ns <= int(row.get('source_ns', -1)) <= landed_ns]
    raw_t = np.asarray([int(row['source_ns']) for row in raw], dtype=np.int64)
    raw_p = np.asarray([row['xyz'] for row in raw], dtype=float)
    raw_q = np.asarray([_unit_quaternion(row['q_xyzw']) for row in raw])
    if len(raw_t) < 3 or np.any(np.diff(raw_t) <= 0):
        raise ValueError('raw VINS pose samples must be sufficient and strictly monotonic')

    truth, truth_contract = imu_truth_samples(run, truth_report)
    require_same_truth_reference(odometry, truth_contract)
    truth_t = np.asarray([int(row['stamp_ns']) for row in truth], dtype=np.int64)
    truth_p = np.asarray([row['xyz'] for row in truth], dtype=float)
    truth_q = np.asarray([_unit_quaternion(row['q_xyzw']) for row in truth])
    if len(truth_t) < 3 or np.any(np.diff(truth_t) <= 0):
        raise ValueError('Gazebo truth pose samples must be sufficient and strictly monotonic')

    alignment_r = np.asarray(odometry['alignment']['rotation'], dtype=float)
    if alignment_r.shape != (3, 3) or odometry['alignment'].get('scale') != 1:
        raise ValueError('the frozen scale-one alignment is missing')

    with (run / 'odometry-errors.csv').open(newline='') as stream:
        errors = list(csv.DictReader(stream))

    velocity_report, velocity_samples = evaluate_velocity(run)

    # Use the same source-time arrival implementation as N10 acceptance.
    # The common reader already converted model-origin truth to the IMU.
    with tempfile.TemporaryDirectory(prefix='n10-full-route-arrival-') as temp_dir:
        arrival_report, _ = evaluate_arrival(
            run, output_name=str(Path(temp_dir) / 'arrival-evaluation.json'))
    arrival = arrival_report
    arrival_target = np.asarray(arrival['world_imu_goal_xyz'], dtype=float)
    yaw_offset_world = float(arrival['ground_yaw_offset_rad'])
    goal_yaw_world = float(flight['goal']['yaw_enu']) + yaw_offset_world
    position_tolerance_m = float(arrival['position_tolerance_m'])
    yaw_tolerance_deg = float(arrival['yaw_tolerance_deg'])
    independent_arrival = summarize_arrival_report(arrival_report)

    hold_truth_samples = []
    for row in truth:
        stamp = int(row['stamp_ns'])
        if not goal_end_ns <= stamp <= hold_end_ns:
            continue
        rotation_world = rotation(_unit_quaternion(row['q_xyzw']))
        yaw_world = float(np.arctan2(rotation_world[1, 0], rotation_world[0, 0]))
        yaw_error_deg = abs(float(np.degrees(np.arctan2(
            np.sin(yaw_world - goal_yaw_world), np.cos(yaw_world - goal_yaw_world)))))
        hold_truth_samples.append({
            'source_ns': stamp,
            'position_error_m': float(np.linalg.norm(
                np.asarray(row['xyz'], dtype=float) - arrival_target)),
            'yaw_error_deg': yaw_error_deg,
        })
    if len(hold_truth_samples) < 3:
        raise ValueError('insufficient truth samples during the requested hold')
    hold_position_errors = [row['position_error_m'] for row in hold_truth_samples]
    hold_yaw_errors = [row['yaw_error_deg'] for row in hold_truth_samples]
    first_position_exit = next((row for row in hold_truth_samples
                                if row['position_error_m'] > position_tolerance_m), None)
    target_hold_truth = {
        'start_source_ns': hold_truth_samples[0]['source_ns'],
        'end_source_ns': hold_truth_samples[-1]['source_ns'],
        'duration_sim_s': (hold_truth_samples[-1]['source_ns'] - hold_truth_samples[0]['source_ns']) / 1e9,
        'truth_sample_count': len(hold_truth_samples),
        'position_error_to_goal_m': _stats(hold_position_errors),
        'absolute_yaw_error_to_goal_deg': _stats(hold_yaw_errors),
        'inside_simultaneous_goal_tolerances_fraction': sum(
            p <= position_tolerance_m and y <= yaw_tolerance_deg
            for p, y in zip(hold_position_errors, hold_yaw_errors)) / len(hold_truth_samples),
        'first_position_exit_from_goal_sphere': None,
        'truth_is_offline_only': True,
    }
    if first_position_exit is not None:
        target_hold_truth['first_position_exit_from_goal_sphere'] = {
            'source_ns': first_position_exit['source_ns'],
            'elapsed_from_goal_completion_sim_s': (first_position_exit['source_ns'] - goal_end_ns) / 1e9,
            'position_error_m': first_position_exit['position_error_m'],
            'position_tolerance_m': position_tolerance_m,
        }

    intervals = {
        'goal_motion_and_arrival_dwell': (goal_start_ns, goal_end_ns),
        'diagnostic_post_goal_active_hold': (goal_end_ns, hold_end_ns),
        'diagnostic_hold_end_to_landed': (hold_end_ns, landed_ns),
        'prestream_to_landed': (prestream_ns, landed_ns),
    }
    horizons = (1.0, 5.0, 10.0)
    rpe_rows, rpe_detail = _rpe(
        raw_t, raw_p, raw_q, truth_t, truth_p, truth_q, alignment_r,
        horizons, 200_000_000, 40_000_000)

    def pose_error_summary(start_ns, end_ns):
        selected = [row for row in errors if start_ns <= int(row['source_ns']) <= end_ns]
        if not selected:
            return {'sample_count': 0, 'supported': False}
        position = [float(row['position_error_m']) for row in selected]
        yaw_abs = [abs(float(row['yaw_error_deg'])) for row in selected]
        return {
            'sample_count': len(selected), 'supported': True,
            'position_error_m': _stats(position),
            'absolute_yaw_error_deg': _stats(yaw_abs),
            'source_max_gap_sim_s': float(np.diff([int(row['source_ns']) for row in selected]).max() / 1e9)
            if len(selected) > 1 else None,
        }

    def velocity_summary(start_ns, end_ns):
        selected = [row for row in velocity_samples
                    if start_ns <= int(row['source_ns']) <= end_ns]
        if len(selected) < 3:
            return {'sample_count': len(selected), 'supported': False}
        error_norm = [float(row['velocity_error_norm_m_s']) for row in selected]
        truth_speed = [float(row['truth_speed_imu_m_s']) for row in selected]
        return {
            'sample_count': len(selected), 'supported': True,
            'velocity_error_norm_m_s': _stats(error_norm),
            'truth_speed_imu_m_s': _stats(truth_speed),
            'source_max_gap_sim_s': float(np.diff([int(row['source_ns']) for row in selected]).max() / 1e9),
        }

    def rpe_summary(start_ns, end_ns):
        result = {}
        for aggregate in rpe_rows:
            horizon = float(aggregate['target_window_s'])
            candidate = [int(stamp) for stamp in raw_t
                         if start_ns <= int(stamp) and int(stamp) + int(round(horizon * 1e9)) <= end_ns]
            supported = [row for row in rpe_detail
                         if float(row['window_s']) == horizon
                         and start_ns <= int(row['start_source_ns'])
                         and int(row['end_source_ns']) <= end_ns]
            if not supported:
                result[f'{horizon:g}s'] = {
                    'candidate_pairs': len(candidate), 'supported_pairs': 0,
                    'rejected_pairs': len(candidate), 'supported': False,
                }
                continue
            result[f'{horizon:g}s'] = {
                'candidate_pairs': len(candidate), 'supported_pairs': len(supported),
                'rejected_pairs': len(candidate) - len(supported), 'supported': True,
                'translation_error_m': _stats([float(row['translation_error_m']) for row in supported]),
                'rotation_error_deg': _stats([float(row['rotation_error_deg']) for row in supported]),
            }
        return result

    segments = {}
    for name, (start_ns, end_ns) in intervals.items():
        segments[name] = {
            'start_source_ns': start_ns, 'end_source_ns': end_ns,
            'duration_sim_s': (end_ns - start_ns) / 1e9,
            'absolute_pose_error': pose_error_summary(start_ns, end_ns),
            'relative_pose_error': rpe_summary(start_ns, end_ns),
            'velocity_error': velocity_summary(start_ns, end_ns),
        }

    landed_ns_from_odometry = int(odometry['interval']['end_source_ns'])
    if landed_ns_from_odometry != landed_ns:
        raise ValueError('bridge LANDED and odometry interval endpoints disagree')
    input_names = [
        'alignment-observation.json', 'debug-truth-evaluation.json',
        'odometry-evaluation.json', 'odometry-errors.csv', 'flight.json',
        'arrival-evaluation.json', 'bridge-alignment-timeline.jsonl', 'runtime-contract.json',
    ]
    input_hashes = {name: hashlib.sha256((run / name).read_bytes()).hexdigest()
                    for name in input_names}
    velocity_tool = ROOT / 'tools/debug_truth/evaluate_n10_vins_velocity.py'
    self_path = Path(__file__).resolve()
    report = {
        'schema': 'n10-full-route-vio-segmented-metrics/v1',
        'truth_reference_contract': truth_contract,
        'run_id': run.name,
        'classification': 'offline diagnostic re-segmentation; no acceptance thresholds declared',
        'runtime_contract_sha256': _load(run / 'runtime-contract.json')['sha256'],
        'alignment': odometry['alignment'],
        'segmentation': {
            'goal_start_source_ns': goal_start_ns,
            'goal_completion_source_ns': goal_end_ns,
            'hold_requested_sim_s': requested_hold_s,
            'hold_completed_sim_s': float(hold['observed_sim_s']),
            'hold_window_classification': 'diagnostic-only; not formal N16 600-s qualification',
            'formal_n16_qualification': False,
            'hold_end_source_ns': hold_end_ns,
            'hold_end_boundary_basis': 'goal completion source stamp plus completed requested simulation hold duration; the runner did not persist the exact clock stamp at hold-loop entry/exit',
            'landed_source_ns': landed_ns,
            'source_timestamp_domain': 'VINS and PX4/Gazebo simulation time; no wall-clock substitution',
        },
        'independent_arrival': independent_arrival,
        'target_relative_truth_during_hold': target_hold_truth,
        'segments': segments,
        'velocity_evaluator_original_window_note': 'Velocity evaluator v2 separates goal motion, completed requested hold, and landing; legacy v1 hold statistics included landing and must not be reused as hold-only evidence.',
        'coverage': {
            'raw_vins_pose_samples': len(raw_t),
            'raw_vins_max_source_gap_sim_s': float(np.diff(raw_t).max() / 1e9),
            'truth_pose_samples': len(truth_t),
            'truth_max_source_gap_sim_s': float(np.diff(truth_t).max() / 1e9),
            'velocity_supported_pairs': velocity_report['coverage']['truth_supported_pairs'],
            'velocity_pair_fraction': velocity_report['coverage']['truth_pair_fraction'],
        },
        'methods': {
            'position_yaw': 'Same prestream rigid rotation and scale=1 used by odometry-evaluation.json; absolute error samples are segmented by source timestamp.',
            'rpe': 'N01 evaluate_vio_full_state._rpe implementation; body-relative SE(3) increments over exact 1/5/10 simulated-second windows, raw interpolation gap <=0.2s, truth interpolation bracket <=0.04s, no per-segment refit.',
            'velocity': 'Same raw WORLD_FRAME_ID twist.linear and centered 0.2-s truth finite difference as the frozen #381 velocity evaluator; only segment boundaries are corrected.',
            'arrival': 'Delegates to evaluate_arrival.py: one fixed prestream scale-one SE(3), converted IMU truth reference, simultaneous position/yaw tolerances and contiguous Gazebo source-time dwell. Wall time is diagnostic only.',
            'hold_target_error': 'Uses the converted IMU truth point and goal from evaluate_arrival.py throughout the hold; no second PX4/body lever arm is applied and truth remains offline-only.',
            'thresholds': 'No runtime gate or acceptance threshold is created by this diagnostic.',
        },
        'input_sha256': input_hashes,
        'evaluator_sha256': {
            str(self_path.relative_to(ROOT)): hashlib.sha256(self_path.read_bytes()).hexdigest(),
            str(velocity_tool.relative_to(ROOT)): hashlib.sha256(velocity_tool.read_bytes()).hexdigest(),
        },
    }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    report = evaluate(args.run)
    out = args.run / 'n10-full-route-vio-segmented-metrics.json'
    out.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
