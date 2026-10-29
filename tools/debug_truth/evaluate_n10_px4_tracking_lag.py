#!/usr/bin/env python3
"""Measure PX4 body setpoint tracking in the PX4 timestamp domain.

This is a read-only post-run diagnostic. PX4 TrajectorySetpoint positions and
VehicleLocalPosition states are both NED body-reference values, so their
difference does not depend on the VIO-to-Gazebo alignment used by other N10
evaluators. The time-shift sweep is descriptive; it is not a control delay
estimate or an acceptance threshold.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def stats(values):
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        return {'count': 0, 'p50': None, 'p95': None, 'p99': None,
                'max': None, 'rms': None}
    return {
        'count': int(values.size),
        'p50': float(np.percentile(values, 50)),
        'p95': float(np.percentile(values, 95)),
        'p99': float(np.percentile(values, 99)),
        'max': float(np.max(values)),
        'rms': float(np.sqrt(np.mean(np.square(values)))),
    }


def interpolate_rows(stamps, values, query, max_bracket_gap):
    index = int(np.searchsorted(stamps, query, side='left'))
    if index < stamps.size and stamps[index] == query:
        return values[index], 0.0
    if index == 0 or index >= stamps.size:
        return None, None
    gap = float(stamps[index] - stamps[index - 1])
    if gap <= 0.0 or gap > max_bracket_gap:
        return None, gap
    ratio = (query - stamps[index - 1]) / gap
    return values[index - 1] + ratio * (values[index] - values[index - 1]), gap


def common_support_lag_sweep(local_stamps, local_positions, setpoint_stamps,
                             setpoint_positions, candidate_lags_s,
                             max_bracket_gap_us):
    """Compare every lag on the same local-state samples and setpoint coverage.

    A local sample is retained only when every candidate lag has a measured or
    tightly bracketed setpoint. This prevents a lag from appearing better only
    because its candidate used a different part of the route.
    """
    lags = [float(lag) for lag in candidate_lags_s]
    errors_by_lag = [[] for _ in lags]
    retained_stamps = []
    for stamp, position in zip(local_stamps, local_positions):
        references = []
        for lag in lags:
            query = int(round(int(stamp) - lag * 1e6))
            reference, _ = interpolate_rows(
                setpoint_stamps, setpoint_positions, query,
                max_bracket_gap_us)
            if reference is None:
                break
            references.append(reference)
        if len(references) != len(lags):
            continue
        retained_stamps.append(int(stamp))
        for errors, reference in zip(errors_by_lag, references):
            errors.append(float(np.linalg.norm(position - reference)))
    candidates = [
        {'setpoint_lookback_s': lag, **stats(errors)}
        for lag, errors in zip(lags, errors_by_lag)
    ]
    return {
        'sample_count': len(retained_stamps),
        'local_source_interval_us': ([retained_stamps[0], retained_stamps[-1]]
                                     if retained_stamps else None),
        'candidates': candidates,
    }


def evaluate(run, output=None):
    run = Path(run).resolve()
    flight_path = run / 'flight.json'
    runtime_path = run / 'runtime-contract.json'
    if not flight_path.is_file() or not runtime_path.is_file():
        raise FileNotFoundError('flight.json and runtime-contract.json are required')
    flight = json.loads(flight_path.read_text())
    runtime = json.loads(runtime_path.read_text())
    local_rows = [row for row in flight.get('local_position_history', [])
                  if row.get('wall_elapsed_s') is not None
                  and row.get('timestamp_sample_us', row.get('timestamp_us')) is not None
                  and all(math.isfinite(float(row.get(key, math.nan)))
                          for key in ('x', 'y', 'z'))]
    setpoint_rows = [row for row in flight.get('px4_trajectory_setpoint_observations', [])
                     if row.get('wall_elapsed_s') is not None
                     and row.get('timestamp_us') is not None
                     and len(row.get('position_ned', [])) == 3
                     and all(math.isfinite(float(value))
                             for value in row['position_ned'])]
    if not local_rows or not setpoint_rows:
        raise ValueError('PX4 local-position and trajectory-setpoint histories are required')

    goal_wall_start = float(flight['goal_sent_wall_elapsed_s'])
    goal_wall_end = goal_wall_start + float(
        flight.get('goal_timing', {}).get('wall_elapsed_s', 0.0))
    if goal_wall_end <= goal_wall_start:
        raise ValueError('flight record has no positive goal wall interval')

    local_rows.sort(key=lambda row: int(row.get('timestamp_sample_us', row['timestamp_us'])))
    local_stamps = np.asarray([
        int(row.get('timestamp_sample_us', row['timestamp_us']))
        for row in local_rows], dtype=np.int64)
    local_positions = np.asarray([[row['x'], row['y'], row['z']]
                                  for row in local_rows], dtype=float)
    local_wall = np.asarray([float(row['wall_elapsed_s']) for row in local_rows])
    setpoint_rows.sort(key=lambda row: int(row['timestamp_us']))
    setpoint_stamps = np.asarray([int(row['timestamp_us'])
                                  for row in setpoint_rows], dtype=np.int64)
    setpoint_positions = np.asarray([row['position_ned'] for row in setpoint_rows],
                                    dtype=float)
    setpoint_wall = np.asarray([float(row['wall_elapsed_s'])
                                for row in setpoint_rows])

    # Restrict statistics to observations received during the goal, then pair
    # position states and setpoints using their common PX4 boot-time stamps.
    active_setpoints = [i for i, wall in enumerate(setpoint_wall)
                        if goal_wall_start <= wall <= goal_wall_end]
    active_local = [i for i, wall in enumerate(local_wall)
                    if goal_wall_start <= wall <= goal_wall_end]
    max_pair_gap_us = 40_000
    paired_errors = []
    pair_gaps = []
    for i in active_setpoints:
        position, gap = interpolate_rows(
            local_stamps, local_positions, int(setpoint_stamps[i]), max_pair_gap_us)
        if position is None:
            continue
        paired_errors.append(float(np.linalg.norm(setpoint_positions[i] - position)))
        if gap is not None:
            pair_gaps.append(gap / 1e6)

    candidate_lags_s = np.round(np.arange(0.0, 3.0001, 0.02), 8)
    lag_sweep = []
    for lag_s in candidate_lags_s:
        errors = []
        for i in active_local:
            query = int(round(local_stamps[i] - lag_s * 1e6))
            reference, _ = interpolate_rows(
                setpoint_stamps, setpoint_positions, query, max_pair_gap_us)
            if reference is not None:
                errors.append(float(np.linalg.norm(local_positions[i] - reference)))
        if errors:
            summary = stats(errors)
            lag_sweep.append({'setpoint_lookback_s': float(lag_s), **summary})
    best_lag = min(lag_sweep, key=lambda row: row['rms']) if lag_sweep else None
    common_support = common_support_lag_sweep(
        local_stamps[active_local], local_positions[active_local],
        setpoint_stamps, setpoint_positions, candidate_lags_s,
        max_pair_gap_us)
    common_candidates = common_support['candidates']
    best_common_lag = (min(common_candidates, key=lambda row: row['rms'])
                       if common_candidates and common_support['sample_count']
                       else None)
    # The preliminary varying-support scan on #381/#385 selected 1.06 s.
    # Re-evaluate that fixed candidate beside zero lag on the exact same local
    # state rows. This remains descriptive because candidate selection used
    # these archives; it is not an independent causal confirmation.
    fixed_lag_s = 1.06
    fixed_lag_contrast = common_support_lag_sweep(
        local_stamps[active_local], local_positions[active_local],
        setpoint_stamps, setpoint_positions, [0.0, fixed_lag_s],
        max_pair_gap_us)

    detail = [row.get('detail', {}) for row in flight.get('bridge_detail_history', [])]
    clock_gaps = [float(row['px4_ros_clock_gap_sim_s']) for row in detail
                  if row.get('px4_ros_clock_gap_sim_s') is not None
                  and math.isfinite(float(row['px4_ros_clock_gap_sim_s']))]
    result = {
        'schema': 'n10-px4-position-tracking-lag/v2',
        'run_id': run.name,
        'classification': 'offline same-PX4-domain tracking diagnostic; no acceptance threshold or runtime effect',
        'read_only': True,
        'control_published': False,
        'identity': {
            'runtime_contract_sha256': runtime.get('sha256'),
            'goal_id': flight.get('goal_id'),
            'epoch': flight.get('localization_epoch'),
            'goal_wall_interval_s': [goal_wall_start, goal_wall_end],
        },
        'reference': {
            'setpoint': 'PX4 TrajectorySetpoint.position in local NED body coordinates',
            'state': 'PX4 VehicleLocalPosition x/y/z in local NED body coordinates',
            'state_timestamp': 'timestamp_sample_us, falling back to timestamp_us',
            'pairing': 'linear interpolation in the shared PX4 timestamp domain; no extrapolation; bracket at most 0.04 s',
        },
        'sample_counts': {
            'local_position_goal_window': len(active_local),
            'trajectory_setpoint_goal_window': len(active_setpoints),
            'paired_same_time_samples': len(paired_errors),
            'unpaired_setpoints': len(active_setpoints) - len(paired_errors),
        },
        'same_time_position_error_m': stats(paired_errors),
        'maximum_state_interpolation_bracket_s': max(pair_gaps, default=None),
        'setpoint_lookback_sweep': {
            'purpose': 'diagnostic only: compare current PX4 position with earlier published setpoints; no control timing is changed',
            'best_rms_candidate': best_common_lag,
            'common_support_sample_count': common_support['sample_count'],
            'common_support_local_source_interval_us': common_support['local_source_interval_us'],
            'common_support_candidates': common_candidates,
            'fixed_candidate_contrast': {
                'candidate_lookback_s': fixed_lag_s,
                'selection_basis': '1.06 s was the preliminary varying-support minimum-RMS candidate on #381/#385; this matched-support comparison uses the same archives and is not an independent holdout.',
                'pairing_max_bracket_s': max_pair_gap_us / 1e6,
                'sample_count': fixed_lag_contrast['sample_count'],
                'local_source_interval_us': fixed_lag_contrast['local_source_interval_us'],
                'zero_lookback': fixed_lag_contrast['candidates'][0],
                'fixed_lookback': fixed_lag_contrast['candidates'][1],
                'classification': 'descriptive same-sample time-shift correlation; not a measured control delay or causal diagnosis',
            },
            'varying_support_best_rms_candidate': best_lag,
            'varying_support_candidates': lag_sweep,
            'interpretation_limit': 'The common-support sweep equalizes local-state rows and measured/bracketed setpoint coverage across lag candidates. A lower residual still shows only time-shift correlation; it does not identify a physical/software delay or justify delay compensation.',
        },
        'bridge_px4_ros_clock_gap_sim_s': stats(clock_gaps),
        'inputs_sha256': {
            'flight.json': sha256(flight_path),
            'runtime-contract.json': sha256(runtime_path),
        },
        'tool_sha256': sha256(Path(__file__)),
        'limitations': [
            'This comparison verifies the direct PX4 setpoint-to-state discrepancy without relying on Gazebo truth or VIO alignment.',
            'It does not diagnose whether the discrepancy comes from controller response, trajectory replanning, clocking, or vehicle dynamics.',
            'The common-support lookback sweep is descriptive and must not be converted into controller delay compensation without a separate causal test.',
        ],
    }
    output = Path(output) if output else run / 'n10-px4-position-tracking-analysis.json'
    if not output.is_absolute():
        output = run / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = evaluate(args.run, args.output)
    print(json.dumps({
        'run_id': result['run_id'],
        'same_time_position_error_m': result['same_time_position_error_m'],
        'best_rms_lookback': result['setpoint_lookback_sweep']['best_rms_candidate'],
        'paired_same_time_samples': result['sample_counts']['paired_same_time_samples'],
    }, allow_nan=False))


if __name__ == '__main__':
    main()
