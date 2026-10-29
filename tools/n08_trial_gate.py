"""Read-only geometric admission for one bounded N08 forward braking trial."""
import math
import numpy as np
from evaluate_n08_curve_certificate import (raw_sphere_query, bspline_eval,
                                            derivative_polygon)
from n05_entry import (check_entry_schedule, load_policy, collision_primitives,
                       _rotation, _candidate_index_range)


TRIAL_TAKEOFF_TOTAL_SPEED_LIMIT_M_S = 0.03
TRIAL_TAKEOFF_VERTICAL_SPEED_LIMIT_M_S = 0.01
TRIAL_TAKEOFF_SETTLE_DURATION_S = 1.0
TRIAL_FORWARD_REFERENCE_TUBE_M = 0.05
TRIAL_FORWARD_CORRIDOR_LOOKAHEAD_M = 0.075
# Fixed-heading translation scope. #294 measured a 0.01555 rad maximum PX4
# heading deviation; this small bound also retains margin in the raw-map query.
TRIAL_FORWARD_YAW_DEVIATION_BOUND_RAD = 0.019
# A small initial EGO spline transient is permitted only when the expanded
# directional raw-map certificate proves it remains inside the existing margin.
TRIAL_FORWARD_INITIAL_REVERSE_BOUND_M = 0.005


def trial_takeoff_velocity_settled(local_position):
    """Require the existing low total speed plus a stricter vertical settle."""
    if not isinstance(local_position, dict):
        return False
    try:
        velocity = tuple(float(local_position[key]) for key in ('vx', 'vy', 'vz'))
    except (KeyError, TypeError, ValueError, OverflowError):
        return False
    if not all(math.isfinite(value) for value in velocity):
        return False
    total_speed = math.sqrt(sum(value * value for value in velocity))
    return (total_speed < TRIAL_TAKEOFF_TOTAL_SPEED_LIMIT_M_S
            and abs(velocity[2]) < TRIAL_TAKEOFF_VERTICAL_SPEED_LIMIT_M_S)


def trial_fixed_heading_deviation_rad(reference_yaw, observed_yaw):
    """Return wrapped absolute yaw deviation for the fixed-heading trial."""
    reference_yaw = float(reference_yaw)
    observed_yaw = float(observed_yaw)
    if not math.isfinite(reference_yaw) or not math.isfinite(observed_yaw):
        return math.inf
    return abs(math.atan2(math.sin(observed_yaw - reference_yaw),
                          math.cos(observed_yaw - reference_yaw)))


def trial_fixed_heading_within_bound(reference_yaw, observed_yaw):
    return (trial_fixed_heading_deviation_rad(reference_yaw, observed_yaw)
            <= TRIAL_FORWARD_YAW_DEVIATION_BOUND_RAD)


def candidate_landing_pose_from_ground_planes(home_ground_pose,
                                               home_ground_plane,
                                               candidate_ground_plane,
                                               candidate_xy_m,
                                               yaw_rad):
    """Project the IMU's observed ground standoff onto a raw candidate plane."""
    center = np.asarray(home_ground_pose.get('center_xyz_m', ()), dtype=float)
    xy = np.asarray(candidate_xy_m, dtype=float)
    yaw = float(yaw_rad)
    for name, plane in (('home', home_ground_plane),
                        ('candidate', candidate_ground_plane)):
        if not isinstance(plane, dict) or plane.get('valid') is not True:
            raise ValueError(name + '_ground_plane_not_valid')
        coeff = np.asarray(plane.get('coefficients_ax_by_c_m', ()), dtype=float)
        residual = float(plane.get('residual_p95_m', math.nan))
        if (coeff.shape != (3,) or not np.isfinite(coeff).all()
                or not math.isfinite(residual) or residual < 0):
            raise ValueError(name + '_ground_plane_geometry_invalid')
    if (center.shape != (3,) or xy.shape != (2,) or not np.isfinite(center).all()
            or not np.isfinite(xy).all() or not math.isfinite(yaw)):
        raise ValueError('candidate_landing_pose_input_invalid')
    home_coeff = np.asarray(home_ground_plane['coefficients_ax_by_c_m'], dtype=float)
    candidate_coeff = np.asarray(
        candidate_ground_plane['coefficients_ax_by_c_m'], dtype=float)
    home_plane_z = float(home_coeff @ [center[0], center[1], 1.0])
    candidate_plane_z = float(candidate_coeff @ [xy[0], xy[1], 1.0])
    imu_standoff = float(center[2] - home_plane_z)
    if not math.isfinite(imu_standoff) or imu_standoff <= 0:
        raise ValueError('home_imu_ground_standoff_invalid')
    candidate_center = [float(xy[0]), float(xy[1]),
                        float(candidate_plane_z + imu_standoff)]
    return {
        'center_xyz_m': candidate_center,
        'yaw_rad': yaw,
        'home_ground_plane_z_m': home_plane_z,
        'candidate_ground_plane_z_m': candidate_plane_z,
        'imu_standoff_above_raw_ground_m': imu_standoff,
        'candidate_plane_height_delta_m': candidate_plane_z - home_plane_z,
        'actual_ground_confirmed': False,
    }


def trial_limits(profile, planner):
    trial = profile.get('n08_braking_trial') or {}
    if trial.get('braking_kind') != 'planned_terminal_stop':
        raise ValueError('trial_requires_planned_terminal_stop')
    offset = np.asarray(profile.get('target_offset_enu_m', []), dtype=float)
    if (offset.shape != (3,) or not np.isfinite(offset).all()
            or not 0.2 <= offset[0] <= 0.6 or np.linalg.norm(offset[1:]) > 1e-9
            or float(profile.get('yaw_offset_rad', 0)) != 0):
        raise ValueError('trial_requires_short_forward_level_goal')
    values = {k: float(trial.get(k, math.nan)) for k in (
        'tracking_margin_m', 'forward_stopping_extension_m',
        'cancel_stop_distance_envelope_m',
        'actual_vector_speed_limit_m_s', 'maximum_tracking_error_m',
        'post_goal_hold_sim_s')}
    turn_approach = float(trial.get('turn_approach_distance_m', 0.0))
    if any(not math.isfinite(v) or (v < 0 if k == 'forward_stopping_extension_m' else v <= 0)
           for k, v in values.items()):
        raise ValueError('invalid_trial_limits')
    if (not math.isfinite(turn_approach) or turn_approach < 0
            or 0 < turn_approach < 0.2 or turn_approach > 0.25):
        raise ValueError('invalid_turn_approach_distance')
    if (values['tracking_margin_m'] < 0.25
            or values['forward_stopping_extension_m'] != 0
            or values['cancel_stop_distance_envelope_m'] <= 0
            or values['cancel_stop_distance_envelope_m'] > 0.6
            or values['actual_vector_speed_limit_m_s'] > 0.12
            or values['maximum_tracking_error_m'] > 0.15
            or values['post_goal_hold_sim_s'] < 3.0
            or float(planner['max_velocity_m_s']) > 0.1):
        raise ValueError('trial_outside_calibrated_protocol')
    values['offset_enu_m'] = offset.tolist()
    values['turn_approach_distance_m'] = turn_approach
    values['configured_axis_velocity_limit_m_s'] = float(planner['max_velocity_m_s']) * 1.05 + 0.0001
    values['conservative_vector_velocity_limit_m_s'] = math.sqrt(3)*values['configured_axis_velocity_limit_m_s']
    return values


def remaining_forward_corridor_distance(start, current, offset):
    """Project the remaining tested straight-ahead route onto its forward axis."""
    start=np.asarray(start,dtype=float)
    current=np.asarray(current,dtype=float)
    offset=np.asarray(offset,dtype=float)
    if (start.shape!=(3,) or current.shape!=(3,) or offset.shape!=(3,)
            or not np.isfinite(start).all() or not np.isfinite(current).all()
            or not np.isfinite(offset).all() or offset[0]<=0
            or np.linalg.norm(offset[1:])>1e-9):
        raise ValueError('invalid_forward_corridor_pose')
    direction=offset/np.linalg.norm(offset)
    return float(np.linalg.norm(offset)-np.dot(current-start,direction))


def certify_trial_reference_tube(knots, control, degree, trial_start,
                                 forward_distance, tolerance_m=0.05,
                                 max_sample_spacing_m=0.001,
                                 minimum_forward_delta_m=None):
    """Bound the actual spline inside the fixed N08 translation tube.

    The control polygon encloses a B-spline but can extend outside the curve.
    Check the curve at bounded spatial intervals and use the derivative
    control polygon's norm bound to cover every point between samples. The
    configured lateral/vertical tolerance is not enlarged.
    """
    knots = np.asarray(knots, dtype=float)
    control = np.asarray(control, dtype=float)
    start = np.asarray(trial_start, dtype=float)
    degree = int(degree)
    forward_distance = float(forward_distance)
    tolerance_m = float(tolerance_m)
    max_sample_spacing_m = float(max_sample_spacing_m)
    minimum_forward_delta = (-tolerance_m if minimum_forward_delta_m is None
                              else float(minimum_forward_delta_m))
    if (control.ndim != 2 or control.shape[1] != 3
            or start.shape != (3,) or control.shape[0] <= degree
            or knots.shape != (control.shape[0] + degree + 1,)
            or not np.isfinite(control).all() or not np.isfinite(start).all()
            or not np.isfinite(knots).all() or np.any(np.diff(knots) <= 0)
            or degree < 1 or not math.isfinite(forward_distance)
            or forward_distance <= 0 or not math.isfinite(tolerance_m)
            or tolerance_m <= 0 or not math.isfinite(max_sample_spacing_m)
            or max_sample_spacing_m <= 0
            or not math.isfinite(minimum_forward_delta)
            or minimum_forward_delta < -tolerance_m
            or minimum_forward_delta > forward_distance):
        raise ValueError('invalid_trial_reference_tube_inputs')
    begin = float(knots[degree])
    end = float(knots[control.shape[0]])
    duration = end - begin
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('invalid_trial_reference_tube_duration')
    derivative, _ = derivative_polygon(knots, control, degree)
    if (derivative.ndim != 2 or derivative.shape[1] != 3
            or not np.isfinite(derivative).all()):
        raise ValueError('invalid_trial_reference_tube_derivative')
    speed_bound = float(np.max(np.linalg.norm(derivative, axis=1)))
    if not math.isfinite(speed_bound):
        raise ValueError('invalid_trial_reference_tube_speed_bound')
    interval_count = max(1, int(math.ceil(
        speed_bound * duration / max_sample_spacing_m)))
    sample_interval = duration / interval_count
    between_sample_bound = speed_bound * sample_interval / 2.0
    times = np.linspace(begin, end, interval_count + 1)
    samples = np.asarray([bspline_eval(knots, control, degree, t)
                          for t in times], dtype=float)
    if samples.shape != (interval_count + 1, 3) or not np.isfinite(samples).all():
        raise ValueError('invalid_trial_reference_tube_samples')
    delta = samples - start
    lateral_vertical = np.linalg.norm(delta[:, 1:], axis=1)
    clearances = np.column_stack((
        delta[:, 0] - minimum_forward_delta,
        forward_distance + tolerance_m - delta[:, 0],
        tolerance_m - lateral_vertical))
    sample_index, component_index = np.unravel_index(
        int(np.argmin(clearances)), clearances.shape)
    minimum_clearance = float(clearances[sample_index, component_index])
    component_names = ('rear_x', 'forward_x', 'lateral_vertical')
    continuous_required_clearance = between_sample_bound + 1e-9
    passed = minimum_clearance >= continuous_required_clearance
    return {
        'passed': bool(passed),
        'reason': ('curve_and_inter_sample_bound_inside_trial_tube' if passed
                   else 'sampled_curve_outside_continuous_tube_bound'),
        'forward_x_bounds_relative_to_start_m': [minimum_forward_delta,
                                                 forward_distance + tolerance_m],
        'lateral_vertical_radius_m': tolerance_m,
        'sample_count': int(len(samples)),
        'sample_interval_s': float(sample_interval),
        'maximum_sample_spacing_m': float(speed_bound * sample_interval),
        'derivative_control_speed_bound_m_s': speed_bound,
        'between_sample_displacement_bound_m': float(between_sample_bound),
        'continuous_required_sample_clearance_m': float(continuous_required_clearance),
        'minimum_sample_clearance_m': minimum_clearance,
        'limiting_boundary': component_names[component_index],
        'limiting_sample_time_s': float(times[sample_index] - begin),
        'curve_x_delta_min_m': float(delta[:, 0].min()),
        'curve_x_delta_max_m': float(delta[:, 0].max()),
        'curve_lateral_vertical_deviation_max_m': float(lateral_vertical.max()),
    }


def raw_vehicle_reachable_query(snapshot, center_xyz_m, yaw_rad,
                                longitudinal_offsets_m,
                                lateral_vertical_radius_m,
                                tracking_error_radius_m,
                                policy=None, primitives=None,
                                yaw_deviation_bound_rad=TRIAL_FORWARD_YAW_DEVIATION_BOUND_RAD):
    """Check raw cells against a conservative X500/D435i reachable envelope.

    The locked SDF collision primitives are enclosed by world AABBs. The
    spatial uncertainty and tracking error are represented by a 3D ball;
    the sampled path interval and 5cm lateral/vertical tube remain directional.
    Spatial uncertainty includes the voxel half diagonal, so voxel-center
    classification conservatively covers complete raw voxels.
    """
    policy = policy or load_policy()
    primitives = primitives or collision_primitives()
    try:
        occupancy = np.asarray(snapshot['occupancy'])
        origin = np.asarray(snapshot['origin_m'], dtype=float)
        resolution = float(snapshot['resolution_m'])
        center = np.asarray(center_xyz_m, dtype=float)
        offsets = np.asarray(longitudinal_offsets_m, dtype=float)
        yaw = float(yaw_rad)
        yaw_deviation = float(yaw_deviation_bound_rad)
        tube = float(lateral_vertical_radius_m)
        tracking_error = float(tracking_error_radius_m)
        uncertainty = float(policy['spatial_budget']['combined_uncertainty_margin_m'])
    except (KeyError, TypeError, ValueError, OverflowError):
        return {'accepted': False, 'reason': 'invalid_snapshot_or_query',
                'unknown_count': 0, 'free_count': 0, 'occupied_count': 0,
                'components_checked': 0}
    failure = {'accepted': False, 'reason': 'invalid_snapshot_or_query',
               'unknown_count': 0, 'free_count': 0, 'occupied_count': 0,
               'components_checked': 0}
    if (occupancy.ndim != 3 or origin.shape != (3,) or center.shape != (3,)
            or offsets.shape != (2,) or not np.isfinite(origin).all()
            or not np.isfinite(center).all() or not np.isfinite(offsets).all()
            or (snapshot.get('dimensions_xyz') is not None
                and tuple(occupancy.shape) != tuple(snapshot['dimensions_xyz']))
            or not math.isfinite(resolution) or resolution <= 0
            or not math.isfinite(yaw) or not math.isfinite(yaw_deviation)
            or yaw_deviation < 0 or yaw_deviation > TRIAL_FORWARD_YAW_DEVIATION_BOUND_RAD
            or not math.isfinite(tube) or tube < 0
            or not math.isfinite(tracking_error) or tracking_error < 0
            or not math.isfinite(uncertainty) or uncertainty <= 0
            or offsets[0] > offsets[1]):
        return failure
    ball_radius = uncertainty + tracking_error
    if not math.isfinite(ball_radius) or ball_radius <= 0:
        return failure
    yaw_sample_count = 31
    yaw_samples = np.linspace(yaw - yaw_deviation, yaw + yaw_deviation,
                              yaw_sample_count)
    yaw_sample_spacing = (2.0 * yaw_deviation / (yaw_sample_count - 1))
    offset_midpoint = float(np.mean(offsets))
    offset_halfspan = float((offsets[1] - offsets[0]) / 2.0)
    counts = {'unknown': 0, 'free': 0, 'occupied': 0}
    components_checked = 0
    for primitive in primitives:
        try:
            local_center = np.asarray(primitive['center_imu_m'], dtype=float)
            if local_center.shape != (3,) or not np.isfinite(local_center).all():
                return {**failure, 'reason': 'invalid_vehicle_primitive'}
            if primitive['kind'] == 'box':
                local_rotation = _rotation(primitive['rpy_rad'])
                half = np.asarray(primitive['size_m'], dtype=float) / 2.0
                if (local_rotation.shape != (3, 3) or half.shape != (3,)
                        or not np.isfinite(local_rotation).all()
                        or not np.isfinite(half).all()):
                    return {**failure, 'reason': 'invalid_vehicle_primitive'}
                local_corners = (local_center
                                 + (np.asarray([
                                     [-1, -1, -1], [-1, -1, 1], [-1, 1, -1],
                                     [-1, 1, 1], [1, -1, -1], [1, -1, 1],
                                     [1, 1, -1], [1, 1, 1]], dtype=float)
                                    * half) @ local_rotation.T)
                radial_bound = float(np.max(np.linalg.norm(
                    local_corners[:, :2], axis=1)))
                swept = []
                for sample_yaw in yaw_samples:
                    rotation = np.asarray([
                        [math.cos(sample_yaw), -math.sin(sample_yaw), 0.0],
                        [math.sin(sample_yaw), math.cos(sample_yaw), 0.0],
                        [0.0, 0.0, 1.0],
                    ])
                    swept.append(center + local_corners @ rotation.T)
                swept = np.concatenate(swept, axis=0)
                angular_cover = radial_bound * yaw_sample_spacing / 2.0
                world_low = np.min(swept, axis=0)
                world_high = np.max(swept, axis=0)
                world_low[:2] -= angular_cover
                world_high[:2] += angular_cover
                world_center = (world_low + world_high) / 2.0
                world_half = (world_high - world_low) / 2.0
            elif primitive['kind'] == 'rotor_disk':
                radius = float(primitive['radius_m'])
                half_height = float(primitive['half_height_m'])
                if (not math.isfinite(radius) or radius <= 0
                        or not math.isfinite(half_height) or half_height <= 0):
                    return {**failure, 'reason': 'invalid_vehicle_primitive'}
                rotor_centers = []
                for sample_yaw in yaw_samples:
                    rotation = np.asarray([
                        [math.cos(sample_yaw), -math.sin(sample_yaw), 0.0],
                        [math.sin(sample_yaw), math.cos(sample_yaw), 0.0],
                        [0.0, 0.0, 1.0],
                    ])
                    rotor_centers.append(center + rotation @ local_center)
                rotor_centers = np.asarray(rotor_centers)
                angular_cover = float(np.linalg.norm(local_center[:2])) * yaw_sample_spacing / 2.0
                world_low = np.min(rotor_centers, axis=0) - [radius + angular_cover,
                                                             radius + angular_cover,
                                                             half_height]
                world_high = np.max(rotor_centers, axis=0) + [radius + angular_cover,
                                                             radius + angular_cover,
                                                             half_height]
                world_center = (world_low + world_high) / 2.0
                world_half = (world_high - world_low) / 2.0
            else:
                return {**failure, 'reason': 'unsupported_vehicle_primitive'}
        except (KeyError, TypeError, ValueError, OverflowError):
            return {**failure, 'reason': 'invalid_vehicle_primitive'}

        component_center = world_center.copy()
        component_center[0] += offset_midpoint
        component_half = world_half.copy()
        component_half[0] += offset_halfspan
        extent = np.asarray([ball_radius, ball_radius + tube,
                             ball_radius + tube])
        ranges = [_candidate_index_range(
            component_center[axis] - component_half[axis] - extent[axis],
            component_center[axis] + component_half[axis] + extent[axis],
            origin[axis], resolution, occupancy.shape[axis])
            for axis in range(3)]
        if any(item is None for item in ranges):
            return {'accepted': False, 'reason': 'outside_map',
                    'unknown_count': counts['unknown'],
                    'free_count': counts['free'],
                    'occupied_count': counts['occupied'],
                    'components_checked': components_checked,
                    'component': primitive.get('name')}
        slices = tuple(slice(item[0], item[1] + 1) for item in ranges)
        axes = [origin[axis] + (np.arange(ranges[axis][0], ranges[axis][1] + 1)
                                + 0.5) * resolution for axis in range(3)]
        xx, yy, zz = np.meshgrid(*axes, indexing='ij')
        dx = np.maximum(np.abs(xx - component_center[0])
                        - component_half[0], 0.0)
        dy = np.maximum(np.abs(yy - component_center[1])
                        - component_half[1], 0.0)
        dz = np.maximum(np.abs(zz - component_center[2])
                        - component_half[2], 0.0)
        tube_excess = np.maximum(np.hypot(dy, dz) - tube, 0.0)
        intersects = np.hypot(dx, tube_excess) <= ball_radius + 1e-12
        local = occupancy[slices]
        if not np.all(np.isin(local, (-1, 0, 100))):
            return {'accepted': False, 'reason': 'snapshot_occupancy_code_invalid',
                    'unknown_count': counts['unknown'],
                    'free_count': counts['free'],
                    'occupied_count': counts['occupied'],
                    'components_checked': components_checked,
                    'component': primitive.get('name')}
        classes = local[intersects]
        counts['unknown'] += int(np.count_nonzero(classes == -1))
        counts['occupied'] += int(np.count_nonzero(classes == 100))
        counts['free'] += int(np.count_nonzero(classes == 0))
        components_checked += 1
        reason = ('occupied' if counts['occupied'] else
                  'unknown' if counts['unknown'] else
                  'free' if counts['free'] else 'empty_query')
        if reason != 'free':
            return {'accepted': True, 'reason': reason,
                    'unknown_count': counts['unknown'],
                    'free_count': counts['free'],
                    'occupied_count': counts['occupied'],
                    'components_checked': components_checked,
                    'component': primitive.get('name')}
    return {'accepted': True,
            'reason': 'free' if counts['free'] else 'empty_query',
            'unknown_count': counts['unknown'],
            'free_count': counts['free'],
            'occupied_count': counts['occupied'],
            'components_checked': components_checked}


def certify_forward_trial_corridor(snapshot, start, offset, body_radius,
                                   tracking_margin, maximum_tracking_error,
                                   extension=0.0, step=0.025, yaw_rad=0.0,
                                   policy=None, primitives=None,
                                   yaw_deviation_bound_rad=TRIAL_FORWARD_YAW_DEVIATION_BOUND_RAD):
    """Certify a one-way N08 reachable set against the locked airframe shape."""
    start = np.asarray(start, dtype=float)
    offset = np.asarray(offset, dtype=float)
    body_radius = float(body_radius)
    tracking_margin = float(tracking_margin)
    maximum_tracking_error = float(maximum_tracking_error)
    extension = float(extension)
    step = float(step)
    yaw_rad = float(yaw_rad)
    yaw_deviation_bound_rad = float(yaw_deviation_bound_rad)
    policy = policy or load_policy()
    primitives = primitives or collision_primitives()
    lookahead = TRIAL_FORWARD_CORRIDOR_LOOKAHEAD_M
    if (start.shape != (3,) or offset.shape != (3,)
            or not np.isfinite(start).all() or not np.isfinite(offset).all()
            or offset[0] <= 0 or np.linalg.norm(offset[1:]) > 1e-9
            or not math.isfinite(body_radius) or body_radius <= 0
            or not math.isfinite(tracking_margin) or tracking_margin < 0.25
            or not math.isfinite(maximum_tracking_error)
            or maximum_tracking_error <= 0 or maximum_tracking_error > 0.15
            or not math.isfinite(extension) or extension != 0.0
            or not math.isfinite(step) or not 0 < step <= 0.025
            or not math.isfinite(yaw_rad)
            or not math.isfinite(yaw_deviation_bound_rad)
            or not 0 <= yaw_deviation_bound_rad <= TRIAL_FORWARD_YAW_DEVIATION_BOUND_RAD):
        raise ValueError('invalid_forward_trial_corridor')
    locked_body_radius = float(
        policy['spatial_budget']['body_reference_clearance_radius_m'])
    if abs(body_radius - locked_body_radius) > 1e-6:
        raise ValueError('forward_trial_vehicle_envelope_mismatch')

    distance = float(np.linalg.norm(offset)) + extension
    direction = offset / np.linalg.norm(offset)
    count = int(math.ceil(distance / step))
    spacing = distance / count
    spatial_uncertainty = float(
        policy['spatial_budget']['combined_uncertainty_margin_m'])
    start_hold_shift = lookahead + (
        tracking_margin - (lookahead + maximum_tracking_error))
    start_hold = raw_vehicle_reachable_query(
        snapshot, start + direction * start_hold_shift, yaw_rad,
        (-start_hold_shift, -start_hold_shift), 0.0,
        maximum_tracking_error, policy, primitives,
        yaw_deviation_bound_rad)
    terminal_hold = raw_vehicle_reachable_query(
        snapshot, start + offset, yaw_rad, (0.0, 0.0), 0.0,
        tracking_margin, policy, primitives, yaw_deviation_bound_rad)
    reverse_allowance = TRIAL_FORWARD_INITIAL_REVERSE_BOUND_M
    rows = []
    for index in range(count + 1):
        along = index * spacing
        center = start + direction * (along + lookahead)
        longitudinal_offsets = (
            -lookahead - (reverse_allowance if index == 0 else spacing / 2.0),
            -lookahead + spacing / 2.0)
        query = raw_vehicle_reachable_query(
            snapshot, center, yaw_rad, longitudinal_offsets,
            TRIAL_FORWARD_REFERENCE_TUBE_M, maximum_tracking_error,
            policy, primitives, yaw_deviation_bound_rad)
        center_bound = (
            math.hypot(max(abs(longitudinal_offsets[0]),
                           abs(longitudinal_offsets[1])),
                       TRIAL_FORWARD_REFERENCE_TUBE_M)
            + maximum_tracking_error)
        rows.append({'distance_from_start_m': float(along),
                     'center_xyz_m': center.tolist(),
                     'longitudinal_offsets_m': list(longitudinal_offsets),
                     'reachable_center_bound_m': center_bound,
                     **query})

    first_bound = math.hypot(lookahead + reverse_allowance,
                             TRIAL_FORWARD_REFERENCE_TUBE_M) + maximum_tracking_error
    repeated_bound = math.hypot(lookahead + spacing / 2.0,
                                TRIAL_FORWARD_REFERENCE_TUBE_M) + maximum_tracking_error
    reachable_center_bound = max(first_bound, repeated_bound)
    available_center_bound = tracking_margin + spacing / 2.0
    start_hold_bound = start_hold_shift + maximum_tracking_error
    passed = (start_hold.get('accepted') and start_hold.get('reason') == 'free'
              and start_hold_bound <= tracking_margin + 1e-12
              and len(rows) == count + 1
              and all(row.get('accepted') and row.get('reason') == 'free'
                      for row in rows)
              and terminal_hold.get('accepted')
              and terminal_hold.get('reason') == 'free'
              and reachable_center_bound <= available_center_bound + 1e-12)
    return {
        'passed': bool(passed),
        'reason': ('vehicle_shape_forward_corridor_and_holds_known_free'
                   if passed else 'vehicle_shape_forward_corridor_or_hold_not_clear'),
        'start_xyz_m': start.tolist(),
        'goal_xyz_m': (start + offset).tolist(),
        'corridor_end_xyz_m': (start + direction * distance).tolist(),
        'tracking_margin_m': tracking_margin,
        'body_radius_m': body_radius,
        'spatial_uncertainty_margin_m': spatial_uncertainty,
        'vehicle_geometry': 'locked_x500_d435i_sdf_collision_primitives',
        'geometry_query': 'primitive_aabb_superset_dilated_by_spatial_and_tracking_balls',
        'yaw_rad': yaw_rad,
        'yaw_deviation_bound_rad': yaw_deviation_bound_rad,
        'maximum_tracking_error_m': maximum_tracking_error,
        'forward_lookahead_m': lookahead,
        'reference_tube_lateral_vertical_m': TRIAL_FORWARD_REFERENCE_TUBE_M,
        'initial_reverse_allowance_m': reverse_allowance,
        'reference_tube_forward_bounds_relative_to_start_m': [
            -reverse_allowance, distance + TRIAL_FORWARD_REFERENCE_TUBE_M],
        'first_station_center_bound_m': first_bound,
        'reachable_center_bound_m': reachable_center_bound,
        'available_center_bound_m': available_center_bound,
        'remaining_geometric_slack_m': available_center_bound - reachable_center_bound,
        'start_hold_center_bound_m': start_hold_bound,
        'start_hold_available_bound_m': tracking_margin,
        'start_hold_geometric_slack_m': tracking_margin - start_hold_bound,
        'query_spacing_m': spacing,
        'equivalent_spherical_budget_radius_m': body_radius + tracking_margin + spacing / 2.0,
        'cover_radius_m': body_radius + tracking_margin + spacing / 2.0,
        'start_hold': start_hold,
        'required_queries': count + 1,
        'queries': rows,
        'terminal_hold': terminal_hold,
        'terminal_hold_center_xyz_m': (start + offset).tolist(),
        'terminal_hold_tracking_allowance_m': tracking_margin,
    }


def certify_trial_capsule(snapshot, airborne_start, offset, body_radius,
                          tracking_margin, extension, step=0.025):
    start = np.asarray(airborne_start, dtype=float)
    offset = np.asarray(offset, dtype=float)
    if (start.shape != (3,) or offset.shape != (3,)
            or not np.isfinite(start).all() or not np.isfinite(offset).all()
            or not 0 < step <= 0.025 or body_radius <= 0
            or tracking_margin < 0.25 or extension < 0
            or np.linalg.norm(offset) <= 0):
        raise ValueError('invalid_trial_corridor')
    distance = float(np.linalg.norm(offset)) + extension
    direction = offset / np.linalg.norm(offset)
    count = int(math.ceil(distance/step))
    cover_radius = float(body_radius + tracking_margin + distance/count/2)
    rows=[]
    for i in range(count):
        along=(i+0.5)*distance/count
        center=start+direction*along
        q=raw_sphere_query(snapshot,center,cover_radius)
        rows.append({'distance_from_start_m':along,'center_xyz_m':center.tolist(),**q})
        if not q.get('accepted') or q.get('reason') != 'free':
            break
    passed=len(rows)==count and all(r['reason']=='free' and r['accepted'] for r in rows)
    return {'passed':passed,'start_xyz_m':start.tolist(),
            'goal_xyz_m':(start+offset).tolist(),
            'corridor_end_xyz_m':(start+direction*distance).tolist(),
            'tracking_margin_m':tracking_margin,'forward_extension_m':extension,
            'cover_radius_m':cover_radius,'required_queries':count,'queries':rows}


def certify_trial_turn_approach(snapshot, start, yaw, distance, body_radius,
                                tracking_margin, turn_radius, step=0.025):
    """Certify one bounded forward EGO hop and its stationary-turn hold volume."""
    start = np.asarray(start, dtype=float)
    yaw = float(yaw)
    distance = float(distance)
    body_radius = float(body_radius)
    tracking_margin = float(tracking_margin)
    turn_radius = float(turn_radius)
    step = float(step)
    if (start.shape != (3,) or not np.isfinite(start).all()
            or not math.isfinite(yaw) or not math.isfinite(distance)
            or not 0.2 <= distance <= 0.25
            or not math.isfinite(body_radius) or body_radius <= 0
            or not math.isfinite(tracking_margin) or tracking_margin < 0.25
            or not math.isfinite(turn_radius)
            or turn_radius < body_radius + tracking_margin
            or not math.isfinite(step) or not 0 < step <= 0.025):
        raise ValueError('invalid_turn_approach_certificate_inputs')
    offset = distance * np.asarray([math.cos(yaw), math.sin(yaw), 0.0])
    target = start + offset
    capsule = certify_trial_capsule(snapshot, start, offset, body_radius,
                                    tracking_margin, 0.0, step)
    turn_hold = raw_sphere_query(snapshot, target, turn_radius)
    passed = bool(capsule['passed'] and turn_hold.get('accepted')
                  and turn_hold.get('reason') == 'free')
    return {'passed': passed, 'distance_m': distance, 'start_xyz_m': start.tolist(),
            'yaw_rad': yaw, 'forward_offset_m': offset.tolist(),
            'candidate_turn_center_xyz_m': target.tolist(),
            'forward_capsule': capsule, 'candidate_turn_hold': turn_hold,
            'qualification': 'read-only map admission; execute only as a new EGO goal'}


def certify_trial_landings(snapshot, ground_pose, limits, policy, primitives):
    """Prospective geometry while DISARMED, based on the confirmed raw floor."""
    distance=limits['offset_enu_m'][0]+limits['forward_stopping_extension_m']
    rows=[]
    for along in np.linspace(0,distance,int(math.ceil(distance/0.1))+1):
        pose={**ground_pose,'center_xyz_m':list(ground_pose['center_xyz_m'])}
        pose['center_xyz_m'][0]+=float(along)
        result=check_entry_schedule(snapshot,pose,ground_confirmed=True,
                                    disarmed=True,control_disabled=True,
                                    policy=policy,primitives=primitives)
        rows.append({'distance_from_start_m':float(along),'accepted':result['accepted'],
                     'reason':result['reason']})
        if not result['accepted']:
            break
    return {'passed':bool(rows) and rows[-1]['distance_from_start_m']>=distance-1e-9
                     and all(r['accepted'] for r in rows),'queries':rows}
