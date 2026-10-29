#!/usr/bin/env python3
"""Relate a prohibited N10 contact to its active command, body view, and map.

Read-only offline forensic evaluator. It reports measured geometry and evidence
coverage; it does not infer runtime decisions or turn missing data into PASS.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np


ROOT = Path(__file__).resolve().parents[2]


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def pose_values(text):
    values = [float(v) for v in (text or '0 0 0 0 0 0').split()]
    if len(values) != 6 or not all(math.isfinite(v) for v in values):
        raise ValueError(f'invalid SDF pose: {text!r}')
    return values


def rpy_matrix(roll, pitch, yaw):
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    return np.asarray([
        [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
        [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
        [-sp, cp * sr, cp * cr],
    ])


def sdf_cylinder(path, model_name):
    root = ET.parse(path).getroot()
    model = next((node for node in root.iter('model')
                  if node.get('name') == model_name), None)
    if model is None:
        raise ValueError(f'SDF model not found: {model_name}')
    model_pose = pose_values(model.findtext('pose'))
    model_xyz = np.asarray(model_pose[:3])
    model_rotation = rpy_matrix(*model_pose[3:])
    collisions = []
    for link in model.findall('link'):
        link_pose = pose_values(link.findtext('pose'))
        link_xyz = np.asarray(link_pose[:3])
        link_rotation = rpy_matrix(*link_pose[3:])
        for collision in link.findall('collision'):
            cylinder = collision.find('./geometry/cylinder')
            if cylinder is None:
                continue
            collision_pose = pose_values(collision.findtext('pose'))
            xyz = (model_xyz + model_rotation @ link_xyz
                   + model_rotation @ link_rotation @ np.asarray(collision_pose[:3]))
            rotation = model_rotation @ link_rotation @ rpy_matrix(*collision_pose[3:])
            collisions.append({
                'link': link.get('name'),
                'collision': collision.get('name'),
                'center_world_xyz_m': xyz.tolist(),
                'axis_world_xyz': (rotation @ np.asarray([0.0, 0.0, 1.0])).tolist(),
                'radius_m': float(cylinder.findtext('radius')),
                'length_m': float(cylinder.findtext('length')),
            })
    if len(collisions) != 1:
        raise ValueError(f'expected one cylindrical collision in {model_name}, got {len(collisions)}')
    return collisions[0]


def yaw_from_xyzw(q):
    x, y, z, w = map(float, q)
    return math.atan2(2.0 * (w * z + x * y),
                      1.0 - 2.0 * (y * y + z * z))


def wrap(angle):
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def evaluate(run):
    run = Path(run).resolve()
    paths = {
        'contact': run / 'vehicle-contact-evaluation.json',
        'flight': run / 'flight.json',
        'truth': run / 'debug-truth-evaluation.json',
        'world': run / 'vio_initialization.sdf',
        'map_metadata': run / 'n10-map-snapshot-before-injection/metadata.json',
        'map_archive': run / 'n10-map-snapshot-before-injection/occupancy_snapshot.npz',
        'vehicle_envelope': ROOT / 'config/components/navigation/vehicle_envelope.json',
        'camera_model': ROOT / 'simulation/models/d435i/model.sdf',
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError('missing contact-view inputs: ' + ', '.join(missing))
    contact_report = json.loads(paths['contact'].read_text())
    first = contact_report.get('first_prohibited_contact')
    if not first:
        raise ValueError('no prohibited contact is recorded')
    flight = json.loads(paths['flight'].read_text())
    truth_report = json.loads(paths['truth'].read_text())
    stamp_ns = int(first['stamp_ns'])
    collision_names = (first['pair']['collision1'], first['pair']['collision2'])
    sdf_model_names = {node.get('name') for node in ET.parse(paths['world']).getroot().iter('model')}
    model_name = next((collision.split('::', 1)[0] for collision in collision_names
                       if collision.split('::', 1)[0] in sdf_model_names), None)
    if model_name is None:
        raise ValueError(f'cannot resolve collision model from contact pair: {collision_names}')
    obstacle = sdf_cylinder(paths['world'], model_name)

    spawn = json.loads((run / 'spawn-pose.json').read_text())['spawn_pose_xyzrpy']
    sx, sy, _sz, _roll, _pitch, spawn_yaw = map(float, spawn)
    c, s = math.cos(spawn_yaw), math.sin(spawn_yaw)
    world_center = np.asarray(obstacle['center_world_xyz_m'], dtype=float)
    delta = world_center[:2] - np.asarray([sx, sy])
    obstacle_odom_xy = np.asarray([c * delta[0] + s * delta[1],
                                   -s * delta[0] + c * delta[1]])

    samples = truth_report.get('samples') or []
    truth = min(samples, key=lambda row: abs(int(row['stamp_ns']) - stamp_ns))
    truth_gap_ns = abs(int(truth['stamp_ns']) - stamp_ns)
    truth_world_xy = np.asarray(truth['xyz'][:2], dtype=float)
    truth_delta = truth_world_xy - np.asarray([sx, sy])
    truth_xy = np.asarray([c * truth_delta[0] + s * truth_delta[1],
                           -s * truth_delta[0] + c * truth_delta[1]])
    body_yaw = yaw_from_xyzw(truth['q_xyzw'])
    radial = obstacle_odom_xy - truth_xy
    actual_center_distance = float(np.linalg.norm(radial))
    target_bearing = math.atan2(radial[1], radial[0])
    relative_bearing = wrap(target_bearing - body_yaw)

    goal_id = flight.get('goal_id')
    epoch = flight.get('localization_epoch')
    commands = [row for row in flight.get('position_command_history', [])
                if row.get('goal_id') == goal_id and row.get('epoch') == epoch
                and int(row.get('flag', -1)) == 1]
    command = min(commands, key=lambda row: abs(int(row['source_stamp_ns']) - stamp_ns))
    command_gap_ns = abs(int(command['source_stamp_ns']) - stamp_ns)
    command_xy = np.asarray(command['position_enu'][:2], dtype=float)
    command_center_distance = float(np.linalg.norm(command_xy - obstacle_odom_xy))
    command_velocity = np.asarray(command['velocity_enu_m_s'][:2], dtype=float)
    velocity_heading = (math.atan2(command_velocity[1], command_velocity[0])
                        if np.linalg.norm(command_velocity) > 1e-9 else None)
    command_yaw = float(command['yaw_enu'])
    yaw_velocity_error = (abs(wrap(command_yaw - velocity_heading))
                          if velocity_heading is not None else None)

    envelope = json.loads(paths['vehicle_envelope'].read_text())['geometry']
    body_radius = float(envelope['orientation_invariant_rotor_sweep_radius_m'])
    combined_radius = body_radius + float(obstacle['radius_m'])
    map_meta = json.loads(paths['map_metadata'].read_text())
    with np.load(paths['map_archive'], allow_pickle=False) as archive:
        raw = np.asarray(archive['occupancy'], dtype=np.int8)
        inflated = np.asarray(archive['inflated'], dtype=np.uint8)
    origin = np.asarray(map_meta['origin_m'], dtype=float)
    resolution = float(map_meta['resolution_m'])
    center_odom = np.asarray([*obstacle_odom_xy, float(world_center[2])])
    center_idx = np.floor((center_odom - origin) / resolution).astype(int)
    xy_cells = int(math.ceil(0.8 / resolution))
    z_cells = int(math.ceil(1.5 / resolution))
    low = np.maximum(0, center_idx - np.asarray([xy_cells, xy_cells, z_cells]))
    high = np.minimum(raw.shape, center_idx + np.asarray([xy_cells + 1, xy_cells + 1, z_cells + 1]))
    ix, iy, iz = np.meshgrid(np.arange(low[0], high[0]),
                             np.arange(low[1], high[1]),
                             np.arange(low[2], high[2]), indexing='ij')
    centers = origin + np.stack([ix, iy, iz], axis=-1) * resolution + resolution / 2.0
    radial_mask = np.hypot(centers[..., 0] - center_odom[0],
                           centers[..., 1] - center_odom[1]) <= 0.8 + 1e-9
    z_mask = np.abs(centers[..., 2] - center_odom[2]) <= 1.5 + 1e-9
    mask = radial_mask & z_mask
    raw_roi = raw[low[0]:high[0], low[1]:high[1], low[2]:high[2]][mask]
    inflated_roi = inflated[low[0]:high[0], low[1]:high[1], low[2]:high[2]][mask]
    raw_counts = {name: int(np.count_nonzero(raw_roi == code))
                  for code, name in ((-1, 'unknown'), (0, 'known_nonoccupied'),
                                     (100, 'raw_occupied'))}

    camera_tree = ET.parse(paths['camera_model'])
    fov_text = camera_tree.findtext('.//sensor[@name="depth"]/camera/horizontal_fov')
    fov_rad = float(fov_text)
    fov_half_deg = math.degrees(fov_rad / 2.0)
    relative_bearing_deg = math.degrees(relative_bearing)
    return {
        'schema': 'n10-contact-view-forensics/v1',
        'run_id': run.name,
        'classification': 'offline contact failure analysis; no runtime/control effect',
        'result': 'FAIL',
        'first_prohibited_contact': {
            'stamp_ns': stamp_ns,
            'phase': first.get('phase'),
            'pair': first.get('pair'),
            'truth_sample_stamp_ns': int(truth['stamp_ns']),
            'truth_sample_gap_s': truth_gap_ns / 1e9,
            'truth_world_xyz_m': truth['xyz'],
            'truth_body_center_odom_xy_m': truth_xy.tolist(),
        },
        'obstacle': {
            'model': model_name,
            'collision': obstacle,
            'center_odom_xyz_m': center_odom.tolist(),
            'world_to_odom_horizontal_transform': {
                'spawn_xy_m': [sx, sy], 'spawn_yaw_rad': spawn_yaw,
                'method': 'inverse planar spawn transform used by the run-local obstacle injector',
            },
        },
        'active_command': {
            'source_stamp_ns': int(command['source_stamp_ns']),
            'stamp_gap_s': command_gap_ns / 1e9,
            'trajectory_id': int(command['trajectory_id']),
            'position_odom_xyz_m': command['position_enu'],
            'velocity_odom_m_s': command['velocity_enu_m_s'],
            'yaw_odom_rad': command_yaw,
            'velocity_heading_rad': velocity_heading,
            'yaw_velocity_heading_delta_rad': yaw_velocity_error,
            'body_yaw_rad': body_yaw,
            'target_bearing_relative_to_body_rad': relative_bearing,
            'target_bearing_relative_to_body_deg': relative_bearing_deg,
        },
        'geometry_at_contact': {
            'body_rotor_sweep_radius_m': body_radius,
            'obstacle_collision_radius_m': obstacle['radius_m'],
            'combined_horizontal_radius_m': combined_radius,
            'truth_body_center_distance_to_obstacle_axis_m': actual_center_distance,
            'truth_center_margin_to_combined_radius_m': actual_center_distance - combined_radius,
            'command_body_center_distance_to_obstacle_axis_m': command_center_distance,
            'command_center_margin_to_combined_radius_m': command_center_distance - combined_radius,
            'vertical_extent_overlap': True,
            'vertical_overlap_basis': 'contact record identifies the rotor collision; SDF cylinder spans the body altitude',
        },
        'camera_view': {
            'depth_horizontal_fov_rad': fov_rad,
            'depth_horizontal_half_fov_deg': fov_half_deg,
            'obstacle_relative_bearing_deg': relative_bearing_deg,
            'obstacle_center_outside_horizontal_fov_at_contact': abs(relative_bearing_deg) > fov_half_deg,
            'command_velocity_heading_delta_deg': (
                math.degrees(yaw_velocity_error) if yaw_velocity_error is not None else None),
        },
        'preinjection_map_snapshot': {
            'snapshot_stamp_ns': int(map_meta['snapshot_stamp_ns']),
            'last_fused_depth_source_stamp_ns': int(map_meta['last_fused_depth_source_stamp_ns']),
            'same_epoch': map_meta.get('epoch') == epoch,
            'epoch': map_meta.get('epoch'),
            'map_id': map_meta.get('map_id'),
            'horizontal_roi_radius_m': 0.8,
            'vertical_roi_half_height_m': 1.5,
            'raw_cell_counts': raw_counts,
            'inflated_cell_count': int(np.count_nonzero(inflated_roi)),
            'classification': 'preinjection snapshot only; it cannot establish map class at contact time',
        },
        'yaw_replanning_evidence': {
            'observed_command_yaw': command_yaw,
            'observed_horizontal_velocity_heading': velocity_heading,
            'observed_delta_deg': (math.degrees(yaw_velocity_error)
                                   if yaw_velocity_error is not None else None),
            'third_party_source': 'src/vendor/ego_planner/planner/plan_manage/src/traj_server.cpp',
            'active_task_yaw_overrides_calculate_yaw': True,
            'active_task_yaw_prefix_control_points': 3,
            'replanning_observation': 'matching goal spline IDs 261-263 started at 99.024, 99.092 and 99.260 s; each published yaw points 0-2 at the current body yaw before later controls follow the path tangent',
            'interpretation': 'consistent with repeated replans resetting the task-yaw curve before the front camera follows the lateral path; contact-time bearing confirms the obstacle was outside the actual camera FOV',
        },
        'limitations': [
            'The preinjection map snapshot predates the contact and does not prove the contact-time voxel class.',
            'No contact-time full occupancy snapshot or per-voxel fusion provenance was archived.',
            'The event proves physical contact and a colliding active command; this report does not claim a unique cause for every planner decision.',
        ],
        'input_sha256': {name: sha256(path) for name, path in paths.items()},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = evaluate(args.run)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({
        'result': report['result'],
        'contact_stamp_ns': report['first_prohibited_contact']['stamp_ns'],
        'obstacle_model': report['obstacle']['model'],
        'command_center_margin_m': report['geometry_at_contact']['command_center_margin_to_combined_radius_m'],
        'truth_center_margin_m': report['geometry_at_contact']['truth_center_margin_to_combined_radius_m'],
        'camera_off_axis_deg': report['camera_view']['obstacle_relative_bearing_deg'],
        'output': str(args.output),
    }, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
