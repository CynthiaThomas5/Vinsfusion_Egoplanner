#!/usr/bin/env python3
"""Offline repeated-return drift baseline; never realigns individual returns."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def wrap(angle):
    return (angle + 180) % 360 - 180


def circle_mean(values):
    radians = np.radians(values)
    return float(np.degrees(np.arctan2(np.sin(radians).mean(), np.cos(radians).mean())))


def score_windows(rows, stages, protocol):
    stamps = np.array([int(p['source_ns']) for p in rows], dtype=np.int64)
    if len(stamps) < 3 or np.any(np.diff(stamps) <= 0):
        raise ValueError('nonmonotonic or insufficient pose-error rows')
    checkpoints = [s for s in stages if s['label'] in ('reference', 'return')]
    if not checkpoints or checkpoints[0]['label'] != 'reference':
        raise ValueError('no initial reference checkpoint')
    if sum(s['label'] == 'reference' for s in checkpoints) != 1:
        raise ValueError('cannot realign additional references')
    measurements = []
    for stage in checkpoints:
        end = round(stage['end_sim_s'] * 1e9)
        begin = end - round(protocol['stationary_tail_sim_s'] * 1e9)
        selected = [p for p in rows if begin <= int(p['source_ns']) <= end]
        if (len(selected) < 3 or int(selected[0]['source_ns']) - begin > 250_000_000
                or end - int(selected[-1]['source_ns']) > 250_000_000
                or max(np.diff([int(p['source_ns']) for p in selected])) > 250_000_000):
            raise ValueError('insufficient source-time coverage of a return hold')
        truth = np.array([[float(p['truth_'+axis+'_m']) for axis in 'xyz'] for p in selected])
        errors = np.array([[float(p['d'+axis+'_m']) for axis in 'xyz'] for p in selected])
        yaws = np.array([float(p['truth_yaw_deg']) for p in selected])
        yaw_errors = np.array([float(p['yaw_error_deg']) for p in selected])
        m = {'label': stage['label'], 'cycle': stage.get('cycle', 0),
             'checkpoint_sim_s': stage['end_sim_s'], 'samples': len(selected),
             'mean_truth_xyz_m': truth.mean(axis=0).tolist(),
             'mean_truth_yaw_deg': circle_mean(yaws),
             'mean_position_error_vector_m': errors.mean(axis=0).tolist(),
             'position_error_of_mean_m': float(np.linalg.norm(errors.mean(axis=0))),
             'position_error_rmse_m': float(np.sqrt(np.mean(np.sum(errors**2, axis=1)))),
             'position_error_max_m': float(np.max(np.linalg.norm(errors, axis=1))),
             'mean_yaw_error_deg': circle_mean(yaw_errors)}
        reference = measurements[0] if measurements else m
        m['truth_return_distance_m'] = float(np.linalg.norm(truth.mean(axis=0)-reference['mean_truth_xyz_m']))
        m['truth_return_yaw_difference_deg'] = float(wrap(m['mean_truth_yaw_deg']-reference['mean_truth_yaw_deg']))
        m['truth_return_max_distance_m'] = float(np.max(np.linalg.norm(truth-reference['mean_truth_xyz_m'], axis=1)))
        m['truth_return_max_yaw_difference_deg'] = float(np.max(np.abs(wrap(yaws-reference['mean_truth_yaw_deg']))))
        m['repeatable_truth_pose'] = (m['truth_return_max_distance_m'] <= protocol['return_position_tolerance_m']
                                      and m['truth_return_max_yaw_difference_deg'] <= protocol['return_yaw_tolerance_deg'])
        m['drift_since_reference_vector_m'] = (errors.mean(axis=0)-reference['mean_position_error_vector_m']).tolist()
        m['drift_since_reference_m'] = float(np.linalg.norm(m['drift_since_reference_vector_m']))
        m['yaw_drift_since_reference_deg'] = float(wrap(m['mean_yaw_error_deg']-reference['mean_yaw_error_deg']))
        measurements.append(m)
    cycles = [m['cycle'] for m in measurements if m['label'] == 'return']
    elapsed = measurements[-1]['checkpoint_sim_s'] - measurements[0]['checkpoint_sim_s']
    complete = (cycles == list(range(1, protocol['required_returns']+1))
                and elapsed >= protocol['minimum_duration_sim_s']
                and all(m['repeatable_truth_pose'] for m in measurements))
    times = np.array([m['checkpoint_sim_s']-measurements[0]['checkpoint_sim_s'] for m in measurements]) / 60
    trend = None
    if len(times) >= 2:
        centered = times-times.mean()
        def slope(values):
            a = np.array(values)
            return float(np.dot(centered, a-a.mean()) / np.dot(centered, centered))
        trend = {'return_drift_norm_slope_m_per_min': slope([m['drift_since_reference_m'] for m in measurements]),
                 'signed_yaw_drift_slope_deg_per_min': slope([m['yaw_drift_since_reference_deg'] for m in measurements]),
                 'note': 'Descriptive fit across one reference and available returns; not proof of long-term stability.'}
    return {'measurement_completed': bool(complete), 'elapsed_reference_to_last_return_sim_s': elapsed,
            'returns': len(cycles), 'checkpoints': measurements, 'descriptive_trend': trend}


def evaluate(run):
    report = json.loads((run/'fixture-odometry-errors.json').read_text())
    fixture = json.loads((run/'fixture-result.json').read_text())
    if fixture['profile'] != 'drift' or fixture['epoch'] != report['epoch']:
        raise ValueError('not the same drift session')
    # Protocol is captured before the run, not silently taken from a later config.
    protocol = json.loads((run/'drift-protocol.json').read_text())['drift_measurement']
    stages = json.loads((run/'fixture-stages.json').read_text())
    rows = list(csv.DictReader((run/'fixture-odometry-errors.csv').open()))
    result = score_windows(rows, stages, protocol)
    result.update(scope=__doc__, epoch=fixture['epoch'], protocol=protocol,
                  fixture_outcome=fixture['outcome'], fixture_error=fixture['error'],
                  fixed_initial_alignment_only=True, no_drift_proven=False,
                  odometry_summary=report,
                  limitations=['Local supported motion only, not long-distance flight or actual loop correction.',
                               'One session with three returns cannot guarantee long-term bounded drift.',
                               'Truth-repeatability tolerances judge the experiment, not odometry accuracy.'])
    result['input_sha256'] = {name: hashlib.sha256((run/name).read_bytes()).hexdigest() for name in
                              ['fixture-odometry-errors.json', 'fixture-odometry-errors.csv',
                               'fixture-result.json', 'fixture-stages.json', 'drift-protocol.json']}
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    result = evaluate(args.run)
    (args.run/'return-drift.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
