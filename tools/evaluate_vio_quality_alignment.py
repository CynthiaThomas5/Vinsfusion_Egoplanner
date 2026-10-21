#!/usr/bin/env python3
"""Correlate read-only Gazebo VIO pose error with VINS quality telemetry."""
import argparse
import json
from pathlib import Path

import numpy as np

from evaluate_vins_motion import rotation


def _stamp(sample):
    if 'stamp_ns' in sample:
        return int(sample['stamp_ns'])
    return int(round(float(sample['stamp']) * 1e9))


def _unit_quaternion(value):
    q = np.asarray(value, dtype=float)
    norm = np.linalg.norm(q)
    if q.shape != (4,) or not np.isfinite(norm) or norm < 1e-9:
        raise ValueError('Invalid pose quaternion')
    return q / norm


def _interpolate_position(stamps, positions, query_ns):
    right = int(np.searchsorted(stamps, query_ns, side='left'))
    if right < len(stamps) and stamps[right] == query_ns:
        return positions[right].copy(), 0
    if right == 0 or right == len(stamps):
        raise ValueError('Pose sample lies outside truth coverage')
    left = right - 1
    gap = int(stamps[right] - stamps[left])
    ratio = (query_ns - stamps[left]) / gap
    return positions[left] + ratio * (positions[right] - positions[left]), gap


def _interpolate_quaternion(stamps, quaternions, query_ns):
    right = int(np.searchsorted(stamps, query_ns, side='left'))
    if right < len(stamps) and stamps[right] == query_ns:
        return quaternions[right].copy()
    if right == 0 or right == len(stamps):
        raise ValueError('Pose sample lies outside truth coverage')
    left = right - 1
    q0, q1 = quaternions[left], quaternions[right]
    dot = float(np.dot(q0, q1))
    if dot < 0.0:
        q1, dot = -q1, -dot
    ratio = (query_ns - stamps[left]) / (stamps[right] - stamps[left])
    if dot > 0.9995:
        return _unit_quaternion(q0 + ratio * (q1 - q0))
    angle = np.arccos(np.clip(dot, -1.0, 1.0))
    sine = np.sin(angle)
    return _unit_quaternion(
        np.sin((1.0 - ratio) * angle) / sine * q0
        + np.sin(ratio * angle) / sine * q1)


def _stats(values):
    values = np.asarray(values, dtype=float)
    if not len(values):
        return {'count': 0, 'rmse': None, 'median': None, 'p95': None, 'max': None}
    return {'count': int(len(values)),
            'rmse': float(np.sqrt(np.mean(values ** 2))),
            'median': float(np.median(values)),
            'p95': float(np.percentile(values, 95)),
            'max': float(np.max(values))}


def _quality_rows(telemetry):
    rows = []
    for sample in telemetry:
        stamp = _stamp(sample)
        residuals = int(sample.get('residual_components', 0) or 0)
        if 'normalized_cost' in sample:
            cost = float(sample['normalized_cost'])
        elif residuals > 0:
            cost = float(np.sqrt(2.0 * float(sample['final_cost']) / residuals))
        else:
            continue
        if not np.isfinite(cost):
            continue
        rows.append((stamp, cost, sample))
    rows.sort(key=lambda row: row[0])
    stamps = np.asarray([row[0] for row in rows], dtype=np.int64)
    if len(stamps) < 3 or np.any(np.diff(stamps) <= 0):
        raise ValueError('Quality telemetry needs at least three strictly increasing stamps')
    return stamps, rows


def _quality_sample_summary(row):
    stamp, cost, sample = row
    return {
        'stamp_ns': int(stamp),
        'normalized_cost': float(cost),
        'final_cost': float(sample['final_cost']),
        'residual_components': int(sample['residual_components']),
        'visual_observations': int(sample.get('visual_observations', 0)),
        'termination_type': int(sample.get('termination_type', -1)),
        'iterations': int(sample.get('iterations', 0)),
    }


def _quality_gate_dynamics(quality, gate_index, threshold, followup_s=2.0):
    if gate_index is None:
        return None

    gate = quality[gate_index]
    gate_stamp = gate[0]
    previous = quality[gate_index - 1] if gate_index > 0 else None
    followup_end = gate_stamp + int(followup_s * 1e9)
    followup = [row for row in quality
                if gate_stamp < row[0] <= followup_end]
    recovery = next((row for row in followup if row[1] <= threshold), None)
    peak = max([gate] + followup, key=lambda row: row[1])

    deltas = None
    if previous is not None:
        previous_sample = previous[2]
        gate_sample = gate[2]
        deltas = {
            'normalized_cost': float(gate[1] - previous[1]),
            'final_cost': float(gate_sample['final_cost'] - previous_sample['final_cost']),
            'residual_components': int(
                gate_sample['residual_components'] - previous_sample['residual_components']),
            'visual_observations': int(
                gate_sample.get('visual_observations', 0)
                - previous_sample.get('visual_observations', 0)),
        }

    return {
        'threshold': float(threshold),
        'crossing': _quality_sample_summary(gate),
        'previous_sample': _quality_sample_summary(previous) if previous else None,
        'change_from_previous': deltas,
        'first_recovery_at_or_below_threshold': ({
            **_quality_sample_summary(recovery),
            'delay_s': float((recovery[0] - gate_stamp) / 1e9),
        } if recovery else None),
        'followup_horizon_s': float(followup_s),
        'followup_sample_count': len(followup),
        'followup_samples_above_threshold': sum(
            row[1] > threshold for row in followup),
        'peak_within_followup': _quality_sample_summary(peak),
    }


def evaluate(capture, flight_report, max_normalized_cost=1.0,
             max_truth_gap_s=0.08, max_quality_gap_s=0.10):
    truth = capture['truth']
    odometry = capture['optimized']
    telemetry = capture['telemetry']
    health = flight_report.get('localization_quality_history', [])
    if len(truth) < 20 or len(odometry) < 20 or len(health) < 3:
        raise ValueError('Insufficient truth, optimized odometry, or health history')

    truth_stamps = np.asarray([_stamp(row) for row in truth], dtype=np.int64)
    vio_stamps = np.asarray([_stamp(row) for row in odometry], dtype=np.int64)
    if np.any(np.diff(truth_stamps) <= 0) or np.any(np.diff(vio_stamps) <= 0):
        raise ValueError('Truth and VIO source stamps must be strictly increasing')

    health_stamps = np.asarray([int(row['stamp_ns']) for row in health], dtype=np.int64)
    window_start, window_end = int(health_stamps.min()), int(health_stamps.max())
    keep = (vio_stamps >= window_start) & (vio_stamps <= window_end)
    odometry = [row for row, valid in zip(odometry, keep) if valid]
    vio_stamps = vio_stamps[keep]
    if len(odometry) < 20:
        raise ValueError('Insufficient VIO samples in the PX4 flight probe window')

    truth_positions = np.asarray([row['position'] for row in truth], dtype=float)
    truth_quaternions = np.asarray([_unit_quaternion(row['quaternion']) for row in truth])
    estimated_positions = np.asarray([row['position'] for row in odometry], dtype=float)
    estimated_quaternions = np.asarray([_unit_quaternion(row['quaternion']) for row in odometry])
    paired_truth_positions, paired_truth_quaternions, truth_gaps = [], [], []
    for stamp in vio_stamps:
        position, gap = _interpolate_position(truth_stamps, truth_positions, int(stamp))
        quaternion = _interpolate_quaternion(truth_stamps, truth_quaternions, int(stamp))
        paired_truth_positions.append(position)
        paired_truth_quaternions.append(quaternion)
        truth_gaps.append(gap)
    paired_truth_positions = np.asarray(paired_truth_positions)
    paired_truth_quaternions = np.asarray(paired_truth_quaternions)
    if max(truth_gaps, default=0) > max_truth_gap_s * 1e9:
        raise ValueError('Truth interpolation gap exceeds the configured limit')

    # Use one fixed pose alignment at the first paired sample. This keeps yaw
    # observable on the mostly vertical flight path without fitting a scale.
    align_rotation = (rotation(paired_truth_quaternions[0])
                      @ rotation(estimated_quaternions[0]).T)
    align_translation = (paired_truth_positions[0]
                         - align_rotation @ estimated_positions[0])
    aligned_positions = (align_rotation @ estimated_positions.T).T + align_translation
    position_errors = np.linalg.norm(aligned_positions - paired_truth_positions, axis=1)
    orientation_errors = np.asarray([
        np.arccos(np.clip((np.trace(
            rotation(reference).T @ align_rotation @ rotation(estimated)) - 1.0) / 2.0,
            -1.0, 1.0)) * 180.0 / np.pi
        for estimated, reference in zip(estimated_quaternions, paired_truth_quaternions)
    ])

    quality_stamps, quality = _quality_rows(telemetry)
    telemetry_index = np.searchsorted(quality_stamps, vio_stamps, side='left')
    telemetry_index = np.clip(telemetry_index, 0, len(quality_stamps) - 1)
    previous = np.maximum(telemetry_index - 1, 0)
    use_previous = (np.abs(quality_stamps[previous] - vio_stamps)
                    < np.abs(quality_stamps[telemetry_index] - vio_stamps))
    telemetry_index = np.where(use_previous, previous, telemetry_index)
    quality_gaps = np.abs(quality_stamps[telemetry_index] - vio_stamps)
    matched = quality_gaps <= max_quality_gap_s * 1e9

    timeline = []
    for index, row in enumerate(odometry):
        cost_index = int(telemetry_index[index]) if matched[index] else None
        metrics = quality[cost_index][2] if cost_index is not None else {}
        timeline.append({
            'stamp_ns': int(vio_stamps[index]),
            'position_error_m': float(position_errors[index]),
            'orientation_error_deg': float(orientation_errors[index]),
            'normalized_cost': float(quality[cost_index][1]) if cost_index is not None else None,
            'quality_gap_s': float(quality_gaps[index] / 1e9) if cost_index is not None else None,
            'input_features': metrics.get('input_features'),
            'stereo_features': metrics.get('stereo_features'),
            'continued_tracks': metrics.get('continued_tracks'),
            'long_tracks': metrics.get('long_tracks'),
            'accel_bias_norm': metrics.get('accel_bias_norm'),
            'gyro_bias_norm': metrics.get('gyro_bias_norm'),
            'solve_seconds': metrics.get('solve_seconds'),
        })

    cost_rows = [row for row in timeline if row['normalized_cost'] is not None]
    costs = np.asarray([row['normalized_cost'] for row in cost_rows], dtype=float)
    errors = np.asarray([row['position_error_m'] for row in cost_rows], dtype=float)
    correlation = None
    if len(costs) >= 3 and np.std(costs) > 0.0 and np.std(errors) > 0.0:
        correlation = float(np.corrcoef(costs, errors)[0, 1])
    quality_correlations = {}
    for field in ('input_features', 'stereo_features', 'continued_tracks',
                  'long_tracks', 'accel_bias_norm', 'gyro_bias_norm'):
        samples = [(row[field], row['position_error_m']) for row in cost_rows
                   if row.get(field) is not None]
        values = np.asarray([sample[0] for sample in samples], dtype=float)
        pose_errors = np.asarray([sample[1] for sample in samples], dtype=float)
        quality_correlations[field + '_position_error_pearson_r'] = (
            float(np.corrcoef(values, pose_errors)[0, 1])
            if len(values) >= 3 and np.std(values) > 0.0
            and np.std(pose_errors) > 0.0 else None)

    first_gate = next((row for row in health
                       if row.get('normalized_cost', 0.0) > max_normalized_cost
                       or row.get('reason') == 'normalized_cost_exceeded'), None)
    gate_status_source_stamp = int(first_gate['source_stamp_ns']) if first_gate else None
    gate_quality_stamp = None
    gate_quality_index = None
    gate_index = None
    if gate_status_source_stamp is not None:
        gate_cost = float(first_gate['normalized_cost'])
        matching_cost_rows = [index for index, row in enumerate(quality)
                              if abs(row[1] - gate_cost) <= 1e-9]
        if matching_cost_rows:
            quality_index = min(
                matching_cost_rows,
                key=lambda index: abs(quality[index][0] - gate_status_source_stamp))
        else:
            quality_index = int(np.argmin(
                np.abs(quality_stamps - gate_status_source_stamp)))
        gate_quality_stamp = int(quality_stamps[quality_index])
        gate_quality_index = quality_index
        nearest = int(np.argmin(np.abs(vio_stamps - gate_quality_stamp)))
        if abs(int(vio_stamps[nearest]) - gate_quality_stamp) <= max_quality_gap_s * 1e9:
            gate_index = nearest

    high_cost = [row for row in cost_rows
                 if row['normalized_cost'] > max_normalized_cost]
    after_gate = ([row['position_error_m'] for row in timeline
                   if gate_quality_stamp is not None
                   and row['stamp_ns'] >= gate_quality_stamp])

    return {
        'scope': 'Diagnostic VIO flight comparison; evaluator-only truth, not formal acceptance',
        'alignment': 'One rigid SE(3) anchored at the first paired pose; scale fixed to 1; no segment realignment',
        'flight_window_stamp_ns': [window_start, window_end],
        'paired_samples': len(timeline),
        'truth_child_frames': sorted({row.get('child_frame', '') for row in truth}),
        'vio_child_frames': sorted({row.get('child_frame', '') for row in odometry}),
        'truth_position_span_m': np.ptp(paired_truth_positions, axis=0).tolist(),
        'vio_position_span_m': np.ptp(estimated_positions, axis=0).tolist(),
        'position_error_m': _stats(position_errors),
        'orientation_error_deg': _stats(orientation_errors),
        'alignment_rotation': align_rotation.tolist(),
        'alignment_translation': align_translation.tolist(),
        'quality_samples_matched': len(cost_rows),
        'quality_match_max_gap_s': float(np.max(quality_gaps[matched]) / 1e9) if matched.any() else None,
        'normalized_cost_max': float(np.max(costs)) if len(costs) else None,
        'normalized_cost_position_error_pearson_r': correlation,
        'quality_metrics_position_error_pearson_r': quality_correlations,
        'samples_above_health_limit': len(high_cost),
        'position_error_when_cost_above_limit_m': _stats(
            [row['position_error_m'] for row in high_cost]),
        'first_health_gate_crossing': ({
            'localization_status_stamp_ns': int(first_gate['stamp_ns']),
            'localization_status_source_stamp_ns': gate_status_source_stamp,
            'quality_telemetry_stamp_ns': gate_quality_stamp,
            'quality_to_status_source_gap_s': (
                float((gate_quality_stamp - gate_status_source_stamp) / 1e9)
                if gate_quality_stamp is not None else None),
            'normalized_cost': float(first_gate['normalized_cost']),
            'reason': first_gate['reason'],
            'aligned_position_error_m': (float(position_errors[gate_index])
                                         if gate_index is not None else None),
        } if first_gate else None),
        'quality_gate_dynamics': _quality_gate_dynamics(
            quality, gate_quality_index, max_normalized_cost),
        'position_error_after_first_gate_m': _stats(after_gate),
        'timeline': timeline,
        'interpretation_limit': 'One run can show temporal association but cannot establish a universal quality-to-error threshold.',
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--capture', type=Path, required=True,
                        help='Directory written by probe_vins.py with diagnostic truth enabled')
    parser.add_argument('--flight-report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--max-normalized-cost', type=float, default=1.0)
    args = parser.parse_args()
    if args.max_normalized_cost <= 0.0:
        parser.error('--max-normalized-cost must be positive')
    capture_summary = json.loads((args.capture / 'summary.json').read_text())
    if (capture_summary.get('diagnostic_truth_enabled') is not True
            or capture_summary.get('truth_topic') != '/debug_truth/base_odometry'
            or capture_summary.get('imu_topic') != '/sensors/d435i/imu'):
        raise ValueError('Capture was not made with the guarded read-only Gazebo truth observer')
    capture = {
        'truth': json.loads((args.capture / 'truth-motion.json').read_text())['truth'],
        'optimized': json.loads((args.capture / 'raw-odometry.json').read_text())['optimized'],
        'telemetry': json.loads((args.capture / 'telemetry.json').read_text()),
    }
    report = json.loads(args.flight_report.read_text())
    if report.get('profile') != 'vio_closed_loop':
        raise ValueError('Flight report is not from the vio_closed_loop profile')
    result = evaluate(capture, report, args.max_normalized_cost)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key != 'timeline'}, indent=2))


if __name__ == '__main__':
    main()
