#!/usr/bin/env python3
"""Read-only independent goal/dwell check using one fixed ground SE(3).

Dwell is evaluated on Gazebo simulation source time. Wall duration is reported
only as a separate diagnostic and cannot satisfy the simulated-time contract.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from truth_reference import imu_truth_samples, require_same_truth_reference, fixed_prestream_alignment

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from evaluate_vins_motion import rotation
from flight_profile import attempts

MAX_TRUTH_SAMPLE_GAP_SIM_S = 0.04


def wrap_abs_angle(a, b):
    return abs(math.atan2(math.sin(a - b), math.cos(a - b)))


def fixed_sensor_reference_alignment(odom_position, odom_quaternion,
                                    truth_sensor_position, truth_sensor_quaternion):
    """Map the VINS D435i-IMU point into the coincident Gazebo IMU point."""
    align = rotation(truth_sensor_quaternion) @ rotation(odom_quaternion).T
    translation = np.asarray(truth_sensor_position, dtype=float) - align @ np.asarray(
        odom_position, dtype=float)
    return align, translation


def longest_joint_window(rows, max_gap_sim_s=MAX_TRUTH_SAMPLE_GAP_SIM_S):
    """Return the longest simultaneously in-tolerance contiguous truth window.

    Rows are mappings with sim_s, wall_s, position_error_m,
    yaw_error_rad and inside. A nonmonotonic source time or a sample gap over
    max_gap_sim_s breaks continuity. No timestamp interpolation/extrapolation
    is done for dwell credit.
    """
    best = None
    start = None
    previous = None
    points = []

    def consider():
        nonlocal best
        if len(points) < 2:
            return
        candidate = {
            'start_sim_s': points[0]['sim_s'],
            'end_sim_s': points[-1]['sim_s'],
            'duration_sim_s': points[-1]['sim_s'] - points[0]['sim_s'],
            'start_wall_s': points[0]['wall_s'],
            'end_wall_s': points[-1]['wall_s'],
            'duration_wall_s': points[-1]['wall_s'] - points[0]['wall_s'],
            'sample_count': len(points),
            'max_position_error_m': max(p['position_error_m'] for p in points),
            'max_yaw_error_rad': max(p['yaw_error_rad'] for p in points),
        }
        if best is None or candidate['duration_sim_s'] > best['duration_sim_s']:
            best = candidate

    for row in rows:
        sim_s = float(row['sim_s'])
        if previous is not None:
            gap = sim_s - float(previous['sim_s'])
            if gap <= 0.0 or gap - max_gap_sim_s > 1e-9:
                consider()
                points = []
        if not row['inside']:
            consider()
            points = []
        else:
            points.append(row)
        previous = row
    consider()
    return best


def load_arrival_contract(acceptance_path, goal_config):
    acceptance_path = Path(acceptance_path).resolve()
    acceptance = json.loads(acceptance_path.read_text())
    thresholds = (acceptance.get('metrics', {})
                  .get('arrival_position_yaw_dwell', {}).get('thresholds', {}))
    contract = {
        'position_tolerance_m': float(thresholds.get(
            'position_error_max_m', goal_config.get('verification_position_tolerance_m',
                                                     goal_config['position_tolerance_m']))),
        'yaw_tolerance_rad': math.radians(float(thresholds.get(
            'absolute_yaw_error_max_deg', math.degrees(float(goal_config['yaw_tolerance_rad']))))),
        'required_dwell_sim_s': float(thresholds.get(
            'continuous_dwell_min_sim_s', goal_config.get(
                'verification_dwell_sim_s', goal_config['dwell_s']))),
        'maximum_truth_gap_sim_s': float(thresholds.get(
            'maximum_truth_source_gap_sim_s', MAX_TRUTH_SAMPLE_GAP_SIM_S)),
    }
    if not all(math.isfinite(value) and value > 0.0 for value in contract.values()):
        raise ValueError('acceptance arrival thresholds must be finite and positive')
    return {
        **contract,
        'path': acceptance_path,
        'sha256': hashlib.sha256(acceptance_path.read_bytes()).hexdigest(),
    }


def _load_run(run):
    def load(name):
        return json.loads((run / name).read_text())
    flight = load('flight.json')
    truth, _ = imu_truth_samples(run, load('debug-truth-evaluation.json'))
    odom = [x for x in load('alignment-observation.json')['samples']
            if x['kind'] == 'odom']
    preflight = load('preflight.json')
    planner = load('planner-observation.json')
    timeline = [json.loads(s) for s in
                (run / 'bridge-alignment-timeline.jsonl').read_text().splitlines()]
    return flight, truth, odom, preflight, planner, timeline


def evaluate_run(run, output_name='arrival-evaluation.json', acceptance_config_path=None):
    run = Path(run)
    flight, truth, odom, preflight, planner, phases = _load_run(run)
    if not flight.get('goal'):
        raise ValueError('No navigation goal was dispatched')
    if not truth or not odom:
        raise ValueError('Truth and raw odometry samples are required')

    goal_cfg_name = flight.get('goal_config',
                               'config/components/navigation/room_crossing_goal.json')
    cfg = json.loads((ROOT / goal_cfg_name).read_text())
    acceptance_path = (Path(acceptance_config_path).resolve() if acceptance_config_path
                       else ROOT / 'config/acceptance.json')
    contract = load_arrival_contract(acceptance_path, cfg)
    pos_tol = contract['position_tolerance_m']
    yaw_tol = contract['yaw_tolerance_rad']
    required = contract['required_dwell_sim_s']
    max_truth_gap = contract['maximum_truth_gap_sim_s']
    A, origin, anchor = fixed_prestream_alignment(run, truth)
    ref = {'source_ns': anchor['reference_source_ns']}
    ref_gap_ns = anchor['truth_bracket_gap_sim_s'] * 1e9
    yawoff = math.atan2(A[1, 0], A[0, 0])

    phase_stamps = [(x.get('phase'), int(x.get('stamp_ns', 0))) for x in phases]
    start_candidates = [stamp for phase, stamp in phase_stamps if phase == 'PRESTREAM']
    landing_candidates = [stamp for phase, stamp in phase_stamps if phase == 'LANDING']
    landed_candidates = [stamp for phase, stamp in phase_stamps if phase == 'LANDED']
    if not start_candidates:
        raise ValueError('No PRESTREAM source timestamp in bridge timeline')
    enable_start = start_candidates[0]

    reports = []
    for leg in attempts(flight):
        target = A @ leg['goal']['target_enu'] + origin
        target_yaw = leg['goal']['yaw_enu'] + yawoff
        if 'source_ns' in leg['goal']:
            goal_stamp = int(leg['goal']['source_ns'])
        else:
            event = next(x for x in planner['messages'] if x['type'] == 'goal')
            h = event['message']['target']['header']['stamp']
            goal_stamp = h['sec'] * 10**9 + h['nanosec']
        end_stamp = min(landing_candidates[0] if landing_candidates else truth[-1]['stamp_ns'],
                        int(leg.get('goal_completed_source_ns',
                                    landed_candidates[0] if landed_candidates else truth[-1]['stamp_ns'])))

        rows = []
        selected = [p for p in truth if goal_stamp <= p['stamp_ns'] <= end_stamp]
        if not selected:
            raise ValueError('No truth samples overlap the dispatched goal interval')
        stamps = [int(p['stamp_ns']) for p in selected]
        if any(b <= a for a, b in zip(stamps, stamps[1:])):
            raise ValueError('Truth source timestamps are not strictly increasing')
        observed_max_gap = max(((b - a) / 1e9 for a, b in zip(stamps, stamps[1:])),
                      default=0.0)

        for p in selected:
            R = rotation(p['q_xyzw'])
            sensor_position = np.asarray(p['xyz'])
            position_error = float(np.linalg.norm(sensor_position - target))
            yaw = math.atan2(R[1, 0], R[0, 0])
            yaw_error = wrap_abs_angle(yaw, target_yaw)
            rows.append({
                'sim_s': p['stamp_ns'] / 1e9,
                'wall_s': float(p.get('wall_s', 0.0)),
                'position_error_m': position_error,
                'yaw_error_rad': yaw_error,
                'inside': position_error <= pos_tol and yaw_error <= yaw_tol,
            })

        best = longest_joint_window(rows, max_gap_sim_s=max_truth_gap)
        contiguous_pass = bool(best and best['duration_sim_s'] >= required)
        # If there is no qualifying window and the truth trace has a gap large
        # enough to hide one, do not convert lack of support into a numeric FAIL.
        status = 'PASS' if contiguous_pass else ('FAIL' if observed_max_gap <= max_truth_gap else 'INSUFFICIENT')
        report = {
            'truth_reference_contract': imu_truth_samples(run, {'samples': []})[1],
            'time_domain': 'gazebo_sim_source_stamp',
            'wall_time_role': 'diagnostic_only',
            'scope': 'Offline, single fixed ground SE(3), scale 1; no truth feedback or timestamp repair.',
            'ground_rotation': A.tolist(),
            'ground_translation': origin.tolist(),
            'ground_yaw_offset_rad': yawoff,
            'reference_source_ns': ref['source_ns'],
            'alignment_anchor': anchor,
            'reference_truth_gap_sim_s': ref_gap_ns / 1e9,
            'world_imu_goal_xyz': target.tolist(),
            'minimum_true_3d_position_error_m': min(
                row['position_error_m'] for row in rows),
            'position_tolerance_m': pos_tol,
            'yaw_tolerance_deg': math.degrees(yaw_tol),
            'required_contiguous_dwell_sim_s': required,
            'max_truth_sample_gap_sim_s': observed_max_gap,
            'max_allowed_truth_sample_gap_sim_s': max_truth_gap,
            'acceptance_config_path': str(acceptance_path.relative_to(ROOT)
                                         if acceptance_path.is_relative_to(ROOT)
                                         else acceptance_path),
            'acceptance_config_sha256': contract['sha256'],
            'goal_truth_sample_count': len(rows),
            'longest_joint_tolerance_window': best,
            'independent_goal_dwell_status': status,
            'independent_goal_dwell_passed': contiguous_pass,
            'native_action_success': bool(leg.get('action_success', False)),
            'truth_is_offline_only': True,
        }
        reports.append(report)

    landed_stamp = landed_candidates[0] if landed_candidates else truth[-1]['stamp_ns']
    invalid_status_observations = [x for x in flight.get('localization_quality_history', [])
                                   if enable_start <= x['stamp_ns'] <= landed_stamp and not x.get('valid', True)]
    # These values are retained as observations, not gates: project-added
    # localization quality/age policies were explicitly removed.
    failures = []
    if (run / 'vio.log').exists():
        lines = (run / 'vio.log').read_text().splitlines()
        begin = next((i for i, line in enumerate(lines)
                      if 'bridge phase=PRESTREAM' in line), 0)
        finish = next((i for i, line in enumerate(lines[begin:], begin)
                       if 'bridge phase=LANDED' in line), len(lines))
        failures = [line for line in lines[begin:finish + 1]
                    if any(pattern in line for pattern in
                           ['mapping gate closed', 'odom or depth lost',
                            'localization status became stale', 'EMERGENCY_STOP'])]
    publisher_counts = flight.get('publisher_counts', {})
    unique_control = bool(publisher_counts) and all(v == 1 for v in publisher_counts.values())
    all_geom_pass = all(x['independent_goal_dwell_passed'] for x in reports)
    action_pass = bool(flight.get('result') == 'PASS' and
                       all(x['native_action_success'] for x in reports))
    landed_disarmed = bool(flight.get('landed_and_disarmed', False))
    result = {
        **reports[-1],
        'legs': reports,
        'classification': 'PASS' if all_geom_pass and action_pass and landed_disarmed and unique_control
                          else ('INSUFFICIENT' if any(x['independent_goal_dwell_status'] == 'INSUFFICIENT'
                                                     for x in reports)
                                else 'FAIL'),
        'independent_goal_dwell_passed': all_geom_pass,
        'native_action_success': action_pass,
        'landed_and_disarmed': landed_disarmed,
        'invalid_localization_status_samples_observed_not_gated': len(invalid_status_observations),
        'upstream_or_diagnostic_failure_log_lines': failures,
        'failure_log_lines_are_observations_not_project_health_gates': True,
        'control_publisher_counts': publisher_counts,
        'unique_control_publishers_passed': unique_control,
    }
    output = run / output_name
    output.write_text(json.dumps(result, indent=2) + '\n')
    return result, output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--output', default='arrival-evaluation.json',
                        help='output filename inside run_dir (default: arrival-evaluation.json)')
    parser.add_argument('--acceptance-config', type=Path,
                        default=ROOT / 'config/acceptance.json',
                        help='offline acceptance thresholds; never used by runtime control')
    args = parser.parse_args(argv)
    result, output = evaluate_run(args.run_dir, args.output, args.acceptance_config)
    print(json.dumps({'output':str(output),'classification':result['classification'],
                      'independent_goal_dwell_status':result['independent_goal_dwell_status'],
                      'longest_joint_tolerance_window':result['longest_joint_tolerance_window'],
                      'required_contiguous_dwell_sim_s':result['required_contiguous_dwell_sim_s']}, indent=2))


if __name__ == '__main__':
    main()
