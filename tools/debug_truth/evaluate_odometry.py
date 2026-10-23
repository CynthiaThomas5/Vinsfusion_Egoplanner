#!/usr/bin/env python3
"""Offline raw VINS errors with one pre-enable pose alignment, scale fixed to one.

In the simulation, Gazebo's world -> d435i_link truth origin coincides with the
D435i IMU. No translation is added to this truth point. The SDF base_link mount
offset is for base-to-sensor conversion and must not be added twice.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src/own/uav_sim'))
from evaluate_vins_motion import rotation
from evaluate_vio_quality_alignment import (
    _interpolate_position, _interpolate_quaternion, _stats, _unit_quaternion)
from uav_sim.geometry import px4_sensor_mount


def pose_arrays(rows, stamp_key):
    stamps = np.asarray([p[stamp_key] for p in rows], dtype=np.int64)
    xyz = np.asarray([p['xyz'] for p in rows], dtype=float)
    if len(stamps) < 3 or np.any(np.diff(stamps) <= 0):
        raise ValueError('Need strictly increasing source stamps; no sorting or repair')
    if xyz.shape != (len(stamps), 3) or not np.isfinite(xyz).all():
        raise ValueError('Invalid position samples')
    quaternions = np.asarray([_unit_quaternion(p['q_xyzw']) for p in rows])
    return stamps, xyz, quaternions


def evaluate(observation, truth, phases, preflight, flight, lever,
             truth_gap_s=0.04, support_gap_s=0.2):
    if not (np.isfinite(truth_gap_s) and np.isfinite(support_gap_s)
            and truth_gap_s > 0 and support_gap_s > 0):
        raise ValueError('Interpolation and reporting gap limits must be positive')
    epoch = observation['epoch']
    if not epoch or observation['raw_topic'] != '/vins_raw/s_' + epoch + '/odometry':
        raise ValueError('Raw topic and epoch disagree')
    raw = [p for p in observation['samples'] if p['kind'] == 'raw_odom']
    adapted = [p for p in observation['samples'] if p['kind'] == 'odom']
    for rows, world, body in [(raw, f'vins_{epoch}_world', f'vins_{epoch}_imu'),
                              (adapted, f'odom_{epoch}', f'd435i_imu_{epoch}')]:
        if any(p['frame_id'] != world or p['child_frame_id'] != body for p in rows):
            raise ValueError('Frame or epoch changed; cannot stitch sessions')
        pose_arrays(rows, 'source_ns')
    et, ep, eq = pose_arrays(raw, 'source_ns')
    tt, tp, tq = pose_arrays(truth, 'stamp_ns')
    lever = np.asarray(lever, dtype=float)
    if lever.shape != (3,) or not np.isfinite(lever).all():
        raise ValueError('Invalid model-to-IMU lever arm')
    starts = [p['stamp_ns'] for p in phases if p['phase'] == 'PRESTREAM']
    ends = [p['stamp_ns'] for p in phases if p['phase'] == 'LANDED']
    if len(starts) != 1 or len(ends) != 1 or ends[0] <= starts[0]:
        raise ValueError('Need one complete PRESTREAM-to-LANDED flight')
    start, end = starts[0], ends[0]
    target = preflight['clock_samples'][-1]['sim_ns'] - 1_000_000_000
    before = np.flatnonzero(et <= target)
    if not len(before) or target >= start:
        raise ValueError('No pre-enable initialization reference')
    anchor = int(before[-1])
    if target - et[anchor] > 150_000_000:
        raise ValueError('Initialization reference is more than 150ms old')

    def reference(stamp):
        p, gap = _interpolate_position(tt, tp, stamp)
        if gap > truth_gap_s * 1e9:
            raise ValueError('Truth interpolation gap exceeds limit')
        q = _interpolate_quaternion(tt, tq, stamp)
        r = rotation(q)
        return p + r @ lever, r

    p0, r0 = reference(et[anchor])
    align_r = r0 @ rotation(eq[anchor]).T
    align_t = p0 - align_r @ ep[anchor]
    curve, rejected = [], []
    indices = np.flatnonzero((et >= start) & (et <= end))
    if len(indices) < 3:
        raise ValueError('Insufficient raw VINS samples during flight')
    for i in indices:
        stamp = int(et[i])
        try:
            actual, actual_r = reference(stamp)
        except ValueError as exc:
            rejected.append({'source_ns': stamp, 'reason': str(exc)})
            continue
        estimate = align_r @ ep[i] + align_t
        residual = estimate - actual
        estimate_r = align_r @ rotation(eq[i])
        yaw_delta = (np.arctan2(estimate_r[1, 0], estimate_r[0, 0])
                     - np.arctan2(actual_r[1, 0], actual_r[0, 0]))
        yaw_error = float(np.degrees(np.arctan2(np.sin(yaw_delta), np.cos(yaw_delta))))
        curve.append({'source_ns': stamp, 'elapsed_sim_s': (stamp-start)/1e9,
                      'position_error_m': float(np.linalg.norm(residual)),
                      'yaw_error_deg': yaw_error,
                      **dict(zip(('dx_m', 'dy_m', 'dz_m'), map(float, residual))),
                      **dict(zip(('truth_x_m', 'truth_y_m', 'truth_z_m'), map(float, actual))),
                      **dict(zip(('estimate_x_m', 'estimate_y_m', 'estimate_z_m'), map(float, estimate)))})
    if len(curve) < 3:
        raise ValueError('Insufficient truth-paired raw VINS samples')
    times = np.asarray([p['source_ns'] for p in curve], dtype=np.int64)
    grid = tt[(tt >= start) & (tt <= end)]
    if not len(grid):
        raise ValueError('No truth samples during flight')
    # Coverage reports bounded temporal support, not a health or accuracy pass.
    supported = 0
    for stamp in grid:
        j = int(np.searchsorted(times, stamp))
        if j < len(times) and times[j] == stamp:
            supported += 1
        elif 0 < j < len(times) and times[j]-times[j-1] <= support_gap_s*1e9:
            supported += 1
    gaps = np.diff(times) / 1e9
    duration = (end-start)/1e9
    truth_intervals_valid = np.diff(tt) <= truth_gap_s*1e9
    supported_ns = 0
    for left, right in zip(times[:-1], times[1:]):
        if right-left <= support_gap_s*1e9:
            overlaps = np.maximum(0, np.minimum(tt[1:], right)-np.maximum(tt[:-1], left))
            supported_ns += int(np.sum(overlaps[truth_intervals_valid]))
    by_stamp = {p['source_ns']: p for p in raw}
    shared = [p for p in adapted if start <= p['source_ns'] <= end and p['source_ns'] in by_stamp]
    mismatch = sum(p['xyz'] != by_stamp[p['source_ns']]['xyz']
                   or p['q_xyzw'] != by_stamp[p['source_ns']]['q_xyzw'] for p in shared)
    position = _stats([p['position_error_m'] for p in curve])
    yaw = _stats(np.abs([p['yaw_error_deg'] for p in curve]))
    last = curve[-1]
    residuals = np.asarray([[p[k] for k in ('dx_m', 'dy_m', 'dz_m')] for p in curve])
    steps = np.linalg.norm(np.diff(residuals, axis=0), axis=1)
    jump = int(np.argmax(steps))
    segment = np.asarray([[p[k] for k in ('truth_x_m', 'truth_y_m', 'truth_z_m')] for p in curve])
    invalid = [p for p in flight['localization_quality_history']
               if start <= p['stamp_ns'] <= end and not p['valid']]
    report = {
        'scope': __doc__, 'epoch': epoch, 'raw_topic': observation['raw_topic'],
        'alignment': {'method': 'one pre-enable pose pair; never fitted to the flight path',
                      'scale': 1, 'target_source_ns': target,
                      'reference_source_ns': int(et[anchor]),
                      'rotation': align_r.tolist(), 'translation_m': align_t.tolist()},
        'interval': {'start_phase': 'PRESTREAM', 'end_phase': 'LANDED',
                     'start_source_ns': start, 'end_source_ns': end,
                     'duration_sim_s': duration,
                     'paired_truth_path_length_m': float(np.linalg.norm(np.diff(segment, axis=0), axis=1).sum())},
        'position_error_m': position, 'absolute_yaw_error_deg': yaw,
        'endpoint': {'source_ns': last['source_ns'], 'age_before_landed_sim_s': (end-last['source_ns'])/1e9,
                     'position_error_m': last['position_error_m'], 'yaw_error_deg': last['yaw_error_deg']},
        'coverage': {'raw_samples_in_interval': len(indices), 'paired_samples': len(curve),
                     'paired_raw_fraction': len(curve)/len(indices),
                     'truth_grid_samples': len(grid), 'supported_truth_grid_samples': supported,
                     'truth_grid_support_fraction': supported/len(grid),
                     'bounded_time_support_fraction': supported_ns/(end-start),
                     'truth_max_gap_sim_s': float(np.diff(tt).max()/1e9),
                     'raw_max_gap_sim_s': float(np.diff(et[indices]).max()/1e9),
                     'paired_max_gap_sim_s': float(gaps.max()),
                     'start_uncovered_sim_s': (times[0]-start)/1e9,
                     'end_uncovered_sim_s': (end-times[-1])/1e9,
                     'truth_interpolation_limit_sim_s': truth_gap_s,
                     'odometry_support_limit_sim_s': support_gap_s,
                     'note': 'Reporting limits only; no extrapolation, timestamp repair or health gate changes.',
                     'rejected_samples': rejected},
        'raw_adapter_pose_check': {'same_stamp_pairs': len(shared), 'mismatched_pose_pairs': mismatch,
                                   'adapted_samples_in_interval': sum(start <= p['source_ns'] <= end for p in adapted)},
        'largest_residual_step': {'source_ns': curve[jump+1]['source_ns'],
                                  'delta_m': float(steps[jump]), 'interval_sim_s': float(gaps[jump]),
                                  'note': 'Descriptive residual change, not a classified tracking failure.'},
        'invalid_localization_status_samples': len(invalid),
        'landed_and_disarmed': flight['landed_and_disarmed'],
        'limitations': ['One simulation route; no loop closure, map reuse or real-device validation.',
                        'Reference pose uncertainty affects all subsequent errors; scale is never fitted.',
                        'RMSE is sample weighted; coverage is reported separately, gaps are not hidden.',
                        'Endpoint is the last paired source sample, with its age explicitly reported.',
                        'No accuracy acceptance threshold is declared by this diagnostic.']}
    return report, curve


def plot(curve, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 1, figsize=(10, 10))
    axes[0].plot([p['truth_x_m'] for p in curve], [p['truth_y_m'] for p in curve], label='Gazebo IMU truth')
    axes[0].plot([p['estimate_x_m'] for p in curve], [p['estimate_y_m'] for p in curve], label='Raw VINS (fixed initial alignment)')
    axes[0].set(xlabel='World X (m)', ylabel='World Y (m)')
    axes[0].set_aspect('equal', adjustable='datalim')
    times = [p['elapsed_sim_s'] for p in curve]
    axes[1].plot(times, [p['position_error_m'] for p in curve], label='3D position error')
    axes[1].set(ylabel='Position error (m)')
    axes[2].plot(times, [p['yaw_error_deg'] for p in curve], label='Signed yaw error')
    axes[2].set(xlabel='Simulation seconds since PRESTREAM', ylabel='Yaw error (deg)')
    for ax in axes:
        ax.grid(alpha=0.25)
        ax.legend()
    fig.suptitle('Raw VINS baseline — one initialization alignment, scale = 1')
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--plot', action='store_true')
    args = parser.parse_args()
    run = args.run.resolve()
    load = lambda name: json.loads((run / name).read_text())
    mount = px4_sensor_mount(ROOT/'simulation/models/x500_d435i/model.sdf')
    lever = np.zeros(3, dtype=float)
    phases = [json.loads(line) for line in (run/'bridge-alignment-timeline.jsonl').read_text().splitlines()]
    report, curve = evaluate(load('alignment-observation.json'), load('debug-truth-evaluation.json')['samples'],
                             phases, load('preflight.json'), load('flight.json'), lever)
    report['run_id'] = run.name
    report['runtime_contract_sha256'] = load('runtime-contract.json')['sha256']
    report['sensor_mount'] = mount
    report['coordinate_contract'] = {
        'truth_point': 'd435i_link', 'raw_vins_point': f"vins_{report['epoch']}_imu",
        'imu_sensor_pose_in_d435i_link_m': [0.0, 0.0, 0.0],
        'truth_to_raw_point_translation_m': [0.0, 0.0, 0.0],
        'base_link_mount_translation_not_applied_to_truth': True}
    inputs = ['alignment-observation.json', 'debug-truth-evaluation.json',
              'bridge-alignment-timeline.jsonl', 'preflight.json', 'flight.json', 'runtime-contract.json']
    report['input_sha256'] = {name: hashlib.sha256((run/name).read_bytes()).hexdigest() for name in inputs}
    report['evaluator_sha256'] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in [Path(__file__), ROOT/'tools/evaluate_vins_motion.py',
                                          ROOT/'tools/evaluate_vio_quality_alignment.py',
                                          ROOT/'src/own/uav_sim/uav_sim/geometry.py']}
    with (run/'odometry-errors.csv').open('w') as out:
        writer = csv.DictWriter(out, fieldnames=list(curve[0]))
        writer.writeheader()
        writer.writerows(curve)
    if args.plot:
        plot(curve, run/'odometry-errors.png')
    (run/'odometry-evaluation.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
