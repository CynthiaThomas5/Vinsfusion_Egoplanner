#!/usr/bin/env python3
"""Replay N08 prospective landing geometry against retained raw occupancy maps."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from n05_entry import (check_candidate_landing_schedule, collision_primitives,
                       fit_ground_plane, load_policy)
from n08_trial_gate import candidate_landing_pose_from_ground_planes


ARCHIVES = (
    ('n08-20261025-260-terminal-braking-measurement', 'n08-trial-airborne-map'),
    ('n08-20261025-267-yaw-first-return', 'n08-trial-airborne-map'),
    ('n08-20261025-273-observer-pre-enable-repeatability', 'n08-trial-pre-turn-map'),
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit_run(run_id, map_label, policy, primitives):
    run = ROOT / 'artifacts/runs' / run_id
    flight_path = run / 'flight.json'
    live_path = run / 'n05-current-area/n05-live-entry-check.json'
    metadata_path = run / (map_label + '.json')
    archive_path = run / (map_label + '.npz')
    flight = json.loads(flight_path.read_text())
    live = json.loads(live_path.read_text())
    metadata = json.loads(metadata_path.read_text())
    with np.load(archive_path) as archive:
        occupancy = archive['occupancy']
    snapshot = {
        'occupancy': occupancy,
        'origin_m': metadata['origin_m'],
        'resolution_m': float(metadata['resolution_m']),
    }
    goal = flight['goal']
    home_pose = live['state']['body_pose_imu_m']
    home_plane = flight['pre_enable_corridor']['home_pad_entry']['ground_plane']
    guess = [float(goal['target_enu'][0]), float(goal['target_enu'][1]),
             float(home_pose['center_xyz_m'][2])]
    plane = fit_ground_plane(occupancy, metadata['origin_m'],
                             metadata['resolution_m'], guess, policy)
    if plane.get('valid'):
        landing_pose = candidate_landing_pose_from_ground_planes(
            home_pose, home_plane, plane, goal['target_enu'][:2], goal['yaw_enu'])
        certificate = check_candidate_landing_schedule(
            snapshot, landing_pose, hold_height_m=1.0,
            policy=policy, ground_plane=plane, primitives=primitives)
    else:
        landing_pose = None
        certificate = {'accepted': False,
                       'reason': plane.get('reason', 'candidate_ground_plane_invalid'),
                       'ground_confirmed': False, 'phases': {}}
    return {
        'run_id': run_id,
        'map_label': map_label,
        'map_identity': {'epoch': metadata.get('epoch'), 'map_id': metadata.get('map_id')},
        'goal_target_enu_m': goal['target_enu'],
        'landing_pose': landing_pose,
        'candidate_ground_plane': plane,
        'certificate': certificate,
        'actual_ground_confirmed': False,
        'scope': 'raw-map prospective landing geometry replay only; not touchdown or flight evidence',
        'input_sha256': {
            'flight.json': digest(flight_path),
            'n05-live-entry-check.json': digest(live_path),
            metadata_path.name: digest(metadata_path),
            archive_path.name: digest(archive_path),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    policy = load_policy(ROOT)
    primitives = collision_primitives(ROOT)
    rows = [audit_run(run_id, map_label, policy, primitives)
            for run_id, map_label in ARCHIVES]
    report = {
        'schema': 'n08-candidate-landing-archive-audit/v1',
        'result': 'PASS' if all(row['certificate'].get('accepted') is True
                                and row['certificate'].get('ground_confirmed') is False
                                for row in rows) else 'FAIL',
        'scope': 'prospective landing candidate geometry; no run, mode or physical touchdown is certified',
        'source_sha256': {
            'tools/diagnostics/audit_n08_candidate_landing_archives.py': digest(__file__),
            'tools/n05_entry.py': digest(ROOT / 'tools/n05_entry.py'),
            'tools/n08_trial_gate.py': digest(ROOT / 'tools/n08_trial_gate.py'),
        },
        'runs': rows,
    }
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'result': report['result'], 'output': str(output),
                      'accepted_candidates': sum(
                          row['certificate'].get('accepted') is True for row in rows),
                      'count': len(rows)}, indent=2))
    return 0 if report['result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
