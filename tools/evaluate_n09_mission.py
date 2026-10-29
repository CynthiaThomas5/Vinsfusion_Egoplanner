#!/usr/bin/env python3
"""Read-only N09 evaluator for 3D/yaw arrival, live source freshness and PX4 handoff."""
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from n09_contact_evaluation import evaluate_contacts

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(Path(path).read_text())


def interpolate_truth(rows, stamp_ns, maximum_gap_s=0.04):
    stamps = np.asarray([int(row['stamp_ns']) for row in rows], dtype=np.int64)
    positions = np.asarray([row['xyz'] for row in rows], dtype=float)
    if (len(stamps) < 2 or np.any(np.diff(stamps) <= 0)
            or positions.shape != (len(stamps), 3)
            or not np.isfinite(positions).all()):
        raise ValueError('truth_samples_not_finite_strictly_increasing')
    index = int(np.searchsorted(stamps, int(stamp_ns)))
    if index < len(stamps) and stamps[index] == stamp_ns:
        return positions[index].copy(), 0.0
    if index == 0 or index == len(stamps):
        raise ValueError('truth_does_not_bracket_goal_timestamp')
    gap = int(stamps[index] - stamps[index - 1]) / 1e9
    if gap > maximum_gap_s:
        raise ValueError(f'truth_interpolation_gap_exceeded:{gap:.6f}s')
    fraction = (int(stamp_ns) - int(stamps[index - 1])) / (stamps[index] - stamps[index - 1])
    return positions[index - 1] + fraction * (positions[index] - positions[index - 1]), gap


def wrap_angle(value):
    return math.atan2(math.sin(value), math.cos(value))


def quaternion_yaw(q):
    x, y, z, w = map(float, q)
    norm = math.sqrt(x*x + y*y + z*z + w*w)
    if not math.isfinite(norm) or norm < 1e-9:
        raise ValueError('invalid_truth_quaternion')
    x, y, z, w = x/norm, y/norm, z/norm, w/norm
    return math.atan2(2.0*(w*z + x*y), 1.0 - 2.0*(y*y + z*z))


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def localization_receipt_freshness(timeline, status_limit_s=0.5, odometry_limit_s=0.3):
    # record_n08_localization_sources emits stream_summary, never streams.
    summaries = timeline.get('stream_summary', {})
    gaps = [summaries.get(key, {}).get('max_receipt_gap_wall_s')
            for key in ('localization_status', 'adapter_optimized')]
    passed = all(isinstance(gap, (int, float)) and math.isfinite(gap)
                 and 0.0 <= gap <= limit
                 for gap, limit in zip(gaps, (status_limit_s, odometry_limit_s)))
    return {'passed': passed, 'max_status_receipt_gap_wall_s': gaps[0],
            'max_optimized_odometry_receipt_gap_wall_s': gaps[1]}


def evaluate(run):
    run = Path(run).resolve()
    profile_path = ROOT / 'config/components/navigation/n09_3d_waypoint_goal.json'
    profile = load(profile_path)
    flight = load(run / 'flight.json')
    arrival = load(run / 'arrival-evaluation.json')
    truth = load(run / 'debug-truth-evaluation.json')['samples']
    source_timeline = load(run / 'n08-localization-source-timeline.json')
    contact_report = load(run / 'n09-contact-observation.json')
    live_refusal = load(run / 'n09-live-refusal.json')
    planner = load(run / 'planner-observation.json')['messages']
    bridge = read_jsonl(run / 'bridge-alignment-timeline.jsonl')

    goal = flight.get('goal') or {}
    goal_id = flight.get('goal_id', '')
    epoch = flight.get('localization_epoch', '')
    goal_stamp = int(goal.get('source_ns', 0))
    completed_stamp = int(flight.get('goal_completed_source_ns', 0))
    landed = [row for row in bridge if row.get('phase') == 'LANDED']
    landed_stamp = int(landed[-1]['stamp_ns']) if landed else 0

    target_offset = np.asarray(profile['target_offset_enu_m'], dtype=float)
    native_position_tolerance = float(profile['position_tolerance_m'])
    native_yaw_tolerance = float(profile['yaw_tolerance_rad'])
    expected_displacement = float(np.linalg.norm(target_offset))
    actual_start, start_truth_gap = interpolate_truth(truth, goal_stamp)
    actual_finish, finish_truth_gap = interpolate_truth(truth, completed_stamp)
    true_displacement = float(np.linalg.norm(actual_finish - actual_start))
    true_height_change = abs(float(actual_finish[2] - actual_start[2]))

    alignment_rotation = np.asarray(arrival['ground_rotation'], dtype=float)
    alignment_translation = np.asarray(arrival['ground_translation'], dtype=float)
    origin_odom = np.asarray(flight['airborne_origin_enu'], dtype=float)
    if alignment_rotation.shape != (3, 3) or alignment_translation.shape != (3,):
        raise ValueError('invalid_fixed_truth_alignment')
    target_world = alignment_rotation @ np.asarray(goal['target_enu'], dtype=float) + alignment_translation
    origin_world = alignment_rotation @ origin_odom + alignment_translation
    independent_goal_offset = float(np.linalg.norm(target_world - origin_world))

    start_truth_row = min(truth, key=lambda row: abs(int(row['stamp_ns']) - goal_stamp))
    finish_truth_row = min(truth, key=lambda row: abs(int(row['stamp_ns']) - completed_stamp))
    yaw_start = quaternion_yaw(start_truth_row['q_xyzw'])
    yaw_finish = quaternion_yaw(finish_truth_row['q_xyzw'])
    yaw_change = abs(wrap_angle(yaw_finish - yaw_start))
    target_yaw_world = float(goal['yaw_enu']) + math.atan2(
        alignment_rotation[1, 0], alignment_rotation[0, 0])
    yaw_error_at_finish = abs(wrap_angle(yaw_finish - target_yaw_world))

    events = source_timeline.get('events', [])
    map_rows = [row for row in events if row.get('stream') == 'map_status'
                and isinstance(row.get('clock_ns_at_receipt'), int)
                and isinstance(row.get('source_stamp_ns'), int)]
    pregoal_map = [row for row in map_rows
                   if goal_stamp - 1_000_000_000 <= row['clock_ns_at_receipt'] <= goal_stamp]
    during_map = [row for row in map_rows
                  if goal_stamp <= row['clock_ns_at_receipt'] <= landed_stamp]
    mapping_policy = load(ROOT / 'config/components/mapping/ego_planner.json')
    map_age_limit = float(mapping_policy['odom_depth_timeout_sim_s'])
    relevant_map = pregoal_map[-1:] + during_map
    map_ages = []
    map_identity = set()
    map_ready = True
    for row in relevant_map:
        clock_ns = int(row['clock_ns_at_receipt'])
        source_age = (clock_ns - int(row['source_stamp_ns'])) / 1e9
        occupancy_age = (clock_ns - int(row['last_occupancy_stamp_ns'])) / 1e9
        map_ages.extend((source_age, occupancy_age))
        map_identity.add((row.get('epoch'), row.get('map_id')))
        map_ready = map_ready and bool(row.get('input_ready')) and bool(row.get('reset_acknowledged'))
    map_fresh = bool(
        pregoal_map and during_map and map_ready and len(map_identity) == 1
        and next(iter(map_identity))[0] == epoch
        and all(-0.02 <= age <= map_age_limit for age in map_ages))

    localization_rows = [row for row in events
                         if row.get('stream') == 'localization_status'
                         and isinstance(row.get('clock_ns_at_receipt'), int)
                         and goal_stamp - 1_000_000_000 <= row['clock_ns_at_receipt'] <= landed_stamp]
    localization_valid = bool(localization_rows) and all(
        row.get('epoch') == epoch and row.get('valid') is True
        and int(row.get('state', -1)) == 1
        for row in localization_rows)
    nav_policy = load(ROOT / 'config/components/navigation/task_supervisor.json')
    receipt_freshness = localization_receipt_freshness(
        source_timeline, nav_policy['max_localization_receipt_age_s'],
        nav_policy['max_odometry_receipt_age_s'])
    localization_gaps_ok = receipt_freshness['passed']

    goal_messages = [row.get('message', {}) for row in planner
                     if row.get('type') == 'goal'
                     and row.get('message', {}).get('goal_id') == goal_id]
    matching_commands = [row for row in flight.get('position_command_history', [])
                         if row.get('goal_id') == goal_id and row.get('epoch') == epoch
                         and int(row.get('flag', -1)) == 1]
    publisher_counts = flight.get('publisher_counts', {})
    unique_output = bool(publisher_counts) and all(int(count) == 1
                                                   for count in publisher_counts.values())

    contact_manifest = load(run / 'n09-contact-model-manifest.json')
    contacts = evaluate_contacts(contact_report, contact_manifest, bridge, goal_stamp)

    action_success = bool(
        flight.get('result') == 'PASS' and flight.get('action_success')
        and (flight.get('action_result') or {}).get('outcome') == 'succeeded'
        and (flight.get('action_result') or {}).get('success') is True)
    independent_arrival = bool(
        arrival.get('independent_goal_dwell_passed')
        and arrival.get('native_action_success')
        and arrival.get('landed_and_disarmed')
        and float(arrival.get('minimum_true_3d_position_error_m', float('inf')))
        <= float(profile['verification_position_tolerance_m'])
        and yaw_error_at_finish <= native_yaw_tolerance)
    displacement_clear = bool(
        expected_displacement > 3.0 * native_position_tolerance
        and true_displacement > max(3.0 * native_position_tolerance, 0.20)
        and independent_goal_offset > max(3.0 * native_position_tolerance, 0.20))

    checks = {
        'native_action_succeeded_and_landed': action_success and landed_stamp > 0,
        '3d_displacement_exceeded_tolerance': displacement_clear,
        'height_change_exceeded_tolerance': abs(float(goal['target_enu'][2]) - origin_odom[2])
        > native_position_tolerance and true_height_change > native_position_tolerance,
        'yaw_change_exceeded_tolerance': yaw_change > native_yaw_tolerance,
        'independent_true_arrival_position_and_yaw': independent_arrival,
        'same_epoch_map_id_fresh_before_goal_through_landing': map_fresh,
        'localization_and_odometry_fresh_through_landing': localization_valid and localization_gaps_ok,
        'matching_goal_map_admission_and_ego_command': bool(goal_messages)
        and goal_messages[-1].get('epoch') == epoch
        and goal_messages[-1].get('map_id') in {row.get('map_id') for row in relevant_map}
        and bool(matching_commands),
        'unique_bridge_owned_px4_control_publishers': unique_output,
        'contact_sensors_live_and_no_prohibited_vehicle_contact': contacts['passed'],
        'live_out_of_map_goal_refused_while_disarmed_without_ego_forwarding': bool(
            live_refusal.get('passed') is True
            and live_refusal.get('reason') == 'map_query_outside_map'
            and not live_refusal.get('matching_ego_commands')
            and live_refusal.get('bridge_after', {}).get('phase') in ('DISABLED', 'LANDED')
            and live_refusal.get('bridge_after', {}).get('armed') is False
            and live_refusal.get('bridge_after', {}).get('landed') is True),
    }
    checks = {name: bool(value) for name, value in checks.items()}
    report = {
        'schema': 'n09-mission-evaluation/v1',
        'run_id': run.name,
        'passed': all(checks.values()),
        'checks': checks,
        'goal_id': goal_id,
        'epoch': epoch,
        'map_id': next(iter(map_identity))[1] if map_identity else None,
        'target_offset_enu_m': target_offset.tolist(),
        'expected_3d_displacement_m': expected_displacement,
        'independent_3d_displacement_m': true_displacement,
        'independent_displacement_xyz_m': (actual_finish - actual_start).tolist(),
        'independent_height_change_m': true_height_change,
        'independent_goal_offset_m': independent_goal_offset,
        'independent_yaw_change_rad': yaw_change,
        'independent_yaw_error_at_completion_rad': yaw_error_at_finish,
        'native_position_tolerance_m': native_position_tolerance,
        'native_yaw_tolerance_rad': native_yaw_tolerance,
        'independent_true_goal_dwell_wall_s': arrival.get('max_contiguous_true_goal_dwell_wall_s'),
        'takeoff_admission': load(run / 'takeoff-admission.json'),
        'map_freshness': {
            'max_source_age_s': max((age for index, age in enumerate(map_ages) if index % 2 == 0), default=None),
            'max_occupancy_age_s': max((age for index, age in enumerate(map_ages) if index % 2 == 1), default=None),
            'limit_s': map_age_limit,
            'samples_before_goal': len(pregoal_map),
            'samples_goal_through_landing': len(during_map),
            'identities': sorted([list(pair) for pair in map_identity]),
        },
        'localization_freshness': {
            'samples_goal_through_landing': len(localization_rows),
            'max_status_receipt_gap_wall_s': receipt_freshness['max_status_receipt_gap_wall_s'],
            'max_optimized_odometry_receipt_gap_wall_s': receipt_freshness['max_optimized_odometry_receipt_gap_wall_s'],
        },
        'matching_position_command_samples': len(matching_commands),
        'control_publisher_counts': publisher_counts,
        'contacts': {
            **contacts,
            'messages': contact_report.get('total_contact_messages', 0),
        },
        'live_refusal': live_refusal,
        'truth_interpolation_gaps_s': [start_truth_gap, finish_truth_gap],
        'limitations': [
            'This is a single-current-room diagnostic run; it does not count toward N11-N14.',
            'Official inflated-occupied planning and sampled contact observations do not certify physical clearance of unobserved space.',
            'The D435i truth channel is read-only evaluation input and is forbidden from the control chain.'
        ],
    }
    input_names = ('flight.json', 'arrival-evaluation.json', 'debug-truth-evaluation.json',
                   'n08-localization-source-timeline.json', 'planner-observation.json',
                   'bridge-alignment-timeline.jsonl', 'runtime-contract.json',
                   'n09-contact-observation.json', 'n09-contact-model-manifest.json',
                   'n09-live-refusal.json', 'takeoff-admission.json')
    report['input_sha256'] = {
        name: hashlib.sha256((run / name).read_bytes()).hexdigest()
        for name in input_names if (run / name).is_file()}
    report['evaluator_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (run / 'n09-mission-evaluation.json').write_text(
        json.dumps(report, indent=2, allow_nan=False) + '\n')
    return report


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: evaluate_n09_mission.py RUN_DIR')
    result = evaluate(sys.argv[1])
    print(json.dumps(result, indent=2, allow_nan=False))
    if not result['passed']:
        raise SystemExit(1)
