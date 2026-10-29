#!/usr/bin/env python3
"""Read one real layout map and submit a planner-only EGO diagnostic goal.

The N04 live stack has no navigation supervisor, PX4 bridge, traj_server, or
control publisher. A resulting B-spline is observed only; this tool does not
forward it to an actuator.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time
import uuid
import xml.etree.ElementTree as ET

import numpy as np

import rclpy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from rcl_interfaces.msg import Log
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from traj_utils.msg import Bspline
from uav_interfaces.msg import MapStatus, NavigationCommand, TrajectoryCancel
from uav_interfaces.srv import GetMapStatus, QueryOccupancySphere


ROOT = Path(__file__).resolve().parents[1]


def stamp_ns(stamp):
    return int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def raw_sphere_query(snapshot, center, radius):
    """Mirror the production raw closed-cell sphere query on an archive."""
    center = np.asarray(center, dtype=float)
    origin = np.asarray(snapshot['origin_m'], dtype=float)
    occupancy = snapshot['occupancy']
    resolution = float(snapshot['resolution_m'])
    extent = np.asarray(occupancy.shape, dtype=float) * resolution
    epsilon = 1e-9
    if (center.shape != (3,) or not np.isfinite(center).all()
            or not math.isfinite(radius) or radius <= 0 or radius > 2
            or not math.isfinite(resolution) or resolution <= 0):
        return {'accepted': False, 'reason': 'invalid_query',
                'unknown_count': 0, 'free_count': 0, 'occupied_count': 0}
    lower, upper = center - radius, center + radius
    if np.any(lower <= origin) or np.any(upper >= origin + extent):
        return {'accepted': False, 'reason': 'outside_map',
                'unknown_count': 0, 'free_count': 0, 'occupied_count': 0}
    size = np.asarray(occupancy.shape, dtype=int)
    lo = np.maximum(0, np.floor((lower - origin - epsilon) / resolution).astype(int))
    hi = np.minimum(size - 1,
                    np.floor((upper - origin + epsilon) / resolution).astype(int))
    if np.any(hi < lo):
        return {'accepted': False, 'reason': 'invalid_map_geometry',
                'unknown_count': 0, 'free_count': 0, 'occupied_count': 0}
    if int(np.prod(hi - lo + 1, dtype=np.int64)) > 100000:
        return {'accepted': False, 'reason': 'query_too_large',
                'unknown_count': 0, 'free_count': 0, 'occupied_count': 0}
    axes = [np.arange(lo[axis], hi[axis] + 1) for axis in range(3)]
    xx, yy, zz = np.meshgrid(*axes, indexing='ij')
    distance_squared = np.zeros(xx.shape, dtype=float)
    for axis, index in enumerate((xx, yy, zz)):
        cell_lower = origin[axis] + index * resolution
        cell_upper = cell_lower + resolution
        distance = np.maximum(np.maximum(cell_lower - center[axis], 0.0),
                              center[axis] - cell_upper)
        distance_squared += distance * distance
    local = occupancy[lo[0]:hi[0] + 1, lo[1]:hi[1] + 1, lo[2]:hi[2] + 1]
    cells = local[distance_squared <= (radius + epsilon) ** 2]
    unknown = int(np.count_nonzero(cells == -1))
    occupied = int(np.count_nonzero(cells == 100))
    free = int(np.count_nonzero(cells == 0))
    reason = ('occupied' if occupied else 'unknown' if unknown else
              'free' if free else 'empty_query')
    return {'accepted': True, 'reason': reason,
            'unknown_count': unknown, 'free_count': free,
            'occupied_count': occupied}


def raw_line_sweep(snapshot, start, end, body_radius, speed_bound):
    """Mirror the production continuous cover used for raw curve admission."""
    start, end = np.asarray(start, dtype=float), np.asarray(end, dtype=float)
    length = float(np.linalg.norm(end - start))
    if not np.isfinite(start).all() or not np.isfinite(end).all():
        return {'free': False, 'reason': 'invalid_endpoint', 'queries': 0,
                'first_failure': None}
    if not math.isfinite(speed_bound) or speed_bound <= 0:
        return {'free': False, 'reason': 'invalid_speed_bound', 'queries': 0,
                'first_failure': None}
    duration = length / speed_bound
    resolution = float(snapshot['resolution_m'])
    count = max(1, math.ceil(speed_bound * duration / (resolution / 4.0)))
    if count > 10000:
        return {'free': False, 'reason': 'sweep_too_large', 'queries': 0,
                'first_failure': None}
    dt = duration / count
    cover_radius = body_radius + speed_bound * dt / 2.0
    for index in range(count):
        midpoint = (index + 0.5) * dt
        fraction = 0.5 if duration == 0 else midpoint / duration
        center = start + (end - start) * fraction
        result = raw_sphere_query(snapshot, center, cover_radius)
        if not result['accepted'] or result['reason'] != 'free':
            return {'free': False, 'reason': result['reason'],
                    'queries': index + 1, 'continuous_cover_radius_m': cover_radius,
                    'first_failure': {'sample_index': index,
                                      'time_s': midpoint,
                                      'center_xyz_m': center.tolist(), **result}}
    return {'free': True, 'reason': 'free', 'queries': count,
            'continuous_cover_radius_m': cover_radius, 'first_failure': None}


def archived_snapshot_certificate(run_id, expected_epoch, offsets,
                                  body_radius, hold_radius, speed_bound,
                                  offset_profile_key='planner_goal_offset_xyz_m'):
    """Require three fresh snapshots with exact fused-source camera poses."""
    run_dir = ROOT / 'artifacts/runs' / run_id
    input_path = run_dir / 'inputs/mapping-inputs.json'
    inputs = json.loads(input_path.read_text())
    run_inputs = json.loads((run_dir / 'run-inputs.json').read_text())
    profile_info = run_inputs.get('n06_observation_profile', {})
    profile_path = ROOT / profile_info.get('path', '')
    if (not profile_path.is_file()
            or sha256_file(profile_path) != profile_info.get('sha256')):
        return {'passed': False, 'reason': 'observation_profile_hash_mismatch',
                'snapshots': []}
    profile = json.loads(profile_path.read_text())
    if not profile.get('require_snapshot_goal_certificate', False):
        return {'passed': False, 'reason': 'profile_does_not_require_snapshot_certificate',
                'snapshots': []}
    configured_offset = profile.get(offset_profile_key)
    if configured_offset is None or not np.allclose(
            np.asarray(configured_offset, dtype=float), offsets,
            rtol=0.0, atol=1e-12):
        return {'passed': False, 'reason': 'goal_offset_does_not_match_profile',
                'offset_profile_key': offset_profile_key,
                'snapshots': [], 'configured_offset_xyz_m': configured_offset}

    current_planner_hash = sha256_file(ROOT / 'config/components/mapping/ego_planner.json')
    current_policy_hash = sha256_file(ROOT / 'config/components/navigation/vehicle_envelope.json')
    toolchain = run_inputs.get('toolchain_sha256', {})
    if (toolchain.get('config/components/mapping/ego_planner.json') != current_planner_hash
            or toolchain.get('config/components/navigation/vehicle_envelope.json')
            != current_policy_hash):
        return {'passed': False, 'reason': 'run_configuration_hash_mismatch',
                'snapshots': []}

    matched_identity = None
    results = []
    for name in ('snapshot-01', 'snapshot-02', 'snapshot-03'):
        snapshot_dir = run_dir / 'snapshots' / name
        metadata_path = snapshot_dir / 'metadata.json'
        archive_path = snapshot_dir / 'occupancy_snapshot.npz'
        if not metadata_path.is_file() or not archive_path.is_file():
            results.append({'snapshot': name, 'passed': False,
                            'reason': 'snapshot_artifact_missing'})
            continue
        metadata = json.loads(metadata_path.read_text())
        identity = (metadata.get('epoch'), metadata.get('map_id'),
                    metadata.get('frame_id'))
        source_stamp = int(metadata['last_fused_depth_source_stamp_ns'])
        snapshot_stamp = int(metadata['snapshot_stamp_ns'])
        fusion_stamp = int(metadata['last_fusion_stamp_ns'])
        source_age = (snapshot_stamp - source_stamp) / 1e9
        fusion_age = (snapshot_stamp - fusion_stamp) / 1e9
        valid_identity = bool(
            metadata.get('expected_epoch') == expected_epoch
            and identity[0] == expected_epoch
            and str(identity[1]).startswith(expected_epoch + '-')
            and identity[2] == 'odom_' + expected_epoch
            and metadata.get('map_status_before', {}).get('map_id') == identity[1]
            and metadata.get('map_status_after', {}).get('map_id') == identity[1]
            and metadata.get('map_status_before', {}).get('epoch') == expected_epoch
            and metadata.get('map_status_after', {}).get('epoch') == expected_epoch
            and metadata.get('map_status_before', {}).get('input_ready')
            and metadata.get('map_status_after', {}).get('input_ready')
            and metadata.get('map_status_before', {}).get('reset_acknowledged')
            and metadata.get('map_status_after', {}).get('reset_acknowledged'))
        valid_freshness = bool(0.0 <= source_age <= 0.4
                               and 0.0 <= fusion_age <= 0.4
                               and source_age <= 0.4 and fusion_age <= 0.4)
        if matched_identity is None:
            matched_identity = identity
        valid_identity = valid_identity and identity == matched_identity
        poses = [pose for pose in inputs.get('camera_poses', [])
                 if int(pose.get('stamp_ns', -1)) == source_stamp
                 and pose.get('frame_id') == identity[2]]
        source_pose = poses[0] if len(poses) == 1 else None
        result = {'snapshot': name, 'identity': {
            'epoch': identity[0], 'map_id': identity[1], 'frame_id': identity[2],
            'matches_all_three': valid_identity},
            'freshness': {'source_age_s': source_age, 'fusion_age_s': fusion_age,
                          'limit_s': 0.4, 'fresh': valid_freshness},
            'source_pose_match': {'stamp_ns': source_stamp,
                                  'exact_unique_camera_pose': source_pose is not None,
                                  'match_count': len(poses)}}
        if source_pose is not None:
            try:
                with np.load(archive_path, allow_pickle=False) as archive:
                    occupancy = np.asarray(archive['occupancy'], dtype=np.int8)
                expected_shape = tuple(int(v) for v in metadata['dimensions_xyz'])
                archive_valid = bool(occupancy.shape == expected_shape
                                     and np.isin(occupancy, (-1, 0, 100)).all())
                if archive_valid:
                    snapshot = {'occupancy': occupancy,
                                'origin_m': metadata['origin_m'],
                                'resolution_m': metadata['resolution_m']}
                    start = np.asarray(source_pose['position'], dtype=float)
                    target = start + np.asarray(offsets, dtype=float)
                    body = raw_sphere_query(snapshot, start, body_radius)
                    sweep = raw_line_sweep(snapshot, start, target,
                                           body_radius, speed_bound)
                    hold = raw_sphere_query(snapshot, target,
                                            body_radius + hold_radius)
                else:
                    body = {'accepted': False, 'reason': 'invalid_archive_geometry'}
                    sweep = {'free': False, 'reason': 'invalid_archive_geometry',
                             'queries': 0, 'first_failure': None}
                    hold = {'accepted': False, 'reason': 'invalid_archive_geometry'}
                result.update({'archive': {'path': str(archive_path.relative_to(ROOT)),
                                           'sha256': sha256_file(archive_path),
                                           'valid': archive_valid},
                               'source_pose_xyz_m': start.tolist(),
                               'target_xyz_m': target.tolist(),
                               'body_sphere': body, 'continuous_sweep': sweep,
                               'terminal_hold': hold})
                result['passed'] = bool(
                    archive_valid and valid_identity and valid_freshness
                    and body.get('accepted') and body.get('reason') == 'free'
                    and sweep.get('free')
                    and hold.get('accepted') and hold.get('reason') == 'free')
                result['reason'] = 'free' if result['passed'] else 'raw_predicate_rejected'
            except (OSError, ValueError, KeyError) as error:
                result.update({'passed': False,
                               'reason': f'snapshot_read_failed:{error}'})
        else:
            result.update({'passed': False, 'reason': 'source_pose_not_uniquely_matched'})
        results.append(result)
    passed = len(results) == 3 and all(item.get('passed') for item in results)
    return {'passed': passed,
            'reason': 'all_three_source_matched_snapshots_free' if passed else
                      'one_or_more_snapshot_certificates_failed',
            'policy': 'raw occupancy only; body sphere, continuous sweep, and terminal hold all require known free',
            'snapshot_count': len(results), 'snapshots': results}


def live_query_record(response, expected_epoch, expected_map_id, frame):
    return {
        'accepted': bool(response.accepted), 'free': bool(response.free),
        'reason': response.reason,
        'epoch': response.epoch, 'map_id': response.map_id,
        'frame_id': response.header.frame_id,
        'identity_matches': (response.epoch == expected_epoch
                             and response.map_id == expected_map_id
                             and response.header.frame_id == frame),
        'unknown_count': int(response.unknown_count),
        'occupied_count': int(response.occupied_count),
        'free_count': int(response.free_count),
    }


def live_sweep_certificate(node, expected_epoch, expected_map_id, frame,
                           start, end, body_radius, hold_radius, speed_bound,
                           map_resolution, body_query):
    """Repeat all three raw predicates against the current identity-bound map."""
    start, end = np.asarray(start, dtype=float), np.asarray(end, dtype=float)
    length = float(np.linalg.norm(end - start))
    resolution = float(map_resolution)
    duration = length / speed_bound
    count = max(1, math.ceil(speed_bound * duration / (resolution / 4.0)))
    query_results = []
    failure = None
    for index in range(count):
        midpoint = (index + 0.5) * duration / count
        fraction = 0.5 if duration == 0 else midpoint / duration
        center = start + (end - start) * fraction
        request = QueryOccupancySphere.Request()
        request.expected_epoch = expected_epoch
        request.expected_map_id = expected_map_id
        request.frame_id = frame
        request.center.x, request.center.y, request.center.z = center.tolist()
        request.radius_m = body_radius + speed_bound * duration / count / 2.0
        try:
            response = node.call(node.query_client, request)
            record = live_query_record(response, expected_epoch, expected_map_id, frame)
        except (RuntimeError, TimeoutError) as error:
            record = {'accepted': False, 'free': False,
                      'reason': f'query_failed:{error}',
                      'identity_matches': False}
        query_results.append(record)
        if not record.get('accepted') or not record.get('free') \
                or not record.get('identity_matches'):
            failure = {'sample_index': index, 'center_xyz_m': center.tolist(),
                       'radius_m': request.radius_m, **record}
            break
    hold_request = QueryOccupancySphere.Request()
    hold_request.expected_epoch = expected_epoch
    hold_request.expected_map_id = expected_map_id
    hold_request.frame_id = frame
    hold_request.center.x, hold_request.center.y, hold_request.center.z = end.tolist()
    hold_request.radius_m = body_radius + hold_radius
    try:
        hold_response = node.call(node.query_client, hold_request)
        hold = live_query_record(hold_response, expected_epoch, expected_map_id, frame)
    except (RuntimeError, TimeoutError) as error:
        hold = {'accepted': False, 'free': False,
                'reason': f'query_failed:{error}', 'identity_matches': False}
    body_free = bool(body_query.get('accepted') and body_query.get('free')
                     and body_query.get('epoch') == expected_epoch
                     and body_query.get('map_id') == expected_map_id
                     and body_query.get('frame_id') == frame)
    sweep_free = failure is None and len(query_results) == count
    hold_free = bool(hold.get('accepted') and hold.get('free')
                     and hold.get('identity_matches'))
    return {'passed': body_free and sweep_free and hold_free,
            'body_sphere_free': body_free,
            'continuous_sweep_free': sweep_free,
            'terminal_hold_free': hold_free,
            'continuous_sweep': {'query_count': count,
                                 'queries_completed': len(query_results),
                                 'speed_bound_m_s': speed_bound,
                                 'body_radius_m': body_radius,
                                 'terminal_hold_radius_m': body_radius + hold_radius,
                                 'first_failure': failure,
                                 'failed_query_count': sum(
                                     not item.get('free') for item in query_results)},
            'terminal_hold': hold}


def status_record(status):
    return {
        'epoch': status.epoch, 'map_id': status.map_id,
        'frame_id': status.header.frame_id,
        'input_ready': bool(status.input_ready),
        'reset_acknowledged': bool(status.reset_acknowledged),
        'reason': status.reason,
        'last_depth_source_stamp_ns': stamp_ns(status.last_depth_source_stamp),
        'last_occupancy_stamp_ns': stamp_ns(status.last_occupancy_stamp),
        'forwarded_depth_count': int(status.forwarded_depth_count),
    }


def curve_record(msg):
    control_points = [[float(p.x), float(p.y), float(p.z)] for p in msg.pos_pts]
    return {
        'goal_id': msg.goal_id, 'epoch': msg.epoch,
        'traj_id': int(msg.traj_id), 'order': int(msg.order),
        'start_time_ns': stamp_ns(msg.start_time),
        'knots': [float(v) for v in msg.knots],
        'position_control_points': control_points,
        'planned_start_xyz_m': control_points[0] if control_points else None,
        'planned_end_xyz_m': control_points[-1] if control_points else None,
        'yaw_points': [float(v) for v in msg.yaw_pts],
        'yaw_dt': float(msg.yaw_dt),
    }


def live_map_gate(node, status_request, expected_epoch, expected_map_id, frame):
    response = node.call(node.status_client, status_request)
    status = status_record(response.status)
    now_ns = node.get_clock().now().nanoseconds
    source_age = (now_ns - status['last_depth_source_stamp_ns']) / 1e9
    fusion_age = (now_ns - status['last_occupancy_stamp_ns']) / 1e9
    identity_matches = bool(status['epoch'] == expected_epoch
                            and status['map_id'] == expected_map_id
                            and status['frame_id'] == frame)
    fresh = bool(0 <= source_age <= 0.4 and 0 <= fusion_age <= 0.4)
    ready = bool(response.accepted and identity_matches and fresh
                 and status['input_ready'] and status['reset_acknowledged'])
    return status, {'accepted': bool(response.accepted),
                    'identity_matches': identity_matches,
                    'source_age_sim_s': source_age,
                    'fusion_age_sim_s': fusion_age,
                    'limit_sim_s': 0.4, 'fresh': fresh, 'ready': ready}, ready


def load_dynamic_obstacle_profile(run_id):
    run_dir = ROOT / 'artifacts/runs' / run_id
    run_inputs = json.loads((run_dir / 'run-inputs.json').read_text())
    profile_info = run_inputs.get('n06_observation_profile', {})
    profile_path = ROOT / profile_info.get('path', '')
    if not profile_path.is_file() or sha256_file(profile_path) != profile_info.get('sha256'):
        raise RuntimeError('observation profile is missing or its locked hash changed')
    profile = json.loads(profile_path.read_text())
    return profile.get('dynamic_obstacle_after_curve')


def _query_raw_sphere(node, expected_epoch, expected_map_id, frame, center, radius):
    request = QueryOccupancySphere.Request()
    request.expected_epoch = expected_epoch
    request.expected_map_id = expected_map_id
    request.frame_id = frame
    request.center.x, request.center.y, request.center.z = [float(v) for v in center]
    request.radius_m = float(radius)
    response = node.call(node.query_client, request)
    return live_query_record(response, expected_epoch, expected_map_id, frame)


def _spawn_static_box(run_id, config):
    import gz.transport13 as transport
    from gz.msgs10.boolean_pb2 import Boolean
    from gz.msgs10.entity_factory_pb2 import EntityFactory

    model_name = str(config['model_name'])
    if not model_name or any(ch not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_' for ch in model_name):
        raise ValueError('dynamic obstacle model name must be a simple Gazebo identifier')
    pose = [float(v) for v in config['world_pose_xyz_m']]
    size = [float(v) for v in config['size_xyz_m']]
    if (len(pose) != 3 or len(size) != 3
            or not all(math.isfinite(v) for v in pose)
            or not all(math.isfinite(v) and v > 0 for v in size)):
        raise ValueError('dynamic obstacle pose and size must be finite 3D values')
    sdf = ET.Element('sdf', version='1.9')
    model = ET.SubElement(sdf, 'model', name=model_name)
    ET.SubElement(model, 'static').text = 'true'
    ET.SubElement(model, 'pose').text = ' '.join(map(str, (*pose, 0.0, 0.0, 0.0)))
    link = ET.SubElement(model, 'link', name='body')
    collision = ET.SubElement(link, 'collision', name='collision')
    collision_geometry = ET.SubElement(collision, 'geometry')
    ET.SubElement(collision_geometry, 'box')
    ET.SubElement(collision_geometry.find('box'), 'size').text = ' '.join(map(str, size))
    visual = ET.SubElement(link, 'visual', name='visual')
    visual_geometry = ET.SubElement(visual, 'geometry')
    ET.SubElement(visual_geometry, 'box')
    ET.SubElement(visual_geometry.find('box'), 'size').text = ' '.join(map(str, size))
    material = ET.SubElement(visual, 'material')
    ET.SubElement(material, 'ambient').text = '0.82 0.22 0.08 1'
    ET.SubElement(material, 'diffuse').text = '0.82 0.22 0.08 1'
    ET.indent(sdf)
    run_dir = ROOT / 'artifacts/runs' / run_id
    sdf_path = run_dir / 'n06-dynamic-obstacle.sdf'
    if sdf_path.exists():
        raise FileExistsError(sdf_path)
    sdf_path.write_text(ET.tostring(sdf, encoding='unicode') + '\n')
    gz_node = transport.Node()
    request = EntityFactory()
    request.sdf_filename = str(sdf_path)
    success, response = gz_node.request(
        '/world/sensor_calibration/create', request, EntityFactory, Boolean, 3000)
    if not success or response is None or not response.data:
        raise RuntimeError('Gazebo rejected dynamic obstacle creation')
    return {'model_name': model_name, 'sdf_path': str(sdf_path.relative_to(ROOT)),
            'sdf_sha256': sha256_file(sdf_path), 'world_pose_xyz_m': pose,
            'size_xyz_m': size, 'create_service_acknowledged': bool(response.data)}


def inject_dynamic_obstacle_after_curve(node, run_id, config, expected_epoch,
                                        expected_map_id, frame, target_xyz,
                                        body_radius, hold_radius):
    result = {'enabled': True, 'spawned': False, 'passed': False}
    before_request = GetMapStatus.Request()
    before_request.expected_epoch = expected_epoch
    before_status, before_freshness, before_ready = live_map_gate(
        node, before_request, expected_epoch, expected_map_id, frame)
    result['map_status_before'] = before_status
    result['map_freshness_before'] = before_freshness
    if not before_ready:
        result['reason'] = 'map_identity_readiness_or_freshness_changed_before_injection'
        return result

    verification_center = [float(v) for v in config['verification_query_center_xyz_m']]
    verification_radius = float(config['verification_query_radius_m'])
    query_before = _query_raw_sphere(node, expected_epoch, expected_map_id,
                                     frame, verification_center, verification_radius)
    result['injection_site_query_before'] = query_before
    if (not query_before.get('accepted') or not query_before.get('identity_matches')
            or query_before.get('reason') != 'free'):
        result['reason'] = 'injection_site_not_known_free_before_obstacle'
        return result

    curve_count_before = len(node.curves)
    fault_count_before = len(node.faults)
    log_count_before = len(node.logs)
    mapping_stack_log = ROOT / 'artifacts/runs' / run_id / 'mapping-stack.log'
    mapping_log_before = (mapping_stack_log.read_text(errors='replace')
                         if mapping_stack_log.is_file() else '')
    spawn_result = _spawn_static_box(run_id, config)
    result['spawn'] = spawn_result
    result['spawned'] = True

    map_deadline = time.monotonic() + float(config.get('map_wait_timeout_wall_s', 8.0))
    observed_query = None
    status_after_spawn = None
    freshness_after_spawn = None
    status_accepted_after_spawn = False
    while time.monotonic() < map_deadline:
        status_request = GetMapStatus.Request()
        status_request.expected_epoch = expected_epoch
        status_after_spawn, freshness_after_spawn, map_ready_after_spawn = live_map_gate(
            node, status_request, expected_epoch, expected_map_id, frame)
        status_accepted_after_spawn = freshness_after_spawn['accepted']
        observed_query = _query_raw_sphere(
            node, expected_epoch, expected_map_id, frame,
            verification_center, verification_radius)
        if (map_ready_after_spawn and observed_query.get('accepted')
                and observed_query.get('identity_matches')
                and observed_query.get('reason') == 'occupied'):
            break
        rclpy.spin_once(node, timeout_sec=0.05)
    result['map_status_after_spawn'] = status_after_spawn
    result['map_freshness_after_spawn'] = freshness_after_spawn
    result['map_status_accepted_after_spawn'] = status_accepted_after_spawn
    result['injection_site_query_after'] = observed_query
    result['obstacle_observed_raw_occupied'] = bool(
        observed_query and observed_query.get('accepted')
        and observed_query.get('identity_matches')
        and observed_query.get('reason') == 'occupied')

    current_odom = node.odom
    if current_odom is not None:
        current_pose = current_odom.pose.pose
        current_xyz = [float(current_pose.position.x),
                       float(current_pose.position.y),
                       float(current_pose.position.z)]
        current_odom_age = (node.get_clock().now().nanoseconds
                            - stamp_ns(current_odom.header.stamp)) / 1e9
        result['current_odom_freshness'] = {
            'frame_matches': current_odom.header.frame_id == frame,
            'age_sim_s': current_odom_age, 'limit_sim_s': 0.4,
            'fresh': bool(current_odom.header.frame_id == frame
                          and 0 <= current_odom_age <= 0.4)}
        result['current_hold_after'] = _query_raw_sphere(
            node, expected_epoch, expected_map_id, frame,
            current_xyz, body_radius + hold_radius)
        result['current_pose_xyz_m'] = current_xyz
    result['goal_hold_after'] = _query_raw_sphere(
        node, expected_epoch, expected_map_id, frame,
        target_xyz, body_radius + hold_radius)
    result['target_xyz_m'] = [float(v) for v in target_xyz]

    safety_deadline = time.monotonic() + float(
        config.get('safety_event_timeout_wall_s', 5.0))
    mapping_log_delta = ''
    transition_lines = []
    while time.monotonic() < safety_deadline:
        rclpy.spin_once(node, timeout_sec=0.03)
        mapping_log_now = (mapping_stack_log.read_text(errors='replace')
                           if mapping_stack_log.is_file() else '')
        mapping_log_delta = mapping_log_now[len(mapping_log_before):]
        transition_lines = [line.strip() for line in mapping_log_delta.splitlines()
                            if 'from ' in line and ' to ' in line]
        if (any('to EMERGENCY_STOP' in line for line in transition_lines)
                or len(node.faults) > fault_count_before):
            break
    emergency_transition_lines = [line for line in transition_lines
                                  if 'to EMERGENCY_STOP' in line]
    active_curve_blocked_log = any(
        'Active curve blocked by map' in item['message']
        for item in node.logs[log_count_before:])
    emergency_transition_observed = bool(emergency_transition_lines)
    event_observed = bool(active_curve_blocked_log and emergency_transition_observed)
    curves_at_transition = (len(node.curves)
                            if emergency_transition_observed else None)
    if event_observed:
        quiet_deadline = time.monotonic() + 0.5
        while time.monotonic() < quiet_deadline:
            rclpy.spin_once(node, timeout_sec=0.03)
        mapping_log_now = (mapping_stack_log.read_text(errors='replace')
                           if mapping_stack_log.is_file() else '')
        mapping_log_delta = mapping_log_now[len(mapping_log_before):]
        transition_lines = [line.strip() for line in mapping_log_delta.splitlines()
                            if 'from ' in line and ' to ' in line]
        emergency_transition_lines = [line for line in transition_lines
                                      if 'to EMERGENCY_STOP' in line]
        emergency_transition_observed = bool(emergency_transition_lines)
    result['safety_event_observed'] = bool(event_observed)
    result['active_curve_blocked_log_observed'] = active_curve_blocked_log
    result['emergency_transition_observed'] = emergency_transition_observed
    result['emergency_transition_lines'] = emergency_transition_lines
    result['safety_logs'] = node.logs[log_count_before:]
    result['faults_after_injection'] = [
        {'goal_id': fault.goal_id, 'epoch': fault.epoch,
         'mode': int(fault.mode), 'reason': fault.reason}
        for fault in node.faults[fault_count_before:]]
    result['curves_after_injection'] = node.curves[curve_count_before:]
    result['curve_count_at_emergency_transition'] = curves_at_transition
    result['post_transition_curve_count'] = (
        max(0, len(node.curves) - curves_at_transition)
        if emergency_transition_observed else None)
    result['stationary_curves_after_injection'] = [
        curve for curve in result['curves_after_injection']
        if curve.get('position_control_points')
        and max(float(np.linalg.norm(np.asarray(point, dtype=float)
                                     - np.asarray(curve['position_control_points'][0], dtype=float)))
                for point in curve['position_control_points']) <= 0.02]
    result['nonstationary_curves_after_injection'] = [
        curve for curve in result['curves_after_injection']
        if curve not in result['stationary_curves_after_injection']]
    result['hold_curve_certificate_free'] = any(
        'Full-curve certificate metrics' in item.get('message', '')
        and 'reason=free' in item.get('message', '')
        for item in result['safety_logs'])
    result['mapping_log_transitions_after_injection'] = transition_lines
    result['map_identity_stable'] = bool(
        status_after_spawn
        and status_after_spawn.get('epoch') == expected_epoch
        and status_after_spawn.get('map_id') == expected_map_id
        and status_after_spawn.get('frame_id') == frame
        and status_after_spawn.get('input_ready')
        and status_after_spawn.get('reset_acknowledged'))
    result['map_fresh_after_spawn'] = bool(
        freshness_after_spawn and freshness_after_spawn.get('ready'))
    result['current_hold_fresh_free'] = bool(
        result.get('current_odom_freshness', {}).get('fresh')
        and result.get('current_hold_after', {}).get('accepted')
        and result.get('current_hold_after', {}).get('identity_matches')
        and result.get('current_hold_after', {}).get('reason') == 'free')
    result['goal_hold_blocked'] = bool(
        result.get('goal_hold_after', {}).get('accepted')
        and result.get('goal_hold_after', {}).get('identity_matches')
        and result.get('goal_hold_after', {}).get('reason') == 'occupied')
    result['passed'] = bool(
        result['spawned'] and result['obstacle_observed_raw_occupied']
        and result['map_identity_stable'] and result['map_fresh_after_spawn']
        and result['current_hold_fresh_free'] and result['goal_hold_blocked']
        and result['active_curve_blocked_log_observed']
        and result['emergency_transition_observed']
        and bool(result['stationary_curves_after_injection'])
        and result['hold_curve_certificate_free']
        and not result['nonstationary_curves_after_injection'])
    if not result['passed']:
        result['reason'] = 'dynamic_obstacle_did_not_produce_certified_safety_response'
    return result


class LiveLayoutProbe(Node):
    def __init__(self):
        super().__init__('n06_live_layout_probe',
                         parameter_overrides=[rclpy.parameter.Parameter(
                             'use_sim_time', value=True)])
        self.status_client = self.create_client(GetMapStatus, '/mapping/get_map_status')
        self.query_client = self.create_client(QueryOccupancySphere,
                                               '/mapping/query_occupancy_sphere')
        self.odom = None
        self.curves = []
        self.faults = []
        self.logs = []
        self.create_subscription(Odometry, '/localization/optimized_imu_odom',
                                 self._on_odom, 20)
        self.create_subscription(Bspline, '/drone_0_planning/bspline',
                                 lambda msg: self.curves.append(curve_record(msg)), 20)
        self.create_subscription(TrajectoryCancel, '/navigation/planner_fault',
                                 self.faults.append, 20)
        reliable = QoSProfile(depth=1000, reliability=ReliabilityPolicy.RELIABLE)
        self.create_subscription(Log, '/rosout', self._on_log, reliable)
        self.goal_pub = self.create_publisher(NavigationCommand,
                                              '/navigation/ego_goal', 10)

    def _on_odom(self, msg):
        self.odom = msg

    def _on_log(self, msg):
        if ('Full-curve' in msg.msg or 'reboundReplan' in msg.msg
                or 'Unable to' in msg.msg or 'Active curve blocked' in msg.msg
                or 'EMERGENCY_STOP' in msg.msg or 'FULL_CURVE_BLOCKED' in msg.msg
                or 'Suddenly discovered obstacles' in msg.msg):
            self.logs.append({'stamp_ns': stamp_ns(msg.stamp),
                              'name': msg.name, 'level': int(msg.level),
                              'message': msg.msg})

    def spin_until(self, predicate, timeout_s, label):
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.03)
            if predicate():
                return True
        return False

    def call(self, client, request, timeout_s=3.0):
        future = client.call_async(request)
        if not self.spin_until(future.done, timeout_s, 'service response'):
            raise TimeoutError(f'service timed out: {client.srv_name}')
        response = future.result()
        if response is None:
            raise RuntimeError(f'service returned no response: {client.srv_name}')
        return response


def run(args):
    session_path = ROOT / 'artifacts/runs' / (args.run_id + '-stack') / 'session/session.json'
    session = json.loads(session_path.read_text())
    expected_epoch = session['epoch']
    dynamic_obstacle_config = load_dynamic_obstacle_profile(args.run_id)
    envelope = json.loads((ROOT / 'config/components/navigation/vehicle_envelope.json').read_text())
    body_radius = float(envelope['spatial_budget']['body_reference_clearance_radius_m'])
    hold_radius = float(envelope['map_policy']['terminal_hold_neighborhood_radius_m'])
    map_resolution = float(envelope['spatial_budget']['map_resolution_m'])
    planner = json.loads((ROOT / 'config/components/mapping/ego_planner.json').read_text())
    speed_bound = float(planner['max_velocity_m_s'])
    offsets = [args.target_dx_m, args.target_dy_m, args.target_dz_m]
    handoff_offsets = (None if args.handoff_target_dy_m is None else
                       [args.handoff_target_dx_m, args.handoff_target_dy_m,
                        args.handoff_target_dz_m])
    snapshot_certificate = None
    handoff_snapshot_certificate = None
    if args.require_snapshot_certificate:
        try:
            snapshot_certificate = archived_snapshot_certificate(
                args.run_id, expected_epoch, offsets, body_radius, hold_radius,
                speed_bound)
        except (OSError, ValueError, KeyError, TypeError) as error:
            snapshot_certificate = {'passed': False,
                                    'reason': f'snapshot_gate_error:{error}',
                                    'snapshots': []}
        if handoff_offsets is not None:
            try:
                handoff_snapshot_certificate = archived_snapshot_certificate(
                    args.run_id, expected_epoch, handoff_offsets,
                    body_radius, hold_radius, speed_bound,
                    offset_profile_key='planner_handoff_goal_offset_xyz_m')
            except (OSError, ValueError, KeyError, TypeError) as error:
                handoff_snapshot_certificate = {
                    'passed': False,
                    'reason': f'snapshot_gate_error:{error}', 'snapshots': []}
    rclpy.init()
    node = LiveLayoutProbe()
    try:
        if not node.status_client.wait_for_service(timeout_sec=15.0):
            raise TimeoutError('MapStatus service is unavailable')
        if not node.query_client.wait_for_service(timeout_sec=15.0):
            raise TimeoutError('raw occupancy sphere service is unavailable')
        if not node.spin_until(lambda: node.odom is not None, 10.0, 'VINS odometry'):
            raise TimeoutError('fresh VINS odometry was not received')

        status_request = GetMapStatus.Request()
        status_request.expected_epoch = expected_epoch
        before_response = node.call(node.status_client, status_request)
        status_before = status_record(before_response.status)
        odom_wait_started = time.monotonic()

        def has_fresh_odom():
            if node.odom is None:
                return False
            current_stamp = stamp_ns(node.odom.header.stamp)
            age = (node.get_clock().now().nanoseconds - current_stamp) / 1e9
            return (0.0 <= age <= 0.4
                    and node.odom.header.frame_id == 'odom_' + expected_epoch)

        fresh_odom_observed = node.spin_until(
            has_fresh_odom, 2.0, 'fresh identity-matched VINS odometry')
        odom_freshness_wait_wall_s = time.monotonic() - odom_wait_started
        now_ns = node.get_clock().now().nanoseconds
        source_age = (now_ns - status_before['last_depth_source_stamp_ns']) / 1e9
        fusion_age = (now_ns - status_before['last_occupancy_stamp_ns']) / 1e9
        odom = node.odom
        pose = odom.pose.pose
        position = [float(pose.position.x), float(pose.position.y), float(pose.position.z)]
        frame = odom.header.frame_id
        odom_age = (now_ns - stamp_ns(odom.header.stamp)) / 1e9
        map_ready = bool(
            before_response.accepted and status_before['epoch'] == expected_epoch
            and status_before['map_id'].startswith(expected_epoch + '-')
            and status_before['frame_id'] == 'odom_' + expected_epoch
            and status_before['input_ready'] and status_before['reset_acknowledged']
            and 0 <= source_age <= 0.4 and 0 <= fusion_age <= 0.4
            and frame == 'odom_' + expected_epoch
            and fresh_odom_observed
            and (not args.require_snapshot_certificate
                 or 0 <= odom_age <= 0.4))

        query = QueryOccupancySphere.Request()
        query.expected_epoch = expected_epoch
        query.expected_map_id = status_before['map_id']
        query.frame_id = frame
        query.center.x, query.center.y, query.center.z = position
        query.radius_m = body_radius
        pose_response = node.call(node.query_client, query)
        pose_query = {
            **live_query_record(pose_response, expected_epoch,
                                status_before['map_id'], frame),
            'body_center_xyz_m': position, 'radius_m': body_radius,
        }

        graph_nodes = sorted(node.get_node_names())
        graph_topics = sorted(name for name, _types in node.get_topic_names_and_types())
        forbidden_nodes = [name for name in graph_nodes
                           if any(token in name.lower() for token in
                                  ('px4', 'uav_px4_bridge', 'controller',
                                   'traj_server', 'navigation_supervisor'))]
        forbidden_topics = [name for name in graph_topics
                            if name.startswith('/fmu/') or name.startswith('/navigation/setpoint')]
        control_free_graph = not forbidden_nodes and not forbidden_topics
        goal_id = uuid.uuid4().hex
        goal_record = {'published': False, 'goal_id': goal_id}
        live_certificate = None
        if args.require_snapshot_certificate:
            target_position = (np.asarray(position, dtype=float)
                               + np.asarray(offsets, dtype=float))
            live_certificate = live_sweep_certificate(
                node, expected_epoch, status_before['map_id'], frame,
                position, target_position, body_radius, hold_radius,
                speed_bound, map_resolution, pose_query)
            prepublish_response = node.call(node.status_client, status_request)
            prepublish_status = status_record(prepublish_response.status)
            prepublish_now_ns = node.get_clock().now().nanoseconds
            prepublish_source_age = (
                prepublish_now_ns - prepublish_status['last_depth_source_stamp_ns']) / 1e9
            prepublish_fusion_age = (
                prepublish_now_ns - prepublish_status['last_occupancy_stamp_ns']) / 1e9
            prepublish_ready = bool(
                prepublish_response.accepted
                and prepublish_status['epoch'] == expected_epoch
                and prepublish_status['map_id'] == status_before['map_id']
                and prepublish_status['frame_id'] == frame
                and prepublish_status['input_ready']
                and prepublish_status['reset_acknowledged']
                and 0 <= prepublish_source_age <= 0.4
                and 0 <= prepublish_fusion_age <= 0.4)
            snapshot_ready = bool(snapshot_certificate
                                  and snapshot_certificate.get('passed'))
            gated_ready = bool(map_ready and control_free_graph
                               and live_certificate['passed']
                               and prepublish_ready and snapshot_ready)
            goal_record['prepublish_map_status'] = prepublish_status
            goal_record['prepublish_freshness'] = {
                'source_age_sim_s': prepublish_source_age,
                'fusion_age_sim_s': prepublish_fusion_age,
                'limit_sim_s': 0.4, 'ready': prepublish_ready}
            goal_record['snapshot_certificate_passed'] = snapshot_ready
            goal_record['live_certificate_passed'] = live_certificate['passed']
            goal_record['live_certificate'] = live_certificate
        else:
            gated_ready = bool(map_ready and control_free_graph)

        has_goal_subscriber = (gated_ready and node.spin_until(
            lambda: node.goal_pub.get_subscription_count() > 0,
            5.0, 'EGO goal subscriber'))
        if gated_ready and has_goal_subscriber:
            command = NavigationCommand()
            command.goal_id = goal_id
            command.epoch = expected_epoch
            command.map_id = status_before['map_id']
            command.target.header.frame_id = frame
            command.target.header.stamp = node.get_clock().now().to_msg()
            command.target.pose.position.x = position[0] + args.target_dx_m
            command.target.pose.position.y = position[1] + args.target_dy_m
            command.target.pose.position.z = position[2] + args.target_dz_m
            command.target.pose.orientation = pose.orientation
            before_curves = len(node.curves)
            before_faults = len(node.faults)
            node.goal_pub.publish(command)
            goal_record.update({'published': True,
                                'target_xyz_m': [command.target.pose.position.x,
                                                 command.target.pose.position.y,
                                                 command.target.pose.position.z],
                                'map_id': status_before['map_id'],
                                'epoch': expected_epoch,
                                'qualification': 'planner only; no bridge, traj_server, PX4, or control subscriber'})
            goal_record['event_observed'] = node.spin_until(
                lambda: len(node.curves) > before_curves
                or len(node.faults) > before_faults,
                args.observe_s, 'curve or planner fault')
            goal_record['new_curves'] = [
                curve for curve in node.curves[before_curves:]
                if curve['goal_id'] == goal_id]
            goal_record['new_faults'] = [
                {'goal_id': fault.goal_id, 'epoch': fault.epoch,
                 'mode': int(fault.mode), 'reason': fault.reason}
                for fault in node.faults[before_faults:]]
            goal_record['certificate_logs'] = node.logs[:]
            if goal_record['new_curves']:
                encoded = json.dumps(goal_record['new_curves'][0], sort_keys=True,
                                     separators=(',', ':')).encode()
                goal_record['curve_sha256'] = sha256_bytes(encoded)
            matching_faults = [fault for fault in node.faults[before_faults:]
                               if fault.goal_id == goal_id]
            if matching_faults:
                late_deadline = time.monotonic() + 0.5
                curves_at_fault = len(node.curves)
                while time.monotonic() < late_deadline:
                    rclpy.spin_once(node, timeout_sec=0.03)
                goal_record['late_curves_after_fault'] = max(
                    0, len(node.curves) - curves_at_fault)
            else:
                goal_record['late_curves_after_fault'] = 0
        else:
            if not control_free_graph:
                goal_record['reason'] = 'control_node_or_topic_present'
            elif args.require_snapshot_certificate and not snapshot_certificate.get('passed', False):
                goal_record['reason'] = 'source_matched_snapshot_certificate_failed'
            elif args.require_snapshot_certificate and live_certificate is not None \
                    and not live_certificate.get('passed', False):
                goal_record['reason'] = 'live_raw_certificate_failed'
            elif args.require_snapshot_certificate and not prepublish_ready:
                goal_record['reason'] = 'live_map_identity_or_freshness_failed'
            elif not map_ready:
                goal_record['reason'] = 'live_map_or_odometry_not_ready'
            elif not has_goal_subscriber:
                goal_record['reason'] = 'live_map_or_goal_subscriber_not_ready'
            else:
                goal_record['reason'] = 'goal_gate_failed'

        if dynamic_obstacle_config is not None:
            if goal_record.get('published') and goal_record.get('new_curves'):
                target_xyz = goal_record['target_xyz_m']
                goal_record['dynamic_obstacle'] = inject_dynamic_obstacle_after_curve(
                    node, args.run_id, dynamic_obstacle_config, expected_epoch,
                    status_before['map_id'], frame, target_xyz,
                    body_radius, hold_radius)
            else:
                goal_record['dynamic_obstacle'] = {
                    'enabled': True, 'spawned': False, 'passed': False,
                    'reason': 'initial_goal_did_not_produce_a_certified_curve'}

        handoff_record = None
        if handoff_offsets is not None:
            handoff_record = {
                'requested': True, 'published': False,
                'goal_id': uuid.uuid4().hex,
                'offset_xyz_m': handoff_offsets,
                'archived_snapshot_certificate': handoff_snapshot_certificate,
                'source_curve_goal_id': goal_id,
                'source_curve_traj_id': (goal_record['new_curves'][0]['traj_id']
                                         if goal_record.get('new_curves') else None),
            }
            initial_curve_available = bool(
                goal_record.get('published') and goal_record.get('new_curves')
                and not goal_record.get('new_faults'))
            if not initial_curve_available:
                handoff_record['reason'] = 'initial_goal_did_not_produce_a_certified_curve'
            else:
                # Let the FSM settle into EXEC_TRAJ before queuing the replacement.
                settle_deadline = time.monotonic() + 0.2
                while time.monotonic() < settle_deadline:
                    rclpy.spin_once(node, timeout_sec=0.02)

                current_odom = node.odom
                current_pose = current_odom.pose.pose
                handoff_start = [float(current_pose.position.x),
                                 float(current_pose.position.y),
                                 float(current_pose.position.z)]
                handoff_frame = current_odom.header.frame_id
                handoff_record['start_xyz_m'] = handoff_start
                handoff_record['frame_id'] = handoff_frame
                handoff_record['odom_stamp_ns'] = stamp_ns(current_odom.header.stamp)
                handoff_record['odometry_age_sim_s'] = (
                    node.get_clock().now().nanoseconds
                    - stamp_ns(current_odom.header.stamp)) / 1e9
                handoff_record['control_free_graph'] = control_free_graph

                try:
                    handoff_body_request = QueryOccupancySphere.Request()
                    handoff_body_request.expected_epoch = expected_epoch
                    handoff_body_request.expected_map_id = status_before['map_id']
                    handoff_body_request.frame_id = handoff_frame
                    handoff_body_request.center.x, handoff_body_request.center.y, \
                        handoff_body_request.center.z = handoff_start
                    handoff_body_request.radius_m = body_radius
                    handoff_body_response = node.call(node.query_client,
                                                       handoff_body_request)
                    handoff_body_query = {
                        **live_query_record(handoff_body_response, expected_epoch,
                                            status_before['map_id'], handoff_frame),
                        'body_center_xyz_m': handoff_start,
                        'radius_m': body_radius,
                    }
                    handoff_live_certificate = live_sweep_certificate(
                        node, expected_epoch, status_before['map_id'], handoff_frame,
                        handoff_start,
                        np.asarray(handoff_start, dtype=float)
                        + np.asarray(handoff_offsets, dtype=float),
                        body_radius, hold_radius, speed_bound, map_resolution,
                        handoff_body_query)
                    handoff_record['body_query'] = handoff_body_query
                    handoff_record['live_certificate'] = handoff_live_certificate
                    prepublish_status, prepublish_freshness, prepublish_ready = \
                        live_map_gate(node, status_request, expected_epoch,
                                      status_before['map_id'], handoff_frame)
                    handoff_record['prepublish_map_status'] = prepublish_status
                    handoff_record['prepublish_freshness'] = prepublish_freshness
                    handoff_record['snapshot_certificate_passed'] = bool(
                        handoff_snapshot_certificate
                        and handoff_snapshot_certificate.get('passed'))
                    handoff_gate_ready = bool(
                        handoff_record['snapshot_certificate_passed']
                        and handoff_live_certificate.get('passed')
                        and prepublish_ready and control_free_graph
                        and handoff_frame == 'odom_' + expected_epoch
                        and (not args.require_snapshot_certificate
                             or 0 <= handoff_record['odometry_age_sim_s'] <= 0.4))
                    handoff_record['gate_ready'] = handoff_gate_ready
                    handoff_has_subscriber = (handoff_gate_ready and node.spin_until(
                        lambda: node.goal_pub.get_subscription_count() > 0,
                        5.0, 'EGO goal subscriber for handoff'))
                    if handoff_gate_ready and handoff_has_subscriber:
                        handoff_command = NavigationCommand()
                        handoff_command.goal_id = handoff_record['goal_id']
                        handoff_command.epoch = expected_epoch
                        handoff_command.map_id = status_before['map_id']
                        handoff_command.target.header.frame_id = handoff_frame
                        handoff_command.target.header.stamp = node.get_clock().now().to_msg()
                        handoff_command.target.pose.position.x = (
                            handoff_start[0] + handoff_offsets[0])
                        handoff_command.target.pose.position.y = (
                            handoff_start[1] + handoff_offsets[1])
                        handoff_command.target.pose.position.z = (
                            handoff_start[2] + handoff_offsets[2])
                        handoff_command.target.pose.orientation = current_pose.orientation
                        before_handoff_curves = len(node.curves)
                        before_handoff_faults = len(node.faults)
                        before_handoff_logs = len(node.logs)
                        mapping_stack_log = (ROOT / 'artifacts/runs'
                                             / args.run_id / 'mapping-stack.log')
                        mapping_log_before = (
                            mapping_stack_log.read_text(errors='replace')
                            if mapping_stack_log.is_file() else '')
                        node.goal_pub.publish(handoff_command)
                        handoff_record.update({
                            'published': True,
                            'target_xyz_m': [handoff_command.target.pose.position.x,
                                             handoff_command.target.pose.position.y,
                                             handoff_command.target.pose.position.z],
                            'map_id': status_before['map_id'],
                            'epoch': expected_epoch,
                            'qualification': 'planner-only replacement goal; no curve execution'})
                        handoff_record['event_observed'] = node.spin_until(
                            lambda: len(node.curves) > before_handoff_curves
                            or len(node.faults) > before_handoff_faults,
                            args.observe_s, 'replacement curve or planner fault')
                        handoff_record['new_curves'] = [
                            curve for curve in node.curves[before_handoff_curves:]
                            if curve['goal_id'] == handoff_record['goal_id']]
                        handoff_record['new_faults'] = [
                            {'goal_id': fault.goal_id, 'epoch': fault.epoch,
                             'mode': int(fault.mode), 'reason': fault.reason}
                            for fault in node.faults[before_handoff_faults:]]
                        mapping_log_after = (
                            mapping_stack_log.read_text(errors='replace')
                            if mapping_stack_log.is_file() else '')
                        handoff_log_delta = mapping_log_after[
                            len(mapping_log_before):]
                        handoff_certificate_lines = [
                            line.strip() for line in handoff_log_delta.splitlines()
                            if 'Full-curve certificate metrics:' in line]
                        handoff_ros_certificate_logs = [
                            item for item in node.logs[before_handoff_logs:]
                            if 'Full-curve certificate metrics:' in item.get('message', '')]
                        # EGO publishes its spline before the ROS logger event is
                        # guaranteed to reach this probe. Wait briefly for that
                        # event, while also checking the planner process log so a
                        # delivered certificate cannot be lost to /rosout timing.
                        certificate_deadline = time.monotonic() + min(
                            1.0, max(0.5, args.observe_s))
                        while (not handoff_ros_certificate_logs
                               and not handoff_certificate_lines
                               and time.monotonic() < certificate_deadline):
                            rclpy.spin_once(node, timeout_sec=0.03)
                            mapping_log_after = (
                                mapping_stack_log.read_text(errors='replace')
                                if mapping_stack_log.is_file() else '')
                            handoff_log_delta = mapping_log_after[
                                len(mapping_log_before):]
                            handoff_certificate_lines = [
                                line.strip() for line in handoff_log_delta.splitlines()
                                if 'Full-curve certificate metrics:' in line]
                            handoff_ros_certificate_logs = [
                                item for item in node.logs[before_handoff_logs:]
                                if 'Full-curve certificate metrics:'
                                in item.get('message', '')]
                        handoff_record['certificate_logs'] = node.logs[
                            before_handoff_logs:]
                        if (not handoff_ros_certificate_logs
                                and handoff_certificate_lines):
                            handoff_record['certificate_logs'].extend(
                                {'stamp_ns': None,
                                 'name': 'drone_0_ego_planner_node',
                                 'level': 20,
                                 'message': 'Full-curve certificate metrics:'
                                     + line.split(
                                         'Full-curve certificate metrics:', 1)[1],
                                 'source': 'mapping-stack.log'}
                                for line in handoff_certificate_lines)
                            handoff_record['certificate_log_source'] = (
                                'mapping-stack.log')
                        elif handoff_ros_certificate_logs:
                            handoff_record['certificate_log_source'] = '/rosout'
                        handoff_transitions = mapping_log_after[
                            len(mapping_log_before):].splitlines()
                        handoff_record['fsm_transition_lines'] = [
                            line for line in handoff_transitions
                            if 'from ' in line and ' to ' in line]
                        handoff_record['replan_transition_observed'] = any(
                            'from EXEC_TRAJ to REPLAN_TRAJ' in line
                            for line in handoff_record['fsm_transition_lines'])
                        if handoff_record['new_curves']:
                            replacement_curve = handoff_record['new_curves'][0]
                            encoded = json.dumps(replacement_curve, sort_keys=True,
                                                 separators=(',', ':')).encode()
                            handoff_record['curve_sha256'] = sha256_bytes(encoded)
                            handoff_record['trajectory_id_changed'] = (
                                replacement_curve['traj_id']
                                != handoff_record['source_curve_traj_id'])
                        matching_handoff_faults = [
                            fault for fault in node.faults[before_handoff_faults:]
                            if fault.goal_id == handoff_record['goal_id']]
                        if matching_handoff_faults:
                            fault_curve_count = len(node.curves)
                            fault_deadline = time.monotonic() + 0.5
                            while time.monotonic() < fault_deadline:
                                rclpy.spin_once(node, timeout_sec=0.03)
                            handoff_record['late_curves_after_fault'] = max(
                                0, len(node.curves) - fault_curve_count)
                        else:
                            handoff_record['late_curves_after_fault'] = 0
                        handoff_record['passed'] = bool(
                            handoff_record['new_curves']
                            and handoff_record.get('trajectory_id_changed')
                            and handoff_record.get('replan_transition_observed')
                            and not matching_handoff_faults
                            and any('reason=free' in item.get('message', '')
                                    for item in handoff_record['certificate_logs'])
                            and handoff_record['late_curves_after_fault'] == 0)
                    else:
                        handoff_record['reason'] = (
                            'handoff_gate_or_subscriber_failed'
                            if handoff_gate_ready else 'handoff_map_identity_freshness_or_raw_gate_failed')
                        handoff_record['passed'] = False
                except (RuntimeError, TimeoutError) as error:
                    handoff_record.update({'passed': False,
                                           'reason': f'handoff_query_or_status_failed:{error}'})
            goal_record['handoff'] = handoff_record

        after_response = node.call(node.status_client, status_request)
        status_after = status_record(after_response.status)
        goal_record['status_identity_stable'] = (
            status_after['epoch'] == status_before['epoch']
            and status_after['map_id'] == status_before['map_id'])
        report = {
            'schema': 'n06-live-layout-probe/v2',
            'run_id': args.run_id, 'expected_epoch': expected_epoch,
            'scope': 'actual Gazebo+VINS+plan_env/EGO; compute-only planner goal, optional post-certificate dynamic Gazebo obstacle, and optional gated replacement handoff; no PX4, bridge, traj_server, navigation supervisor, control publisher, or curve execution',
            'map_ready': map_ready,
            'freshness': {'source_age_sim_s': source_age,
                          'fusion_age_sim_s': fusion_age,
                          'odometry_age_sim_s': odom_age, 'limit_sim_s': 0.4},
            'odometry_freshness_wait': {
                'fresh_identity_matched_sample_observed': fresh_odom_observed,
                'wall_wait_s': odom_freshness_wait_wall_s,
                'limit_sim_s': 0.4},
            'status_before': status_before, 'status_after': status_after,
            'odom': {'stamp_ns': stamp_ns(odom.header.stamp),
                     'frame_id': frame, 'position_xyz_m': position},
            'body_sphere_query_at_actual_vins_pose': pose_query,
            'goal_certificate': {
                'required': bool(args.require_snapshot_certificate),
                'archived_snapshots': snapshot_certificate,
                'live_body_sweep_hold': live_certificate,
                'handoff_archived_snapshots': handoff_snapshot_certificate},
            'goal': goal_record,
            'graph': {'nodes': graph_nodes, 'topics': graph_topics,
                      'forbidden_nodes': forbidden_nodes,
                      'forbidden_control_topics': forbidden_topics,
                      'control_free': control_free_graph},
            'probe_source_sha256': sha256_bytes(Path(__file__).read_bytes()),
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))
        return report
    finally:
        node.destroy_node()
        rclpy.shutdown()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--target-dx-m', type=float, default=0.5)
    parser.add_argument('--target-dy-m', type=float, default=0.0)
    parser.add_argument('--target-dz-m', type=float, default=0.5)
    parser.add_argument('--handoff-target-dx-m', type=float)
    parser.add_argument('--handoff-target-dy-m', type=float)
    parser.add_argument('--handoff-target-dz-m', type=float)
    parser.add_argument('--require-snapshot-certificate', action='store_true',
                        help='Require three exact source-pose snapshot certificates and a live raw body/sweep/hold certificate before publishing.')
    parser.add_argument('--observe-s', type=float, default=6.0)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.observe_s <= 0:
        raise ValueError('--observe-s must be positive')
    handoff_values = (args.handoff_target_dx_m, args.handoff_target_dy_m,
                      args.handoff_target_dz_m)
    if any(value is not None for value in handoff_values) \
            and not all(value is not None for value in handoff_values):
        raise ValueError('all three handoff target offsets must be supplied together')
    if all(value is not None for value in handoff_values) \
            and not args.require_snapshot_certificate:
        raise ValueError('a handoff goal requires --require-snapshot-certificate')
    report = run(args)
    if (report.get('goal', {}).get('dynamic_obstacle', {}).get('enabled')
            and not report.get('goal', {}).get('dynamic_obstacle', {}).get('passed')):
        raise SystemExit(3)
    if all(value is not None for value in handoff_values) \
            and not report.get('goal', {}).get('handoff', {}).get('passed', False):
        raise SystemExit(2)


if __name__ == '__main__':
    main()
