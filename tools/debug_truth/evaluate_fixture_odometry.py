#!/usr/bin/env python3
"""Offline unarmed-fixture pose errors; one stationary alignment, scale one.

In the current D435i simulation, Gazebo publishes world -> d435i_link truth and
the IMU is mounted at that link origin. The runtime entry point therefore uses
zero truth-to-IMU translation; the SDF base_link mount offset must not be added
to d435i_link truth a second time.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

from evaluate_odometry import pose_arrays, rotation, _interpolate_position, _interpolate_quaternion

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src/own/uav_sim'))
from uav_sim.geometry import px4_sensor_mount


def compare(raw, truth, anchor_ns, lever):
    lever = np.asarray(lever, dtype=float)
    if lever.shape != (3,) or not np.isfinite(lever).all():
        raise ValueError('invalid model-to-IMU lever arm')
    et, ep, eq = pose_arrays(raw, 'source_ns')
    tt, tp, tq = pose_arrays(truth, 'stamp_ns')
    anchor = np.flatnonzero(et <= anchor_ns)
    if not len(anchor) or anchor_ns - et[anchor[-1]] > 150_000_000:
        raise ValueError('no fresh stationary alignment sample')
    anchor = int(anchor[-1])

    def reference(stamp):
        p, gap = _interpolate_position(tt, tp, stamp)
        if gap > 40_000_000:
            raise ValueError('truth gap exceeds 40ms')
        r = rotation(_interpolate_quaternion(tt, tq, stamp))
        return p + r @ lever, r

    p0, r0 = reference(int(et[anchor]))
    alignment_r = r0 @ rotation(eq[anchor]).T
    alignment_t = p0 - alignment_r @ ep[anchor]
    rows, rejected = [], []
    for i in range(anchor, len(et)):
        stamp = int(et[i])
        try:
            actual, actual_r = reference(stamp)
        except ValueError as exc:
            rejected.append({'source_ns': stamp, 'reason': str(exc)})
            continue
        estimate = alignment_r @ ep[i] + alignment_t
        estimate_r = alignment_r @ rotation(eq[i])
        yaw = np.arctan2(estimate_r[1, 0], estimate_r[0, 0]) - np.arctan2(actual_r[1, 0], actual_r[0, 0])
        rows.append({'source_ns': stamp, 'position_error_m': float(np.linalg.norm(estimate - actual)),
                     'yaw_error_deg': float(np.degrees(np.arctan2(np.sin(yaw), np.cos(yaw)))),
                     'truth_yaw_deg': float(np.degrees(np.arctan2(actual_r[1,0],actual_r[0,0]))),
                     **dict(zip(('dx_m','dy_m','dz_m'), map(float, estimate-actual))),
                     **dict(zip(('truth_x_m','truth_y_m','truth_z_m'), map(float, actual))),
                     **dict(zip(('estimate_x_m','estimate_y_m','estimate_z_m'), map(float, estimate)))})
    if len(rows) < 3:
        raise ValueError('insufficient source-time paired poses')
    errors = np.array([p['position_error_m'] for p in rows])
    return {'scope': __doc__, 'anchor_ns': int(et[anchor]), 'alignment_rotation': alignment_r.tolist(),
            'alignment_translation': alignment_t.tolist(), 'pairs': len(rows), 'rejected': rejected,
            'duration_sim_s': (rows[-1]['source_ns'] - rows[0]['source_ns']) / 1e9,
            'raw_gap_max_s': float(np.max(np.diff(et)) / 1e9),
            'raw_intervals_over_0_2_s': int(np.sum(np.diff(et) > 200_000_002)),
            'timestamp_comparison_tolerance_ns': 2,
            'position_rmse_m': float(np.sqrt(np.mean(errors**2))), 'position_max_m': float(errors.max()),
            'position_last_m': float(errors[-1]),
            'yaw_rmse_deg': float(np.sqrt(np.mean([p['yaw_error_deg']**2 for p in rows]))),
            'yaw_max_abs_deg': float(max(abs(p['yaw_error_deg']) for p in rows)),
            'limitations': ['Alignment fixes one initial pose; no trajectory/time/scale fitting.',
                            'Unarmed physical support is not a flight qualification.']}, rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--idle', action='store_true', help='evaluate the read-only stationary control')
    args = parser.parse_args()
    load = lambda name: [json.loads(line) for line in (args.run / name).open()]
    prefix = 'idle' if args.idle else 'fixture'
    raw = load(prefix + '-odometry.jsonl')
    if not args.idle:
        raw = [p for p in raw if p['kind'] == 'raw']
    fixture = json.loads((args.run / (prefix + '-result.json')).read_text())
    if any(p['frame'] != 'vins_' + fixture['epoch'] + '_world' for p in raw):
        raise ValueError('raw frame/epoch changed')
    if args.idle:
        anchor_ns = fixture['start_ns'] + 1_000_000_000
    else:
        trace = load('fixture-trace.jsonl')
        if trace[0]['target'] != [0, 0, 0, 0]:
            raise ValueError('stationary fixture start required')
        anchor_ns = int((trace[0]['sim_s'] + 1) * 1e9)
        stationary = [p for p in trace if p['sim_s'] <= anchor_ns / 1e9]
        if any(p['target'] != [0, 0, 0, 0] for p in stationary):
            raise ValueError('alignment interval is not stationary')
    mount = px4_sensor_mount(ROOT / 'simulation/models/x500_d435i/model.sdf')
    lever = np.zeros(3, dtype=float)
    truth = load(prefix + '-truth.jsonl')
    if any(p.get('frame_id', 'world') != 'world'
           or p.get('child_frame_id', 'd435i_link') != 'd435i_link' for p in truth):
        raise ValueError('Gazebo truth is not world -> d435i_link')
    if any(p.get('child_frame', f"vins_{fixture['epoch']}_imu") != f"vins_{fixture['epoch']}_imu"
           for p in raw):
        raise ValueError('raw VINS child frame is not the epoch IMU frame')
    report, rows = compare(raw, truth, anchor_ns, lever)
    report['epoch'] = fixture['epoch']
    report['sensor_mount'] = mount
    report['coordinate_contract'] = {
        'truth_point': 'd435i_link', 'raw_vins_point': f"vins_{fixture['epoch']}_imu",
        'imu_sensor_pose_in_d435i_link_m': [0.0, 0.0, 0.0],
        'truth_to_raw_point_translation_m': [0.0, 0.0, 0.0],
        'base_link_mount_translation_not_applied_to_truth': True}
    names = [prefix + suffix for suffix in ['-odometry.jsonl', '-truth.jsonl', '-result.json']]
    if args.idle:
        positions = np.array([p['xyz'] for p in truth if p['stamp_ns'] >= fixture['start_ns']])
        report['truth_max_translation_from_first_m'] = float(np.max(np.linalg.norm(positions-positions[0], axis=1)))
        report['limitations'].append('Ideal stationary simulation is not a real sensor precision measurement.')
    else:
        names.append('fixture-trace.jsonl')
    report['input_sha256'] = {name: hashlib.sha256((args.run / name).read_bytes()).hexdigest() for name in names}
    (args.run / (prefix + '-odometry-errors.json')).write_text(json.dumps(report, indent=2) + '\n')
    with (args.run / (prefix + '-odometry-errors.csv')).open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
