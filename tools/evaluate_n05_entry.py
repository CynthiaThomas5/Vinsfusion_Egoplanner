#!/usr/bin/env python3
"""Replay one archived N05 live snapshot and compare its online admission."""
import argparse
import hashlib
import json
import math
import numbers
from pathlib import Path

import numpy as np

from n05_entry import ROOT, check_entry_schedule, collision_primitives, load_policy


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def n05_results_match(left, right):
    """Compare replay output while tolerating floating-point fit roundoff."""
    if isinstance(left, dict) and isinstance(right, dict):
        return (left.keys() == right.keys()
                and all(n05_results_match(left[key], right[key]) for key in left))
    if isinstance(left, list) and isinstance(right, list):
        return (len(left) == len(right)
                and all(n05_results_match(a, b) for a, b in zip(left, right)))
    if isinstance(left, bool) or isinstance(right, bool):
        return left is right
    if isinstance(left, numbers.Real) and isinstance(right, numbers.Real):
        return math.isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-12)
    return left == right


def evaluate(report_path, output_path=None):
    report_path = Path(report_path).resolve()
    report = json.loads(report_path.read_text())
    policy = load_policy(ROOT)
    archive = report_path.parent / report['snapshot']['archive']
    if not archive.is_file() or sha256(archive) != report['snapshot']['archive_sha256']:
        raise ValueError('archived map snapshot is absent or its SHA256 does not match')
    identity = report['identity']
    if (not identity.get('epoch') or not identity.get('map_id', '').startswith(identity['epoch']+'-')
            or identity.get('frame_id') != 'odom_'+identity['epoch']):
        raise ValueError('snapshot frame/epoch/map_id identity is inconsistent')
    freshness = report['freshness']
    limit = policy['map_policy']['freshness_limit_sim_s']
    for name in ('snapshot_age_sim_s', 'depth_source_age_sim_s', 'fusion_age_sim_s'):
        age = float(freshness[name])
        if age < 0 or age > limit:
            raise ValueError(f'{name} is outside the N05 freshness limit')
    with np.load(archive, allow_pickle=False) as arrays:
        occupancy = arrays['occupancy']
        if tuple(occupancy.shape) != tuple(report['snapshot']['dimensions_xyz']):
            raise ValueError('archived occupancy dimensions do not match the online metadata')
        snapshot = {
            'occupancy': occupancy,
            'origin_m': report['snapshot']['origin_m'],
            'map_size_m': report['snapshot']['map_size_m'],
            'resolution_m': report['snapshot']['resolution_m'],
            'dimensions_xyz': report['snapshot']['dimensions_xyz'],
            'frame_id': identity['frame_id'],
            'epoch': identity['epoch'], 'map_id': identity['map_id'],
        }
        state = report['state']
        pose = state['body_pose_imu_m']
        admission = report['online_admission']
        hold_height_m = float(admission.get('hold_height_m', 1.0))
        sample_step_m = float(admission.get('sample_step_m', 0.05))
        if (not np.isfinite(hold_height_m) or hold_height_m <= 0
                or not np.isfinite(sample_step_m) or sample_step_m <= 0):
            raise ValueError('online report has invalid entry schedule parameters')
        result = check_entry_schedule(
            snapshot, pose,
            hold_height_m=hold_height_m,
            sample_step_m=sample_step_m,
            ground_confirmed=bool(state['landed'] and not state['armed'] and not state['control_enabled']),
            disarmed=not state['armed'], control_disabled=not state['control_enabled'],
            policy=policy, primitives=collision_primitives(ROOT))
    output = {
        'schema': 'n05-offline-entry-replay/v1',
        'source_report': str(report_path.relative_to(ROOT)) if report_path.is_relative_to(ROOT) else str(report_path),
        'source_report_sha256': sha256(report_path),
        'source_snapshot_sha256': sha256(archive),
        'identity': identity,
        'offline_sweep': result,
        'online_admission': report['online_admission'],
        'matches_online_result': n05_results_match(
            result, report['online_admission']),
        'debug_truth_used': False,
        'scope': 'archived current-source raw occupancy replay; not flight approval',
    }
    output_path = Path(output_path) if output_path else report_path.parent/'n05-offline-entry-replay.json'
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False)+'\n')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live-report', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = evaluate(args.live_report, args.output)
    print(json.dumps({'matches_online_result':result['matches_online_result'],
                      'offline_sweep':result['offline_sweep']['reason'],
                      'online_admission':result['online_admission']['reason']},
                     ensure_ascii=False,indent=2))
    return 0 if result['matches_online_result'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
