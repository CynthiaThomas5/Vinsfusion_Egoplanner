#!/usr/bin/env python3
"""Recompute N04 truth projection, VINS-map geometry and voxel class metrics."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools/debug_truth'))
sys.path.insert(0, str(ROOT/'tools'))
sys.path.insert(0, str(ROOT/'src/own/uav_sim'))
sys.path.insert(0, str(ROOT/'src/own/uav_mapping/uav_mapping'))
from world_geometry import distances, load_obstacles
from evaluate_vins_motion import rigid_alignment, rotation
from mapping_input import depth_camera_pose, slerp
from uav_sim.geometry import calibration


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def interpolate_pose(rows, stamp_ns, stamp_key='stamp_ns', time_scale=1.0,
                     max_bracket_s=0.05):
    rows = sorted(rows, key=lambda row: row[stamp_key])
    if not rows:
        return None
    stamp = stamp_ns*time_scale
    before = None
    for row in rows:
        current = float(row[stamp_key])*time_scale
        if current == stamp:
            return np.asarray(row['position'], dtype=float), tuple(row['quaternion'])
        if current > stamp:
            if before is None:
                return None
            gap = current-float(before[stamp_key])*time_scale
            if gap <= 0 or gap > max_bracket_s:
                return None
            fraction = (stamp-float(before[stamp_key])*time_scale)/gap
            position = ((1-fraction)*np.asarray(before['position'], dtype=float)
                        + fraction*np.asarray(row['position'], dtype=float))
            return position, slerp(before['quaternion'], row['quaternion'], fraction)
        before = row
    return None


def _camera_truth_pose(motion_truth, stamp_ns, rig):
    # Gazebo motion truth stores seconds; convert the image source stamp once.
    body = interpolate_pose(motion_truth, stamp_ns*1e-9, 'stamp', 1.0, 0.05)
    if body is None:
        return None
    return depth_camera_pose(body[0], body[1], rig['imu']['translation'],
                             rig['cameras']['depth']['translation'],
                             rig['cameras']['depth']['R_body_optical'])


def _ray_cells(start, end, origin, resolution, dims):
    """Port of current plan_env RayCaster; return cells before the end cell."""
    start = (np.asarray(start, dtype=float)-origin)/resolution
    end = (np.asarray(end, dtype=float)-origin)/resolution
    cell = np.floor(start).astype(int)
    end_cell = np.floor(end).astype(int)
    delta = end-start
    step = np.sign(delta).astype(int)
    inf = float('inf')
    t_max = np.full(3, inf, dtype=float)
    t_delta = np.full(3, inf, dtype=float)
    for axis in range(3):
        if delta[axis] > 0:
            t_max[axis] = (np.floor(start[axis])+1.0-start[axis])/delta[axis]
            t_delta[axis] = 1.0/abs(delta[axis])
        elif delta[axis] < 0:
            t_max[axis] = (start[axis]-np.floor(start[axis]))/-delta[axis]
            t_delta[axis] = 1.0/abs(delta[axis])
    result = []
    max_steps = int(np.sum(np.abs(end_cell-cell)))+4
    for _ in range(max_steps):
        if np.array_equal(cell, end_cell):
            return result
        if np.all(cell >= 0) and np.all(cell < np.asarray(dims)):
            result.append(tuple(int(v) for v in cell))
        if t_max[0] < t_max[1]:
            axis = 0 if t_max[0] < t_max[2] else 2
        else:
            axis = 1 if t_max[1] < t_max[2] else 2
        cell[axis] += step[axis]
        t_max[axis] += t_delta[axis]
    raise ValueError('ray traversal exceeded its bounded cell count')


def _sampled_frames(input_report, pixel_stride, frame_stride, snapshot_source_ns,
                    expected_epoch, expected_map_id, expected_frame_id):
    frame_by_stamp = {int(row['stamp_ns']): row for row in input_report['depth_frames']
                      if row.get('pixels_recorded')}
    pose_by_stamp = {int(row['stamp_ns']): row for row in input_report['camera_poses']}
    events = {}
    for event in input_report['fusion_trace']:
        if (event.get('phase') != 'fused' or event.get('epoch') != expected_epoch
                or event.get('map_id') != expected_map_id):
            continue
        source = int(event.get('image_source_stamp_ns', 0))
        pose_source = int(event.get('pose_source_stamp_ns', 0))
        if source <= snapshot_source_ns:
            events[source] = event
    ordered = [events[key] for key in sorted(events)]
    mismatches = sum(int(row.get('image_source_stamp_ns', 0)) !=
                     int(row.get('pose_source_stamp_ns', 0)) for row in ordered)
    selected = ordered[::frame_stride]
    if ordered and (not selected or selected[-1] is not ordered[-1]):
        selected.append(ordered[-1])
    pairs, missing = [], []
    for event in selected:
        source = int(event['image_source_stamp_ns'])
        frame, pose = frame_by_stamp.get(source), pose_by_stamp.get(source)
        if frame is None or pose is None:
            missing.append(source)
            continue
        if int(event.get('pose_source_stamp_ns', -1)) != source:
            continue
        if pose['frame_id'] != expected_frame_id:
            missing.append(source)
            continue
        pairs.append((event, frame, pose))
    return pairs, {'fused_event_count_before_snapshot': len(ordered),
                   'sampled_fusion_count': len(selected),
                   'sampled_pair_count': len(pairs),
                   'missing_sample_source_stamps_ns': missing,
                   'image_pose_stamp_mismatch_count': mismatches}


def _project_returns(depth_array, frame, camera_pose, k, pixel_stride, capture_stride,
                     min_depth, max_filter_depth, max_ray_length):
    fx, fy, cx, cy = k[0], k[4], k[2], k[5]
    factor = pixel_stride//capture_stride
    if factor < 1 or pixel_stride % capture_stride:
        raise ValueError('reference ray pixel stride must be a multiple of depth capture stride')
    rows, cols = depth_array.shape
    rr = np.arange(0, rows, factor, dtype=int)
    cc = np.arange(0, cols, factor, dtype=int)
    vv = int(frame.get('margin_px', 2))+rr*capture_stride
    uu = int(frame.get('margin_px', 2))+cc*capture_stride
    values = depth_array[np.ix_(rr, cc)].astype(np.float64, copy=False)
    valid = np.isfinite(values)&(values > 0)
    if not np.any(valid):
        return (np.empty((0, 3)), np.empty((0, 2), dtype=int),
                {'sampled_pixels': int(values.size), 'valid_depth_pixels': 0,
                 'invalid_depth_pixels': int(values.size), 'below_minimum_pixels': 0,
                 'over_filter_max_pixels': 0, 'projected_pixels': 0})
    z = values[valid]
    # Mirror the 32FC1 -> uint16-mm conversion and plan_env depth clipping.
    z = np.rint(z*1000.0).clip(0, 65535)/1000.0
    below_min = z < min_depth
    over_filter = z > max_filter_depth
    z[over_filter] = max_ray_length+0.1
    keep = ~below_min
    rows_idx, cols_idx = np.nonzero(valid)
    rows_idx, cols_idx = rows_idx[keep], cols_idx[keep]
    z = z[keep]
    u = uu[cols_idx].astype(float)
    v = vv[rows_idx].astype(float)
    xyz = np.column_stack(((u-cx)*z/fx, (v-cy)*z/fy, z))
    position = np.asarray(camera_pose['position'], dtype=float)
    rcam = rotation(camera_pose['quaternion'])
    endpoints = (rcam@xyz.T).T+position
    rays = np.column_stack((rows_idx, cols_idx)).astype(int)
    return endpoints, rays, {
        'sampled_pixels': int(values.size),
        'valid_depth_pixels': int(np.count_nonzero(valid)),
        'invalid_depth_pixels': int(values.size-np.count_nonzero(valid)),
        'below_minimum_pixels': int(np.count_nonzero(below_min)),
        'over_filter_max_pixels': int(np.count_nonzero(over_filter)),
        'projected_pixels': int(len(z)),
    }


def _reference_votes(pairs, arrays, origin, resolution, dims, k, cfg, max_source_ns,
                     use_truth, truth, rig):
    free_votes = Counter()
    hit_votes = Counter()
    ray_count = 0
    clipped_endpoints = 0
    debug_endpoint_points = []
    used_sources = []
    for event, frame, ego_pose in pairs:
        source = int(event['image_source_stamp_ns'])
        if source > max_source_ns:
            continue
        if use_truth:
            pose = _camera_truth_pose(truth, source, rig)
            if pose is None:
                continue
            camera_pose = {'position': list(pose[0]), 'quaternion': list(pose[1])}
        else:
            camera_pose = ego_pose
        array_index = int(frame['array_index'])
        if array_index >= len(arrays):
            continue
        # Only sample 16 px-spaced rays from the 2 px EGO lattice. This is an
        # auditable lower-bound view reference, not an approximation of all rays.
        endpoints, ray_pixels, _ = _project_returns(
            arrays[array_index], frame, camera_pose, k,
            cfg['sampling']['reference_ray_pixel_stride'],
            cfg['sampling']['depth_capture_pixel_stride'],
            cfg['sampling']['depth_min_m'], cfg['sampling']['depth_max_filter_m'],
            cfg['depth_limit_m'])
        position = np.asarray(camera_pose['position'], dtype=float)
        frame_free, frame_hit = set(), set()
        for endpoint in endpoints:
            vec = endpoint-position
            length = float(np.linalg.norm(vec))
            if length <= 1e-9:
                continue
            endpoint_is_hit = True
            if length > cfg['depth_limit_m']:
                endpoint = position+vec/length*cfg['depth_limit_m']
                endpoint_is_hit = False
                clipped_endpoints += 1
            end_idx = np.floor((endpoint-origin)/resolution).astype(int)
            if np.any(end_idx < 0) or np.any(end_idx >= np.asarray(dims)):
                clipped_endpoints += 1
                continue
            key = tuple(int(v) for v in end_idx)
            (frame_hit if endpoint_is_hit else frame_free).add(key)
            frame_free.update(_ray_cells(position, endpoint, origin, resolution, dims))
            if use_truth:
                debug_endpoint_points.append(endpoint)
            ray_count += 1
        for cell in frame_free:
            free_votes[cell] += 1
        for cell in frame_hit:
            hit_votes[cell] += 1
        used_sources.append(source)
    shape = tuple(int(v) for v in dims)
    free_count = np.zeros(shape, dtype=np.uint16)
    hit_count = np.zeros(shape, dtype=np.uint16)
    for cell, count in free_votes.items():
        free_count[cell] = min(count, 65535)
    for cell, count in hit_votes.items():
        hit_count[cell] = min(count, 65535)
    free_mask = (free_count > 0)&(hit_count == 0)
    surface_mask = (hit_count > 0)&(free_count == 0)
    ambiguous_mask = (hit_count > 0)&(free_count > 0)
    return {
        'free_vote_count': free_count,
        'hit_vote_count': hit_count,
        'free_mask': free_mask,
        'surface_mask': surface_mask,
        'ambiguous_mask': ambiguous_mask,
        'ray_count': ray_count,
        'clipped_endpoint_count': clipped_endpoints,
        'used_source_stamps_ns': used_sources,
        'debug_endpoint_points': np.asarray(debug_endpoint_points, dtype=float).reshape(-1, 3),
    }


def _cell_centers(indices, origin, resolution):
    return origin+(np.asarray(indices, dtype=float)+0.5)*resolution


def _array_region(roi, origin, resolution, dims, alignment_rotation=None,
                  alignment_translation=None):
    corners = np.array([[x, y, z] for x in roi[0] for y in roi[1] for z in roi[2]], dtype=float)
    if alignment_rotation is None:
        map_corners = corners
    else:
        map_corners = (alignment_rotation.T@(corners-alignment_translation).T).T
    low = np.floor((map_corners.min(axis=0)-origin)/resolution).astype(int)-1
    high = np.ceil((map_corners.max(axis=0)-origin)/resolution).astype(int)+1
    low = np.maximum(low, 0)
    high = np.minimum(high, np.asarray(dims)-1)
    if np.any(high < low):
        return np.empty((0, 3), dtype=int), np.empty((0, 3), dtype=float)
    axes = [np.arange(low[i], high[i]+1) for i in range(3)]
    grid = np.stack(np.meshgrid(*axes, indexing='ij'), axis=-1).reshape(-1, 3)
    centers = _cell_centers(grid, origin, resolution)
    if alignment_rotation is not None:
        centers = (alignment_rotation@centers.T).T+alignment_translation
    mask = np.ones(len(grid), dtype=bool)
    for axis in range(3):
        mask &= (centers[:, axis] >= roi[axis][0])&(centers[:, axis] < roi[axis][1])
    return grid[mask], centers[mask]


def _class_counts(occupancy, inflated, indices):
    if len(indices) == 0:
        return {'voxel_count': 0, 'raw': {}, 'inflated_count': 0}
    values = occupancy[tuple(indices.T)]
    inflate = inflated[tuple(indices.T)] != 0
    return {'voxel_count': int(len(values)),
            'raw': {'unknown': int(np.count_nonzero(values == -1)),
                    'free': int(np.count_nonzero(values == 0)),
                    'occupied': int(np.count_nonzero(values == 100))},
            'inflated_count': int(np.count_nonzero(inflate)),
            'raw_and_inflated_overlap_count': int(np.count_nonzero(inflate&(values == 100)))}


def _reference_class_metrics(occupancy, free_mask, surface_mask, ambiguous_mask):
    result = {}
    for label, mask in [('expected_visible_free', free_mask),
                        ('expected_surface_hit_without_conflicting_free', surface_mask),
                        ('ray_vote_ambiguous', ambiguous_mask),
                        ('observed_return_any_hit', surface_mask|ambiguous_mask),
                        ('observed_ray_any_free', free_mask|ambiguous_mask)]:
        n = int(np.count_nonzero(mask))
        values = occupancy[mask]
        result[label] = {
            'voxel_count': n,
            'actual_raw_unknown': int(np.count_nonzero(values == -1)),
            'actual_raw_free': int(np.count_nonzero(values == 0)),
            'actual_raw_occupied': int(np.count_nonzero(values == 100)),
        }
        if n:
            result[label]['fraction_known'] = float(np.mean(values != -1))
            result[label]['fraction_free'] = float(np.mean(values == 0))
            result[label]['fraction_occupied'] = float(np.mean(values == 100))
    return result


def _surface_report(occupancy, metadata, alignment_rotation, alignment_translation,
                    obstacles, resolution):
    cells = np.argwhere(occupancy == 100)
    if len(cells) == 0:
        return {'occupied_voxel_count': 0, 'per_obstacle': {}, 'quantization_bound_m': resolution*np.sqrt(3)/2}
    origin = np.asarray(metadata['origin_m'], dtype=float)
    map_points = _cell_centers(cells, origin, resolution)
    world_points = (alignment_rotation@map_points.T).T+alignment_translation
    signed, names = distances(world_points, obstacles)
    residual = np.abs(signed)
    quantization = float(resolution*np.sqrt(3)/2)
    per_object = {}
    for obstacle in obstacles:
        mask = names == obstacle['name']
        if not np.any(mask):
            continue
        local = (world_points[mask]-obstacle['transform'][:3, 3])@obstacle['transform'][:3, :3]
        per_object[obstacle['name']] = {
            'occupied_voxels_assigned': int(np.count_nonzero(mask)),
            'signed_surface_residual_m': {
                'median': float(np.median(signed[mask])),
                'p05': float(np.percentile(signed[mask], 5)),
                'p95': float(np.percentile(signed[mask], 95)),
                'max_abs': float(np.max(residual[mask])),
                'fraction_center_within_half_voxel_diagonal': float(np.mean(residual[mask] <= quantization)),
                'fraction_center_more_than_one_voxel_from_surface': float(np.mean(residual[mask] > resolution)),
            },
            'occupied_local_bounds_m': np.column_stack((local.min(axis=0), local.max(axis=0))).tolist(),
            'signed_residual_band_width_p95_minus_p05_m': float(
                np.percentile(signed[mask], 95)-np.percentile(signed[mask], 5)),
        }
        if obstacle['kind'] == 'box' and obstacle['name'].startswith('calibration_wall/'):
            half = obstacle['shape']
            face = (np.abs(local[:, 1]) < half[1]-0.4
                    )&(np.abs(local[:, 2]) < half[2]-0.4
                    )&(np.abs(local[:, 0]) < half[0]+2*resolution)
            local_face = local[face]
            if len(local_face):
                layer_groups = defaultdict(set)
                bin_y = np.floor((local_face[:, 1]+half[1])/resolution).astype(int)
                bin_z = np.floor((local_face[:, 2]+half[2])/resolution).astype(int)
                bin_x = np.floor((local_face[:, 0]+half[0])/resolution).astype(int)
                for iy, iz, ix in zip(bin_y, bin_z, bin_x):
                    layer_groups[(int(iy), int(iz))].add(int(ix))
                layer_counts = np.asarray([len(v) for v in layer_groups.values()], dtype=float)
                per_object[obstacle['name']]['central_face_occupied_normal_layers'] = {
                    'cross_sections': int(len(layer_counts)),
                    'median_layers': float(np.median(layer_counts)),
                    'p95_layers': float(np.percentile(layer_counts, 95)),
                    'max_layers': int(np.max(layer_counts)),
                    'median_band_width_m': float(np.median(layer_counts)*resolution),
                    'p95_band_width_m': float(np.percentile(layer_counts, 95)*resolution),
                    'source': 'unique voxel layers along the SDF box normal within central wall-face ROI',
                }
    return {
        'occupied_voxel_count': int(len(cells)),
        'center_to_nearest_analytic_surface_abs_error_m': {
            'median': float(np.median(residual)), 'p95': float(np.percentile(residual, 95)),
            'maximum': float(np.max(residual)),
            'fraction_within_half_voxel_diagonal': float(np.mean(residual <= quantization)),
            'fraction_over_one_voxel': float(np.mean(residual > resolution)),
        },
        'quantization_bound_m': quantization,
        'per_obstacle': per_object,
        'qualification': 'Centers are compared after a single VINS-to-truth SE(3) alignment fitted only from trajectories; map points do not affect alignment.',
    }


def _shadow_occlusion_check(roi, truth, rig, obstacles):
    targets = np.array([[x, y, z] for x in roi[0] for y in roi[1] for z in roi[2]], dtype=float)
    # Also include the center, which is not necessarily one of the eight corners.
    targets = np.vstack((targets, np.mean(np.asarray(roi, dtype=float), axis=1)))
    stride = max(1, len(truth)//60)
    selected_truth = truth[::stride]
    blocked, total = 0, 0
    missing_pose = 0
    for row in selected_truth:
        stamp = int(round(float(row['stamp'])*1e9))
        camera = _camera_truth_pose(truth, stamp, rig)
        if camera is None:
            missing_pose += len(targets)
            continue
        start = np.asarray(camera[0], dtype=float)
        for target in targets:
            fractions = np.linspace(0.01, 0.99, 161)
            points = start[None, :]+fractions[:, None]*(target-start)[None, :]
            signed, _ = distances(points, obstacles)
            total += 1
            if np.any(signed < -1e-6):
                blocked += 1
    return {'sampled_camera_poses': len(selected_truth), 'tested_roi_points_per_pose': int(len(targets)),
            'segments_tested': total, 'segments_blocked_by_analytic_sdf': blocked,
            'segments_unblocked': total-blocked, 'missing_truth_pose_count': missing_pose,
            'fully_occluded_by_reference': total > 0 and blocked == total,
            'qualification': 'Offline only: line segments from interpolated Gazebo camera poses to ROI corners/center tested against static SDF solids.'}


def _snapshot_paths(run_dir):
    result = []
    for directory in sorted((run_dir/'snapshots').glob('snapshot-*')):
        meta = directory/'metadata.json'
        archive = directory/'occupancy_snapshot.npz'
        if meta.is_file() and archive.is_file():
            result.append((directory.name, meta, archive))
    return result


def _validate_no_control_graph(run_dir):
    node_path, topic_path = run_dir/'ros-nodes.txt', run_dir/'ros-topics.txt'
    if not node_path.is_file() or not topic_path.is_file():
        raise ValueError('retained ROS node/topic graph is missing')
    nodes = [line.strip() for line in node_path.read_text().splitlines() if line.strip()]
    topics = [line.strip() for line in topic_path.read_text().splitlines() if line.strip()]
    bad_nodes = [name for name in nodes if re.search(r'px4|controller|debug_truth|truth_bridge', name, re.I)]
    bad_topics = [name for name in topics
                  if re.search(r'^/(fmu|debug_truth|truth)(/|$)|world_map', name, re.I)]
    if bad_nodes or bad_topics:
        raise ValueError(f'unexpected control/truth graph entries: nodes={bad_nodes}, topics={bad_topics}')
    return {
        'node_count': len(nodes), 'topic_count': len(topics),
        'forbidden_node_count': len(bad_nodes), 'forbidden_topic_count': len(bad_topics),
        'node_graph_sha256': sha256(node_path), 'topic_graph_sha256': sha256(topic_path),
        'no_px4_control_or_truth_ros_endpoint': True,
    }


def _runtime_mapping_parameters(path, expected):
    document = yaml.safe_load(Path(path).read_text())
    if not isinstance(document, dict) or len(document) != 1:
        raise ValueError('EGO runtime parameter dump must contain exactly one node')
    node = next(iter(document.values()))
    params_tree = node.get('ros__parameters') if isinstance(node, dict) else None
    if not isinstance(params_tree, dict):
        raise ValueError('EGO runtime parameter dump has no ros__parameters map')
    params = {}

    def flatten(prefix, value):
        if isinstance(value, dict):
            for name, child in value.items():
                flatten(f'{prefix}/{name}' if prefix else str(name), child)
        else:
            params[prefix] = value

    flatten('', params_tree)
    missing = [name for name in expected if name not in params]
    if missing:
        raise ValueError(f'EGO runtime parameter dump lacks mapping fields: {missing}')
    actual = {name: params[name] for name in expected}
    differences = {}
    for name, wanted in expected.items():
        got = actual[name]
        if isinstance(wanted, (int, float)) and not isinstance(wanted, bool):
            same = np.isclose(float(got), float(wanted), atol=1e-6, rtol=0.0)
        else:
            same = got == wanted
        if not same:
            differences[name] = {'expected': wanted, 'actual': got}
    if differences:
        raise ValueError(f'EGO mapping parameters differ from the ray reference: {differences}')
    return actual


def evaluate(run_dir):
    run_dir = Path(run_dir).resolve()
    cfg_path = ROOT/'config/components/simulation/n04_geometry_layouts.json'
    cfg = json.loads(cfg_path.read_text())
    world_manifest_path = run_dir/'world-manifest.json'
    world_manifest = json.loads(world_manifest_path.read_text())
    layout = next(row for row in cfg['layouts'] if row['id'] == world_manifest['layout_id'])
    if world_manifest.get('online_truth_input') is not False:
        raise ValueError('N04 generated world manifest does not exclude truth from online inputs')
    if world_manifest['source']['layout_config_sha256'] != sha256(cfg_path):
        raise ValueError('N04 layout source manifest does not match the current layout config')
    for relative, key in ((cfg['base_world'], 'base_world_sha256'),
                          (cfg['sensor_model'], 'sensor_model_sha256')):
        if world_manifest['source'][key] != sha256(ROOT/relative):
            raise ValueError(f'N04 source manifest no longer matches {relative}')
    for path, key in ((run_dir/'world.sdf', 'moving_world_sha256'),
                      (run_dir/'truth-scene.sdf', 'truth_scene_sdf_sha256')):
        if world_manifest['generated'][key] != sha256(path):
            raise ValueError(f'N04 generated SDF hash mismatch: {path.name}')
    input_report = json.loads((run_dir/'inputs/mapping-inputs.json').read_text())
    run_inputs = json.loads((run_dir/'run-inputs.json').read_text())
    runtime_config = json.loads((ROOT/'config/runtime.json').read_text())
    if (run_inputs.get('run_id') != run_dir.name
            or run_inputs.get('layout_id') != layout['id']
            or run_inputs.get('container_image') != runtime_config['image_id']
            or run_inputs.get('control_scope') != 'no PX4/control/navigation goal'):
        raise ValueError('N04 run identity or no-control scope does not match the fixed project image')
    captured_toolchain = run_inputs.get('toolchain_sha256', {})
    toolchain_mismatches = {
        name: {'captured': digest, 'current': sha256(ROOT/name)}
        for name, digest in captured_toolchain.items()
        if digest != sha256(ROOT/name)
    }
    if toolchain_mismatches:
        raise ValueError(f'N04 toolchain source changed after capture: {toolchain_mismatches}')
    graph_scope = _validate_no_control_graph(run_dir)
    motion = json.loads((run_dir/'motion.json').read_text())
    snapshots = _snapshot_paths(run_dir)
    if len(snapshots) != int(cfg['sampling']['snapshot_count_per_layout']):
        raise ValueError(f"expected {cfg['sampling']['snapshot_count_per_layout']} snapshots, got {len(snapshots)}")
    if not motion.get('truth') or not input_report.get('optimized_odometry'):
        raise ValueError('missing offline truth or VINS optimized odometry samples')
    obstacles = load_obstacles(run_dir/'truth-scene.sdf')
    rig = calibration(ROOT/'simulation/models/d435i/model.sdf')
    k = rig['cameras']['depth']['K']
    planner_path = ROOT/'config/components/mapping/ego_planner.json'
    planner_cfg = json.loads(planner_path.read_text())
    expected_params = {
        'grid_map/resolution': cfg['map_resolution_m'],
        'grid_map/map_size_x': planner_cfg['map_size_m'][0],
        'grid_map/map_size_y': planner_cfg['map_size_m'][1],
        'grid_map/map_size_z': planner_cfg['map_size_m'][2],
        'grid_map/fx': k[0], 'grid_map/fy': k[4],
        'grid_map/cx': k[2], 'grid_map/cy': k[5],
        'grid_map/depth_filter_mindist': cfg['sampling']['depth_min_m'],
        'grid_map/depth_filter_maxdist': cfg['sampling']['depth_max_filter_m'],
        'grid_map/depth_filter_margin': cfg['sampling']['depth_filter_margin_px'],
        'grid_map/use_depth_filter': True,
        'grid_map/k_depth_scaling_factor': 1000.0,
        'grid_map/skip_pixel': cfg['sampling']['expected_plan_env_skip_pixel'],
        'grid_map/max_ray_length': cfg['depth_limit_m'],
        'grid_map/frame_id': 'world',
        'grid_map/pose_type': 1,
    }
    runtime_params = _runtime_mapping_parameters(run_dir/'ego-runtime-params.yaml', expected_params)
    truth = motion['truth']
    odometry = input_report['optimized_odometry']
    truth_t = np.asarray([row['stamp'] for row in truth], dtype=float)
    odom_t = np.asarray([row['stamp_ns']*1e-9 for row in odometry], dtype=float)
    overlap = (odom_t >= truth_t[0])&(odom_t <= truth_t[-1])
    odom_overlap = [row for row, keep in zip(odometry, overlap) if keep]
    if len(odom_overlap) < 20:
        raise ValueError(f'insufficient VINS/truth overlap: {len(odom_overlap)}')
    truth_pos = np.asarray([row['position'] for row in truth], dtype=float)
    ref = np.column_stack([np.interp([r['stamp_ns']*1e-9 for r in odom_overlap],
                                       truth_t, truth_pos[:, axis]) for axis in range(3)])
    estimated = np.asarray([row['position'] for row in odom_overlap], dtype=float)
    align_r, align_t = rigid_alignment(estimated, ref)
    traj_error = np.linalg.norm((align_r@estimated.T).T+align_t-ref, axis=1)
    trajectory_alignment = {
        'method': 'single rigid SE(3), scale fixed to one; fit only on time-paired VINS IMU odometry and Gazebo fixture truth',
        'paired_samples': int(len(ref)), 'overlap_s': float(odom_overlap[-1]['stamp_ns']*1e-9-odom_overlap[0]['stamp_ns']*1e-9),
        'position_rmse_m': float(np.sqrt(np.mean(traj_error**2))),
        'position_p95_m': float(np.percentile(traj_error, 95)),
        'position_max_m': float(np.max(traj_error)),
        'rotation': align_r.tolist(), 'translation_m': align_t.tolist(),
    }

    # Verify camera-info K and raw depth headers before making any map claim.
    camera_info = input_report['depth_camera_info']
    camera_info_k = np.median(np.asarray([row['k'] for row in camera_info], dtype=float), axis=0).tolist() if camera_info else []
    k_diff = []
    if camera_info_k:
        k_diff = [abs(camera_info_k[i]-k[i]) for i in range(9)]
    depth_stamp_values = [int(row['stamp_ns']) for row in input_report['depth_frames']
                          if row.get('pixels_recorded')]
    pose_stamp_values = {int(row['stamp_ns']) for row in input_report['camera_poses']}
    stamps_monotonic = all(a < b for a, b in zip(depth_stamp_values, depth_stamp_values[1:]))
    camera_contract = {
        'model_sha256': rig['model_sha256'], 'depth_intrinsics_K': k,
        'depth_extrinsic_body_translation_m': rig['cameras']['depth']['translation'],
        'depth_extrinsic_body_to_optical_rotation': np.asarray(
            rig['cameras']['depth']['R_body_optical']).reshape(3, 3).tolist(),
        'imu_translation_m': rig['imu']['translation'],
        'camera_info_samples': len(camera_info), 'camera_info_median_K': camera_info_k,
        'camera_info_K_absolute_difference': k_diff,
        'camera_info_matches_model_at_1e-3': bool(k_diff and max(k_diff) <= 1e-3),
        'depth_frame_stamps_strictly_increasing': stamps_monotonic,
        'depth_pose_exact_stamp_pair_coverage': (len(set(depth_stamp_values)&pose_stamp_values)/len(set(depth_stamp_values))
                                                  if depth_stamp_values else 0.0),
        'raw_depth_header_count': len(input_report['raw_depth_headers']),
        'raw_depth_to_ego_input_stamp_coverage': (
            len(set(depth_stamp_values)&{int(row['stamp_ns']) for row in input_report['raw_depth_headers']})
            /len(set(depth_stamp_values)) if depth_stamp_values else 0.0),
        'map_input_depth_encoding_counts': dict(Counter(row['encoding'] for row in input_report['depth_frames'])),
        'capture_errors': input_report['depth_frame_header_errors'],
    }

    # Truth-only reference raycast: project the observed depth using the known
    # Gazebo fixture pose. This diagnoses render/K/extrinsic/ray behavior and
    # is saved separately from the online VINS map evaluation below.
    first_meta = json.loads(snapshots[0][1].read_text())
    session_path = run_dir.parent/(run_dir.name+'-stack')/'session'/'session.json'
    session = json.loads(session_path.read_text())
    if first_meta['epoch'] != session.get('epoch'):
        raise ValueError('snapshot epoch does not match the fresh VINS session manifest')
    runtime_params_path = run_dir/'ego-runtime-params.yaml'
    expected_hashes = {
        'calibration_sha256': rig['model_sha256'],
        'input_config_sha256': sha256(ROOT/'config/components/mapping/ego_input.json'),
        'planner_config_sha256': sha256(planner_path),
        'runtime_parameters_sha256': sha256(runtime_params_path),
    }
    if first_meta['configuration'] != expected_hashes:
        raise ValueError('snapshot configuration hashes do not match the current capture files')
    origin = np.asarray(first_meta['origin_m'], dtype=float)
    resolution = float(first_meta['resolution_m'])
    dims = tuple(int(v) for v in first_meta['dimensions_xyz'])
    map_size = np.asarray(first_meta['map_size_m'], dtype=float)
    truth_origin = np.array([-map_size[0]/2, -map_size[1]/2, origin[2]], dtype=float)
    arrays_file = run_dir/'inputs/mapping-depth-pixels.npz'
    with np.load(arrays_file, allow_pickle=False) as archive:
        depth_arrays = archive['depth_m']
    pair_diag, pair_summary = _sampled_frames(
        input_report, cfg['sampling']['reference_ray_pixel_stride'],
        cfg['sampling']['reference_fusion_frame_stride'], 2**63-1,
        first_meta['epoch'], first_meta['map_id'], first_meta['frame_id'])
    # The projection error uses EGO-fused source stamps, but substitutes true
    # camera poses; no truth value reaches a ROS topic.
    truth_returns, truth_depth_stats = [], Counter()
    for event, frame, _pose in pair_diag:
        source = int(event['image_source_stamp_ns'])
        pose = _camera_truth_pose(truth, source, rig)
        if pose is None:
            continue
        endpoints, _, counts = _project_returns(
            depth_arrays[int(frame['array_index'])], frame,
            {'position': list(pose[0]), 'quaternion': list(pose[1])}, k,
            cfg['sampling']['reference_ray_pixel_stride'],
            cfg['sampling']['depth_capture_pixel_stride'],
            cfg['sampling']['depth_min_m'], cfg['sampling']['depth_max_filter_m'],
            cfg['depth_limit_m'])
        camera_position = np.asarray(pose[0], dtype=float)
        surface_hits = np.linalg.norm(endpoints-camera_position[None, :], axis=1) <= cfg['depth_limit_m']+1e-9
        truth_returns.extend(endpoints[surface_hits].tolist())
        truth_depth_stats.update(counts)
    truth_returns = np.asarray(truth_returns, dtype=float).reshape(-1, 3)
    truth_signed, truth_names = distances(truth_returns, obstacles) if len(truth_returns) else (np.empty(0), np.empty(0))
    truth_abs = np.abs(truth_signed)
    quantization_bound = resolution*np.sqrt(3)/2
    truth_projection = {
        'frame_sampling_stride': cfg['sampling']['reference_fusion_frame_stride'],
        'pixel_stride': cfg['sampling']['reference_ray_pixel_stride'],
        'sampled_return_count': int(len(truth_returns)),
        'depth_sample_counts': dict(truth_depth_stats),
        'nearest_sdf_surface_abs_residual_m': {
            'median': float(np.median(truth_abs)) if len(truth_abs) else None,
            'p95': float(np.percentile(truth_abs, 95)) if len(truth_abs) else None,
            'maximum': float(np.max(truth_abs)) if len(truth_abs) else None,
            'fraction_within_half_voxel_diagonal': float(np.mean(truth_abs <= quantization_bound)) if len(truth_abs) else None,
        },
        'per_obstacle_samples': {obstacle['name']: int(np.count_nonzero(truth_names == obstacle['name']))
                                 for obstacle in obstacles},
        'use': 'truth substituted offline for the same sampled fused depth observations; never an online mapping input',
    }

    # Rasterize a standalone truth-camera ray reference. It is not compared to
    # the VINS-frame map; the online reference uses exact EGO camera poses.
    truth_votes = _reference_votes(pair_diag, depth_arrays, truth_origin, resolution, dims,
                                   k, cfg, 2**63-1, True, truth, rig)
    truth_reference = np.full(dims, -1, dtype=np.int8)
    truth_reference[truth_votes['free_mask']] = 0
    truth_reference[truth_votes['surface_mask']] = 100
    truth_reference_path = run_dir/'analysis/truth-ray-reference.npz'
    truth_reference_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(truth_reference_path, reference_state=truth_reference,
                        free_vote_count=truth_votes['free_vote_count'],
                        hit_vote_count=truth_votes['hit_vote_count'],
                        ambiguous_mask=truth_votes['ambiguous_mask'])
    truth_ray_report = {
        'rays': truth_votes['ray_count'], 'free_cells': int(np.count_nonzero(truth_votes['free_mask'])),
        'surface_cells': int(np.count_nonzero(truth_votes['surface_mask'])),
        'ambiguous_cells': int(np.count_nonzero(truth_votes['ambiguous_mask'])),
        'unknown_cells': int(np.count_nonzero(truth_reference == -1)),
        'frame': 'world/truth diagnostic raster; distinct from online VINS map frame',
        'archive': truth_reference_path.relative_to(run_dir).as_posix(),
        'archive_sha256': sha256(truth_reference_path),
    }

    shadow_roi = layout['regions']['wall_shadow_roi_xyz_m']
    shadow_occlusion = _shadow_occlusion_check(shadow_roi, truth, rig, obstacles)
    reports = []
    previous_occupied = None
    previous_wall_x = None
    previous_source_ns = 0
    for snapshot_id, metadata_path, archive_path in snapshots:
        metadata = json.loads(metadata_path.read_text())
        with np.load(archive_path, allow_pickle=False) as archive:
            occupancy = archive['occupancy']
            inflated = archive['inflated']
        if tuple(occupancy.shape) != tuple(metadata['dimensions_xyz']):
            raise ValueError(f'{snapshot_id}: snapshot shape/metadata mismatch')
        if tuple(occupancy.shape) != dims or not np.allclose(metadata['origin_m'], origin):
            raise ValueError(f'{snapshot_id}: map grid changed during same-epoch capture')
        if metadata['epoch'] != first_meta['epoch'] or metadata['map_id'] != first_meta['map_id']:
            raise ValueError(f'{snapshot_id}: epoch/map_id changed within layout run')
        if metadata['frame_id'] != first_meta['frame_id']:
            raise ValueError(f'{snapshot_id}: map frame changed within layout run')
        source_ns = int(metadata['last_fused_depth_source_stamp_ns'])
        if source_ns <= previous_source_ns:
            raise ValueError(f'{snapshot_id}: snapshots are not strictly later in fused source time')
        previous_source_ns = source_ns
        pairs, pairs_report = _sampled_frames(
            input_report, cfg['sampling']['reference_ray_pixel_stride'],
            cfg['sampling']['reference_fusion_frame_stride'], source_ns,
            metadata['epoch'], metadata['map_id'], metadata['frame_id'])
        online_votes = _reference_votes(pairs, depth_arrays, origin, resolution, dims,
                                        k, cfg, source_ns, False, truth, rig)
        ref_path = run_dir/'analysis'/f'{snapshot_id}-vins-ray-reference.npz'
        np.savez_compressed(ref_path, free_vote_count=online_votes['free_vote_count'],
                            hit_vote_count=online_votes['hit_vote_count'],
                            expected_free=online_votes['free_mask'],
                            expected_surface=online_votes['surface_mask'],
                            ambiguous=online_votes['ambiguous_mask'])
        alignment_mask = np.argwhere(occupancy == 100)
        map_points = _cell_centers(alignment_mask, origin, resolution)
        world_points = (align_r@map_points.T).T+align_t if len(map_points) else map_points
        signed, names = distances(world_points, obstacles) if len(world_points) else (np.empty(0), np.empty(0))
        surface = _surface_report(occupancy, metadata, align_r, align_t, obstacles, resolution)
        free_roi_indices, _ = _array_region(
            layout['regions']['pre_obstacle_free_roi_xyz_m'], origin, resolution, dims, align_r, align_t)
        shadow_indices, _ = _array_region(shadow_roi, origin, resolution, dims, align_r, align_t)
        free_roi_counts = _class_counts(occupancy, inflated, free_roi_indices)
        shadow_counts = _class_counts(occupancy, inflated, shadow_indices)
        ray_metrics = _reference_class_metrics(occupancy, online_votes['free_mask'],
                                                online_votes['surface_mask'],
                                                online_votes['ambiguous_mask'])
        # Check every voxel center inside analytic solids, not only occupied
        # voxel centers, so raw-free cells through an obstacle are observable.
        all_cells = np.indices(occupancy.shape, dtype=np.int32).reshape(3, -1).T
        all_map_centers = _cell_centers(all_cells, origin, resolution)
        all_world_centers = (align_r@all_map_centers.T).T+align_t
        all_signed, _ = distances(all_world_centers, obstacles)
        solid_interior = all_signed < -quantization_bound
        flat_occupancy = occupancy.reshape(-1)
        interior_counts = {
            'deep_interior_voxel_count': int(np.count_nonzero(solid_interior)),
            'raw_free_voxel_count': int(np.count_nonzero(solid_interior & (flat_occupancy == 0))),
            'raw_unknown_voxel_count': int(np.count_nonzero(solid_interior & (flat_occupancy == -1))),
            'raw_occupied_voxel_count': int(np.count_nonzero(solid_interior & (flat_occupancy == 100))),
            'interior_definition': 'all map voxel centers more than half a voxel diagonal inside an analytic static solid',
        }
        occupied_set = set(map(tuple, np.argwhere(occupancy == 100).tolist()))
        temporal = None
        if previous_occupied is not None:
            union = len(occupied_set|previous_occupied)
            temporal = {'previous_occupied_count': len(previous_occupied),
                        'current_occupied_count': len(occupied_set),
                        'added': len(occupied_set-previous_occupied),
                        'removed': len(previous_occupied-occupied_set),
                        'jaccard': len(occupied_set&previous_occupied)/union if union else 1.0}
        previous_occupied = occupied_set
        wall = next((o for o in obstacles if o['name'].startswith('calibration_wall/')), None)
        wall_x = None
        if wall is not None and len(world_points):
            wall_mask = names == wall['name']
            local = (world_points[wall_mask]-wall['transform'][:3, 3])@wall['transform'][:3, :3]
            half = wall['shape']
            central = (np.abs(local[:, 1]) < 1.2)&(np.abs(local[:, 2]) < 1.2)
            if np.any(central):
                wall_x = float(np.median(local[central, 0]))
        if temporal is not None:
            temporal['central_wall_median_local_x_m'] = wall_x
            temporal['central_wall_shift_from_previous_m'] = (
                abs(wall_x-previous_wall_x) if wall_x is not None and previous_wall_x is not None else None)
        previous_wall_x = wall_x if wall_x is not None else previous_wall_x

        report = {
            'snapshot_id': snapshot_id,
            'identity': {'epoch': metadata['epoch'], 'map_id': metadata['map_id'],
                         'frame_id': metadata['frame_id'],
                         'snapshot_stamp_ns': metadata['snapshot_stamp_ns'],
                         'source_stamp_ns': source_ns,
                         'fusion_stamp_ns': metadata['last_fusion_stamp_ns'],
                         'source_age_s': metadata['source_age_at_response_s'],
                         'map_origin_m': metadata['origin_m'],
                         'resolution_m': resolution,
                         'dimensions_xyz': metadata['dimensions_xyz']},
            'camera_calibration': {
                'model_sha256': rig['model_sha256'],
                'K': k,
                'depth_extrinsic_translation_body_m': rig['cameras']['depth']['translation'],
                'depth_extrinsic_body_to_optical_rotation': np.asarray(
                    rig['cameras']['depth']['R_body_optical']).reshape(3, 3).tolist(),
                'configuration_hashes': metadata['configuration'],
            },
            'raw_vs_inflated': {
                'voxel_counts': metadata['voxel_counts'],
                'archive_roundtrip_exact': metadata['archive']['readback_exact'],
                'inflation_only_voxel_count': int(np.count_nonzero((inflated != 0)&(occupancy != 100))),
                'inflation_is_a_separate_mask': True,
            },
            'snapshot_service_delay_ms': metadata['snapshot_service_duration_ms'],
            'snapshot_freshness_wait_ms': metadata['snapshot_freshness_wait_ms'],
            'reference_rays': {
                **pairs_report,
                'rays': online_votes['ray_count'],
                'clipped_endpoint_count': online_votes['clipped_endpoint_count'],
                'reference_frame_stride': cfg['sampling']['reference_fusion_frame_stride'],
                'reference_pixel_stride': cfg['sampling']['reference_ray_pixel_stride'],
                'qualification': 'Deterministic subset of exact fused depth/pose inputs; visibility counts are a lower bound, not all plan_env rays.',
                'class_comparison': ray_metrics,
                'reference_archive': ref_path.relative_to(run_dir).as_posix(),
                'reference_archive_sha256': sha256(ref_path),
            },
            'pre_obstacle_free_roi': free_roi_counts,
            'fully_occluded_wall_shadow_roi': {
                'world_bounds_xyz_m': shadow_roi,
                'analytic_occlusion': shadow_occlusion,
                **shadow_counts,
                'raw_unknown_fraction': (shadow_counts['raw']['unknown']/shadow_counts['voxel_count']
                                         if shadow_counts['voxel_count'] else None),
                'raw_known_in_expected_shadow_count': (shadow_counts['raw']['free']+shadow_counts['raw']['occupied']),
                'inflation_reported_separately': True,
            },
            'obstacle_interior_classification': interior_counts,
            'occupied_surface_geometry': surface,
            'temporal_occupied_set_change': temporal,
            'qualified_same_epoch_identity': True,
        }
        reports.append(report)

    # Input-to-map fusion delay is measured from the current EGO trace, with
    # simulation-time source age and steady-clock callback cost kept distinct.
    trace = [row for row in input_report['fusion_trace'] if row.get('phase') == 'fused'
             and row.get('epoch') == first_meta['epoch'] and row.get('map_id') == first_meta['map_id']]
    source_ages = [(int(row['fusion_ros_stamp_ns'])-int(row['image_source_stamp_ns']))/1e9
                   for row in trace if row.get('fusion_ros_stamp_ns') and row.get('image_source_stamp_ns')]
    callback_durations = [(int(row['fusion_monotonic_ns'])-int(row['callback_monotonic_ns']))/1e9
                          for row in trace if row.get('fusion_monotonic_ns') and row.get('callback_monotonic_ns')]
    source_ages = np.asarray(source_ages, dtype=float)
    callback_durations = np.asarray(callback_durations, dtype=float)
    fusion_timing = {
        'fused_trace_events': int(len(trace)),
        'source_stamp_to_fusion_complete_sim_s': {
            'p50': float(np.percentile(source_ages, 50)) if len(source_ages) else None,
            'p95': float(np.percentile(source_ages, 95)) if len(source_ages) else None,
            'max': float(np.max(source_ages)) if len(source_ages) else None,
        },
        'callback_to_fusion_complete_steady_s': {
            'p50': float(np.percentile(callback_durations, 50)) if len(callback_durations) else None,
            'p95': float(np.percentile(callback_durations, 95)) if len(callback_durations) else None,
            'max': float(np.max(callback_durations)) if len(callback_durations) else None,
        },
        'semantics': 'ROS/sim source age and steady-clock callback cost are separate; neither is service response duration.',
    }

    report = {
        'schema': 'n04-map-geometry-analysis/v1',
        'run_id': run_dir.name,
        'layout_id': layout['id'],
        'status': 'measured; acceptance is determined from raw classifications and retained anomalies, without a frozen numeric map-error threshold',
        'provenance': {
            'world_manifest': 'world-manifest.json',
            'world_manifest_sha256': sha256(world_manifest_path),
            'world_sdf_sha256': sha256(run_dir/'world.sdf'),
            'truth_scene_sdf_sha256': sha256(run_dir/'truth-scene.sdf'),
            'mapping_input_report_sha256': sha256(run_dir/'inputs/mapping-inputs.json'),
            'mapping_depth_npz_sha256': sha256(arrays_file),
            'runtime_contract_sha256': sha256(run_dir/'runtime-contract.json'),
            'run_inputs_sha256': sha256(run_dir/'run-inputs.json'),
            'analysis_script_sha256': sha256(Path(__file__)),
            'captured_toolchain_sha256': captured_toolchain,
            'config_sha256': sha256(cfg_path),
            'camera_model_sha256': rig['model_sha256'],
        },
        'camera_and_map_contract': camera_contract,
        'runtime_mapping_parameters': runtime_params,
        'diagnostic_graph_scope': graph_scope,
        'trajectory_alignment': trajectory_alignment,
        'debug_truth_projection': truth_projection,
        'debug_truth_ray_reference': truth_ray_report,
        'fusion_timing': fusion_timing,
        'snapshots': reports,
        'offline_only': True,
        'online_truth_input': False,
        'qualification': 'N04 geometry/classification diagnostic only; not trajectory, clearance, flight, or formal GOAL C acceptance.',
    }
    output = run_dir/'analysis/n04-map-geometry-analysis.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir', type=Path)
    args = parser.parse_args()
    report = evaluate(args.run_dir)
    print(json.dumps({'run_id': report['run_id'], 'layout_id': report['layout_id'],
                      'snapshots': len(report['snapshots']),
                      'fusion_timing': report['fusion_timing'],
                      'analysis': 'analysis/n04-map-geometry-analysis.json'}, indent=2))


if __name__ == '__main__':
    main()
