#!/usr/bin/env python3
"""List fully-contained raw-free voxels from an archived N10 box snapshot.

This is an offline geometry diagnostic. It reads archived map/truth-derived
alignment metadata but does not connect to ROS, Gazebo, or vehicle control.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate_n10_occupancy_snapshot import (  # noqa: E402
    box_local,
    voxel_centers,
    voxel_cells_fully_inside_box,
)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def face_margins_for_cell(index, origin, resolution, rotation, translation,
                          center_world, size_xyz, yaw_rad):
    center_odom = np.asarray(origin, dtype=float) + (
        np.asarray(index, dtype=float) + 0.5) * float(resolution)
    signs = np.asarray([
        [sx, sy, sz]
        for sx in (-1.0, 1.0)
        for sy in (-1.0, 1.0)
        for sz in (-1.0, 1.0)
    ])
    corners_odom = center_odom[None, :] + signs * (float(resolution) / 2.0)
    corners_world = corners_odom @ np.asarray(rotation, dtype=float).T + np.asarray(
        translation, dtype=float)[None, :]
    corners_local = box_local(corners_world, center_world, yaw_rad)
    half = np.asarray(size_xyz, dtype=float) / 2.0
    margins = {
        'x_negative': float(np.min(corners_local[:, 0] + half[0])),
        'x_positive': float(np.min(half[0] - corners_local[:, 0])),
        'y_negative': float(np.min(corners_local[:, 1] + half[1])),
        'y_positive': float(np.min(half[1] - corners_local[:, 1])),
        'z_negative': float(np.min(corners_local[:, 2] + half[2])),
        'z_positive': float(np.min(half[2] - corners_local[:, 2])),
    }
    return center_odom, corners_local, margins


def analyze(run):
    run = Path(run).resolve()
    snapshot_dir = run / 'n10-map-snapshot'
    metadata_path = snapshot_dir / 'metadata.json'
    archive_path = snapshot_dir / 'occupancy_snapshot.npz'
    analysis_path = run / 'n10-box-map-snapshot-analysis.json'
    arrival_path = run / 'arrival-evaluation-simtime-v2.json'
    observation_path = run / 'n10-live-obstacle-observation.json'
    capture_path = run / 'n10-sensor-capture.json'
    required = (metadata_path, archive_path, analysis_path, arrival_path,
                observation_path, capture_path)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError('missing archived inputs: ' + ', '.join(missing))

    metadata = json.loads(metadata_path.read_text())
    analysis = json.loads(analysis_path.read_text())
    arrival = json.loads(arrival_path.read_text())
    observation = json.loads(observation_path.read_text())
    capture = json.loads(capture_path.read_text())
    if metadata.get('archive', {}).get('sha256') != sha256(archive_path):
        raise ValueError('snapshot array SHA-256 does not match metadata')
    if metadata.get('epoch') != observation.get('epoch') or metadata.get('map_id') != observation.get('map_id_at_goal'):
        raise ValueError('snapshot and live obstacle observer identities differ')
    if not analysis.get('snapshot_matches_live_observer_epoch_map_frame'):
        raise ValueError('existing snapshot analysis does not confirm observer identity')

    with np.load(archive_path, allow_pickle=False) as archive:
        occupancy = np.asarray(archive['occupancy'], dtype=np.int8)
    origin = np.asarray(metadata['origin_m'], dtype=float)
    resolution = float(metadata['resolution_m'])
    rotation = np.asarray(arrival['ground_rotation'], dtype=float)
    translation = np.asarray(arrival['ground_translation'], dtype=float)
    center_world = np.asarray(observation['obstacle']['pose_world_xyz_m'], dtype=float)
    size_xyz = np.asarray(observation['obstacle']['size_xyz_m'], dtype=float)
    yaw_rad = float(observation['obstacle'].get('yaw_rad', 0.0))

    free_indices = np.argwhere(occupancy == 0)
    free_centers_odom = voxel_centers(free_indices, origin, resolution)
    free_centers_world = free_centers_odom @ rotation.T + translation
    free_centers_local = box_local(free_centers_world, center_world, yaw_rad)
    half = size_xyz / 2.0
    centers_inside = np.all(np.abs(free_centers_local) <= half[None, :] + 1e-9,
                             axis=1)
    candidate_indices = free_indices[centers_inside]
    fully_inside = voxel_cells_fully_inside_box(
        candidate_indices, origin, resolution, rotation, translation,
        center_world, size_xyz, yaw_rad)

    records = []
    for index in candidate_indices[fully_inside]:
        center_odom, corners_local, margins = face_margins_for_cell(
            index, origin, resolution, rotation, translation,
            center_world, size_xyz, yaw_rad)
        center_world_cell = center_odom @ rotation.T + translation
        center_local = box_local(center_world_cell[None, :], center_world,
                                 yaw_rad)[0]
        records.append({
            'cell_index_xyz': [int(value) for value in index],
            'center_odom_m': center_odom.tolist(),
            'center_world_m': center_world_cell.tolist(),
            'center_box_local_m': center_local.tolist(),
            'minimum_voxel_volume_margin_to_each_box_face_m': margins,
            'minimum_full_cell_interior_margin_m': min(margins.values()),
            'all_corners_inside': bool(np.all(np.abs(corners_local) <= half[None, :] + 1e-9)),
        })
    records.sort(key=lambda row: row['cell_index_xyz'])
    if len(records) != int(analysis['snapshot_roi']['voxel_cell_geometry']
                            ['all_corners_inside_box_counts_by_raw_class']['known_free']):
        raise ValueError('cell-level count disagrees with archived occupancy analysis')

    depth_frames = [row for row in observation.get('depth_and_color_frames', [])
                    if row.get('topic') == '/sensors/d435i/depth']
    sensor_topics = capture.get('topics', {})
    depth_capture_recorded = any(
        isinstance(value, dict) and value.get('topic') == '/sensors/d435i/depth'
        for value in sensor_topics.values())
    return {
        'schema': 'n10-occluded-free-cell-attribution/v1',
        'run_id': run.name,
        'classification': 'offline voxel geometry/source-availability diagnostic; no runtime effect',
        'identity': {key: metadata.get(key) for key in ('epoch', 'map_id', 'frame_id')},
        'snapshot_source_coverage': analysis.get('snapshot_source_coverage'),
        'injection_sim_ns': observation.get('actual_injection_request_sim_ns'),
        'first_roi_point_cloud_stamp_ns': next((
            row.get('header_stamp_ns') for row in observation.get(
                'occupied_cloud_roi_observations', [])
            if row.get('obstacle_roi_point_count', 0) > 0), None),
        'fully_contained_raw_free_cell_count': len(records),
        'cells': records,
        'spatial_summary': {
            'unique_x_indices': sorted({row['cell_index_xyz'][0] for row in records}),
            'unique_y_indices': sorted({row['cell_index_xyz'][1] for row in records}),
            'unique_z_indices': sorted({row['cell_index_xyz'][2] for row in records}),
            'minimum_full_cell_interior_margin_m': min(
                (row['minimum_full_cell_interior_margin_m'] for row in records),
                default=None),
            'maximum_full_cell_interior_margin_m': max(
                (row['minimum_full_cell_interior_margin_m'] for row in records),
                default=None),
        },
        'depth_source_availability': {
            'depth_topic_in_full_sensor_bag': depth_capture_recorded,
            'full_sensor_bag_topics': sorted(
                value.get('topic') for value in sensor_topics.values()
                if isinstance(value, dict) and value.get('topic')),
            'selected_depth_frame_count': len(depth_frames),
            'selected_depth_frame_stamps_ns': [row.get('stamp_ns') for row in depth_frames],
            'pre_injection_depth_frame_count': sum(
                row.get('stamp_ns', 0) < observation.get('actual_injection_request_sim_ns', 0)
                for row in depth_frames),
            'qualification': 'The full sensor bag has no depth topic. Sparse diagnostic depth images do not provide per-cell pre/post update history.'
        },
        'source_code_semantics': {
            'occupancy_model': 'bounded log-odds updates for raycast hits/misses',
            'per_voxel_last_update_stamp_available': False,
            'time_decay_for_unobserved_voxels_found': False,
            'interpretation': 'prior free log-odds may persist when later rays terminate at the newly inserted obstacle surface; this is plausible but not proven for these cells'
        },
        'inputs_sha256': {
            str(path.relative_to(run)): sha256(path)
            for path in (metadata_path, archive_path, analysis_path, arrival_path,
                         observation_path, capture_path)
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = analyze(args.run)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({
        'run_id': report['run_id'],
        'fully_contained_raw_free_cell_count': report['fully_contained_raw_free_cell_count'],
        'minimum_full_cell_interior_margin_m': report['spatial_summary'][
            'minimum_full_cell_interior_margin_m'],
        'full_sensor_bag_has_depth_topic': report['depth_source_availability'][
            'depth_topic_in_full_sensor_bag'],
    }))


if __name__ == '__main__':
    main()
