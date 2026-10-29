#!/usr/bin/env python3
"""Offline compare #391 raw VINS, PX4 hold state, and Gazebo truth."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


PX4_NAV_STATE_NAMES = {
    4: 'AUTO_LOITER',
    12: 'DESCEND',
    14: 'OFFBOARD',
    18: 'AUTO_LAND',
}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def px4_status_transitions(rows):
    """Keep only changes to the archived PX4 mode and arming state."""
    transitions = []
    previous = None
    for row in rows:
        state = (row.get('nav_state'), row.get('arming_state'),
                 row.get('failsafe'), row.get('pre_flight_checks_pass'))
        if state == previous:
            continue
        nav_state = row.get('nav_state')
        transitions.append({
            'timestamp_us': row.get('timestamp'),
            'wall_elapsed_s': row.get('wall_elapsed_s'),
            'nav_state': nav_state,
            'nav_state_name': PX4_NAV_STATE_NAMES.get(nav_state),
            'arming_state': row.get('arming_state'),
            'failsafe': row.get('failsafe'),
            'pre_flight_checks_pass': row.get('pre_flight_checks_pass'),
        })
        previous = state
    return transitions


def stats(values):
    values = np.asarray(values, dtype=float)
    if not values.size:
        return {'count': 0, 'p50': None, 'p95': None, 'max': None}
    return {
        'count': int(values.size),
        'p50': float(np.percentile(values, 50)),
        'p95': float(np.percentile(values, 95)),
        'max': float(np.max(values)),
    }


def evaluate(run_dir):
    run_dir = Path(run_dir).resolve()
    flight_path = run_dir / 'flight.json'
    truth_path = run_dir / 'debug-truth-evaluation.json'
    arrival_path = run_dir / 'n10-arrival-evaluation-diagnostic.json'
    timeline_path = run_dir / 'n08-localization-source-timeline.json'
    hold_path = run_dir / 'n10-partial-hold-drift-before-localization-lock.json'
    contact_path = run_dir / 'n10-contact-evaluation-partial.json'
    clearance_path = run_dir / 'n10-partial-hold-physics-step-clearance-diagnostic.json'
    emergency_precheck_path = run_dir / 'emergency-disarm-immediate-precheck.json'
    emergency_terminal_path = run_dir / 'emergency-disarm-safe-terminal.json'
    px4_status_message_path = (Path(__file__).resolve().parents[2]
                               / 'src/vendor/px4_msgs/msg/VehicleStatus.msg')

    flight = json.loads(flight_path.read_text())
    truth_report = json.loads(truth_path.read_text())
    truth = truth_report['samples']
    arrival = json.loads(arrival_path.read_text())
    timeline = json.loads(timeline_path.read_text())
    hold = json.loads(hold_path.read_text())
    contact = json.loads(contact_path.read_text())
    clearance = json.loads(clearance_path.read_text())
    emergency_precheck = (json.loads(emergency_precheck_path.read_text())
                          if emergency_precheck_path.is_file() else {})
    emergency_terminal = (json.loads(emergency_terminal_path.read_text())
                          if emergency_terminal_path.is_file() else {})
    emergency_status = (emergency_precheck.get('latest') or {}).get('px4_status') or {}

    truth_ns = np.asarray([int(row['stamp_ns']) for row in truth], dtype=np.int64)
    truth_xyz = np.asarray([row['xyz'] for row in truth], dtype=float)
    truth_quat = np.asarray([row['q_xyzw'] for row in truth], dtype=float)
    rotation = np.asarray(arrival['ground_rotation'], dtype=float)
    translation = np.asarray(arrival['ground_translation'], dtype=float)
    goal_completed_ns = int(flight['goal_completed_source_ns'])
    fault_ns = int(hold['interval']['end_source_ns'])
    goal_start_ns = int(flight['goal']['source_ns'])
    contact_ns = int((clearance.get('first_forbidden_contact') or {})['stamp_ns'])

    raw_events = sorted((event for event in timeline['events']
                         if event.get('stream') == 'raw_optimized'
                         and isinstance(event.get('source_stamp_ns'), int)),
                        key=lambda event: event['source_stamp_ns'])
    raw_rows = []
    for event in raw_events:
        source_ns = int(event['source_stamp_ns'])
        if source_ns < goal_start_ns or source_ns > fault_ns:
            continue
        truth_index = int(np.argmin(np.abs(truth_ns - source_ns)))
        truth_gap_s = abs(int(truth_ns[truth_index]) - source_ns) / 1e9
        aligned = rotation @ np.asarray(event['position_xyz_m'], dtype=float) + translation
        error = float(np.linalg.norm(aligned - truth_xyz[truth_index]))
        raw_rows.append({
            'source_ns': source_ns,
            'source_s': source_ns / 1e9,
            'position_error_m': error,
            'truth_pair_gap_s': truth_gap_s,
            'aligned_vins_world_m': aligned.tolist(),
            'truth_world_m': truth_xyz[truth_index].tolist(),
        })

    def raw_interval(start_ns, end_ns):
        return [row for row in raw_rows if start_ns <= row['source_ns'] <= end_ns]

    pre_goal = raw_interval(raw_rows[0]['source_ns'], goal_start_ns)
    goal_motion = raw_interval(goal_start_ns, goal_completed_ns)
    active_hold = raw_interval(goal_completed_ns, fault_ns)
    hold_before_contact = raw_interval(goal_completed_ns, contact_ns)
    hold_contact_to_lock = raw_interval(contact_ns, fault_ns)

    def first_crossing(rows, threshold_m):
        row = next((item for item in rows if item['position_error_m'] >= threshold_m), None)
        if row is None:
            return None
        return {'source_ns': row['source_ns'], 'source_s': row['source_s'],
                'position_error_m': row['position_error_m']}

    crossings = {str(threshold): first_crossing(active_hold, threshold)
                 for threshold in (0.3, 0.5, 1.0, 2.0, 5.0)}

    setpoints = flight.get('px4_trajectory_setpoint_observations', [])
    setpoint_times = np.asarray([int(row['timestamp_us']) for row in setpoints],
                                dtype=np.int64)
    setpoint_positions = np.asarray([row['position_ned'] for row in setpoints],
                                    dtype=float)

    def px4_hold_interval(start_ns, end_ns):
        local_samples = [row for row in flight.get('local_position_history', [])
                         if start_ns / 1000 <= row.get('timestamp_us', -1)
                         <= end_ns / 1000]
        local_tracking_errors, local_speeds, local_pair_gaps = [], [], []
        for row in local_samples:
            timestamp_us = int(row['timestamp_us'])
            index = int(np.argmin(np.abs(setpoint_times - timestamp_us)))
            gap_s = abs(int(setpoint_times[index]) - timestamp_us) / 1e6
            position = np.asarray([row['x'], row['y'], row['z']], dtype=float)
            velocity = np.asarray([row['vx'], row['vy'], row['vz']], dtype=float)
            local_pair_gaps.append(gap_s)
            local_tracking_errors.append(float(np.linalg.norm(position - setpoint_positions[index])))
            local_speeds.append(float(np.linalg.norm(velocity)))
        return {
            'position_error_m': stats(local_tracking_errors),
            'local_speed_m_s': stats(local_speeds),
            'paired_local_setpoint_samples': len(local_tracking_errors),
            'maximum_pair_time_gap_sim_s': max(local_pair_gaps, default=None),
        }

    telemetry = sorted((event for event in timeline['events']
                        if event.get('stream') == 'vins_telemetry'
                        and isinstance(event.get('source_stamp_ns'), int)),
                       key=lambda event: event['source_stamp_ns'])
    feature_rows = []
    for event in telemetry:
        stamp_ns = int(event['source_stamp_ns'])
        if goal_completed_ns <= stamp_ns <= fault_ns:
            metrics = event.get('metrics') or {}
            feature_rows.append({
                'source_ns': stamp_ns,
                'stereo_features': metrics.get('stereo_features'),
                'continued_tracks': metrics.get('continued_tracks'),
                'long_tracks': metrics.get('long_tracks'),
                'normalized_cost_observed': metrics.get('normalized_cost'),
                'solver_usable': metrics.get('solver_usable'),
            })

    features_before_contact = [row for row in feature_rows
                               if row['source_ns'] <= contact_ns]
    features_after_contact = [row for row in feature_rows
                              if row['source_ns'] > contact_ns]

    bridge_alignment = []
    for event in flight.get('bridge_detail_history', []):
        detail = event.get('detail') or {}
        timestamp_us = detail.get('px4_time_reference_us')
        if timestamp_us is None:
            continue
        timestamp_ns = int(timestamp_us) * 1000
        if goal_completed_ns <= timestamp_ns <= fault_ns:
            bridge_alignment.append({
                'source_ns': timestamp_ns,
                'translation_disagreement_m': detail.get('alignment_drift_m'),
                'yaw_disagreement_rad': detail.get('alignment_yaw_error_rad'),
            })

    truth_rows = [row for row in truth if goal_completed_ns <= int(row['stamp_ns']) <= fault_ns]
    truth_before_contact = [row for row in truth_rows
                            if int(row['stamp_ns']) <= contact_ns]
    goal_position = np.asarray(hold['contract_reference']['target_world_imu_m'], dtype=float)
    truth_displacement = [float(np.linalg.norm(np.asarray(row['xyz']) - goal_position))
                          for row in truth_rows]
    raw_sample_gaps_s = np.diff([row['source_ns'] for row in raw_rows]) / 1e9

    return {
        'schema': 'n10-hold-state-divergence/v1',
        'run_id': run_dir.name,
        'classification': 'offline failure analysis; no truth feedback or control; cause not uniquely identified',
        'read_only': True,
        'truth_used_online': False,
        'control_published': False,
        'runtime_contract_sha256': json.loads((run_dir / 'runtime-contract.json').read_text())['sha256'],
        'fixed_alignment': {
            'source': arrival_path.name,
            'method': 'single prestream scale-one SE(3); no segment fit',
            'rotation': rotation.tolist(),
            'translation_m': translation.tolist(),
        },
        'hold_interval': {
            'goal_completion_source_ns': goal_completed_ns,
            'localization_lock_source_ns': fault_ns,
            'duration_sim_s': (fault_ns - goal_completed_ns) / 1e9,
            'gazebo_truth_samples': len(truth_rows),
            'gazebo_truth_max_gap_sim_s': float(np.diff(
                [int(row['stamp_ns']) for row in truth_rows]).max() / 1e9),
        },
        'fixed_aligned_raw_vins_position_error_m': {
            'pre_goal': stats([row['position_error_m'] for row in pre_goal]),
            'goal_motion': stats([row['position_error_m'] for row in goal_motion]),
            'active_hold': stats([row['position_error_m'] for row in active_hold]),
            'active_hold_until_first_contact': stats([
                row['position_error_m'] for row in hold_before_contact]),
            'first_contact_to_integrity_lock': stats([
                row['position_error_m'] for row in hold_contact_to_lock]),
            'active_hold_first_crossings': crossings,
            'sample_pair_time_gap_s': {
                'max': float(np.max(raw_sample_gaps_s)) if raw_sample_gaps_s.size else None,
                'p95': float(np.percentile(raw_sample_gaps_s, 95)) if raw_sample_gaps_s.size else None,
                'truth_match_max': max((row['truth_pair_gap_s'] for row in raw_rows), default=None),
            },
            'sample_count_by_segment': {
                'pre_goal': len(pre_goal), 'goal_motion': len(goal_motion),
                'active_hold': len(active_hold),
            },
        },
        'gazebo_truth_position_error_to_goal_m': stats(truth_displacement),
        'gazebo_truth_position_error_to_goal_until_contact_m': stats([
            float(np.linalg.norm(np.asarray(row['xyz']) - goal_position))
            for row in truth_before_contact]),
        'px4_local_position_vs_trajectory_setpoint': {
            'until_first_contact': px4_hold_interval(goal_completed_ns, contact_ns),
            'first_contact_to_integrity_lock': px4_hold_interval(contact_ns, fault_ns),
        },
        'bridge_alignment_diagnostic': {
            'translation_disagreement_m': stats([
                abs(float(row['translation_disagreement_m']))
                for row in bridge_alignment
                if row['translation_disagreement_m'] is not None]),
            'yaw_disagreement_rad': stats([
                abs(float(row['yaw_disagreement_rad']))
                for row in bridge_alignment
                if row['yaw_disagreement_rad'] is not None]),
            'sample_count': len(bridge_alignment),
        },
        'vins_feature_telemetry': {
            'sample_count': len(feature_rows),
            'first_hold_sample': feature_rows[0] if feature_rows else None,
            'last_prelock_sample': feature_rows[-1] if feature_rows else None,
            'first_contact_to_lock': {
                'sample_count': len(features_after_contact),
                'minimum_stereo_features': min((row['stereo_features'] for row in features_after_contact
                                                if isinstance(row['stereo_features'], int)), default=None),
                'minimum_long_tracks': min((row['long_tracks'] for row in features_after_contact
                                            if isinstance(row['long_tracks'], int)), default=None),
            },
            'until_first_contact': {
                'sample_count': len(features_before_contact),
                'minimum_stereo_features': min((row['stereo_features'] for row in features_before_contact
                                                if isinstance(row['stereo_features'], int)), default=None),
                'minimum_long_tracks': min((row['long_tracks'] for row in features_before_contact
                                            if isinstance(row['long_tracks'], int)), default=None),
            },
            'minimum_stereo_features': min((row['stereo_features'] for row in feature_rows
                                            if isinstance(row['stereo_features'], int)),
                                           default=None),
            'minimum_long_tracks': min((row['long_tracks'] for row in feature_rows
                                        if isinstance(row['long_tracks'], int)), default=None),
            'full_series': feature_rows,
        },
        'fault_and_contact_order': {
            'first_wall_envelope_zero_clearance_source_ns': 271072000000,
            'first_prohibited_contact_source_ns': contact['result'].get(
                'first_forbidden_contact_source_ns', contact_ns),
            'first_prohibited_contact': clearance.get('first_forbidden_contact'),
            'localization_integrity_lock_source_ns': fault_ns,
            'planner_fault_reason': 'full_curve_depth_odom_timeout',
            'px4_nav_state_transitions': px4_status_transitions(
                flight.get('vehicle_status_history', [])),
            'px4_state_at_emergency_precheck': {
                'bridge_phase': 'LANDING', 'bridge_armed': True,
                'bridge_landed': False, 'bridge_control_enabled': True,
                'px4_nav_state': emergency_status.get('nav_state'),
                'px4_nav_state_name': PX4_NAV_STATE_NAMES.get(
                    emergency_status.get('nav_state')),
                'px4_failsafe': emergency_status.get('failsafe'),
            },
            'px4_state_after_emergency_closeout': {
                'bridge_phase': emergency_terminal.get('bridge_phase'),
                'bridge_armed': emergency_terminal.get('bridge_armed'),
                'bridge_landed': emergency_terminal.get('bridge_landed'),
                'bridge_control_enabled': emergency_terminal.get(
                    'bridge_control_enabled'),
                'px4_arming_state': emergency_terminal.get('px4_arming_state'),
                'px4_nav_state': emergency_terminal.get('px4_nav_state'),
                'px4_nav_state_name': PX4_NAV_STATE_NAMES.get(
                    emergency_terminal.get('px4_nav_state')),
                'px4_failsafe': emergency_terminal.get('px4_failsafe'),
                'px4_land_detected': emergency_terminal.get('px4_land_detected'),
            },
            'authorized_emergency_closeout': 'emergency-disarm-safe-terminal.json',
        },
        'interpretation': [
            'PX4 local position remained close to its fixed trajectory setpoint while independently observed Gazebo truth moved away from the target.',
            'Fixed-aligned raw VINS position became nearly stationary relative to world truth during the hold; stereo feature and long-track counts declined near the later integrity lock.',
            'The records support estimator/measurement divergence before contact. They do not identify whether image content, image/IMU delivery, estimator degeneracy, or another cause initiated it.',
            'The bridge requested NAV_LAND. The archived PX4 history shows AUTO_LAND (18), then failsafe DESCEND (12); the immediate pre-disarm readback was still armed in DESCEND, without LandDetected. This sequence does not identify the command ACK or establish native landing completion.',
            'The later emergency closeout readback showed disarmed and LandDetected, while nav_state remained OFFBOARD (14). That readback establishes safe session closeout after the authorized emergency command, not native planner-fault landing completion.',
        ],
        'limitations': [
            'The localization-source timeline is wall-decimated; per-sample truth matches are close, but sparse raw VINS samples do not prove the continuous estimator trajectory.',
            'No camera image or stereo receipt history was archived through the failed hold, so visual observability and image delivery cannot be separated retrospectively.',
            'The independent Gazebo truth and alignment are diagnostic references only; no fitted segment transform is used.',
            'Feature counts, normalized cost and bridge alignment disagreement are observations, not runtime gates.',
        ],
        'input_sha256': {
            'flight.json': sha256(flight_path),
            'debug-truth-evaluation.json': sha256(truth_path),
            'n10-arrival-evaluation-diagnostic.json': sha256(arrival_path),
            'n08-localization-source-timeline.json': sha256(timeline_path),
            'n10-partial-hold-drift-before-localization-lock.json': sha256(hold_path),
            'n10-contact-evaluation-partial.json': sha256(contact_path),
            'n10-partial-hold-physics-step-clearance-diagnostic.json': sha256(clearance_path),
            'emergency-disarm-immediate-precheck.json': (
                sha256(emergency_precheck_path) if emergency_precheck_path.is_file() else None),
            'emergency-disarm-safe-terminal.json': (
                sha256(emergency_terminal_path) if emergency_terminal_path.is_file() else None),
            'VehicleStatus.msg': (sha256(px4_status_message_path)
                                  if px4_status_message_path.is_file() else None),
            'evaluator_source': sha256(Path(__file__)),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = evaluate(args.run_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({
        'output': str(args.output),
        'hold_interval_sim_s': report['hold_interval']['duration_sim_s'],
        'raw_vins_hold_error': report['fixed_aligned_raw_vins_position_error_m']['active_hold'],
        'px4_hold_tracking': report['px4_local_position_vs_trajectory_setpoint'],
        'truth_hold_error': report['gazebo_truth_position_error_to_goal_m'],
        'feature_samples': report['vins_feature_telemetry']['sample_count'],
    }, indent=2))


if __name__ == '__main__':
    main()
