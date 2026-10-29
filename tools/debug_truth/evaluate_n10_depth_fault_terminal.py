#!/usr/bin/env python3
"""Offline evaluation of an isolated N10 depth-input fault through PX4 terminal."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from n10_terminal_readback import summarize_terminal_readback


def evaluate_records(fault, flight, planner_log, bridge_rows, capture,
                     sensor_receipts, safe_record, terminal_readback):
    trigger = fault.get('goal_trigger') or {}
    depth = (fault.get('topics') or {}).get('depth') or {}
    goal_id = str(flight.get('goal_id') or '')
    epoch = str(flight.get('localization_epoch') or '')
    goal_matches = bool(goal_id and epoch
                        and trigger.get('goal_id') == goal_id
                        and trigger.get('epoch') == epoch)
    start_ns = trigger.get('drop_window_start_ns')
    end_ns = trigger.get('drop_window_end_ns')
    dropped = int(depth.get('dropped') or 0)
    before = int(depth.get('forwarded_before') or 0)
    after = int(depth.get('forwarded_after') or 0)
    valid_window = (type(start_ns) is int and type(end_ns) is int and end_ns > start_ns)

    preserved_streams = {'stereo_left_image': 0, 'stereo_right_image': 0, 'camera_imu': 0}
    if valid_window:
        for row in sensor_receipts:
            stream = row.get('stream')
            stamp = row.get('sim_stamp_ns_at_receipt')
            if stream in preserved_streams and type(stamp) is int and start_ns <= stamp < end_ns:
                preserved_streams[stream] += 1
    sensor_capture_ok = (
        all(value > 0 for value in preserved_streams.values())
        and all((capture.get('source_stamp_regressions') or {}).get(name, 1) == 0
                for name in preserved_streams)
        and not capture.get('errors')
    )

    planner_timeout_seen = ('Depth Lost!' in planner_log
                            and 'depth_odom_timeout' in planner_log)
    action_result = flight.get('action_result') or {}
    action_aborted_for_depth = (
        flight.get('action_goal_sent') is True
        and flight.get('action_success') is False
        and action_result.get('outcome') == 'aborted'
        and 'depth_odom_timeout' in str(action_result.get('reason') or '')
    )
    landing_rows = [row for row in bridge_rows
                    if row.get('phase') == 'LANDING'
                    and type(row.get('stamp_ns')) is int
                    and valid_window and row['stamp_ns'] >= start_ns]
    matching_landing = next((row for row in landing_rows
                             if 'depth_odom_timeout' in str(row.get('reason') or '')),
                            None)
    landed_rows = [row for row in bridge_rows if row.get('phase') == 'LANDED'
                   and row.get('landed') is True and row.get('armed') is False]
    terminal = summarize_terminal_readback(terminal_readback)
    native_safe_readback = (
        safe_record.get('safe_to_stop_project_container') is True
        and safe_record.get('native_terminal_evidence_complete') is True
        and terminal['native_terminal_evidence_complete'] is True
        and bool(landed_rows)
    )
    trigger_to_landing_sim_s = None
    if matching_landing is not None and valid_window:
        trigger_to_landing_sim_s = (matching_landing['stamp_ns'] - start_ns) / 1e9

    checks = {
        'relay_report_finalized': (fault.get('finalized') is True
                                   and fault.get('status') == 'finalized'),
        'depth_route_isolated': (
            fault.get('kind') == 'depth'
            and fault.get('scope') == 'Explicit sensor-fault relay with source-stamp scheduled drop window'
            and fault.get('fault_drop_observed') is True
            and before > 0 and dropped > 0 and after > 0
        ),
        'fault_bound_to_active_goal_epoch': goal_matches,
        'stereo_and_imu_remained_live': sensor_capture_ok,
        'native_ego_depth_timeout_observed': planner_timeout_seen,
        'navigation_action_aborted_for_depth_timeout': action_aborted_for_depth,
        'bridge_entered_fault_landing': matching_landing is not None,
        'bridge_reached_landed_disarmed': bool(landed_rows),
        'independent_native_terminal_readback_complete': native_safe_readback,
        'no_emergency_disarm': safe_record.get('emergency_disarm_used') is False,
    }
    return {
        'schema': 'n10-depth-fault-terminal-evaluation/v1',
        'classification': 'offline single-run fault calibration; not formal N15 qualification',
        'status': 'PASS' if all(checks.values()) else 'INSUFFICIENT',
        'checks': checks,
        'identity': {
            'goal_id': goal_id, 'epoch': epoch,
            'fault_goal_id': trigger.get('goal_id'),
            'fault_epoch': trigger.get('epoch'),
            'goal_identity_matches': goal_matches,
        },
        'fault_window': {
            'start_source_ns': start_ns, 'end_source_ns': end_ns,
            'duration_sim_s': ((end_ns - start_ns) / 1e9 if valid_window else None),
            'depth_frames_forwarded_before': before,
            'depth_frames_dropped': dropped,
            'depth_frames_forwarded_after': after,
            'unaffected_stream_receipts_during_window': preserved_streams,
        },
        'terminal': {
            'action_result': action_result,
            'bridge_fault_landing': matching_landing,
            'bridge_landed_transition': landed_rows[-1] if landed_rows else None,
            'trigger_to_landing_sim_s': trigger_to_landing_sim_s,
            'native_terminal_readback': terminal,
            'emergency_disarm_used': safe_record.get('emergency_disarm_used'),
        },
        'scope_limits': [
            'One N10 calibration only; it does not count toward the post-freeze N15 repetitions.',
            'The measured trigger-to-LANDING interval is descriptive; no new runtime threshold is created.',
            'No control, takeoff refusal or landing decision is made by this evaluator.',
        ],
    }


def native_planner_log_path(run):
    """Find the ROS launch log that contains the native EGO diagnostics."""
    run = Path(run)
    candidates = (run / 'vio.log', run.parent / f'{run.name}-stack' / 'vio.log')
    return next((path for path in candidates if path.is_file()), None)


def evaluate(run):
    run = Path(run)
    load = lambda name: json.loads((run / name).read_text())
    receipts = [json.loads(line) for line in
                (run / 'n10-sensor-receipts.jsonl').read_text().splitlines() if line.strip()]
    bridge_rows = [json.loads(line) for line in
                   (run / 'bridge-alignment-timeline.jsonl').read_text().splitlines()
                   if line.strip()]
    planner_log = native_planner_log_path(run)
    native_planner_log = planner_log.read_text() if planner_log is not None else ''
    report = evaluate_records(
        load('n10-depth-fault-relay.json'), load('flight.json'),
        native_planner_log, bridge_rows, load('n10-sensor-capture.json'),
        receipts, load('safe-to-stop.json'),
        load('postflight-px4-bridge-readback.json'))
    report['native_planner_log_path'] = (
        str(planner_log.relative_to(run.parent)) if planner_log is not None else None)
    report['native_planner_log_available'] = planner_log is not None
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = evaluate(args.run)
    output = args.output or args.run / 'n10-depth-fault-terminal-evaluation.json'
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(report, indent=2, allow_nan=False))
    if report['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
