#!/usr/bin/env python3
"""Compare one EGO occupancy cloud with the known calibration wall offline."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from evaluate_vins_motion import evaluate


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate_map(world_path, motion_path, odometry_path, cloud_path, session_path):
    motion = json.loads(motion_path.read_text())
    odometry = json.loads(odometry_path.read_text())
    cloud = json.loads(cloud_path.read_text())
    session = json.loads(session_path.read_text())
    expected_frame = f"odom_{session['epoch']}"
    if cloud['frame_id'] != expected_frame:
        raise ValueError(f"Map frame {cloud['frame_id']} does not match session frame {expected_frame}")

    sdf = ET.parse(world_path).getroot()
    wall = sdf.find("world/model[@name='calibration_wall']")
    pose = [float(v) for v in wall.findtext('pose').split()]
    size = [float(v) for v in wall.find('link/collision/geometry/box/size').text.split()]
    if any(abs(v) > 1e-8 for v in pose[3:]):
        raise ValueError('This evaluator requires the calibration wall to be axis-aligned')
    wall_faces_x = [pose[0] - size[0] / 2, pose[0] + size[0] / 2]

    map_points = np.asarray(cloud['points'], dtype=float)
    if map_points.ndim != 2 or map_points.shape[1] != 3 or len(map_points) < 3:
        raise ValueError('Map cloud must contain at least three xyz points')
    if not np.isfinite(map_points).all():
        raise ValueError('Map cloud contains non-finite points')

    trajectory = evaluate(motion, odometry)
    rotation = np.asarray(trajectory['alignment_rotation'], dtype=float)
    translation = np.asarray(trajectory['alignment_translation'], dtype=float)
    world_points = (rotation @ map_points.T).T + translation
    distances = np.min(np.abs(world_points[:, 0, None] - np.asarray(wall_faces_x)[None, :]), axis=1)
    map_stamp_ns = int(cloud['stamp_ns'])
    optimized_stamps = np.asarray([int(row['stamp_ns']) for row in odometry['optimized']], dtype=np.int64)
    clock_start_ns, clock_end_ns = (int(round(value * 1e9)) for value in motion['clock'])
    return {
        'scope': 'Exploratory offline EGO occupancy-to-SDF wall comparison; not a frozen acceptance test',
        'alignment': trajectory['alignment'],
        'trajectory': {
            'paired_samples': trajectory['paired_samples'],
            'position_rmse_m': trajectory['position_rmse_m'],
            'position_p95_m': trajectory['position_p95_m'],
            'position_max_m': trajectory['position_max_m'],
            'orientation_rmse_deg': trajectory['orientation_rmse_deg'],
        },
        'map_cloud': {
            'point_count': int(len(map_points)),
            'frame_id': cloud['frame_id'],
            'header_stamp_ns': map_stamp_ns,
            'header_stamp_uses_sim_time': clock_start_ns <= map_stamp_ns <= clock_end_ns,
            'nearest_optimized_odometry_stamp_delta_s': float(np.min(np.abs(optimized_stamps - map_stamp_ns)) * 1e-9),
            'world_bounds_xyz_m': np.column_stack((world_points.min(axis=0), world_points.max(axis=0))).tolist(),
        },
        'reference_wall': {
            'source_world': str(world_path),
            'center_pose': pose,
            'box_size_m': size,
            'visible_face_x_m': wall_faces_x,
        },
        'nearest_wall_face_abs_residual_m': {
            'median': float(np.median(distances)),
            'p95': float(np.percentile(distances, 95)),
            'maximum': float(distances.max()),
            'fraction_within_0_10m': float(np.mean(distances <= 0.10)),
        },
        'provenance': {
            'world_sha256': sha256(world_path),
            'motion_sha256': sha256(motion_path),
            'odometry_sha256': sha256(odometry_path),
            'map_cloud_sha256': sha256(cloud_path),
            'session_sha256': sha256(session_path),
        },
        'limitations': [
            'The only alignment is the single rigid SE(3) trajectory alignment; map points do not influence the alignment.',
            'The probe selects the largest occupancy PointCloud2 observed during one run, not a persistent map snapshot.',
            'This compares distance to the two x faces of one planar wall and does not score coverage, unknown/free classification, inflation, obstacle clearance, or planner response.',
            'The publication stamp is checked against the recorded simulation clock and optimized odometry time range; mapping latency is not separately measured.',
            'No acceptance thresholds are frozen; these values are descriptive only.',
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--world', type=Path, required=True)
    parser.add_argument('--motion', type=Path, required=True)
    parser.add_argument('--odometry', type=Path, required=True)
    parser.add_argument('--map-cloud', type=Path, required=True)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = evaluate_map(args.world, args.motion, args.odometry, args.map_cloud, args.session)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
