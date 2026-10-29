#!/usr/bin/env python3
"""Independently check the N08 compute-only cancel/hold/land record."""
import argparse
import hashlib
import json
from pathlib import Path


CONTROL_TOPICS = (
    '/fmu/in/vehicle_visual_odometry',
    '/fmu/in/offboard_control_mode',
    '/fmu/in/trajectory_setpoint',
    '/fmu/in/vehicle_command',
)


def evaluate(path):
    path = Path(path).resolve()
    report = json.loads(path.read_text())
    graph = report.get('compute_only_graph') or {}
    mode = report.get('launch_mode_record') or {}
    publishers = report.get('publisher_counts') or {}
    ready_samples = report.get('ready_position_command_samples') or []
    checks = {
        'runner_completed_successfully': report.get('result') == 'PASS',
        'compute_only_launch_mode': mode.get('mode') == 'compute_only',
        'bridge_remapped_from_ego_output': (
            graph.get('bridge_subscribed_to_position_cmd') is False
            and graph.get('bridge_subscribed_to_isolated_input') is True),
        'one_ready_curve_for_goal_epoch': bool(
            report.get('goal_id') and report.get('epoch')
            and any(row.get('goal_id') == report['goal_id']
                    and row.get('epoch') == report['epoch']
                    for row in ready_samples)),
        'cancel_acknowledged': report.get('cancel_accepted') is True,
        'action_cancel_confirmed': report.get('action_cancel_confirmed') is True,
        'bridge_remained_in_hold_after_cancel': (
            report.get('bridge_hold_confirmed_after_cancel') is True
            and float(report.get('hold_after_cancel_sim_s') or 0.0) >= 2.0),
        'no_clock_regressions': report.get('clock_regressions') == 0,
        'landed_and_disarmed': report.get('landed_and_disarmed') is True,
        'n05_online_offline_admission': (
            (report.get('n05_current_area') or {}).get('accepted') is True
            and (report.get('n05_current_area') or {}).get('online_offline_identical') is True),
        'unique_px4_bridge_control_publishers': all(
            publishers.get(topic) == 1 for topic in CONTROL_TOPICS),
        'truth_not_used_for_control': report.get('debug_truth_used_for_control') is False,
    }
    output = {
        'schema': 'n08-compute-only-evaluation/v1',
        'source_record': str(path),
        'source_record_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'source_failure': report.get('failure'),
        'action_terminal_result': (report.get('action_terminal_result_before_ready')
                                   or report.get('failure_action_terminal_result')
                                   or report.get('action_terminal_result_before_cancel')
                                   or report.get('action_terminal_result_after_cancel')),
        'checks': checks,
        'passed': all(checks.values()),
        'scope': 'compute-only trajectory generation, cancel, bridge hold and landing; no translation/braking qualification',
        'n08_exit_satisfied': False,
    }
    destination = path.parent / 'n08-compute-only-evaluation.json'
    destination.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n',
                           encoding='utf-8')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('flight_record', type=Path)
    args = parser.parse_args()
    result = evaluate(args.flight_record)
    print(json.dumps({'passed': result['passed'], 'checks': result['checks']},
                     indent=2, ensure_ascii=False))
    return 0 if result['passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
