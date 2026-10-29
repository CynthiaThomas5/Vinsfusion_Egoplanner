#!/usr/bin/env python3
"""Replay N08 forward and cancel corridors against one archived raw map."""
import argparse
import bisect
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from n05_entry import collision_primitives, load_policy  # noqa: E402
from n08_trial_gate import (certify_forward_trial_corridor,
                            certify_trial_capsule)  # noqa: E402


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def historical_heading_basis(flight_path):
    flight = json.loads(flight_path.read_text())
    goal_id = flight['goal_id']
    target_yaw = float(flight['goal']['yaw_enu'])
    commands = [row for row in flight['position_command_history']
                if row.get('goal_id') == goal_id]
    px4_rows = sorted(flight['local_position_history'],
                      key=lambda row: float(row['wall_elapsed_s']))
    if not commands or not px4_rows:
        raise ValueError('historical_heading_samples_missing')
    wall_times = [float(row['wall_elapsed_s']) for row in px4_rows]
    errors = []
    for command in commands:
        wall = float(command['wall_elapsed_s'])
        index = bisect.bisect_left(wall_times, wall)
        candidates = [i for i in (index - 1, index) if 0 <= i < len(px4_rows)]
        nearest = min(candidates, key=lambda i: abs(wall_times[i] - wall))
        row = px4_rows[nearest]
        actual_enu_yaw = math.atan2(
            math.sin(math.pi / 2 - float(row['heading'])),
            math.cos(math.pi / 2 - float(row['heading'])))
        error = math.atan2(math.sin(actual_enu_yaw - target_yaw),
                           math.cos(actual_enu_yaw - target_yaw))
        errors.append((abs(error), abs(wall_times[nearest] - wall)))
    maximum = max(errors, key=lambda item: item[0])
    return {
        'source_run_id': 'n08-cancel-translation-prescan-20261026-294',
        'source_evidence': 'progress/evidence/n08-cancel-stop-qualified-replay-20261026-294.md',
        'measurement': 'PX4 local NED heading converted to ENU, paired by nearest recorded wall time to the goal PositionCommand; max absolute difference from requested yaw',
        'goal_id': goal_id,
        'command_samples': len(commands),
        'maximum_absolute_error_rad': maximum[0],
        'maximum_pairing_wall_gap_s': maximum[1],
        'selected_trial_geometry_bound_rad': 0.019,
    }


def audit(run_dir):
    run_dir = Path(run_dir).resolve()
    map_meta_path = run_dir / 'n08-trial-ground-map.json'
    map_archive_path = run_dir / 'n08-trial-ground-map.npz'
    admission_path = run_dir / 'n08-trial-pre-enable-admission.json'
    n05_path = run_dir / 'n05-current-area/n05-live-entry-check.json'
    heading_basis_path = ROOT / 'artifacts/runs/n08-cancel-translation-prescan-20261026-294/flight.json'
    for path in (map_meta_path, map_archive_path, admission_path, n05_path,
                 heading_basis_path):
        if not path.is_file():
            raise FileNotFoundError(path)

    metadata = json.loads(map_meta_path.read_text())
    prior = json.loads(admission_path.read_text())
    n05 = json.loads(n05_path.read_text())
    start = np.asarray(prior['capsule']['start_xyz_m'], dtype=float)
    yaw = float(n05['state']['body_pose_imu_m']['yaw_rad'])
    with np.load(map_archive_path) as archive:
        occupancy = np.asarray(archive['occupancy'])
    snapshot = {
        'occupancy': occupancy,
        'origin_m': metadata['origin_m'],
        'resolution_m': metadata['resolution_m'],
        'dimensions_xyz': metadata.get('shape', occupancy.shape),
    }
    policy = load_policy(ROOT)
    primitives = collision_primitives(ROOT)
    body_radius = float(policy['spatial_budget']['body_reference_clearance_radius_m'])
    tests = {}
    for name, distance in (('single_goal_forward_0p6m', 0.6),
                           ('motion_cancel_stop_0p5m', 0.5)):
        tests[name] = certify_forward_trial_corridor(
            snapshot, start, [distance, 0.0, 0.0], body_radius,
            tracking_margin=0.25, maximum_tracking_error=0.15,
            extension=0.0, step=0.025, yaw_rad=yaw,
            policy=policy, primitives=primitives)

    old_forward = prior['capsule']
    old_cancel = prior.get('cancel_stop_envelope', {})
    baseline = {
        'sphere_goal_first_query': old_forward.get('queries', [{}])[0],
        'sphere_cancel_start_hold': old_cancel.get('start_hold'),
        'sphere_cancel_first_query': old_cancel.get('queries', [{}])[0],
        'sphere_cancel_terminal_hold': old_cancel.get('terminal_hold'),
    }
    return {
        'schema': 'n08-forward-reachable-geometry-audit/v1',
        'scope': 'offline raw-map geometry replay only; no live admission, goal, enable, control, or flight',
        'run_id': run_dir.name,
        'map_identity': {
            'epoch': metadata['epoch'], 'map_id': metadata['map_id'],
            'frame_id': metadata['frame_id'],
        },
        'map_geometry': {
            'origin_m': metadata['origin_m'],
            'resolution_m': metadata['resolution_m'],
            'dimensions_xyz': list(occupancy.shape),
            'raw_codes': sorted(int(v) for v in np.unique(occupancy)),
        },
        'start_xyz_m': start.tolist(),
        'yaw_rad': yaw,
        'historical_heading_basis': historical_heading_basis(heading_basis_path),
        'unchanged_limits': {
            'spatial_uncertainty_margin_m': policy['spatial_budget']['combined_uncertainty_margin_m'],
            'tracking_margin_m': 0.25,
            'maximum_tracking_error_m': 0.15,
            'reference_tube_lateral_vertical_m': 0.05,
            'initial_reverse_allowance_m': 0.005,
            'maximum_sample_spacing_m': 0.025,
            'fixed_heading_deviation_bound_rad': 0.019,
            'fixed_heading_bound_basis': (
                'N08 #294 PX4 local heading versus requested yaw maximum absolute error '
                '0.0155451539 rad; 0.019 rad is the geometry/query and runtime watchdog bound'),
            'unknown_occupied_outside_map_rejected': True,
        },
        'baseline_spherical_gate': baseline,
        'exact_shape_replay': tests,
        'all_exact_queries_reject_unknown_and_occupied': all(
            result['passed']
            and result['start_hold']['unknown_count'] == 0
            and result['start_hold']['occupied_count'] == 0
            and result['terminal_hold']['unknown_count'] == 0
            and result['terminal_hold']['occupied_count'] == 0
            and all(query['unknown_count'] == 0 and query['occupied_count'] == 0
                    for query in result['queries'])
            for result in tests.values()),
        'input_sha256': {
            str(path.relative_to(ROOT)): sha256(path)
            for path in (map_meta_path, map_archive_path, admission_path, n05_path,
                         heading_basis_path,
                         ROOT / 'tools/n08_trial_gate.py',
                         ROOT / 'tools/run_n08_braking_trial.py',
                         ROOT / 'tools/n05_entry.py',
                         ROOT / 'config/components/mapping/n08_low_speed_trial.json',
                         ROOT / 'config/components/navigation/n08_forward_braking_trial_goal.json',
                         ROOT / 'config/components/navigation/vehicle_envelope.json',
                         ROOT / 'simulation/models/x500_d435i/model.sdf',
                         ROOT / 'simulation/models/d435i/model.sdf',
                         ROOT / 'external/PX4-Autopilot/Tools/simulation/gz/models/x500_base/model.sdf')
        },
        'flight_qualification': False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, default=ROOT / 'artifacts/runs/n08-cancel-highspeed-prescan-20261026-305')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = audit(args.run_dir)
    serialized = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized)
    print(json.dumps({
        'run_id': result['run_id'],
        'all_exact_queries_reject_unknown_and_occupied': result['all_exact_queries_reject_unknown_and_occupied'],
        'cases': {name: {
            'passed': case['passed'],
            'query_count': case['required_queries'],
            'unknown_count': (case['start_hold']['unknown_count']
                              + case['terminal_hold']['unknown_count']
                              + sum(row['unknown_count'] for row in case['queries'])),
            'occupied_count': (case['start_hold']['occupied_count']
                               + case['terminal_hold']['occupied_count']
                               + sum(row['occupied_count'] for row in case['queries'])),
            'reachable_center_bound_m': case['reachable_center_bound_m'],
            'available_center_bound_m': case['available_center_bound_m'],
        } for name, case in result['exact_shape_replay'].items()},
        'flight_qualification': False,
        'output': str(args.output) if args.output else None,
    }, indent=2))


if __name__ == '__main__':
    main()
