#!/usr/bin/env python3
"""Offline failed-flight prefix analysis; no terminal or acceptance inference."""
import argparse
import bisect
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/debug_truth')]
from evaluate_arrival import fixed_sensor_reference_alignment
from evaluate_n10_cross_run_calibration import _quat_slerp
from evaluate_n10_clearance import (parse_obstacles, vehicle_vertical_cylinder,
                                    distance_to_obstacle)
from evaluate_vins_motion import rotation


def sample_at(rows, stamps, stamp, field, max_gap_ns, quaternion=False):
    """Only interpolate inside measured support; exact endpoints are supported."""
    index = bisect.bisect_left(stamps, stamp)
    if index < len(stamps) and stamps[index] == stamp:
        value, gap = np.asarray(rows[index][field], dtype=float), 0
    else:
        if index == 0 or index == len(stamps):
            raise ValueError('query would extrapolate')
        gap = stamps[index] - stamps[index - 1]
        if gap <= 0 or gap > max_gap_ns:
            raise ValueError('query bracket exceeds declared maximum')
        weight = (stamp - stamps[index - 1]) / gap
        left, right = rows[index - 1][field], rows[index][field]
        value = (np.asarray(_quat_slerp(left, right, weight)) if quaternion else
                 (1.0 - weight) * np.asarray(left) + weight * np.asarray(right))
    if not np.isfinite(value).all():
        raise ValueError('nonfinite measured value')
    return value, gap


def decompose_positions(command_world, estimate_world, truth_world):
    vio = np.asarray(estimate_world) - truth_world
    follow = np.asarray(command_world) - estimate_world
    total = np.asarray(command_world) - truth_world
    return {'vio_error_vector_world_m': vio.tolist(),
            'command_minus_estimate_vector_world_m': follow.tolist(),
            'command_minus_truth_vector_world_m': total.tolist(),
            'vio_error_m': float(np.linalg.norm(vio)),
            'command_minus_estimate_m': float(np.linalg.norm(follow)),
            'command_minus_truth_m': float(np.linalg.norm(total)),
            'vector_sum_closure_error_m': float(np.linalg.norm(vio + follow - total))}


def stamps_for(rows, key):
    stamps = [int(row[key]) for row in rows]
    if len(stamps) < 2 or any(b <= a for a, b in zip(stamps, stamps[1:])):
        raise ValueError('source stamps must be sufficient and strictly increasing')
    return stamps


def canonical_commands(commands):
    """Collapse identical deliveries; retain conflicting stamps as unsupported."""
    if any(int(b['source_stamp_ns']) < int(a['source_stamp_ns'])
           for a, b in zip(commands, commands[1:])):
        raise ValueError('command source time regressed')
    groups = {}
    for row in commands:
        groups.setdefault(int(row['source_stamp_ns']), []).append(row)
    result, ambiguous, collapsed = [], [], 0
    for stamp, rows in groups.items():
        payloads = [{k: v for k, v in row.items() if k != 'wall_elapsed_s'} for row in rows]
        if any(payload != payloads[0] for payload in payloads[1:]):
            result.append({**rows[0], 'position_enu': [math.nan] * 3})
            ambiguous.append({'source_stamp_ns': stamp, 'delivery_count': len(rows),
                              'trajectory_ids': [row.get('trajectory_id') for row in rows]})
        else:
            result.append(rows[0])
            collapsed += len(rows) - 1
    return result, ambiguous, collapsed


def evaluate(run):
    run = Path(run).resolve()
    names = ['flight.json', 'debug-truth-evaluation.json', 'alignment-observation.json',
             'n09-contact-observation.json', 'bridge-alignment-timeline.jsonl',
             'runtime-contract.json', 'vio_initialization.sdf']
    load = lambda name: json.loads((run / name).read_text())
    flight, truth_report, alignment, contacts = map(load, names[:4])
    raw = [row for row in alignment['samples'] if row['kind'] == 'raw_odom']
    truth = truth_report['samples']
    epoch, goal_id = flight['localization_epoch'], flight['goal_id']
    if alignment.get('epoch') != epoch:
        raise ValueError('raw odometry epoch conflicts with flight')
    goal_start = int(flight['goal']['source_ns'])
    events = [dict(stamp_ns=int(event['stamp_ns']), pairs=[pair for pair in event['pairs']
              if 'ground_plane' not in pair['collision1']
              and 'ground_plane' not in pair['collision2']])
              for event in contacts['events'] if int(event['stamp_ns']) >= goal_start]
    events = [event for event in events if event['pairs']]
    if not events:
        raise ValueError('no measured obstacle contact to define a failure prefix')
    first = min(events, key=lambda row: row['stamp_ns'])
    end = first['stamp_ns']
    # Select the actual contacted static model, rather than an observer's ROI label.
    pair = first['pairs'][0]
    target_name = next(name.split('::')[0] for name in
                       [pair['collision1'], pair['collision2']]
                       if not name.startswith('x500_d435i_'))
    obstacles, _ = parse_obstacles(run / 'vio_initialization.sdf')
    target = next(row for row in obstacles if row['name'].startswith(target_name + '/'))
    if target['kind'] != 'vertical_cylinder':
        raise ValueError('this diagnostic currently requires a measured cylinder contact')
    phases = [json.loads(line) for line in (run / names[4]).read_text().splitlines() if line.strip()]
    prestream = min(int(row['stamp_ns']) for row in phases if row['phase'] == 'PRESTREAM')
    ref = max((row for row in raw if int(row['source_ns']) < prestream),
              key=lambda row: int(row['source_ns']))
    raw_stamps, truth_stamps = stamps_for(raw, 'source_ns'), stamps_for(truth, 'stamp_ns')
    ref_stamp = int(ref['source_ns'])
    ref_truth, ref_gap = sample_at(truth, truth_stamps, ref_stamp, 'xyz', 20_000_000)
    ref_q, _ = sample_at(truth, truth_stamps, ref_stamp, 'q_xyzw', 20_000_000, True)
    align, translation = fixed_sensor_reference_alignment(ref['xyz'], ref['q_xyzw'], ref_truth, ref_q)
    commands = [row for row in flight['position_command_history']
                if row.get('goal_id') == goal_id and row.get('epoch') == epoch
                and row.get('flag') == 1]
    commands, ambiguous_commands, identical_deliveries = canonical_commands(commands)
    command_stamps = stamps_for(commands, 'source_stamp_ns')
    env_path = ROOT / 'config/components/navigation/vehicle_envelope.json'
    env = json.loads(env_path.read_text())['geometry']
    bounds = env['collision_bounds_xyz_m'][2]
    radius = env['orientation_invariant_rotor_sweep_radius_m']

    def at(stamp):
        c, cg = sample_at(commands, command_stamps, stamp, 'position_enu', 40_000_000)
        e, eg = sample_at(raw, raw_stamps, stamp, 'xyz', 150_000_000)
        eq, _ = sample_at(raw, raw_stamps, stamp, 'q_xyzw', 150_000_000, True)
        p, tg = sample_at(truth, truth_stamps, stamp, 'xyz', 40_000_000)
        q, _ = sample_at(truth, truth_stamps, stamp, 'q_xyzw', 40_000_000, True)
        cw, ew = align @ c + translation, align @ e + translation
        # Additional local counterfactual removes measured instantaneous SE(3)
        # pose discrepancy. Neither counterfactual predicts actual dynamics.
        corrected = p + rotation(q) @ rotation(eq).T @ (c - e)
        vr, zmin, zmax, tilt = vehicle_vertical_cylinder(p, q, radius, min(bounds), max(bounds))
        clearance = lambda point: distance_to_obstacle(
            point, vr, zmin + point[2] - p[2], zmax + point[2] - p[2], target)
        center = np.asarray(target['center_xyz_m'])
        signed_gap = lambda point: float(np.linalg.norm(point[:2] - center[:2]) - target['radius_m'])
        return {'source_stamp_ns': stamp, **decompose_positions(cw, ew, p),
                'command_world_m': cw.tolist(), 'estimate_world_m': ew.tolist(),
                'truth_world_m': p.tolist(), 'pose_corrected_command_world_m': corrected.tolist(),
                'fixed_aligned_command_point_radial_gap_m': signed_gap(cw),
                'pose_corrected_command_point_radial_gap_m': signed_gap(corrected),
                'command_point_within_obstacle_height': bool(target['z_min_m'] <= cw[2] <= target['z_max_m']),
                'command_envelope_clearance_m': clearance(cw),
                'pose_corrected_command_envelope_clearance_m': clearance(corrected),
                'actual_envelope_clearance_m': clearance(p), 'actual_tilt_sin': tilt,
                'support_gap_ns': {'command': cg, 'raw_odom': eg, 'truth': tg}}

    paired, rejected = [], []
    for stamp in command_stamps:
        if not goal_start <= stamp <= end:
            continue
        try:
            paired.append(at(stamp))
        except ValueError as exc:
            rejected.append({'source_stamp_ns': stamp, 'reason': str(exc)})
    diagnostic_times = [end - 2_000_000_000, end - 1_000_000_000, end]
    diagnostics = [at(stamp) for stamp in diagnostic_times]
    all_paths = [run / name for name in names] + [env_path]
    return {'schema': 'n10-precontact-diagnostic/v1', 'run_id': run.name,
            'classification': 'failed-flight prefix only; no acceptance or terminal credit',
            'runtime_sha256': load('runtime-contract.json')['sha256'],
            'epoch': epoch, 'goal_id': goal_id, 'goal_start_ns': goal_start,
            'first_contact': first, 'target_obstacle': target,
            'fixed_alignment': {'scale': 1, 'reference_source_ns': ref_stamp,
                                'prestream_ns': prestream, 'truth_reference_bracket_ns': ref_gap,
                                'rotation': align.tolist(), 'translation_m': translation.tolist()},
            'paired_count': len(paired), 'rejected': rejected,
            'ambiguous_command_stamps': ambiguous_commands,
            'identical_duplicate_deliveries_collapsed': identical_deliveries,
            'diagnostic_samples': diagnostics, 'per_sample': paired,
            'input_sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in all_paths},
            'limits': ['A measured first contact defines this prefix, not a synthesized successful endpoint.',
                       'All positions use the D435i IMU point; fixed SE(3) uses only a prestream reference.',
                       'Envelope overlap is conservative; the point radial gap is separate from body clearance.',
                       'Instantaneous-pose correction is a local counterfactual, not an alternative flight alignment.',
                       'Reference/true obstacle disagreement does not identify the contemporaneous occupancy map cause.',
                       'No runtime threshold, control action, or successful terminal state is inferred.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = args.output or args.run_dir / 'n10-precontact-diagnostic.json'
    result = evaluate(args.run_dir)
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'output': str(output), 'paired_count': result['paired_count'],
                      'rejected_count': len(result['rejected']),
                      'diagnostic_samples': result['diagnostic_samples']}, indent=2))


if __name__ == '__main__':
    main()
