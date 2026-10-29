#!/usr/bin/env python3
"""Evaluate a same-run N08 spline speed and raw-map geometry certificate."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
EGO_FEASIBILITY_TOLERANCE = 0.05
EGO_VELOCITY_LIMIT_EPSILON_M_S = 1e-4
EXPLICIT_VECTOR_SPEED_CAP_M_S = 0.15


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ns(stamp):
    return int(stamp['sec']) * 1_000_000_000 + int(stamp['nanosec'])


def resolve_trial_speed_profile(launch, root=ROOT):
    """Bind speed limits to the actual launch profile and its recorded bytes."""
    relative = Path(str(launch.get('planner_config', '')))
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if (relative.is_absolute() or not path.is_relative_to(root)
            or relative.parent.as_posix() != 'config/components/mapping'
            or not relative.name.startswith('n08_') or not path.is_file()):
        raise ValueError('invalid_n08_planner_profile')
    expected = (launch.get('source_sha256') or {}).get(relative.as_posix())
    if expected != digest(path):
        raise ValueError('planner_profile_hash_mismatch')
    profile = json.loads(path.read_text())
    maximum = profile.get('max_velocity_m_s')
    acceleration = profile.get('max_acceleration_m_s2')
    cap = profile.get('n08_vector_speed_cap_m_s')
    if cap is None and relative.name == 'n08_low_speed_vector_cap.json':
        cap = EXPLICIT_VECTOR_SPEED_CAP_M_S
    if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0
           for v in (maximum, acceleration, cap)):
        raise ValueError('invalid_trial_speed_limits')
    args = launch.get('ego_launch_arguments') or {}
    if (not np.isclose(float(args.get('max_vel', -1)), maximum, rtol=0, atol=1e-12)
            or not np.isclose(float(args.get('max_acc', -1)), acceleration, rtol=0, atol=1e-12)):
        raise ValueError('launch_speed_or_acceleration_mismatch')
    return {'path': relative.as_posix(), 'max_velocity_m_s': float(maximum),
            'max_acceleration_m_s2': float(acceleration), 'vector_speed_cap_m_s': float(cap),
            'sha256': expected}


def bspline_eval(knots, control, degree, value):
    """Evaluate a B-spline with the de Boor algorithm (NumPy only)."""
    last = len(control) - 1
    if value < knots[degree] - 1e-12 or value > knots[last + 1] + 1e-12:
        return np.full(control.shape[1], np.nan)
    if value >= knots[last + 1]:
        span = last
    else:
        span = int(np.searchsorted(knots, value, side='right') - 1)
        span = min(last, max(degree, span))
    work = np.asarray(control[span - degree:span + 1], dtype=float).copy()
    for level in range(1, degree + 1):
        for index in range(degree, level - 1, -1):
            knot_index = span - degree + index
            denominator = (knots[knot_index + degree - level + 1]
                           - knots[knot_index])
            alpha = (0.0 if abs(denominator) <= 1e-15 else
                     (value - knots[knot_index]) / denominator)
            work[index] = ((1.0 - alpha) * work[index - 1]
                           + alpha * work[index])
    return work[degree]


def derivative_polygon(knots, control, degree):
    """Return the degree-reduced derivative spline control polygon/knots."""
    derivative_control = []
    for index in range(len(control) - 1):
        denominator = knots[index + degree + 1] - knots[index + 1]
        if denominator <= 1e-15:
            derivative_control.append(np.zeros(control.shape[1], dtype=float))
        else:
            derivative_control.append(
                degree * (control[index + 1] - control[index]) / denominator)
    return np.asarray(derivative_control, dtype=float), np.asarray(knots[1:-1], dtype=float)


def certify_speed_bounds(derivative_control, max_velocity,
                         vector_speed_cap=EXPLICIT_VECTOR_SPEED_CAP_M_S):
    """Check EGO's per-axis feasibility limit and the N08 vector-speed cap.

    EGO's UniformBspline feasibility check permits
    ``limit_vel * (1 + feasibility_tolerance) + 1e-4`` per component.
    The derivative control polygon bounds each component and the 3-D norm
    over the whole spline by convex-hull containment.
    """
    values = np.asarray(derivative_control, dtype=float)
    max_velocity = float(max_velocity)
    vector_speed_cap = float(vector_speed_cap)
    if (values.ndim != 2 or values.shape[0] == 0 or values.shape[1] != 3
            or not np.isfinite(values).all()
            or not math.isfinite(max_velocity) or max_velocity <= 0
            or not math.isfinite(vector_speed_cap) or vector_speed_cap <= 0):
        raise ValueError('speed bounds require finite Nx3 derivatives and positive finite limits')
    axis_bound = np.max(np.abs(values), axis=0)
    vector_bound = float(np.max(np.linalg.norm(values, axis=1)))
    per_axis_limit = (max_velocity * (1.0 + EGO_FEASIBILITY_TOLERANCE)
                      + EGO_VELOCITY_LIMIT_EPSILON_M_S)
    per_axis_pass = bool(np.all(axis_bound <= per_axis_limit + 1e-12))
    vector_pass = bool(vector_bound <= vector_speed_cap + 1e-9)
    return {
        'per_axis_pass': per_axis_pass,
        'vector_pass': vector_pass,
        'passed': bool(per_axis_pass and vector_pass),
        'per_axis_derivative_control_bound_m_s': axis_bound.tolist(),
        'per_axis_limit_m_s': per_axis_limit,
        'vector_derivative_control_bound_m_s': vector_bound,
        'vector_limit_m_s': vector_speed_cap,
        'feasibility_tolerance': EGO_FEASIBILITY_TOLERANCE,
        'per_axis_epsilon_m_s': EGO_VELOCITY_LIMIT_EPSILON_M_S,
    }


def raw_sphere_query(snapshot, center, radius):
    """Mirror EGO's canonical closed-cell raw occupancy sphere query."""
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


def failed(run, reason, details=None):
    return {
        'schema': 'n08-live-curve-certificate/v2',
        'run_id': run.name,
        'passed': False,
        'n08_execute_authorized': False,
        'stopping_envelope_proven': False,
        'reason': reason,
        'details': details or {},
        'scope': 'compute-only spline speed and same-identity raw-map geometry; no XY or braking measurement',
    }


def evaluate(run):
    run = Path(run).resolve()
    flight_path = run / 'flight.json'
    capture_path = run / 'n08-live-curve-map.json'
    launch_path = run.parent / f'{run.name}-stack' / 'launch-manifest.json'
    params_path = run / 'px4-boot-parameters.json'
    for path in (flight_path, capture_path, launch_path, params_path):
        if not path.is_file():
            return failed(run, 'required_evidence_missing', {'missing': str(path)})

    flight = json.loads(flight_path.read_text())
    capture = json.loads(capture_path.read_text())
    launch = json.loads(launch_path.read_text())
    params = json.loads(params_path.read_text())
    if flight.get('result') != 'PASS':
        return failed(run, 'compute_only_runner_not_passed', {'runner_result': flight.get('result')})
    mode = flight.get('launch_mode_record') or {}
    graph = flight.get('compute_only_graph') or {}
    if not (mode.get('mode') == 'compute_only'
            and graph.get('bridge_subscribed_to_position_cmd') is False
            and graph.get('bridge_subscribed_to_isolated_input') is True):
        return failed(run, 'compute_only_bridge_isolation_not_proven')
    if capture.get('status') != 'captured':
        return failed(run, 'same_run_live_map_capture_failed',
                      {'capture_failure': capture.get('failure'),
                       'capture_status': capture.get('status')})

    goal = capture.get('goal') or {}
    spline = capture.get('bspline') or {}
    snapshot = capture.get('snapshot') or {}
    expected = flight.get('n05_current_area') or {}
    bspline_identity = (spline.get('goal_id'), spline.get('epoch'))
    if (bspline_identity != (flight.get('goal_id'), flight.get('epoch'))
            or goal.get('goal_id') != flight.get('goal_id')
            or goal.get('epoch') != flight.get('epoch')):
        return failed(run, 'live_spline_goal_or_epoch_mismatch', {
            'flight_goal_id': flight.get('goal_id'), 'flight_epoch': flight.get('epoch'),
            'spline_goal_id': spline.get('goal_id'), 'spline_epoch': spline.get('epoch'),
            'navigation_goal_id': goal.get('goal_id'), 'navigation_epoch': goal.get('epoch')})
    if (snapshot.get('epoch') != flight.get('epoch')
            or snapshot.get('map_id') != goal.get('map_id')
            or snapshot.get('map_id') != expected.get('map_id')
            or snapshot.get('frame_id') != goal.get('target', {}).get('header', {}).get('frame_id')):
        return failed(run, 'live_map_identity_or_frame_mismatch', {
            'snapshot': {k: snapshot.get(k) for k in ('epoch', 'map_id', 'frame_id')},
            'goal_map_id': goal.get('map_id'), 'n05_map_id': expected.get('map_id')})
    if not params.get('passed'):
        return failed(run, 'px4_boot_readback_not_passed')

    args = launch.get('ego_launch_arguments') or {}
    try:
        trial_speed = resolve_trial_speed_profile(launch)
    except (ValueError, TypeError, OSError) as exc:
        return failed(run, 'trial_speed_profile_invalid', {'error': str(exc)})

    archive = run / str(snapshot.get('archive', ''))
    if not archive.is_file():
        return failed(run, 'raw_map_archive_missing', {'archive': str(archive)})
    with np.load(archive) as stored:
        occupancy = np.asarray(stored['occupancy'], dtype=np.int8)
        inflated = np.asarray(stored['inflated'], dtype=np.uint8)

    order = int(spline.get('order', -1))
    knots = np.asarray(spline.get('knots', []), dtype=float)
    points = spline.get('pos_pts', [])
    control = np.asarray([[p['x'], p['y'], p['z']] for p in points], dtype=float)
    if (order < 1 or knots.size != control.shape[0] + order + 1
            or control.ndim != 2 or control.shape[1] != 3
            or not np.isfinite(knots).all() or not np.isfinite(control).all()):
        return failed(run, 'invalid_bspline_message', {
            'order': order, 'knot_count': int(knots.size),
            'control_point_count': int(control.shape[0]) if control.ndim else 0})
    begin = float(knots[order])
    end = float(knots[control.shape[0]])
    duration = end - begin
    if not np.isfinite(duration) or duration <= 0:
        return failed(run, 'invalid_bspline_duration', {'begin': begin, 'end': end})
    derivative_control, derivative_knots = derivative_polygon(knots, control, order)
    dense_t = np.linspace(begin, end, max(1001, int(duration * 1000) + 1))
    dense_position = np.asarray([bspline_eval(knots, control, order, t)
                                 for t in dense_t])
    dense_velocity = np.asarray([bspline_eval(derivative_knots, derivative_control,
                                               order - 1, t)
                                 for t in dense_t])
    speed_metrics = certify_speed_bounds(derivative_control, float(args['max_vel']),
                                         trial_speed['vector_speed_cap_m_s'])
    speed_bound = speed_metrics['vector_derivative_control_bound_m_s']
    peak_speed = float(np.max(np.linalg.norm(dense_velocity, axis=1)))
    component_bound = np.asarray(
        speed_metrics['per_axis_derivative_control_bound_m_s'], dtype=float)
    start = dense_position[0]
    finish = dense_position[-1]

    npz_meta = json.loads(capture_path.read_text())['snapshot']
    raw = {
        'origin_m': np.asarray(npz_meta['origin_m'], dtype=float),
        'resolution_m': float(npz_meta['resolution_m']),
        'occupancy': occupancy,
    }
    body_radius = float(args['obstacles_inflation'])
    hold_neighborhood = float(args['terminal_hold_neighborhood'])
    hold_radius = body_radius + hold_neighborhood
    start_hold = raw_sphere_query(raw, start, hold_radius)
    end_hold = raw_sphere_query(raw, finish, hold_radius)
    start_body = raw_sphere_query(raw, start, body_radius)
    end_body = raw_sphere_query(raw, finish, body_radius)

    resolution = float(snapshot['resolution_m'])
    interval_count = max(1, int(np.ceil(speed_bound * duration / (resolution / 4.0))))
    dt = duration / interval_count
    cover_radius = body_radius + speed_bound * dt / 2.0
    curve_queries = []
    for index in range(interval_count):
        t = begin + (index + 0.5) * dt
        center = np.asarray(bspline_eval(knots, control, order, t), dtype=float)
        query = raw_sphere_query(raw, center, cover_radius)
        curve_queries.append({'index': index, 'time_s': t - begin,
                              'center_xyz_m': center.tolist(), **query})
        if not query.get('accepted') or query.get('reason') != 'free':
            break
    curve_free = (len(curve_queries) == interval_count
                  and all(q.get('accepted') and q.get('reason') == 'free'
                          for q in curve_queries))

    tangent = finish - np.asarray(bspline_eval(
        knots, control, order, max(begin, end - min(1e-3, duration / 100))), dtype=float)
    tangent_norm = float(np.linalg.norm(tangent))
    extension = []
    if tangent_norm > 1e-9:
        direction = tangent / tangent_norm
        for step in range(1, 21):
            distance = step * 0.05
            query = raw_sphere_query(raw, finish + direction * distance, body_radius)
            extension.append({'distance_after_goal_m': distance, **query})
            if not query.get('accepted') or query.get('reason') != 'free':
                break

    capture_stamp = int(snapshot['response_stamp_ns'])
    fusion_age = (capture_stamp - int(snapshot['last_fusion_stamp_ns'])) / 1e9
    source_age = (capture_stamp - int(snapshot['last_depth_source_stamp_ns'])) / 1e9
    freshness_limit = 0.4
    speed_pass = speed_metrics['passed']
    freshness_pass = (0 <= fusion_age <= freshness_limit
                      and 0 <= source_age <= freshness_limit)
    geometry_pass = all(q.get('accepted') and q.get('reason') == 'free'
                        for q in (start_body, end_body, start_hold, end_hold)) and curve_free
    px4 = params.get('parameters') or {}
    certificate = {
        'schema': 'n08-live-curve-certificate/v2',
        'run_id': run.name,
        'passed': bool(speed_pass and geometry_pass and freshness_pass),
        'speed_pass': bool(speed_pass),
        'per_axis_speed_pass': speed_metrics['per_axis_pass'],
        'vector_speed_pass': speed_metrics['vector_pass'],
        'speed_check': speed_metrics,
        'geometry_pass': bool(geometry_pass),
        'map_freshness_pass': bool(freshness_pass),
        'n08_execute_authorized': False,
        'stopping_envelope_proven': False,
        'scope': 'compute-only spline speed and same-identity raw-map geometry; no XY or braking measurement',
        'identity': {'goal_id': flight['goal_id'], 'epoch': flight['epoch'],
                     'map_id': snapshot['map_id'], 'frame_id': snapshot['frame_id'],
                     'goal_map_id_matches_fresh_n05_map': snapshot['map_id'] == expected.get('map_id')},
        'map_freshness': {'snapshot_response_stamp_ns': capture_stamp,
                          'last_fusion_stamp_ns': int(snapshot['last_fusion_stamp_ns']),
                          'last_source_stamp_ns': int(snapshot['last_depth_source_stamp_ns']),
                          'fusion_age_s': fusion_age, 'source_age_s': source_age,
                          'limit_s': freshness_limit},
        'profile': {'path': launch.get('planner_config'),
                    'source_sha256': trial_speed['sha256'],
                    'configured_max_velocity_m_s_per_axis': float(args['max_vel']),
                    'ego_feasibility_tolerance': EGO_FEASIBILITY_TOLERANCE,
                    'configured_max_acceleration_m_s2': float(args['max_acc']),
                    'body_radius_m': body_radius,
                    'terminal_hold_neighborhood_m': hold_neighborhood,
                    'hold_radius_m': hold_radius},
        'bspline': {'order': order, 'control_point_count': int(control.shape[0]),
                    'duration_s': duration, 'start_xyz_m': start.tolist(),
                    'end_xyz_m': finish.tolist(),
                    'speed_bound_from_derivative_control_hull_m_s': speed_bound,
                    'dense_peak_vector_speed_m_s': peak_speed,
                    'per_axis_derivative_control_bound_m_s': component_bound.tolist(),
                    'per_axis_derivative_control_limit_m_s': speed_metrics['per_axis_limit_m_s'],
                    'explicit_vector_speed_cap_m_s': trial_speed['vector_speed_cap_m_s']},
        'raw_geometry': {'start_body_sphere': start_body,
                         'start_hold_sphere': start_hold,
                         'end_body_sphere': end_body,
                         'end_terminal_hold_sphere': end_hold,
                         'continuous_sweep': {'queries': len(curve_queries),
                                              'required_queries': interval_count,
                                              'cover_radius_m': cover_radius,
                                              'first_failure': next((q for q in curve_queries
                                                  if q.get('reason') != 'free'
                                                  or not q.get('accepted')), None)},
                         'post_goal_axis_body_spheres': extension,
                         'raw_snapshot_sha256': digest(archive)},
        'px4_boot_readback': {key: px4.get(key) for key in
                              ('MPC_ACC_HOR', 'MPC_ACC_HOR_MAX',
                               'MPC_JERK_AUTO', 'MPC_XY_VEL_MAX')},
        'px4_readback_scope': 'boot-time native px4-param show; maximum limits only, not a guaranteed minimum deceleration or response-delay bound',
        'canonical_sphere_query_source': {
            'path': 'src/vendor/ego_planner/planner/plan_env/include/plan_env/sphere_query.h',
            'sha256': digest(ROOT / 'src/vendor/ego_planner/planner/plan_env/include/plan_env/sphere_query.h'),
        },
        'velocity_feasibility_source': {
            'path': 'src/vendor/ego_planner/planner/bspline_opt/src/uniform_bspline.cpp',
            'sha256': digest(ROOT / 'src/vendor/ego_planner/planner/bspline_opt/src/uniform_bspline.cpp'),
            'launch_tolerance_path': 'src/vendor/ego_planner/planner/plan_manage/launch/advanced_param.launch.py',
            'launch_tolerance_sha256': digest(ROOT / 'src/vendor/ego_planner/planner/plan_manage/launch/advanced_param.launch.py'),
        },
        'no_xy_executed': True,
    }
    return certificate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir', type=Path)
    args = parser.parse_args()
    try:
        result = evaluate(args.run_dir)
    except Exception as exc:
        result = failed(args.run_dir.resolve(), 'certificate_evaluation_error',
                        {'error': str(exc)})
    output_path = args.run_dir / 'n08-curve-certificate.json'
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n',
                           encoding='utf-8')
    print(json.dumps({'passed': result.get('passed', False),
                      'reason': result.get('reason'),
                      'speed_pass': result.get('speed_pass'),
                      'geometry_pass': result.get('geometry_pass'),
                      'map_freshness_pass': result.get('map_freshness_pass')},
                     ensure_ascii=False))
    # A failed diagnostic certificate is an expected no-go result, distinct
    # from failure of the compute-only cancel/hold/landing runner.
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
