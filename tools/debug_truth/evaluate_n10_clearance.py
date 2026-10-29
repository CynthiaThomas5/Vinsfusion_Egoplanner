#!/usr/bin/env python3
"""Offline sampled clearance lower bound from Gazebo truth and the loaded SDF."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from truth_reference import imu_truth_samples, require_same_truth_reference


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def pose(node):
    values = [float(value) for value in (node.findtext('pose') or '0 0 0 0 0 0').split()]
    if len(values) != 6 or not np.isfinite(values).all():
        raise ValueError('unsupported_or_invalid_sdf_pose')
    x, y, z, roll, pitch, yaw = values
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    rx = np.array([[1, 0, 0], [0, cr, -sr], [0, sr, cr]], dtype=float)
    ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]], dtype=float)
    rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1]], dtype=float)
    matrix = np.eye(4)
    matrix[:3, :3] = rz @ ry @ rx
    matrix[:3, 3] = [x, y, z]
    return matrix


def parse_obstacles(sdf_path):
    root = ET.parse(sdf_path).getroot()
    world = root.find('world')
    if world is None:
        raise ValueError('SDF has no world element')
    obstacles = []
    skipped = []
    for model in world.findall('model'):
        model_name = model.get('name') or 'unnamed_model'
        model_pose = pose(model)
        for link in model.findall('link'):
            link_pose = model_pose @ pose(link)
            for collision in link.findall('collision'):
                geometry = collision.find('geometry')
                if geometry is None or len(geometry) != 1:
                    raise ValueError(f'unsupported SDF collision geometry in {model_name}')
                shape = geometry[0]
                collision_pose = link_pose @ pose(collision)
                center = (collision_pose @ np.array([0.0, 0.0, 0.0, 1.0]))[:3]
                rotation = collision_pose[:3, :3]
                collision_name = collision.get('name') or 'unnamed_collision'
                if shape.tag == 'cylinder':
                    radius = float(shape.findtext('radius'))
                    length = float(shape.findtext('length'))
                    axis_z = rotation[:, 2]
                    if abs(abs(float(axis_z[2])) - 1.0) > 1e-6:
                        raise ValueError(f'nonvertical cylinder unsupported: {model_name}/{collision_name}')
                    obstacles.append({
                        'name': model_name + '/' + link.get('name', '') + '/' + collision_name,
                        'kind': 'vertical_cylinder', 'center_xyz_m': center.tolist(),
                        'radius_m': radius,
                        'z_min_m': float(center[2] - length / 2.0),
                        'z_max_m': float(center[2] + length / 2.0),
                    })
                elif shape.tag == 'box':
                    sizes = np.asarray([float(value) for value in shape.findtext('size').split()], dtype=float)
                    local_z = rotation[:, 2]
                    if len(sizes) != 3 or abs(abs(float(local_z[2])) - 1.0) > 1e-6:
                        raise ValueError(f'nonvertical box unsupported: {model_name}/{collision_name}')
                    yaw = math.atan2(float(rotation[1, 0]), float(rotation[0, 0]))
                    obstacles.append({
                        'name': model_name + '/' + link.get('name', '') + '/' + collision_name,
                        'kind': 'vertical_box', 'center_xyz_m': center.tolist(),
                        'size_xyz_m': sizes.tolist(), 'yaw_rad': yaw,
                        'z_min_m': float(center[2] - sizes[2] / 2.0),
                        'z_max_m': float(center[2] + sizes[2] / 2.0),
                    })
                elif shape.tag == 'plane':
                    skipped.append({'name': model_name + '/' + collision_name,
                                    'kind': 'plane', 'reason': 'ground contact excluded from obstacle clearance'})
                else:
                    raise ValueError(f'unsupported static collision shape {shape.tag} in {model_name}/{collision_name}')
    return obstacles, skipped


def physics_step_seconds(sdf_path):
    root = ET.parse(sdf_path).getroot()
    world = root.find('world')
    value = world.findtext('physics/max_step_size') if world is not None else None
    if value is None:
        return None
    step = float(value)
    if not math.isfinite(step) or step <= 0.0:
        raise ValueError('invalid_world_physics_max_step_size')
    return step


def assess_physics_step_coverage(stamps_ns, physics_step_s):
    """Check timestamp alignment and whether every configured solver step appears."""
    stamps = np.asarray(stamps_ns, dtype=np.int64)
    if physics_step_s is None or len(stamps) < 2:
        return {
            'world_max_step_size_s': physics_step_s,
            'all_received_pose_gaps_within_one_physics_step': False,
            'every_consecutive_physics_state_captured': False,
            'longest_gap_in_physics_steps': None,
            'off_grid_pose_count': None,
            'classification': 'physics-step timestamp coverage unavailable',
        }
    raw_step_ns = float(physics_step_s) * 1e9
    step_ns = int(round(raw_step_ns))
    if step_ns <= 0:
        raise ValueError('physics step is below nanosecond timestamp resolution')
    gaps = np.diff(stamps)
    step_indices = np.rint(stamps.astype(np.float64) / step_ns).astype(np.int64)
    residuals = np.abs(stamps - step_indices * step_ns)
    on_grid = residuals <= 1
    index_gaps = np.diff(step_indices)
    complete = bool(np.all(on_grid) and np.all(index_gaps == 1))
    return {
        'world_max_step_size_s': float(physics_step_s),
        'physics_step_ns': step_ns,
        'all_received_pose_gaps_within_one_physics_step': bool(np.max(gaps) <= step_ns),
        'every_consecutive_physics_state_captured': complete,
        'longest_gap_in_physics_steps': float(np.max(gaps) / step_ns),
        'maximum_physics_step_index_gap': int(np.max(index_gaps)),
        'off_grid_pose_count': int(np.count_nonzero(~on_grid)),
        'one_step_gap_fraction': float(np.count_nonzero(index_gaps == 1) / len(index_gaps)),
        'classification': ('every configured Gazebo solver state recorded' if complete
                           else 'received-state cadence only; solver states are missing or off-grid'),
    }


def quaternion_rotation(q_xyzw):
    x, y, z, w = map(float, q_xyzw)
    norm = math.sqrt(x*x + y*y + z*z + w*w)
    if not math.isfinite(norm) or norm < 1e-12:
        raise ValueError('invalid truth quaternion')
    x, y, z, w = x/norm, y/norm, z/norm, w/norm
    return np.array([
        [1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
        [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
        [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)],
    ], dtype=float)


def vehicle_vertical_cylinder(position, q_xyzw, radius, zmin_local, zmax_local):
    rotation = quaternion_rotation(q_xyzw)
    axis = rotation[:, 2]
    sin_tilt = min(1.0, math.hypot(float(axis[0]), float(axis[1])))
    cos_tilt = float(axis[2])
    radial_half = float(radius) * sin_tilt
    axial_a = float(zmin_local) * cos_tilt
    axial_b = float(zmax_local) * cos_tilt
    z_min = float(position[2]) + min(axial_a, axial_b) - radial_half
    z_max = float(position[2]) + max(axial_a, axial_b) + radial_half
    z_extent = max(abs(float(zmin_local)), abs(float(zmax_local)))
    horizontal_radius = float(radius) + z_extent * sin_tilt
    return horizontal_radius, z_min, z_max, sin_tilt


def distance_to_obstacle(position, vehicle_radius, vehicle_z_min, vehicle_z_max, obstacle):
    center = np.asarray(obstacle['center_xyz_m'], dtype=float)
    if obstacle['kind'] == 'vertical_cylinder':
        horizontal_center_distance = float(np.linalg.norm(np.asarray(position[:2]) - center[:2]))
        horizontal_gap = max(0.0, horizontal_center_distance - vehicle_radius - obstacle['radius_m'])
    else:
        yaw = float(obstacle['yaw_rad'])
        delta = np.asarray(position[:2], dtype=float) - center[:2]
        c, s = math.cos(yaw), math.sin(yaw)
        local = np.array([c*delta[0] + s*delta[1], -s*delta[0] + c*delta[1]])
        half = np.asarray(obstacle['size_xyz_m'][:2], dtype=float) / 2.0
        outside = np.maximum(np.abs(local) - half, 0.0)
        point_to_box = float(np.linalg.norm(outside))
        horizontal_gap = max(0.0, point_to_box - vehicle_radius)
    vertical_gap = max(0.0, obstacle['z_min_m'] - vehicle_z_max,
                       vehicle_z_min - obstacle['z_max_m'])
    return math.hypot(horizontal_gap, vertical_gap)


def evaluate(run, envelope_path, sdf_path):
    flight = json.loads((run / 'flight.json').read_text())
    truth_report = json.loads((run / 'debug-truth-evaluation.json').read_text())
    truth, truth_contract = imu_truth_samples(run, truth_report)
    goal_start = int((flight.get('goal') or {})['source_ns'])
    bridge_rows = [json.loads(line) for line in (run / 'bridge-alignment-timeline.jsonl').read_text().splitlines()
                   if line.strip()]
    landed = [int(row['stamp_ns']) for row in bridge_rows
              if row.get('phase') == 'LANDED' and int(row['stamp_ns']) >= goal_start]
    if not landed:
        raise ValueError('no bridge LANDED source stamp after the goal start')
    goal_end = min(landed)
    rows = [row for row in truth if goal_start <= int(row['stamp_ns']) <= goal_end]
    stamps = np.asarray([int(row['stamp_ns']) for row in rows], dtype=np.int64)
    if len(rows) < 3 or np.any(np.diff(stamps) <= 0):
        raise ValueError('insufficient_or_nonmonotonic_truth_in_goal_to_landed_interval')
    gaps = np.diff(stamps) / 1e9
    positions = [np.asarray(row['xyz'], dtype=float) for row in rows]
    quaternions = [row['q_xyzw'] for row in rows]
    if not all(np.isfinite(p).all() for p in positions):
        raise ValueError('nonfinite_truth_position')
    envelope = json.loads(envelope_path.read_text())['geometry']
    bounds = envelope['collision_bounds_xyz_m']
    z_min_local = min(float(v) for v in bounds[2])
    z_max_local = max(float(v) for v in bounds[2])
    body_radius = float(envelope['orientation_invariant_rotor_sweep_radius_m'])
    obstacles, skipped = parse_obstacles(sdf_path)
    if not obstacles:
        raise ValueError('no supported non-ground SDF collision geometry found')

    best = None
    max_body_center_step = 0.0
    max_truth_gap = float(gaps.max())
    physics_step = physics_step_seconds(sdf_path)
    step_coverage = assess_physics_step_coverage(stamps, physics_step)
    for row, position, quaternion in zip(rows, positions, quaternions):
        vehicle_radius, z_min, z_max, sin_tilt = vehicle_vertical_cylinder(
            position, quaternion, body_radius, z_min_local, z_max_local)
        for obstacle in obstacles:
            clearance = distance_to_obstacle(position, vehicle_radius, z_min, z_max, obstacle)
            if best is None or clearance < best['clearance_lower_bound_m']:
                best = {
                    'clearance_lower_bound_m': clearance,
                    'truth_stamp_ns': int(row['stamp_ns']),
                    'truth_position_xyz_m': position.tolist(),
                    'obstacle': obstacle,
                    'vehicle_envelope_radius_m': vehicle_radius,
                    'vehicle_vertical_bounds_world_m': [z_min, z_max],
                    'body_tilt_sin': sin_tilt,
                }
    for left, right, q0, q1 in zip(positions[:-1], positions[1:], quaternions[:-1], quaternions[1:]):
        dot = abs(float(np.dot(np.asarray(q0, dtype=float), np.asarray(q1, dtype=float))))
        angle = 2.0 * math.acos(min(1.0, max(-1.0, dot)))
        envelope_radius_3d = math.sqrt(body_radius*body_radius + max(abs(z_min_local), abs(z_max_local))**2)
        motion = float(np.linalg.norm(right - left)) + envelope_radius_3d * angle
        max_body_center_step = max(max_body_center_step, motion)
    continuous_lower_bound = float(best['clearance_lower_bound_m']) - max_body_center_step
    return {
        'schema': 'n10-sampled-geometric-clearance/v2',
        'truth_reference_contract': truth_contract,
        'run_id': run.name,
        'classification': 'offline simulated geometry measurement; not a formal clearance qualification',
        'formal_qualification': False,
        'interval': {
            'start_source_ns': goal_start, 'start_event': 'navigation goal source stamp',
            'end_source_ns': goal_end, 'end_event': 'first bridge LANDED sample after goal start',
            'duration_sim_s': (goal_end - goal_start) / 1e9,
            'truth_samples': len(rows), 'truth_max_source_gap_sim_s': max_truth_gap,
        },
        'vehicle_geometry': {
            'source': str(envelope_path),
            'reference_frame': envelope.get('reference_frame'),
            'horizontal_rotor_sweep_radius_m': body_radius,
            'local_vertical_bounds_m': [z_min_local, z_max_local],
            'bounding_method': 'A vertical cylinder around the full yaw-swept envelope; tilt expands horizontal radius and vertical bounds using the measured truth attitude. The cylinder contains the configured collision bounds and remains conservative with respect to the idealized model envelope.',
        },
        'scene_geometry': {
            'source': str(sdf_path), 'sha256': sha256(sdf_path),
            'non_ground_collision_shapes': len(obstacles),
            'obstacle_kinds': {kind: sum(o['kind'] == kind for o in obstacles)
                               for kind in sorted({o['kind'] for o in obstacles})},
            'skipped_geometry': skipped,
        },
        'sampled_minimum': best,
        'sampling': {
            'method': 'At each truth sample, compute Euclidean distance between the attitude-expanded enclosing vehicle cylinder and every static SDF cylinder/box. Ground plane is excluded as an allowed contact surface.',
            'sampled_minimum_clearance_lower_bound_m': float(best['clearance_lower_bound_m']),
            'maximum_observed_inter_sample_envelope_motion_m': max_body_center_step,
            'sampled_continuity_allowance_lower_bound_m': continuous_lower_bound,
            'positive_lower_bound_supported': continuous_lower_bound > 0.0,
            'note': 'The inter-sample motion value uses observed endpoint motion, not a continuous dynamics certificate. A nonpositive adjusted value means this record does not establish positive between-sample clearance.'
        },
        'physics_step_sample_coverage': {
            **step_coverage,
            'minimum_clearance_at_received_states_m': float(best['clearance_lower_bound_m']),
            'positive_clearance_at_all_received_states': bool(best['clearance_lower_bound_m'] > 0.0),
            'note': 'This is a clearance check at captured solver states. It only claims every solver update when exact step-grid alignment and consecutive indices both pass; even then it is a discrete SITL result, not a continuous-time or real-aircraft bound.',
        },
        'limitations': [
            'Uses Gazebo truth and loaded collision SDF for offline evaluation only; neither is connected to control.',
            'Uses the provisional N05 orientation-invariant body envelope. It does not include unmodeled cables, brackets or manufacturing tolerances.',
            'Ground plane is omitted because ground contact is allowed during takeoff and landing.',
            'This is a simulated obstacle-clearance measurement, not a real-aircraft or final mission clearance threshold.',
        ],
        'input_sha256': {
            'flight.json': sha256(run / 'flight.json'),
            'debug-truth-evaluation.json': sha256(run / 'debug-truth-evaluation.json'),
            'bridge-alignment-timeline.jsonl': sha256(run / 'bridge-alignment-timeline.jsonl'),
            'vehicle-envelope.json': sha256(envelope_path),
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--vehicle-envelope', type=Path, default=Path('config/components/navigation/vehicle_envelope.json'))
    parser.add_argument('--world-sdf', type=Path)
    args = parser.parse_args()
    run = args.run.resolve()
    envelope = args.vehicle_envelope.resolve()
    sdf = args.world_sdf.resolve() if args.world_sdf else (run / 'vio_initialization.sdf')
    report = evaluate(run, envelope, sdf)
    output = run / 'n10-clearance-evaluation.json'
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
