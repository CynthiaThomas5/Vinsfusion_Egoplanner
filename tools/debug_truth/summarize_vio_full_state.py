#!/usr/bin/env python3
"""Validate and summarize complete fresh-epoch raw VINS full-state reports."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def _read(path):
    return json.loads(Path(path).read_text())


def _verify_hashes(run, hashes):
    for name, expected in hashes.items():
        path = run / name
        if not path.is_file():
            raise ValueError(f'missing hashed input/output: {path}')
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f'hash mismatch: {path}')


def _range(values):
    array = np.asarray(values, dtype=float)
    return {'count': int(len(array)), 'min': float(np.min(array)),
            'median': float(np.median(array)), 'max': float(np.max(array))}


def _completion_basis(run, report):
    if report.get('fixture_motion_completed') is not True:
        raise ValueError(f'run is incomplete and cannot count toward the three epochs: {run.name}')
    if report.get('fixture_outcome') == 'unarmed_support_drift_completed':
        return 'probe_completed_and_acknowledged_fixture_removal'

    expected_error = 'detached fixture removal was not acknowledged'
    if report.get('fixture_outcome') != 'failed' or report.get('fixture_error') != expected_error:
        raise ValueError(f'run is incomplete and cannot count toward the three epochs: {run.name}')
    audit_path = run / 'fixture-cleanup-audit.json'
    if not audit_path.is_file():
        raise ValueError(f'run is incomplete and cannot count without a cleanup audit: {run.name}')
    audit = _read(audit_path)
    if (audit.get('schema_version') != 1 or audit.get('run_id') != run.name
            or audit.get('probe_outcome') != 'failed'
            or audit.get('probe_error') != expected_error
            or audit.get('completed_stages') != report.get('fixture_completed_stages')
            or audit.get('expected_stages') != report.get('fixture_expected_stages')
            or audit.get('completed_stages') != audit.get('expected_stages')
            or audit.get('attachment_states', [])[-1:] != ['detached']
            or audit.get('fixture_may_remain_attached') is not False
            or audit.get('fixture_present_in_gazebo_pose_info') is not False
            or audit.get('fixture_models') != []
            or audit.get('px4_disarmed') is not True
            or audit.get('px4_arming_state') != 1
            or audit.get('vehicle_landed') is not True):
        raise ValueError(f'cleanup audit does not independently verify safe completed teardown: {run.name}')
    required_inputs = {'fixture-result.json', 'fixture-stages.json', 'fixture-trace.jsonl',
                       'runtime-contract.json', 'vio-state-protocol.json'}
    hashes = audit.get('input_sha256', {})
    if not required_inputs.issubset(hashes):
        raise ValueError(f'cleanup audit does not hash all run evidence: {run.name}')
    _verify_hashes(run, hashes)
    return 'all_motion_stages_complete_and_postdetach_cleanup_independently_verified'


def summarize(run_dirs):
    if len(run_dirs) < 3:
        raise ValueError('N01 requires at least three complete fresh epochs')
    rows = []
    epochs = set()
    protocol_hashes, runtime_hashes = set(), set()
    for run_value in run_dirs:
        run = Path(run_value).resolve()
        report_path = run / 'vio-full-state-report.json'
        report = _read(report_path)
        returns_path = run / 'return-drift.json'
        returns = _read(returns_path)
        _verify_hashes(run, report.get('input_sha256', {}))
        _verify_hashes(run, report.get('output_sha256', {}))
        _verify_hashes(run, returns.get('input_sha256', {}))
        epoch = report.get('epoch')
        if not epoch or epoch in epochs:
            raise ValueError('each run must have a different VINS epoch')
        epochs.add(epoch)
        completion_basis = _completion_basis(run, report)
        if (returns.get('measurement_completed') is not True
                or returns.get('returns') != 3):
            raise ValueError(f'run is incomplete and cannot count toward the three epochs: {run.name}')
        if report.get('coverage', {}).get('velocity_truth_pairs', 0) < 3:
            raise ValueError(f'run lacks independent velocity pairs: {run.name}')
        for window in (1.0, 5.0, 10.0):
            item = next((value for value in report.get('rpe', [])
                         if value.get('target_window_s') == window), None)
            if item is None or item.get('supported_pairs', 0) < 1:
                raise ValueError(f'run lacks RPE support at {window:g}s: {run.name}')
        protocol_hashes.add(report.get('protocol_sha256'))
        runtime_hashes.add(report.get('runtime_contract_sha256'))
        rows.append({'run_id': run.name, 'epoch': epoch, 'report': report,
                     'returns': returns, 'completion_basis': completion_basis})
    if len(protocol_hashes) != 1 or None in protocol_hashes:
        raise ValueError('all epochs must use one byte-identical measurement protocol')
    if len(runtime_hashes) != 1 or None in runtime_hashes:
        raise ValueError('all epochs must use one identical runtime contract')

    def collect(path):
        values = []
        for row in rows:
            value = row['report']
            for key in path.split('.'):
                value = value[key]
            values.append(float(value))
        return _range(values)

    metrics = {
        'position_ate_rmse_m': collect('position_ate_m.rmse'),
        'position_ate_p95_m': collect('position_ate_m.p95'),
        'position_ate_max_m': collect('position_ate_m.max'),
        'attitude_geodesic_rmse_deg': collect('attitude_geodesic_error_deg.rmse'),
        'roll_rmse_deg': collect('roll_error_deg.rmse'),
        'pitch_rmse_deg': collect('pitch_error_deg.rmse'),
        'yaw_rmse_deg': collect('yaw_error_deg.rmse'),
        'velocity_vector_rmse_m_s': collect('velocity_error_m_s.rmse'),
        'source_age_p95_sim_s': collect('timing.source_age_at_receipt_sim_s.p95'),
        'max_source_gap_sim_s': collect('timing.max_source_gap_sim_s'),
        'max_receipt_gap_wall_s': collect('timing.max_receipt_gap_wall_s'),
        'pose_pair_fraction': collect('coverage.pose_pair_fraction'),
        'velocity_pair_fraction': collect('coverage.velocity_pair_fraction'),
        'raw_intervals_over_configured_support_limit': collect(
            'coverage.raw_intervals_over_configured_support_limit'),
        'duration_sim_s': collect('motion_support.source_duration_sim_s'),
        'truth_path_length_m': collect('motion_support.paired_truth_path_length_m'),
        'truth_speed_max_m_s': collect('motion_support.truth_imu_speed_m_s.max'),
        'truth_angular_speed_max_rad_s': collect('motion_support.truth_angular_speed_rad_s.max'),
        'yaw_span_deg': collect('motion_support.truth_yaw_span_deg'),
        'roll_excitation_span_deg': collect('motion_support.truth_roll_pitch_variation_from_level_deg.roll'),
        'pitch_excitation_span_deg': collect('motion_support.truth_roll_pitch_variation_from_level_deg.pitch'),
    }
    rpe = {}
    for window in (1.0, 5.0, 10.0):
        per_epoch = []
        for row in rows:
            value = next(item for item in row['report']['rpe'] if item['target_window_s'] == window)
            per_epoch.append({'run_id': row['run_id'],
                              'candidate_pairs': value['candidate_pairs'],
                              'supported_pairs': value['supported_pairs'],
                              'rejected_pairs': value['rejected_pairs'],
                              'translation_rmse_m': value['translation_error_m']['rmse'],
                              'rotation_rmse_deg': value['rotation_error_deg']['rmse']})
        rpe[f'{window:g}s'] = {
            'translation_rmse_m': _range([item['translation_rmse_m'] for item in per_epoch]),
            'rotation_rmse_deg': _range([item['rotation_rmse_deg'] for item in per_epoch]),
            'per_epoch': per_epoch}
    returns = {}
    for cycle in (1, 2, 3):
        selected = []
        for row in rows:
            value = next(item for item in row['returns']['checkpoints']
                         if item['label'] == 'return' and item['cycle'] == cycle)
            selected.append({'run_id': row['run_id'],
                             'position_drift_m': value['drift_since_reference_m'],
                             'yaw_drift_deg': value['yaw_drift_since_reference_deg'],
                             'truth_return_distance_m': value['truth_return_distance_m']})
        returns[f'cycle_{cycle}'] = {
            'position_drift_m': _range([item['position_drift_m'] for item in selected]),
            'yaw_drift_deg': _range([item['yaw_drift_deg'] for item in selected]),
            'per_epoch': selected}

    return {
        'schema_version': 1,
        'scope': 'Measurement summary only; no final localization accuracy or flight qualification.',
        'complete_fresh_epoch_count': len(rows),
        'epochs': [{'run_id': row['run_id'], 'epoch': row['epoch'],
                    'runtime_contract_sha256': row['report']['runtime_contract_sha256'],
                    'protocol_sha256': row['report']['protocol_sha256'],
                    'fixture_outcome': row['report']['fixture_outcome'],
                    'completion_basis': row['completion_basis']}
                   for row in rows],
        'cross_epoch_metrics': metrics,
        'rpe_by_window': rpe,
        'repeated_return_drift': returns,
        'limitations': [
            'Three-dimensional roll/pitch excitation is not part of the fixture protocol.',
            'Unarmed physical-support motion is not free flight.',
            'Simulation results do not qualify a real D435i, companion computer, texture, vibration, or hardware timing.',
            'Per-epoch metrics are summarized with min/median/max; they are not pooled into a single accuracy claim.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('runs', nargs='+', type=Path)
    args = parser.parse_args()
    result = summarize(args.runs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
