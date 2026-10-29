#!/usr/bin/env python3
"""Compare raw VINS world-frame velocity with independently recorded SITL truth."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from truth_reference import imu_truth_samples, require_same_truth_reference

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/debug_truth'))
sys.path.insert(0, str(ROOT / 'src/own/uav_sim'))
from evaluate_vio_full_state import _stats, _truth_velocity
from uav_sim.geometry import px4_sensor_mount


def velocity_phase_windows(flight, goal_start_ns, goal_end_ns, landed_ns):
    """Separate the requested completed hold from landing; never infer a hold."""
    if not goal_start_ns <= goal_end_ns <= landed_ns:
        raise ValueError('flight phase timestamps are inconsistent')
    hold = flight.get('post_goal_hold') or {}
    duration = hold.get('requested_sim_s')
    if not hold.get('completed') or duration is None or float(duration) <= 0:
        return {'goal_motion_and_dwell': (goal_start_ns, goal_end_ns),
                'post_goal_active_hold': None, 'landing': None}
    hold_end_ns = goal_end_ns + int(round(float(duration) * 1e9))
    if hold_end_ns > landed_ns:
        raise ValueError('requested hold ends after recorded landing')
    return {'goal_motion_and_dwell': (goal_start_ns, goal_end_ns),
            'post_goal_active_hold': (goal_end_ns, hold_end_ns),
            'landing': (hold_end_ns, landed_ns)}


def evaluate(run, truth_gap_s=0.04, velocity_half_window_s=0.1):
    run = Path(run).resolve()
    load = lambda name: json.loads((run / name).read_text())
    observation = load('alignment-observation.json')
    truth_report = load('debug-truth-evaluation.json')
    odometry = load('odometry-evaluation.json')
    flight = load('flight.json')
    phases = [json.loads(line) for line in (run / 'bridge-alignment-timeline.jsonl').read_text().splitlines()
              if line.strip()]

    epoch = odometry.get('epoch')
    if (not epoch or observation.get('epoch') != epoch
            or observation.get('raw_topic') != f'/vins_raw/s_{epoch}/odometry'):
        raise ValueError('raw observation, odometry evaluation, and VINS epoch disagree')
    expected_world = f'vins_{epoch}_world'
    expected_body = f'vins_{epoch}_imu'
    start_ns = int(odometry['interval']['start_source_ns'])
    end_ns = int(odometry['interval']['end_source_ns'])
    rows = [row for row in observation.get('samples', [])
            if row.get('kind') == 'raw_odom'
            and start_ns <= int(row.get('source_ns', -1)) <= end_ns]
    if len(rows) < 3:
        raise ValueError('fewer than three raw VINS velocity samples')
    for row in rows:
        if row.get('frame_id') != expected_world or row.get('child_frame_id') != expected_body:
            raise ValueError('raw VINS frame/epoch changed; sessions cannot be stitched')
        velocity = row.get('linear_velocity_world_m_s')
        if not isinstance(velocity, list) or len(velocity) != 3 or not np.isfinite(velocity).all():
            raise ValueError('raw VINS world-frame velocity is missing or non-finite')
    raw_t = np.asarray([int(row['source_ns']) for row in rows], dtype=np.int64)
    if np.any(np.diff(raw_t) <= 0):
        raise ValueError('raw source stamps must increase strictly; no sorting or repair')

    truth, truth_contract = imu_truth_samples(run, truth_report)
    require_same_truth_reference(odometry, truth_contract)
    truth_t = np.asarray([int(row['stamp_ns']) for row in truth], dtype=np.int64)
    truth_p = np.asarray([row['xyz'] for row in truth], dtype=float)
    truth_q = np.asarray([row['q_xyzw'] for row in truth], dtype=float)
    if (len(truth_t) < 3 or np.any(np.diff(truth_t) <= 0)
            or not np.isfinite(truth_p).all() or not np.isfinite(truth_q).all()):
        raise ValueError('truth samples are incomplete, non-finite, or non-monotonic')

    alignment = odometry.get('alignment', {})
    if alignment.get('scale') != 1:
        raise ValueError('velocity comparison requires the fixed-scale-one pose alignment')
    align_r = np.asarray(alignment.get('rotation'), dtype=float)
    if align_r.shape != (3, 3) or not np.isfinite(align_r).all():
        raise ValueError('odometry evaluation has no valid fixed rotation alignment')

    mount = px4_sensor_mount(ROOT / 'simulation/models/x500_d435i/model.sdf')
    base_to_imu_flu = np.asarray(mount['translation_frd_m'], dtype=float) * [1, -1, -1]
    half_window_ns = int(round(velocity_half_window_s * 1e9))
    truth_gap_ns = int(round(truth_gap_s * 1e9))
    samples = []
    rejected = []
    for row, stamp in zip(rows, raw_t):
        try:
            motion = _truth_velocity(truth_t, truth_p, truth_q, int(stamp),
                                     half_window_ns, truth_gap_ns, base_to_imu_flu)
        except ValueError as exc:
            rejected.append({'source_ns': int(stamp), 'reason': str(exc)})
            continue
        estimate = align_r @ np.asarray(row['linear_velocity_world_m_s'], dtype=float)
        reference = motion['velocity_imu']
        error = estimate - reference
        samples.append({
            'source_ns': int(stamp),
            'elapsed_from_prestream_sim_s': (int(stamp) - int(odometry['interval']['start_source_ns'])) / 1e9,
            'vins_velocity_world_m_s': estimate.tolist(),
            'truth_velocity_imu_world_m_s': reference.tolist(),
            'velocity_error_world_m_s': error.tolist(),
            'velocity_error_norm_m_s': float(np.linalg.norm(error)),
            'truth_speed_imu_m_s': float(np.linalg.norm(reference)),
            'lever_velocity_reconstruction_error_m_s': float(np.linalg.norm(motion['lever_reconstruction_error']))
        })
    if len(samples) < 3:
        raise ValueError('fewer than three raw VINS velocity samples have supported truth')

    goal_start_ns = int(flight.get('goal', {}).get('source_ns', flight.get('goal_start_sim_ns', 0)))
    legs = flight.get('legs', [])
    goal_end_ns = next((int(leg['goal_completed_source_ns']) for leg in legs
                        if leg.get('goal_id') == flight.get('goal_id')
                        and leg.get('goal_completed_source_ns') is not None), None)
    landed_rows = [row for row in phases if row.get('phase') == 'LANDED']
    landed_ns = int(landed_rows[-1]['stamp_ns']) if landed_rows else int(odometry['interval']['end_source_ns'])

    def summarize(name, start_ns, end_ns):
        selected = [sample for sample in samples
                    if start_ns <= sample['source_ns'] <= end_ns]
        if len(selected) < 3:
            return {'sample_count': len(selected), 'supported': False}
        errors = np.asarray([sample['velocity_error_world_m_s'] for sample in selected], dtype=float)
        norms = np.linalg.norm(errors, axis=1)
        return {
            'sample_count': len(selected), 'supported': True,
            'start_source_ns': start_ns, 'end_source_ns': end_ns,
            'duration_sim_s': (end_ns - start_ns) / 1e9,
            'velocity_error_norm_m_s': _stats(norms.tolist()),
            'velocity_error_components_m_s': {axis: _stats(errors[:, index].tolist())
                                              for index, axis in enumerate('xyz')},
            'truth_speed_imu_m_s': _stats([sample['truth_speed_imu_m_s'] for sample in selected]),
            'maximum_lever_reconstruction_error_m_s': max(
                sample['lever_velocity_reconstruction_error_m_s'] for sample in selected),
        }

    if goal_end_ns is None:
        raise ValueError('flight record has no goal completion source stamp')
    if not start_ns <= goal_start_ns <= goal_end_ns <= landed_ns <= end_ns:
        raise ValueError('flight phase timestamps are inconsistent')

    windows = velocity_phase_windows(flight, goal_start_ns, goal_end_ns, landed_ns)
    input_names = ['alignment-observation.json', 'debug-truth-evaluation.json',
                   'odometry-evaluation.json', 'flight.json', 'bridge-alignment-timeline.jsonl']
    input_sha256 = {name: hashlib.sha256((run / name).read_bytes()).hexdigest() for name in input_names}
    evaluator_path = Path(__file__).resolve()
    evaluator_rel = evaluator_path.relative_to(ROOT).as_posix()
    input_sha256[evaluator_rel] = hashlib.sha256(evaluator_path.read_bytes()).hexdigest()
    source_file = ROOT / 'src/vendor/vins_fusion/vins/src/utility/visualization.cpp'
    input_sha256[source_file.relative_to(ROOT).as_posix()] = hashlib.sha256(source_file.read_bytes()).hexdigest()
    report = {
        'schema': 'n10-raw-vins-velocity-diagnostic/v2',
        'truth_reference_contract': truth_contract,
        'run_id': run.name,
        'classification': 'offline diagnostic; no acceptance threshold is declared',
        'runtime_contract_sha256': odometry.get('runtime_contract_sha256'),
        'epoch': epoch,
        'raw_velocity_source': {
            'topic': observation.get('raw_topic'),
            'field': 'nav_msgs/Odometry.twist.twist.linear',
            'frame': 'header.frame_id / VINS WORLD_FRAME_ID',
            'source_semantics': 'The locked VINS visualization publisher copies estimator.Vs into twist.linear; estimator.Vs is expressed in WORLD_FRAME_ID. The recorder does not rotate or otherwise alter these values.',
            'vendor_source': source_file.relative_to(ROOT).as_posix(),
        },
        'truth_velocity_method': {
            'reference_point': 'D435i IMU, converted from raw model-origin truth by the common reader',
            'method': 'Centered finite difference of truth IMU positions over a symmetric 0.2 simulated-second window; lever-arm reconstruction is separately audited.',
            'half_window_sim_s': velocity_half_window_s,
            'truth_pose_interpolation_max_bracket_gap_sim_s': truth_gap_s,
            'no_extrapolation_or_timestamp_repair': True,
            'raw_to_truth_alignment': 'Use the one prestream rigid rotation from odometry-evaluation.json; scale remains 1; no per-segment/path fit.',
        },
        'interval': {'start_source_ns': start_ns, 'end_source_ns': end_ns,
                     'duration_sim_s': (end_ns - start_ns) / 1e9,
                     'supported_velocity_samples': len(samples), 'rejected_velocity_samples': len(rejected)},
        **{name: (summarize(name, *bounds) if bounds is not None else
                  {'supported': False, 'reason': 'completed requested hold boundary missing'})
           for name, bounds in windows.items()},
        'hold_boundary_basis': 'goal completion plus recorded completed requested duration; exact hold loop entry/exit not persisted',
        'full_prestream_to_landed': summarize('full_prestream_to_landed', start_ns, landed_ns),
        'coverage': {
            'raw_velocity_samples': len(rows), 'truth_supported_pairs': len(samples),
            'truth_pair_fraction': len(samples) / len(rows),
            'truth_max_gap_sim_s': float(np.diff(truth_t).max() / 1e9),
            'raw_velocity_max_gap_sim_s': float(np.diff(raw_t).max() / 1e9),
            'truth_interpolation_limit_sim_s': truth_gap_s,
            'velocity_window_total_sim_s': 2 * velocity_half_window_s,
            'rejected_samples': rejected,
        },
        'no_acceptance_threshold_declared': True,
        'input_sha256': input_sha256,
    }
    return report, samples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    report, _ = evaluate(args.run)
    out = args.run / 'n10-vins-velocity-evaluation.json'
    out.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
