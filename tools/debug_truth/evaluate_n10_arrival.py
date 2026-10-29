#!/usr/bin/env python3
"""Measure N10 position and yaw together over the active task and hold."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'src/own/uav_sim'))
from evaluate_vins_motion import rotation
from n10_arrival_metrics import longest_contiguous_window, wrapped_angle_error_rad
from uav_sim.geometry import px4_sensor_mount


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def evaluate(run, position_tolerance_m=0.30, yaw_tolerance_deg=15.0,
             dwell_s=3.0, max_truth_gap_s=0.04, max_wall_gap_s=0.12):
    run = Path(run).resolve()
    required = ['flight.json', 'arrival-evaluation.json',
                'debug-truth-evaluation.json', 'bridge-alignment-timeline.jsonl']
    for name in required:
        if not (run / name).is_file():
            raise ValueError(f'missing required input: {name}')
    flight = json.loads((run / 'flight.json').read_text())
    alignment = json.loads((run / 'arrival-evaluation.json').read_text())
    truth = json.loads((run / 'debug-truth-evaluation.json').read_text())['samples']
    phases = [json.loads(line) for line in
              (run / 'bridge-alignment-timeline.jsonl').read_text().splitlines()
              if line.strip()]
    goal = flight.get('goal')
    if not isinstance(goal, dict) or type(goal.get('source_ns')) is not int:
        raise ValueError('flight has no source-clocked goal')
    if not truth:
        raise ValueError('truth sample set is empty')
    if not flight.get('landed_and_disarmed'):
        raise ValueError('flight does not record landed/disarmed terminal state')

    goal_stamp = int(goal['source_ns'])
    landed_stamps = [int(row['stamp_ns']) for row in phases
                     if row.get('phase') == 'LANDED'
                     and int(row.get('stamp_ns', -1)) >= goal_stamp]
    if not landed_stamps:
        raise ValueError('bridge timeline has no post-goal LANDED sample')
    landed_stamp = landed_stamps[0]

    target_position = np.asarray(alignment['world_imu_goal_xyz'], dtype=float)
    alignment_rotation = np.asarray(alignment['ground_rotation'], dtype=float)
    yaw_offset = math.atan2(float(alignment_rotation[1, 0]),
                            float(alignment_rotation[0, 0]))
    target_yaw = float(goal['yaw_enu']) + yaw_offset
    mount = px4_sensor_mount(ROOT / 'simulation/models/x500_d435i/model.sdf')
    lever = np.asarray(mount['translation_frd_m'], dtype=float) * np.array([1, -1, -1])

    samples = []
    prior_stamp = None
    prior_relevant_stamp = None
    max_gap = 0.0
    for item in truth:
        stamp = int(item['stamp_ns'])
        if prior_stamp is not None:
            gap = (stamp - prior_stamp) / 1e9
            if gap <= 0.0:
                raise ValueError('truth stamps regressed or repeated; no timestamp repair allowed')
        prior_stamp = stamp
        if not goal_stamp <= stamp <= landed_stamp:
            continue
        if prior_relevant_stamp is not None:
            max_gap = max(max_gap, (stamp - prior_relevant_stamp) / 1e9)
        prior_relevant_stamp = stamp
        q = item['q_xyzw']
        actual_imu = np.asarray(item['xyz'], dtype=float) + rotation(q) @ lever
        position_error = float(np.linalg.norm(actual_imu - target_position))
        body_rotation = rotation(q)
        actual_yaw = math.atan2(float(body_rotation[1, 0]),
                                float(body_rotation[0, 0]))
        yaw_error_deg = math.degrees(wrapped_angle_error_rad(actual_yaw, target_yaw))
        samples.append({
            'sim_s': stamp / 1e9,
            'wall_s': float(item['wall_s']),
            'position_error_m': position_error,
            'yaw_error_deg': yaw_error_deg,
            'within_tolerance': (position_error <= position_tolerance_m
                                 and yaw_error_deg <= yaw_tolerance_deg),
        })
    if not samples:
        raise ValueError('no truth samples cover goal dispatch through landing')

    dwell = longest_contiguous_window(samples, max_truth_gap_s, max_wall_gap_s)
    checks = {
        'position_and_yaw_met_simultaneously': dwell['sample_count'] > 0,
        'simultaneous_sim_dwell_met': dwell['sim_duration_s'] >= dwell_s,
        'simultaneous_wall_dwell_met': dwell['wall_duration_s'] >= dwell_s,
        'truth_sample_gaps_bounded': max_gap <= max_truth_gap_s,
        'native_and_independent_terminal_state_present': bool(flight.get('landed_and_disarmed')),
    }
    evaluator_path = Path(__file__).resolve()
    report = {
        'schema': 'n10-arrival-metrics/v1',
        'run_id': run.name,
        'classification': 'offline simulated truth measurement; not final N10 qualification',
        'formal_qualification': False,
        'measurement_interval': {
            'start_event': 'navigation goal source stamp',
            'start_sim_s': goal_stamp / 1e9,
            'end_event': 'first bridge LANDED sample after goal start',
            'end_sim_s': landed_stamp / 1e9,
            'truth_samples': len(samples),
            'max_truth_gap_sim_s': max_gap,
        },
        'limits_from_goal_f_default': {
            'position_error_max_m': position_tolerance_m,
            'yaw_error_max_deg': yaw_tolerance_deg,
            'simultaneous_dwell_min_s': dwell_s,
            'dwell_time_domains_reported': ['gazebo_sim_clock', 'host_wall_clock'],
            'qualification_time_domain': None,
            'note': 'GOAL F sets a 3 s dwell but does not select a clock domain; both are reported pending N10 freeze.',
        },
        'target': {
            'position_world_imu_m': target_position.tolist(),
            'yaw_world_rad': target_yaw,
            'yaw_world_deg': math.degrees(target_yaw),
        },
        'longest_joint_position_yaw_window': dwell,
        'checks': checks,
        'diagnostic_check_passed': all(checks.values()),
        'limitations': [
            'Uses Gazebo truth and model-derived IMU lever arm for offline evaluation only.',
            'One fixed ground SE(3) alignment; no scale fit, segment refit, timestamp repair, or truth feedback.',
            'Uses the provisional current vehicle model and one route/run.',
            'The health policy bypass was active; this result does not qualify localization health or the final N10 runtime.',
        ],
        'input_sha256': {name: sha256(run / name) for name in required},
        'evaluator_sha256': sha256(evaluator_path),
    }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = evaluate(args.run_directory)
    output = args.output or args.run_directory / 'n10-arrival-evaluation.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['diagnostic_check_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
