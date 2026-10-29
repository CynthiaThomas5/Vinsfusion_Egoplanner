#!/usr/bin/env python3
"""Compare same-identity raw/inflated map snapshots around one obstacle insert."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


CLASS_NAMES = {-1: 'unknown', 0: 'known_free', 100: 'raw_occupied'}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _load_snapshot(run, directory):
    root = run / directory
    metadata_path = root / 'metadata.json'
    metadata = json.loads(metadata_path.read_text())
    archive_path = root / metadata['archive']['file']
    if metadata.get('schema') != 'plan-env-voxel-snapshot/v1':
        raise ValueError(f'unsupported snapshot schema: {directory}')
    if sha256(archive_path) != metadata.get('archive', {}).get('sha256'):
        raise ValueError(f'snapshot archive hash mismatch: {directory}')
    with np.load(archive_path, allow_pickle=False) as archive:
        occupancy = np.asarray(archive['occupancy'], dtype=np.int8)
        inflated = np.asarray(archive['inflated'], dtype=np.uint8)
    shape = tuple(int(value) for value in metadata['dimensions_xyz'])
    if occupancy.shape != shape or inflated.shape != shape:
        raise ValueError(f'snapshot dimensions do not match arrays: {directory}')
    if (not np.all(np.isin(occupancy, tuple(CLASS_NAMES)))
            or not np.all(np.isin(inflated, (0, 1)))):
        raise ValueError(f'invalid occupancy or inflation values: {directory}')
    return metadata, metadata_path, archive_path, occupancy, inflated


def _cell_region(metadata, center, size, yaw):
    origin = np.asarray(metadata['origin_m'], dtype=float)
    resolution = float(metadata['resolution_m'])
    shape = np.asarray(metadata['dimensions_xyz'], dtype=int)
    center = np.asarray(center, dtype=float)
    half = np.asarray(size, dtype=float) / 2.0
    c, s = np.cos(yaw), np.sin(yaw)
    rotation = np.asarray([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    world_extent = np.abs(rotation) @ half
    low = np.maximum(0, np.floor((center - world_extent - origin) / resolution).astype(int))
    high = np.minimum(shape, np.ceil((center + world_extent - origin) / resolution).astype(int))
    if np.any(high <= low):
        raise ValueError('obstacle ROI is outside the captured map')
    indices = np.stack(np.meshgrid(
        np.arange(low[0], high[0]), np.arange(low[1], high[1]),
        np.arange(low[2], high[2]), indexing='ij'), axis=-1).reshape(-1, 3)
    centers = origin + (indices + 0.5) * resolution
    local = (centers - center) @ rotation
    center_inside = np.all(np.abs(local) <= half + 1e-9, axis=1)
    projected_cell_half = (resolution / 2.0) * np.sum(np.abs(rotation), axis=0)
    fully_inside = np.all(np.abs(local) + projected_cell_half <= half + 1e-9, axis=1)
    return tuple(indices[center_inside].T), tuple(indices[fully_inside].T), int(
        np.count_nonzero(center_inside)), int(np.count_nonzero(fully_inside))


def _transition_counts(before, after, mask):
    before_values, after_values = before['raw'][mask], after['raw'][mask]
    transitions = {}
    for old_code, old_name in CLASS_NAMES.items():
        for new_code, new_name in CLASS_NAMES.items():
            count = int(np.count_nonzero((before_values == old_code)
                                         & (after_values == new_code)))
            if count:
                transitions[f'{old_name}->{new_name}'] = count
    return {
        'cell_count': int(before_values.size),
        'before_class_counts': {
            name: int(np.count_nonzero(before_values == code))
            for code, name in CLASS_NAMES.items()},
        'after_class_counts': {
            name: int(np.count_nonzero(after_values == code))
            for code, name in CLASS_NAMES.items()},
        'class_transitions': transitions,
        'inflated_before_count': int(np.count_nonzero(before['inflated'][mask])),
        'inflated_after_count': int(np.count_nonzero(after['inflated'][mask])),
    }


def _depth_roi_summary(run, observer, after_source_ns, inject_ns):
    rows = []
    errors = []
    for record in observer.get('depth_and_color_frames', []):
        if record.get('topic') != '/sensors/d435i/depth':
            continue
        path = run / str(record.get('file', ''))
        if not path.is_file():
            errors.append(f"missing_depth_image:{record.get('file')}")
            continue
        if sha256(path) != record.get('file_sha256'):
            errors.append(f"depth_image_hash_mismatch:{record.get('file')}")
            continue
        values = np.asarray(np.load(path, allow_pickle=False), dtype=np.float64)
        if values.ndim != 2:
            errors.append(f"invalid_depth_image_shape:{record.get('file')}")
            continue
        h, w = values.shape
        roi = values[h // 4:3 * h // 4, w // 4:3 * w // 4]
        valid = roi[np.isfinite(roi) & (roi > 0)]
        stamp = int(record.get('stamp_ns', -1))
        rows.append({
            'file': path.name,
            'source_stamp_ns': stamp,
            'frame_id': record.get('frame_id'),
            'encoding': record.get('encoding'),
            'width': w,
            'height': h,
            'center_roi_bounds_px': [w // 4, h // 4, 3 * w // 4, 3 * h // 4],
            'center_roi_valid_pixel_count': int(valid.size),
            'center_roi_depth_p10_p50_p90_m': (
                [float(x) for x in np.percentile(valid, [10, 50, 90])]
                if valid.size else None),
            'after_injection': stamp >= inject_ns if inject_ns is not None else None,
            'covered_by_post_snapshot_fusion_source': (
                stamp <= after_source_ns if after_source_ns is not None else None),
        })
    post_injection_rows = [row for row in rows if row['after_injection'] is True]
    fused_rows = [row for row in post_injection_rows
                  if row['covered_by_post_snapshot_fusion_source'] is True]
    return {
        'status': 'SUPPORTED' if fused_rows and not errors else 'INSUFFICIENT',
        'classification': 'read-only cropped depth summary from saved full-frame samples',
        'saved_depth_frame_count': len(rows),
        'post_injection_depth_frame_count': len(post_injection_rows),
        'post_snapshot_source_covered_frame_count': len(fused_rows),
        'frames': rows,
        'errors': errors,
    }


def evaluate(run, before_dir='n10-map-snapshot-before-injection',
             after_dir='n10-map-snapshot'):
    run = Path(run).resolve()
    observer_path = run / 'n10-live-obstacle-observation.json'
    observer = json.loads(observer_path.read_text())
    before_meta, before_meta_path, before_archive, before_raw, before_inflated = (
        _load_snapshot(run, before_dir))
    after_meta, after_meta_path, after_archive, after_raw, after_inflated = (
        _load_snapshot(run, after_dir))
    identity_keys = ('epoch', 'map_id', 'frame_id')
    before_identity = {key: before_meta.get(key) for key in identity_keys}
    after_identity = {key: after_meta.get(key) for key in identity_keys}
    observer_identity = {
        'epoch': observer.get('epoch'),
        'map_id': observer.get('map_id_at_goal'),
        'frame_id': f"odom_{observer.get('epoch')}" if observer.get('epoch') else None,
    }
    same_identity = (before_identity == after_identity == observer_identity
                     and all(before_identity.values()))
    same_geometry = all(
        before_meta.get(key) == after_meta.get(key)
        for key in ('origin_m', 'map_size_m', 'resolution_m',
                    'dimensions_xyz', 'data_order'))
    injection = observer.get('gazebo_create') or {}
    inject_ns = injection.get('request_sim_ns')
    inject_ns = int(inject_ns) if inject_ns is not None else None
    before_stamp = int(before_meta.get('snapshot_stamp_ns', -1))
    before_source_ns = int(before_meta.get('last_fused_depth_source_stamp_ns', -1))
    after_stamp = int(after_meta.get('snapshot_stamp_ns', -1))
    after_source_ns = int(after_meta.get('last_fused_depth_source_stamp_ns', -1))
    after_coverage = after_meta.get('snapshot_source_coverage') or {}
    time_order_valid = bool(
        inject_ns is not None and before_stamp < inject_ns < after_stamp
        and 0 <= before_source_ns < inject_ns and after_source_ns > inject_ns)
    obstacle = observer.get('obstacle') or {}
    center = obstacle.get('expected_center_odom_xyz_m')
    size = obstacle.get('size_xyz_m')
    yaw = float(obstacle.get('expected_center_odom_yaw_rad', 0.0))
    if not center or not size:
        raise ValueError('obstacle map-frame center and dimensions are missing')
    center_mask, center_indices, center_count, fully_count = _cell_region(
        before_meta, center, size, yaw)
    center_index_mask = np.zeros(before_raw.shape, dtype=bool)
    center_index_mask[center_mask] = True
    full_index_mask = np.zeros(before_raw.shape, dtype=bool)
    full_index_mask[center_indices] = True
    transitions = {
        'voxel_centers_inside_truth_obstacle': _transition_counts(
            {'raw': before_raw, 'inflated': before_inflated},
            {'raw': after_raw, 'inflated': after_inflated}, center_index_mask),
        'voxel_cells_fully_inside_truth_obstacle': _transition_counts(
            {'raw': before_raw, 'inflated': before_inflated},
            {'raw': after_raw, 'inflated': after_inflated}, full_index_mask),
    }
    for key, stats in transitions.items():
        stats['geometric_cell_count'] = (
            center_count if key == 'voxel_centers_inside_truth_obstacle' else fully_count)
    depth_roi = _depth_roi_summary(run, observer, after_source_ns, inject_ns)
    checks = {
        'same_run_epoch_map_frame_identity': same_identity,
        'same_snapshot_grid_geometry': same_geometry,
        'pre_snapshot_precedes_obstacle_create': bool(inject_ns is not None and before_stamp < inject_ns),
        'pre_snapshot_fused_source_precedes_obstacle_create': bool(
            inject_ns is not None and 0 <= before_source_ns < inject_ns),
        'post_snapshot_follows_obstacle_create': bool(inject_ns is not None and after_stamp > inject_ns),
        'post_snapshot_fused_source_covers_injection': bool(
            after_source_ns > inject_ns if inject_ns is not None else False),
        'post_snapshot_cloud_source_coverage': after_coverage.get('covered') is True,
    }
    supported = all(checks.values()) and time_order_valid
    input_paths = [observer_path, before_meta_path, before_archive,
                   after_meta_path, after_archive]
    input_paths.extend(run / row['file'] for row in depth_roi['frames'])
    return {
        'schema': 'n10-occupancy-snapshot-pair/v1',
        'run_id': run.name,
        'classification': 'offline same-identity map transition analysis; no control effect',
        'status': 'SUPPORTED' if supported else 'INSUFFICIENT',
        'read_only': True,
        'truth_used_online': False,
        'control_published': False,
        'identity': {'before': before_identity, 'after': after_identity,
                     'observer': observer_identity},
        'snapshot_times': {
            'before_snapshot_stamp_ns': before_stamp,
            'obstacle_create_request_sim_ns': inject_ns,
            'after_snapshot_stamp_ns': after_stamp,
            'before_last_depth_source_stamp_ns': before_meta.get(
                'last_fused_depth_source_stamp_ns'),
            'after_last_depth_source_stamp_ns': after_source_ns,
            'after_last_fusion_stamp_ns': after_meta.get('last_fusion_stamp_ns'),
            'after_cloud_watermark': after_meta.get('snapshot_roi_cloud_watermark'),
            'after_source_coverage': after_coverage,
        },
        'checks': checks,
        'obstacle_roi': {
            'center_odom_xyz_m': center,
            'size_xyz_m': size,
            'yaw_odom_rad': yaw,
            'resolution_m': before_meta.get('resolution_m'),
            'transitions': transitions,
        },
        'depth_roi': depth_roi,
        'point_query_role': 'optional diagnostic; map arrays above are the comparison source',
        'input_sha256': {str(path.relative_to(run)): sha256(path)
                         for path in input_paths if path.is_file()},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    report = evaluate(args.run)
    output = args.output or args.run / 'n10-map-snapshot-pair-analysis.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'run_id': report['run_id'], 'status': report['status'],
                      'checks': report['checks'],
                      'fully_contained_transitions': report['obstacle_roi'][
                          'transitions']['voxel_cells_fully_inside_truth_obstacle']},
                     allow_nan=False))


if __name__ == '__main__':
    main()
