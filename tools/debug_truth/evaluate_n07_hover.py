#!/usr/bin/env python3
"""Offline N07 localization and no-goal hold error report; never publishes ROS."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools/debug_truth'))
sys.path.insert(0, str(ROOT / 'src/own/uav_sim'))
from evaluate_odometry import evaluate as evaluate_odometry  # noqa: E402


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def stats(values):
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or not len(values) or not np.isfinite(values).all():
        raise ValueError('Cannot summarize empty or non-finite samples')
    return {
        'count': int(len(values)),
        'mean': float(values.mean()),
        'rms': float(np.sqrt(np.mean(values * values))),
        'p95': float(np.percentile(values, 95)),
        'maximum': float(values.max()),
        'endpoint': float(values[-1]),
    }


def interpolate_rows(rows, target_times, key):
    times = np.asarray([row['wall_monotonic_s'] for row in rows], dtype=float)
    values = np.asarray([row[key] for row in rows], dtype=float)
    if (len(times) < 2 or np.any(np.diff(times) <= 0) or not np.isfinite(times).all()
            or not np.isfinite(values).all()):
        raise ValueError('Truth samples are non-finite, unordered, or insufficient')
    target_times = np.asarray(target_times, dtype=float)
    if target_times[0] < times[0] or target_times[-1] > times[-1]:
        raise ValueError('Truth samples do not cover all hover reference times')
    return np.column_stack([
        np.interp(target_times, times, values[:, axis]) for axis in range(values.shape[1])])


def read_phases(path):
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    prestream = [row for row in rows if row.get('phase') == 'PRESTREAM']
    landed = [row for row in rows if row.get('phase') == 'LANDED']
    if not prestream or not landed or landed[-1]['stamp_ns'] <= prestream[0]['stamp_ns']:
        raise ValueError('Bridge timeline lacks ordered PRESTREAM and LANDED phases')
    return rows, prestream[0], landed[-1]


def evaluate(run):
    run = Path(run).resolve()
    flight = load_json(run / 'flight.json')
    observation = load_json(run / 'alignment-observation.json')
    truth_document = load_json(run / 'debug-truth-evaluation.json')
    truth = truth_document['samples']
    phases, prestream, landed = read_phases(run / 'bridge-alignment-timeline.jsonl')

    localization, localization_curve = evaluate_odometry(
        observation, truth, phases, flight, np.zeros(3, dtype=float))

    hover_start_ns = int(flight['hover_start_sim_time_ns'])
    hover_end_ns = int(flight['hover_end_sim_time_ns'])
    requested_hover_s = float(flight['hover_requested_sim_s'])
    if hover_end_ns <= hover_start_ns:
        raise ValueError('Hover simulation-clock interval is invalid')
    hover_curve = [row for row in localization_curve
                   if hover_start_ns <= int(row['source_ns']) <= hover_end_ns]
    if not hover_curve:
        raise ValueError('No independent truth-paired VINS samples during hover')

    wall_origin = float(flight['wall_monotonic_origin_s'])
    hover_wall_start = wall_origin + float(flight['hover_start_wall_elapsed_s'])
    hover_wall_end = wall_origin + float(flight['hover_end_wall_elapsed_s'])
    local_rows = flight.get('hover_local_position_history') or []
    if len(local_rows) < 3:
        raise ValueError('PX4 local-position hold history has fewer than three samples')
    local_times = np.asarray([wall_origin + float(row['wall_elapsed_s']) for row in local_rows])
    local_positions = np.asarray([[row['x'], row['y'], row['z']] for row in local_rows], dtype=float)
    if (np.any(np.diff(local_times) <= 0) or not np.isfinite(local_positions).all()
            or local_times[0] < hover_wall_start - 0.1 or local_times[-1] > hover_wall_end + 0.1):
        raise ValueError('PX4 hold samples are unordered or outside the hover wall interval')
    truth_rows = [row for row in truth if 'wall_monotonic_s' in row]
    if len(truth_rows) < 3:
        raise ValueError('Gazebo read-only truth samples lack cross-process monotonic timestamps')
    truth_positions = interpolate_rows(truth_rows, local_times, 'xyz')
    local_delta = local_positions - local_positions[0]
    truth_delta = truth_positions - truth_positions[0]
    local_drift = np.linalg.norm(local_delta, axis=1)
    truth_drift = np.linalg.norm(truth_delta, axis=1)
    truth_gaps = np.diff([row['wall_monotonic_s'] for row in truth_rows])

    localization_error = np.asarray([row['position_error_m'] for row in hover_curve], dtype=float)
    localization_yaw = np.asarray([abs(row['yaw_error_deg']) for row in hover_curve], dtype=float)
    hover_status = [row for row in flight.get('localization_quality_history', [])
                    if hover_start_ns <= int(row.get('source_stamp_ns', row.get('stamp_ns', 0)))
                    <= hover_end_ns]
    active_details = [row for row in flight.get('bridge_detail_history', [])
                      if float(flight['hover_start_wall_elapsed_s']) <= float(row['wall_elapsed_s'])
                      <= float(flight['hover_end_wall_elapsed_s'])]
    time_errors = sorted({str(row.get('detail', {}).get('odometry_time_error', ''))
                          for row in active_details})
    clock_valid_samples = sum(
        row.get('detail', {}).get('px4_time_domain_valid') is True
        for row in active_details)

    n05_path = run / 'n05-current-area/n05-live-entry-check.json'
    n05 = load_json(n05_path)
    graph = load_json(run / 'ros-graph-audit.json')
    boot_parameters = load_json(run / 'px4-boot-parameters.json')
    ulog = load_json(run / 'px4-ulog-analysis.json')
    runtime = load_json(run / 'runtime-contract.json')
    checks = {
        'n05_current_area_accepted_before_enable': bool(n05.get('accepted'))
            and n05.get('scope', '').startswith('DISARMED'),
        'no_navigation_goal_sent': flight.get('action_goal_sent') is False,
        'hover_completed_at_requested_sim_duration': bool(
            flight.get('hover_completed_without_quality_abort')
            and flight.get('hover_duration_sim_s', 0) >= requested_hover_s),
        'landed_and_disarmed_by_bridge': bool(flight.get('landed_and_disarmed'))
            and bool(flight.get('latest_bridge_status', {}).get('landed'))
            and not bool(flight.get('latest_bridge_status', {}).get('armed')),
        'tracking_remained_valid_through_hover': bool(hover_status)
            and all(row.get('valid') for row in hover_status),
        'odometry_time_mapping_valid_through_hover': bool(active_details)
            and all(not error for error in time_errors)
            and clock_valid_samples == len(active_details),
        'read_only_ros_graph_unique_control_owner': bool(graph.get('checks_passed'))
            and bool(graph.get('airborne_snapshot_captured')),
        'px4_boot_parameters_confirm_vio_no_gnss': bool(boot_parameters.get('passed'))
            and boot_parameters.get('parameters', {}).get('EKF2_EV_CTRL') == 15
            and boot_parameters.get('parameters', {}).get('EKF2_GPS_CTRL') == 0,
        'ulog_confirms_ev_fusion_and_no_gnss_truth_aiding': bool(ulog.get('passed')),
        'independent_localization_and_hold_errors_measured': bool(
            localization_error.size and len(truth_drift) >= 3),
        'same_runtime_contract_recorded': bool(runtime.get('sha256')),
    }
    report = {
        'schema': 'n07-no-goal-hover-evaluation/v1',
        'scope': __doc__,
        'run_id': run.name,
        'result': 'PASS' if all(checks.values()) else 'FAIL',
        'checks': checks,
        'qualification_note': 'N07 defines evidence coverage but no numeric hover/localization error threshold; metrics below are reported without inventing one.',
        'fixed_runtime_contract_sha256': runtime.get('sha256'),
        'current_area_preflight': {
            'accepted': n05.get('accepted'), 'reason': n05.get('reason'),
            'epoch': n05.get('identity', {}).get('epoch'),
            'map_id': n05.get('identity', {}).get('map_id'),
        },
        'hover_interval': {
            'requested_sim_s': requested_hover_s,
            'measured_sim_s': flight.get('hover_duration_sim_s'),
            'wall_s': flight.get('hover_duration_wall_s'),
            'sim_start_ns': hover_start_ns, 'sim_end_ns': hover_end_ns,
            'wall_start_monotonic_s': hover_wall_start,
            'wall_end_monotonic_s': hover_wall_end,
            'local_position_samples': int(len(local_rows)),
            'truth_max_wall_gap_s': float(truth_gaps.max()),
            'valid_localization_status_samples': sum(bool(row.get('valid')) for row in hover_status),
            'localization_status_samples': len(hover_status),
            'active_bridge_detail_samples': len(active_details),
            'odometry_time_error_values': time_errors,
            'px4_time_domain_valid_samples': clock_valid_samples,
        },
        'independent_localization_error': {
            'alignment': localization['alignment'],
            'whole_flight': localization['position_error_m'],
            'whole_flight_absolute_yaw_deg': localization['absolute_yaw_error_deg'],
            'hover_position_error_m': stats(localization_error),
            'hover_absolute_yaw_error_deg': stats(localization_yaw),
            'hover_truth_paired_raw_samples': len(hover_curve),
            'whole_flight_coverage': localization['coverage'],
            'truth_point': 'Gazebo d435i_link; VINS raw odometry IMU point; latest strictly pre-PRESTREAM alignment, scale=1',
        },
        'independent_hold_error': {
            'reference': 'first PX4 local-position sample in the no-goal hover window; truth interpolated on shared process monotonic time',
            'px4_local_ned_displacement_norm_m': stats(local_drift),
            'gazebo_truth_displacement_norm_m': stats(truth_drift),
            'gazebo_truth_point': 'd435i_link',
            'px4_local_invalid_samples': sum(
                not (row.get('xy_valid') and row.get('z_valid')) for row in local_rows),
        },
        'control_and_exit': {
            'action_goal_sent': flight.get('action_goal_sent'),
            'hover_position_command_count': flight.get('hover_position_command_count'),
            'publisher_counts': flight.get('publisher_counts'),
            'bridge_phases': flight.get('bridge_phases'),
            'landed_and_disarmed': flight.get('landed_and_disarmed'),
            'latest_bridge_status': flight.get('latest_bridge_status'),
        },
        'input_sha256': {
            name: hashlib.sha256((run / name).read_bytes()).hexdigest()
            for name in ('flight.json', 'alignment-observation.json',
                         'debug-truth-evaluation.json', 'bridge-alignment-timeline.jsonl',
                         'ros-graph-audit.json', 'px4-boot-parameters.json',
                         'px4-ulog-analysis.json', 'runtime-contract.json',
                         'n05-current-area/n05-live-entry-check.json')
        },
        'evaluator_sha256': {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (Path(__file__), ROOT / 'tools/debug_truth/evaluate_odometry.py',
                         ROOT / 'tools/diagnostics/record_alignment.py',
                         ROOT / 'tools/debug_truth/record_truth.py')
        },
        'limitations': [
            'No numeric accuracy or hold-error acceptance threshold is defined by N07; values are descriptive measurements.',
            'Gazebo truth and PX4 local states are paired by same-container monotonic receipt time for hold drift; VINS localization error uses source-time truth interpolation.',
            'This is a no-navigation-goal hover baseline; it does not qualify EGO trajectory execution, braking, other scenes or real hardware.',
        ],
    }
    (run / 'n07-hover-evaluation.json').write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    report = evaluate(args.run)
    print(json.dumps({
        'run_id': report['run_id'], 'result': report['result'],
        'checks': report['checks'],
        'hover_position_error_m': report['independent_localization_error'].get(
            'hover_position_error_m'),
        'truth_hold_error_m': report['independent_hold_error'].get(
            'gazebo_truth_displacement_norm_m'),
    }, indent=2, sort_keys=True))
    if report['result'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
