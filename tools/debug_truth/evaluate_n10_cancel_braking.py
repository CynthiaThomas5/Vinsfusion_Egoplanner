#!/usr/bin/env python3
"""Offline N10 diagnostic measurement for a speed-triggered EGO goal cancel."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def interpolate_truth(rows, stamp_ns):
    stamps = np.asarray([int(row['stamp_ns']) for row in rows], dtype=np.int64)
    positions = np.asarray([row['xyz'] for row in rows], dtype=float)
    if len(stamps) < 3 or np.any(np.diff(stamps) <= 0):
        raise ValueError('truth_source_stamps_not_strictly_increasing')
    if not np.isfinite(positions).all():
        raise ValueError('truth_positions_non_finite')
    index = int(np.searchsorted(stamps, int(stamp_ns), side='left'))
    if index < len(stamps) and stamps[index] == int(stamp_ns):
        return positions[index], 0.0
    if index == 0 or index == len(stamps):
        raise ValueError('truth_does_not_cover_requested_braking_stamp')
    gap = int(stamps[index] - stamps[index - 1])
    if gap > 40_000_000:
        raise ValueError('truth_interpolation_gap_exceeds_0.04_sim_s')
    alpha = (int(stamp_ns) - int(stamps[index - 1])) / gap
    return positions[index - 1] + alpha * (positions[index] - positions[index - 1]), gap / 1e9


def truth_path(rows, start_ns, end_ns):
    if int(end_ns) <= int(start_ns):
        raise ValueError('invalid_truth_braking_interval')
    p0, gap0 = interpolate_truth(rows, start_ns)
    p1, gap1 = interpolate_truth(rows, end_ns)
    middle = [row for row in rows if int(start_ns) < int(row['stamp_ns']) < int(end_ns)]
    positions = [p0, *[np.asarray(row['xyz'], dtype=float) for row in middle], p1]
    positions = np.asarray(positions, dtype=float)
    stamps = [int(start_ns), *[int(row['stamp_ns']) for row in middle], int(end_ns)]
    if len(stamps) < 3 or np.any(np.diff(stamps) <= 0):
        raise ValueError('insufficient_truth_samples_in_cancel_stop_interval')
    max_gap = max(int(b - a) for a, b in zip(stamps[:-1], stamps[1:])) / 1e9
    if max_gap > 0.04:
        raise ValueError('truth_source_gap_exceeds_0.04_sim_s')
    steps = np.diff(positions[:, :2], axis=0)
    distances = np.linalg.norm(steps, axis=1)
    return {
        'start_xyz_m': positions[0].tolist(),
        'stop_band_entry_xyz_m': positions[-1].tolist(),
        'horizontal_path_length_m': float(distances.sum()),
        'horizontal_endpoint_displacement_m': float(np.linalg.norm(positions[-1, :2] - positions[0, :2])),
        'three_dimensional_path_length_m': float(np.linalg.norm(np.diff(positions, axis=0), axis=1).sum()),
        'max_source_gap_sim_s': max(max_gap, gap0, gap1),
        'truth_samples_in_interval': len(stamps),
    }


def evaluate(run):
    flight_path = run / 'flight.json'
    truth_path_file = run / 'debug-truth-evaluation.json'
    contact_path = run / 'vehicle-contact-evaluation.json'
    readback_path = run / 'postflight-px4-bridge-readback.json'
    observer_path = run / 'n09-contact-observation.json'
    for path in (flight_path, truth_path_file, contact_path, readback_path, observer_path):
        if not path.is_file():
            raise FileNotFoundError(f'missing required input: {path.name}')
    flight = read_json(flight_path)
    truth_report = read_json(truth_path_file)
    truth = truth_report.get('samples') or []
    cancel = flight.get('cancel_stop') or {}
    if not cancel:
        raise ValueError('flight_has_no_cancel_stop_record')
    trigger_ns = int(cancel['request_sim_ns'])
    stop = cancel.get('stop_band') or {}
    stop_start_ns = int(stop['start_sim_ns'])
    stop_confirmed_ns = int(stop['confirmed_sim_ns'])
    path_metrics = truth_path(truth, trigger_ns, stop_start_ns)

    px4_rows = flight.get('local_position_history') or []
    selected = [row for row in px4_rows
                if row.get('sim_time_ns') is not None
                and trigger_ns <= int(row['sim_time_ns']) <= stop_start_ns]
    if len(selected) < 3:
        raise ValueError('insufficient_px4_local_position_samples_for_cancel_stop')
    stamps = np.asarray([int(row['sim_time_ns']) for row in selected], dtype=np.int64)
    speeds = np.asarray([math.hypot(float(row['vx']), float(row['vy'])) for row in selected])
    if np.any(np.diff(stamps) <= 0) or not np.isfinite(speeds).all():
        raise ValueError('px4_cancel_speed_samples_non_monotonic_or_non_finite')
    dt = np.diff(stamps) / 1e9
    acceleration = np.diff(speeds) / dt
    decel = -acceleration[acceleration < 0.0]
    trigger_speed = float(cancel['px4_horizontal_speed_m_s'])
    ninety_percent = np.flatnonzero(speeds <= 0.9 * trigger_speed)
    response_10pct = (None if len(ninety_percent) == 0 else
                      max(0.0, (int(stamps[ninety_percent[0]]) - trigger_ns) / 1e9))
    truth_stamps = np.asarray([int(row['stamp_ns']) for row in truth], dtype=np.int64)
    stop_position, _ = interpolate_truth(truth, stop_start_ns)
    stop_end_position, _ = interpolate_truth(truth, stop_confirmed_ns)
    stop_interval = (truth_stamps >= stop_start_ns) & (truth_stamps <= stop_confirmed_ns)
    stop_positions = np.asarray([row['xyz'] for row in truth], dtype=float)[stop_interval]
    stop_excursion = (float(np.linalg.norm(stop_positions[:, :2] - stop_position[:2], axis=1).max())
                      if len(stop_positions) else None)

    contact = read_json(contact_path)
    readback = read_json(readback_path)
    bridge = readback.get('latest', {}).get('bridge', {})
    observer = read_json(observer_path)
    localization_policy_open = False
    run_manifest_path = run / 'n10-cancel-run-manifest.json'
    runtime_path = run / 'runtime-contract.json'
    if run_manifest_path.is_file() and runtime_path.is_file():
        run_manifest = read_json(run_manifest_path)
        runtime = read_json(runtime_path)
        localization_policy_open = (
            run_manifest.get('localization_quality_freshness_gates') == 'removed'
            and run_manifest.get('runtime_contract_sha256') == runtime.get('sha256'))
    # Keep old diagnostic runs evaluable: those runs explicitly recorded that
    # the same project-owned policy was bypassed rather than removed.
    localization_policy_open = localization_policy_open or (
        flight.get('diagnostic_localization_health_gate_bypass_observed') is True)
    health = flight.get('vins_quality_history') or []
    normalized_costs = [float(row['normalized_cost']) for row in health
                        if row.get('normalized_cost') is not None
                        and math.isfinite(float(row['normalized_cost']))]
    checks = {
        'native_cancel_measurement_completed': flight.get('cancel_diagnostic_completed') is True,
        'trigger_speed_in_requested_px4_window': (
            float(cancel['cancel_trigger_speed_window_m_s'][0]) <= trigger_speed
            <= float(cancel['cancel_trigger_speed_window_m_s'][1])),
        'caller_cancel_acknowledged': cancel.get('cancel_acknowledged') is True,
        'action_reports_caller_cancel': (
            (cancel.get('action_result') or {}).get('status') == 5
            and (cancel.get('action_result') or {}).get('outcome') == 'canceled'
            and (cancel.get('action_result') or {}).get('reason') == 'caller_cancel'),
        'replacement_ego_trajectory_observed': (
            cancel.get('replacement_trajectory', {}).get('distinct_from_canceled_trajectory') is True),
        'px4_stop_band_held_one_sim_second': (
            float(stop.get('dwell_sim_s', 0.0)) >= 1.0
            and float(stop.get('max_sample_gap_sim_s', math.inf)) <= 0.20
            and int(stop.get('sample_count', 0)) >= 2),
        'truth_covers_cancel_to_stop_with_bounded_gaps': (
            path_metrics['max_source_gap_sim_s'] <= 0.04),
        'contact_observer_complete': (
            observer.get('safe_session_terminal_observed') is True
            if 'safe_session_terminal_observed' in observer
            else observer.get('terminal_flight_record_observed') is True),
        'zero_prohibited_contacts': contact.get('passed') is True
            and contact.get('prohibited_contact_event_count') == 0,
        'independent_terminal_readback_safe': (
            bridge.get('phase') == 'LANDED' and bridge.get('landed') is True
            and bridge.get('armed') is False and bridge.get('control_enabled') is False
            and readback.get('vehicle_remained_disarmed') is True
            and readback.get('control_samples_zero') is True),
        'localization_quality_freshness_policy_open': localization_policy_open,
    }
    report = {
        'schema': 'n10-cancel-braking-measurement/v1',
        'run_id': run.name,
        'classification': 'diagnostic_measurement; not a braking guarantee or formal qualification',
        'formal_qualification': False,
        'checks': checks,
        'measurement_complete': all(checks.values()),
        'metrics': {
            'requested_trigger_px4_speed_window_m_s': cancel.get('cancel_trigger_speed_window_m_s'),
            'trigger_px4_horizontal_speed_m_s': trigger_speed,
            'trigger_px4_vertical_speed_m_s': float(cancel['px4_vertical_speed_m_s']),
            'trigger_ego_reference_speed_m_s': float(cancel['ego_reference_speed_m_s']),
            'cancel_ack_wall_delay_s': float(cancel.get('cancel_ack_wall_delay_s', math.nan)),
            'replacement_trajectory_id': cancel.get('replacement_trajectory', {}).get('trajectory_id'),
            'replacement_trajectory_delay_sim_s': (
                int(cancel['replacement_trajectory']['first_source_stamp_ns']) - trigger_ns) / 1e9,
            'px4_stop_band_entry_delay_sim_s': (stop_start_ns - trigger_ns) / 1e9,
            'px4_stop_band_confirmation_delay_sim_s': (stop_confirmed_ns - trigger_ns) / 1e9,
            'stop_band_dwell_sim_s': float(stop.get('dwell_sim_s', 0.0)),
            'stop_band_px4_sample_count': int(stop.get('sample_count', 0)),
            'stop_band_max_px4_sample_gap_sim_s': float(stop.get('max_sample_gap_sim_s', math.nan)),
            'truth_cancel_to_stop_distance': path_metrics,
            'truth_stop_band_1s_max_horizontal_excursion_m': stop_excursion,
            'px4_observed_max_horizontal_speed_during_cancel_m_s': float(speeds.max()),
            'px4_observed_p10_horizontal_deceleration_m_s2': (
                float(np.percentile(decel, 10)) if len(decel) else None),
            'px4_time_to_first_10pct_speed_reduction_sim_s': response_10pct,
            'localization_quality_freshness_gates': (
                'removed' if localization_policy_open else 'not_recorded'),
            'normalized_cost_max_observed': max(normalized_costs) if normalized_costs else None,
            'contact_prohibited_event_count': contact.get('prohibited_contact_event_count'),
            'terminal_bridge_phase': bridge.get('phase'),
        },
        'limitations': [
            'One SITL cancellation sample; not a lower bound or general stopping guarantee.',
            'Localization quality and source/receipt freshness are not runtime gates; raw measurements remain reported for N10 calibration.',
            'The EGO replacement trajectory uses upstream inflated-occupied collision handling; this is not the removed raw-free whole-curve gate.',
            'This report does not provide minimum obstacle clearance; contact-free is not a clearance measurement.',
            'Truth is read-only and is not a navigation or control input.',
        ],
        'input_sha256': {},
    }
    for name in ('flight.json', 'debug-truth-evaluation.json', 'planner-observation.json',
                 'bridge-observation.json', 'n09-contact-observation.json',
                 'vehicle-contact-evaluation.json', 'postflight-px4-bridge-readback.json',
                 'runtime-contract.json', 'n09-run-manifest.json',
                 'n10-cancel-run-manifest.json'):
        path = run / name
        if path.is_file():
            report['input_sha256'][name] = sha256(path)
    csv_path = run / 'n10-cancel-speed-curve.csv'
    with csv_path.open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(('sim_time_ns', 'elapsed_since_cancel_s', 'px4_horizontal_speed_m_s',
                         'px4_vertical_speed_m_s', 'px4_x_ned_m', 'px4_y_ned_m', 'px4_z_ned_m'))
        for row in selected:
            writer.writerow((row['sim_time_ns'],
                             (int(row['sim_time_ns']) - trigger_ns) / 1e9,
                             math.hypot(float(row['vx']), float(row['vy'])), row['vz'],
                             row['x'], row['y'], row['z']))
    report['speed_curve_csv_sha256'] = sha256(csv_path)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    report = evaluate(run)
    output = run / 'n10-cancel-braking-evaluation.json'
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0 if report['measurement_complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
