"""Raw-voxel, fail-closed entry-volume checks for the N05 diagnostic.

This module is deliberately independent of ROS so the exact same classifier can
be applied to a live plan_env snapshot and to its archived offline copy.
"""
import hashlib
import itertools
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / 'config/components/navigation/vehicle_envelope.json'
X500_PATH = ROOT / 'external/PX4-Autopilot/Tools/simulation/gz/models/x500_base/model.sdf'
WRAPPER_PATH = ROOT / 'simulation/models/x500_d435i/model.sdf'
D435I_PATH = ROOT / 'simulation/models/d435i/model.sdf'


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _pose(text):
    values = tuple(float(v) for v in text.split()) if text else (0.0,) * 6
    if len(values) != 6 or not all(math.isfinite(v) for v in values):
        raise ValueError('SDF pose must contain six finite values')
    return values


def _rotation(rpy):
    roll, pitch, yaw = rpy
    cr, sr = math.cos(roll), math.sin(roll)
    cp, sp = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    return np.asarray([
        [cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
        [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
        [-sp, cp * sr, cp * cr],
    ], dtype=float)


def _box_size(collision):
    size = collision.find('geometry/box/size')
    if size is None:
        raise ValueError(f"unsupported vehicle collision geometry: {collision.get('name')}")
    result = tuple(float(v) for v in size.text.split())
    if len(result) != 3 or any(not math.isfinite(v) or v <= 0 for v in result):
        raise ValueError(f"invalid vehicle box: {collision.get('name')}")
    return result


def collision_primitives(root=ROOT):
    """Read the locked SDF collision model in the D435i IMU reference frame."""
    root = Path(root)
    x500 = ET.parse(root / X500_PATH.relative_to(ROOT)).getroot().find('model')
    wrapper = ET.parse(root / WRAPPER_PATH.relative_to(ROOT)).getroot().find('model')
    d435i = ET.parse(root / D435I_PATH.relative_to(ROOT)).getroot().find('model')
    joint_pose = wrapper.find("joint[@name='d435i_mount']/pose")
    if joint_pose is None or joint_pose.get('relative_to') != 'base_link':
        raise ValueError('D435i mount joint pose must be expressed relative to base_link')
    mount = _pose(joint_pose.text)
    include = wrapper.find("include[uri='model://d435i']")
    include_pose = include.find('pose') if include is not None else None
    if (include_pose is None or include_pose.get('relative_to') != 'base_link'
            or any(abs(a-b) > 1e-12 for a, b in
                   zip(mount, _pose(include_pose.text)))):
        raise ValueError('D435i include and fixed mount poses disagree')
    origin = np.asarray(mount[:3], dtype=float)
    result = []

    base = x500.find("link[@name='base_link']")
    base_pose = _pose(base.findtext('pose'))
    for collision in base.findall('collision'):
        p = _pose(collision.findtext('pose'))
        center = np.asarray(p[:3], dtype=float) - origin
        result.append({
            'name': collision.get('name'), 'kind': 'box',
            'center_imu_m': center.tolist(), 'size_m': list(_box_size(collision)),
            'rpy_rad': list(np.asarray(base_pose[3:]) + np.asarray(p[3:])),
        })

    for link in x500.findall('link'):
        if not link.get('name', '').startswith('rotor_'):
            continue
        collision = link.find('collision')
        if collision is None:
            continue
        link_pose = _pose(link.findtext('pose'))
        p = _pose(collision.findtext('pose'))
        center = np.asarray(link_pose[:3], dtype=float) + np.asarray(p[:3], dtype=float) - origin
        size = _box_size(collision)
        result.append({
            'name': collision.get('name'), 'kind': 'rotor_disk',
            'center_imu_m': center.tolist(),
            'radius_m': math.hypot(size[0] / 2.0, size[1] / 2.0),
            'half_height_m': size[2] / 2.0,
        })

    camera = d435i.find("link[@name='d435i_link']")
    for collision in camera.findall('collision'):
        p = _pose(collision.findtext('pose'))
        result.append({
            'name': collision.get('name'), 'kind': 'box',
            'center_imu_m': list(p[:3]), 'size_m': list(_box_size(collision)),
            'rpy_rad': list(p[3:]),
        })

    if len(result) != 10:
        raise ValueError(f'expected 9 x500 and 1 D435i collision components, got {len(result)}')
    return result


def load_policy(root=ROOT):
    root = Path(root)
    policy = json.loads((root / POLICY_PATH.relative_to(ROOT)).read_text())
    terms = policy['spatial_budget']['terms_m']
    expected = (terms['localization_10s_rpe_max_observed']
                + terms['map_surface_error_max_observed']
                + terms['voxel_half_diagonal'] + terms['sweep_sample_half_step'])
    margin = policy['spatial_budget']['combined_uncertainty_margin_m']
    radius = policy['spatial_budget']['body_reference_clearance_radius_m']
    geometry_radius = policy['geometry']['orientation_invariant_rotor_sweep_radius_m']
    if abs(expected - margin) > 1e-9 or abs(geometry_radius + margin - radius) > 1e-9:
        raise ValueError('vehicle envelope uncertainty sum is inconsistent')
    subground = policy['ground_contact']['subground_voxel_exclusion']
    required_ground_phases = {'TAKEOFF_CONTACT', 'ASCENT', 'DESCENT', 'LANDING_CONTACT'}
    if (not isinstance(subground.get('enabled'), bool)
            or set(subground.get('phases', ())) != required_ground_phases
            or not 0 <= float(subground.get('surface_voxel_boundary_allowance_fraction', -1)) <= 1):
        raise ValueError('subground exclusion must be enabled only for the four ground-interaction phases with a bounded surface margin')
    for relpath, expected_hash in policy['geometry']['source_hashes'].items():
        if sha256(root / relpath) != expected_hash:
            raise ValueError(f'vehicle SDF source hash changed: {relpath}')
    return policy


def fit_ground_plane(occupancy, origin, resolution, center_xyz, policy=None):
    """Fit a local horizontal plane from raw occupied voxels, never debug truth."""
    policy = policy or load_policy()
    origin = np.asarray(origin, dtype=float)
    center = np.asarray(center_xyz, dtype=float)
    if occupancy.ndim != 3 or not np.all(np.isin(occupancy, (-1, 0, 100))):
        return {'valid': False, 'reason': 'invalid_raw_occupancy'}
    ranges = []
    for axis, radius in ((0, 1.25), (1, 1.25),
                         (2, 0.8)):
        lower = center[axis] - radius
        upper = center[axis] + (0.8 if axis == 2 else radius)
        if axis == 2:
            boundary_allowance = (
                policy['ground_contact']['ground_plane_voxel_boundary_allowance_fraction']
                * resolution)
            upper = center[2] - 0.1 + boundary_allowance
        lo = max(0, int(math.floor((lower - origin[axis]) / resolution)))
        hi = min(occupancy.shape[axis] - 1,
                 int(math.floor((upper - origin[axis]) / resolution)))
        if hi < lo:
            return {'valid': False, 'reason': 'ground_plane_search_outside_map'}
        ranges.append((lo, hi))
    slices = tuple(slice(lo, hi + 1) for lo, hi in ranges)
    patch = occupancy[slices]
    axes = [origin[i] + (np.arange(ranges[i][0], ranges[i][1] + 1) + 0.5) * resolution
            for i in range(3)]
    grid = np.stack(np.meshgrid(*axes, indexing='ij'), axis=-1)
    xy_radius = np.linalg.norm(grid[..., :2] - center[:2], axis=-1)
    z = grid[..., 2]
    indices_offset = np.asarray([item[0] for item in ranges])
    low = center[2] - 0.8
    high = (center[2] - 0.1
            + policy['ground_contact']['ground_plane_voxel_boundary_allowance_fraction']
            * resolution)
    candidate = (patch == 100) & (xy_radius <= 1.25) & (z >= low) & (z <= high)
    indices = np.argwhere(candidate) + indices_offset
    if len(indices) < policy['ground_contact']['minimum_plane_voxels']:
        return {'valid': False, 'reason': 'ground_plane_insufficient_raw_occupied_voxels',
                'candidate_voxel_count': int(len(indices))}
    points = origin + (indices + 0.5) * resolution
    z_bins = np.rint((points[:, 2] - origin[2]) / resolution).astype(int)
    candidates = []
    minimum = policy['ground_contact']['minimum_plane_voxels']
    for index in np.unique(z_bins):
        band = points[np.abs(z_bins - index) <= 1]
        if len(band) < minimum:
            continue
        span = np.ptp(band[:, :2], axis=0)
        if np.min(span) < 0.5:
            continue
        design = np.column_stack((band[:, 0], band[:, 1], np.ones(len(band))))
        coefficients, *_ = np.linalg.lstsq(design, band[:, 2], rcond=None)
        residual = np.abs(design @ coefficients - band[:, 2])
        residual_p95 = float(np.percentile(residual, 95))
        slope = float(math.hypot(coefficients[0], coefficients[1]))
        candidates.append((float(np.median(band[:, 2])), residual_p95, slope,
                           coefficients, band, span))
    if not candidates:
        return {'valid': False, 'reason': 'ground_plane_not_spatially_supported',
                'candidate_voxel_count': int(len(indices))}
    candidates.sort(key=lambda item: item[0])
    median_z, residual_p95, slope, coeff, band, span = candidates[0]
    max_residual = policy['ground_contact']['maximum_plane_residual_m']
    if residual_p95 > max_residual or slope > 0.1:
        return {'valid': False, 'reason': 'ground_plane_residual_exceeded',
                'candidate_voxel_count': int(len(band)),
                'residual_p95_m': residual_p95, 'slope': slope}
    return {
        'valid': True, 'reason': 'raw_occupied_plane_fit',
        'z_at_center_m': float(coeff[0] * center[0] + coeff[1] * center[1] + coeff[2]),
        'coefficients_ax_by_c_m': [float(v) for v in coeff],
        'residual_p95_m': residual_p95, 'slope': slope,
        'raw_occupied_voxel_count': int(len(band)),
        'xy_span_m': span.tolist(), 'source': 'raw occupancy only',
        'debug_truth_used': False,
    }


def _candidate_index_range(low, high, origin, resolution, size):
    if low <= origin or high >= origin + resolution * size:
        return None
    lo = int(math.floor((low - origin) / resolution))
    hi = int(math.floor((high - origin) / resolution))
    if lo < 0 or hi >= size or hi < lo:
        return None
    return lo, hi


def _ground_voxel_allowed(point, pose, ground_plane, phase, ground_confirmed,
                          policy, footprint_radius):
    if not ground_confirmed or not ground_plane or not ground_plane.get('valid'):
        return False
    if phase not in ('TAKEOFF_CONTACT', 'ASCENT', 'DESCENT', 'LANDING_CONTACT'):
        return False
    a, b, c = ground_plane['coefficients_ax_by_c_m']
    plane_z = a * point[0] + b * point[1] + c
    band = policy['ground_contact']['contact_band_half_width_m']
    if abs(point[2] - plane_z) > band:
        return False
    distance_xy = math.hypot(point[0] - pose['center_xyz_m'][0],
                             point[1] - pose['center_xyz_m'][1])
    return distance_xy <= footprint_radius


def _voxel_is_below_ground(point, resolution, ground_plane, phase,
                           ground_confirmed, policy):
    """Return true only when a whole voxel lies below the conservative floor boundary."""
    rule = policy['ground_contact']['subground_voxel_exclusion']
    if (not rule['enabled'] or not ground_confirmed or not ground_plane
            or not ground_plane.get('valid') or phase not in rule['phases']):
        return False
    coefficients = ground_plane.get('coefficients_ax_by_c_m', ())
    residual = float(ground_plane.get('residual_p95_m', math.inf))
    if len(coefficients) != 3 or not math.isfinite(residual) or residual < 0:
        return False
    a, b, c = (float(value) for value in coefficients)
    if not all(math.isfinite(value) for value in (a, b, c)):
        return False

    half_cell = resolution / 2.0
    plane_center = a * point[0] + b * point[1] + c
    plane_min_xy = plane_center - (abs(a) + abs(b)) * half_cell
    surface_lower_bound = (
        plane_min_xy - residual
        - resolution * rule['surface_voxel_boundary_allowance_fraction'])
    voxel_upper_z = point[2] + half_cell
    return voxel_upper_z <= surface_lower_bound + 1e-9


def check_pose(snapshot, pose, phase, policy=None, primitives=None,
               ground_plane=None, ground_confirmed=False,
               ground_plane_predicted=False, candidate_ground_contact=False):
    """Check the flight-volume envelope against fresh raw occupancy."""
    policy = policy or load_policy()
    primitives = primitives or collision_primitives()
    occupancy = np.asarray(snapshot['occupancy'])
    origin = np.asarray(snapshot['origin_m'], dtype=float)
    resolution = float(snapshot['resolution_m'])
    if occupancy.ndim != 3 or tuple(occupancy.shape) != tuple(snapshot.get('dimensions_xyz', occupancy.shape)):
        return {'accepted': False, 'reason': 'snapshot_dimensions_invalid'}
    if not np.all(np.isin(occupancy, (-1, 0, 100))):
        return {'accepted': False, 'reason': 'snapshot_occupancy_code_invalid'}
    if (not math.isfinite(resolution) or resolution <= 0
            or not np.all(np.isfinite(origin))):
        return {'accepted': False, 'reason': 'snapshot_geometry_invalid'}
    center = np.asarray(pose['center_xyz_m'], dtype=float)
    yaw = float(pose['yaw_rad'])
    if center.shape != (3,) or not np.all(np.isfinite(center)) or not math.isfinite(yaw):
        return {'accepted': False, 'reason': 'body_pose_invalid'}
    if max(abs(float(pose.get('roll_rad', 0.0))), abs(float(pose.get('pitch_rad', 0.0)))) > math.radians(5):
        return {'accepted': False, 'reason': 'body_attitude_outside_level_entry_scope'}

    margin = policy['spatial_budget']['combined_uncertainty_margin_m']
    footprint = policy['geometry']['level_max_horizontal_radius_m']
    body_r = np.asarray([[math.cos(yaw), -math.sin(yaw), 0.0],
                         [math.sin(yaw), math.cos(yaw), 0.0],
                         [0.0, 0.0, 1.0]], dtype=float)
    counts = {
        'free': 0, 'unknown': 0, 'occupied': 0, 'ground_contact': 0,
        'unknown_cells': 0, 'occupied_cells': 0, 'ground_contact_cells': 0,
        'subground_excluded_cells': 0,
    }
    found = set()
    for primitive in primitives:
        local_center = np.asarray(primitive['center_imu_m'], dtype=float)
        world_center = center + body_r @ local_center
        if primitive['kind'] == 'box':
            local_r = _rotation(primitive['rpy_rad'])
            world_r = body_r @ local_r
            half = np.asarray(primitive['size_m'], dtype=float) / 2.0
            world_half = np.abs(world_r) @ half + margin
            ranges = [_candidate_index_range(world_center[i] - world_half[i],
                                             world_center[i] + world_half[i],
                                             origin[i], resolution, occupancy.shape[i])
                      for i in range(3)]
            if any(item is None for item in ranges):
                return {'accepted': False, 'reason': 'outside_map', 'component': primitive['name'],
                        'counts': counts}
            slices = tuple(slice(item[0], item[1] + 1) for item in ranges)
            indices = np.indices(tuple(sl.stop - sl.start for sl in slices), dtype=float)
            indices += np.asarray([[sl.start] for sl in slices]).reshape(3, 1, 1, 1)
            xyz = np.empty(indices.shape, dtype=float)
            for axis in range(3):
                xyz[axis] = origin[axis] + (indices[axis] + 0.5) * resolution
            delta = xyz - world_center.reshape(3, 1, 1, 1)
            local = np.einsum('i...,ij->j...', delta, world_r)
            excess = np.maximum(np.abs(local) - half.reshape(3, 1, 1, 1), 0.0)
            intersects = np.sqrt(np.sum(excess * excess, axis=0)) <= margin + 1e-12
        elif primitive['kind'] == 'rotor_disk':
            radius = float(primitive['radius_m'])
            half_z = float(primitive['half_height_m'])
            world_half = np.asarray([radius + margin, radius + margin, half_z + margin])
            ranges = [_candidate_index_range(world_center[i] - world_half[i],
                                             world_center[i] + world_half[i],
                                             origin[i], resolution, occupancy.shape[i])
                      for i in range(3)]
            if any(item is None for item in ranges):
                return {'accepted': False, 'reason': 'outside_map', 'component': primitive['name'],
                        'counts': counts}
            slices = tuple(slice(item[0], item[1] + 1) for item in ranges)
            indices = np.indices(tuple(sl.stop - sl.start for sl in slices), dtype=float)
            indices += np.asarray([[sl.start] for sl in slices]).reshape(3, 1, 1, 1)
            xyz = np.empty(indices.shape, dtype=float)
            for axis in range(3):
                xyz[axis] = origin[axis] + (indices[axis] + 0.5) * resolution
            delta = xyz - world_center.reshape(3, 1, 1, 1)
            local = np.einsum('i...,ij->j...', delta, body_r)
            radial = np.hypot(local[0], local[1])
            excess_r = np.maximum(radial - radius, 0.0)
            excess_z = np.maximum(np.abs(local[2]) - half_z, 0.0)
            intersects = np.hypot(excess_r, excess_z) <= margin + 1e-12
        else:
            return {'accepted': False, 'reason': 'unsupported_vehicle_primitive',
                    'component': primitive['name'], 'counts': counts}

        classes = occupancy[slices][intersects]
        intersect_indices = np.argwhere(intersects)
        starts = np.asarray([sl.start for sl in slices])
        centers = origin + (intersect_indices + starts + 0.5) * resolution
        for value, point in zip(classes.tolist(), centers):
            key = tuple(int(v) for v in np.rint((point - origin) / resolution - 0.5))
            predicted_plane_phase = (ground_plane_predicted
                                     and phase in ('DESCENT', 'LANDING_CONTACT'))
            if _voxel_is_below_ground(point, resolution, ground_plane, phase,
                                      ground_confirmed or predicted_plane_phase, policy):
                found.add(('subground_excluded', key))
                continue
            if value == 0:
                counts['free'] += 1
                continue
            if value == -1:
                counts['unknown'] += 1
                found.add(('unknown', key))
                continue
            candidate_contact_phase = (candidate_ground_contact
                                       and phase in ('DESCENT', 'LANDING_CONTACT'))
            if value == 100 and _ground_voxel_allowed(
                    point, pose, ground_plane, phase,
                    ground_confirmed or candidate_contact_phase,
                    policy, footprint + margin):
                counts['ground_contact'] += 1
                found.add(('ground_contact', key))
                continue
            counts['occupied'] += 1
            found.add(('occupied', key))

    counts['unknown_cells'] = len({key for kind, key in found if kind == 'unknown'})
    counts['occupied_cells'] = len({key for kind, key in found if kind == 'occupied'})
    counts['ground_contact_cells'] = len({key for kind, key in found if kind == 'ground_contact'})
    counts['subground_excluded_cells'] = len(
        {key for kind, key in found if kind == 'subground_excluded'})
    candidate_landing_contact = candidate_ground_contact and phase == 'LANDING_CONTACT'
    if (not ground_confirmed and not candidate_landing_contact
            and phase in ('TAKEOFF_CONTACT', 'LANDING_CONTACT')):
        return {'accepted': False, 'reason': 'ground_contact_not_confirmed', 'counts': counts}
    if counts['occupied_cells']:
        return {'accepted': False, 'reason': 'raw_occupied_in_expanded_vehicle_envelope', 'counts': counts}
    if counts['unknown_cells']:
        return {'accepted': False, 'reason': 'raw_unknown_in_expanded_vehicle_envelope', 'counts': counts}
    if counts['free'] <= 0:
        return {'accepted': False, 'reason': 'insufficient_known_free_volume', 'counts': counts}
    return {'accepted': True, 'reason': 'raw_vehicle_envelope_known_free', 'counts': counts}


def make_entry_schedule(start_pose, hold_height_m=1.0, sample_step_m=0.05):
    if not math.isfinite(hold_height_m) or hold_height_m <= 0:
        raise ValueError('hold height must be positive and finite')
    if not math.isfinite(sample_step_m) or sample_step_m <= 0 or sample_step_m > 0.05:
        raise ValueError('entry sweep sample step must be in (0, 0.05] m')
    start = np.asarray(start_pose['center_xyz_m'], dtype=float)
    hold = start.copy()
    hold[2] += hold_height_m
    count = int(math.ceil(hold_height_m / sample_step_m))
    points = []
    points.append(('TAKEOFF_CONTACT', {**start_pose, 'center_xyz_m': start.tolist()}))
    for index in range(1, count):
        center = start + np.asarray([0.0, 0.0, hold_height_m * index / count])
        points.append(('ASCENT', {**start_pose, 'center_xyz_m': center.tolist()}))
    points.append(('HOLD', {**start_pose, 'center_xyz_m': hold.tolist()}))
    for index in range(count - 1, 0, -1):
        center = start + np.asarray([0.0, 0.0, hold_height_m * index / count])
        points.append(('DESCENT', {**start_pose, 'center_xyz_m': center.tolist()}))
    points.append(('LANDING_CONTACT', {**start_pose, 'center_xyz_m': start.tolist()}))
    return points


def make_candidate_landing_schedule(landing_pose, hold_height_m=1.0,
                                   sample_step_m=0.05):
    """Sample a future descent and touchdown geometry without claiming landed."""
    if not math.isfinite(hold_height_m) or hold_height_m <= 0:
        raise ValueError('hold height must be positive and finite')
    if not math.isfinite(sample_step_m) or sample_step_m <= 0 or sample_step_m > 0.05:
        raise ValueError('entry sweep sample step must be in (0, 0.05] m')
    center = np.asarray(landing_pose.get('center_xyz_m', ()), dtype=float)
    yaw = float(landing_pose.get('yaw_rad', math.nan))
    if center.shape != (3,) or not np.isfinite(center).all() or not math.isfinite(yaw):
        raise ValueError('candidate landing pose is invalid')
    hold = center.copy()
    hold[2] += hold_height_m
    count = int(math.ceil(hold_height_m / sample_step_m))
    points = [('HOLD', {**landing_pose, 'center_xyz_m': hold.tolist()})]
    for index in range(count - 1, 0, -1):
        point = center + np.asarray([0.0, 0.0, hold_height_m * index / count])
        points.append(('DESCENT', {**landing_pose, 'center_xyz_m': point.tolist()}))
    points.append(('LANDING_CONTACT', {**landing_pose, 'center_xyz_m': center.tolist()}))
    return points


def check_candidate_landing_schedule(snapshot, landing_pose, hold_height_m=1.0,
                                     sample_step_m=0.05, policy=None,
                                     ground_plane=None, primitives=None):
    """Certify predicted hold/descent/contact using a raw plane, not landed state.

    Raw occupancy at the fitted candidate plane may support the predicted
    contact region, and whole voxels strictly below its conservative bound may
    be omitted from the flight volume. Neither result asserts the aircraft is
    physically grounded; PX4 landing feedback remains a separate check.
    """
    policy = policy or load_policy()
    if ground_plane is None:
        ground_plane = fit_ground_plane(
            snapshot['occupancy'], snapshot['origin_m'], snapshot['resolution_m'],
            landing_pose.get('center_xyz_m', ()), policy)
    if not ground_plane.get('valid'):
        return {'accepted': False,
                'reason': ground_plane.get('reason', 'ground_plane_invalid'),
                'ground_plane': ground_plane, 'phases': {},
                'hold_height_m': hold_height_m, 'sample_step_m': sample_step_m,
                'ground_confirmed': False,
                'scope': 'prospective landing geometry only; not physical touchdown'}
    phase_results = {}
    first_rejection = ''
    for phase, pose in make_candidate_landing_schedule(
            landing_pose, hold_height_m, sample_step_m):
        result = check_pose(
            snapshot, pose, phase, policy, primitives, ground_plane,
            ground_confirmed=False, ground_plane_predicted=True,
            candidate_ground_contact=True)
        summary = phase_results.setdefault(phase, {
            'samples': 0, 'accepted_samples': 0, 'refusal_counts': {},
            'maximum_unknown_cells': 0, 'maximum_occupied_cells': 0,
            'maximum_ground_contact_cells': 0,
            'maximum_subground_excluded_cells': 0,
        })
        summary['samples'] += 1
        summary['accepted_samples'] += int(result['accepted'])
        summary['refusal_counts'][result['reason']] = (
            summary['refusal_counts'].get(result['reason'], 0) + 1)
        counts = result.get('counts', {})
        summary['maximum_unknown_cells'] = max(
            summary['maximum_unknown_cells'], counts.get('unknown_cells', 0))
        summary['maximum_occupied_cells'] = max(
            summary['maximum_occupied_cells'], counts.get('occupied_cells', 0))
        summary['maximum_ground_contact_cells'] = max(
            summary['maximum_ground_contact_cells'],
            counts.get('ground_contact_cells', 0))
        summary['maximum_subground_excluded_cells'] = max(
            summary['maximum_subground_excluded_cells'],
            counts.get('subground_excluded_cells', 0))
        if not result['accepted'] and not first_rejection:
            first_rejection = f'{phase}:{result["reason"]}'
    return {
        'accepted': not first_rejection,
        'reason': first_rejection or 'candidate_landing_volume_known_and_clear',
        'ground_plane': ground_plane,
        'ground_confirmed': False,
        'candidate_ground_contact_authorized': True,
        'hold_height_m': hold_height_m,
        'sample_step_m': sample_step_m,
        'sample_count': len(make_candidate_landing_schedule(
            landing_pose, hold_height_m, sample_step_m)),
        'phases': phase_results,
        'scope': 'prospective landing geometry only; actual PX4 landed/disarmed readback is required after descent',
    }


def check_entry_schedule(snapshot, start_pose, hold_height_m=1.0,
                         sample_step_m=0.05, ground_confirmed=False,
                         disarmed=True, control_disabled=True, policy=None,
                         ground_plane=None, primitives=None):
    policy = policy or load_policy()
    if not disarmed:
        return {'accepted': False, 'reason': 'vehicle_not_disarmed', 'phases': {},
                'hold_height_m': hold_height_m, 'sample_step_m': sample_step_m}
    if not control_disabled:
        return {'accepted': False, 'reason': 'control_not_disabled', 'phases': {},
                'hold_height_m': hold_height_m, 'sample_step_m': sample_step_m}
    if not ground_confirmed:
        return {'accepted': False, 'reason': 'ground_contact_not_confirmed', 'phases': {},
                'hold_height_m': hold_height_m, 'sample_step_m': sample_step_m}
    if ground_plane is None:
        ground_plane = fit_ground_plane(
            snapshot['occupancy'], snapshot['origin_m'], snapshot['resolution_m'],
            start_pose['center_xyz_m'], policy)
    if not ground_plane.get('valid'):
        return {'accepted': False, 'reason': ground_plane.get('reason', 'ground_plane_invalid'),
                'ground_plane': ground_plane, 'phases': {},
                'hold_height_m': hold_height_m, 'sample_step_m': sample_step_m}
    phase_results = {}
    first_rejection = ''
    for phase, pose in make_entry_schedule(start_pose, hold_height_m, sample_step_m):
        result = check_pose(snapshot, pose, phase, policy, primitives,
                            ground_plane, ground_confirmed)
        summary = phase_results.setdefault(phase, {
            'samples': 0, 'accepted_samples': 0, 'refusal_counts': {},
            'maximum_unknown_cells': 0, 'maximum_occupied_cells': 0,
            'maximum_ground_contact_cells': 0, 'maximum_subground_excluded_cells': 0,
        })
        summary['samples'] += 1
        summary['accepted_samples'] += int(result['accepted'])
        summary['refusal_counts'][result['reason']] = summary['refusal_counts'].get(result['reason'], 0) + 1
        counts = result.get('counts', {})
        summary['maximum_unknown_cells'] = max(summary['maximum_unknown_cells'], counts.get('unknown_cells', 0))
        summary['maximum_occupied_cells'] = max(summary['maximum_occupied_cells'], counts.get('occupied_cells', 0))
        summary['maximum_ground_contact_cells'] = max(summary['maximum_ground_contact_cells'], counts.get('ground_contact_cells', 0))
        summary['maximum_subground_excluded_cells'] = max(
            summary['maximum_subground_excluded_cells'],
            counts.get('subground_excluded_cells', 0))
        if not result['accepted'] and not first_rejection:
            first_rejection = f'{phase}:{result["reason"]}'
    return {
        'accepted': not first_rejection,
        'reason': first_rejection or 'all_entry_phases_known_and_clear',
        'ground_plane': ground_plane,
        'hold_height_m': hold_height_m,
        'sample_step_m': sample_step_m,
        'sample_count': len(make_entry_schedule(start_pose, hold_height_m, sample_step_m)),
        'ground_confirmed': bool(ground_confirmed),
        'disarmed': bool(disarmed), 'control_disabled': bool(control_disabled),
        'phases': phase_results,
        'scope': 'raw occupancy entry-volume diagnostic; no flight authorization',
    }
