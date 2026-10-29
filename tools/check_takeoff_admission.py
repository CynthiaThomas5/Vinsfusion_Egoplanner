#!/usr/bin/env python3
"""Select the authorized takeoff policy; never turn a skipped N05 into a pass."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def official_takeoff_checks(preflight):
    last = preflight.get('last', {})
    bridge = last.get('bridge') or {}
    odom = last.get('odom') or {}
    linear = odom.get('twist', {}).get('twist', {}).get('linear', {})
    velocity = [float(linear.get(k, math.nan)) for k in ('x', 'y', 'z')]
    speed = math.sqrt(sum(v*v for v in velocity))
    checks = {
        'localization_px4_preflight': preflight.get('passed') is True,
        'landed_unarmed_control_disabled': (
            bridge.get('phase') == 'DISABLED' and bridge.get('landed') is True
            and bridge.get('armed') is False and bridge.get('control_enabled') is False),
    }
    return {
        'schema': 'official-ego-takeoff-admission/v1',
        'policy': 'official_ego', 'passed': all(checks.values()), 'checks': checks,
        'observed_odom_speed_m_s': speed if math.isfinite(speed) else None,
        'speed_metric_effect': 'diagnostic_only_no_takeoff_refusal',
        'n05_raw_volume_gate_required': False,
        'entry_map_known_free_claimed': False,
        'basis': 'PX4-native preflight and landed/disarmed/control-disabled state; takeoff odometry speed is reported without a project-local numeric refusal threshold',
        'scope': 'Simulation launch procedure with operator-selected starting site; no autonomous clearance claim for unseen rear/upper space.',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    policy = json.loads((ROOT/'config/components/navigation/task_supervisor.json').read_text()).get('collision_policy', 'known_free')
    if policy == 'official_ego':
        report = official_takeoff_checks(json.loads((run/'preflight.json').read_text()))
        (run/'takeoff-admission.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps(report))
        if not report['passed']:
            raise SystemExit('official takeoff state checks failed')
    elif policy == 'known_free':
        target = run/'n05-current-area'
        target.mkdir(exist_ok=True)
        subprocess.run([sys.executable, str(ROOT/'tools/check_n05_entry_live.py'), '--output-dir', str(target)], check=True)
        subprocess.run([sys.executable, str(ROOT/'tools/evaluate_n05_entry.py'), '--live-report', str(target/'n05-live-entry-check.json'), '--output', str(target/'n05-offline-entry-replay.json')], check=True)
        live = json.loads((target/'n05-live-entry-check.json').read_text())
        replay = json.loads((target/'n05-offline-entry-replay.json').read_text())
        if not (live.get('accepted') and live.get('online_offline_result_identical') and replay.get('matches_online_result')):
            raise SystemExit('legacy N05 known-free admission refused: '+str(live.get('reason')))
    else:
        raise SystemExit('unsupported collision_policy: '+str(policy))


if __name__ == '__main__':
    main()
