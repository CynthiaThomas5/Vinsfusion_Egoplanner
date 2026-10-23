#!/usr/bin/env python3
"""Offline raw VINS full-state baseline against isolated Gazebo truth.

The raw VINS velocity is expressed in its world frame by the locked VINS source.
The simulated Gazebo truth origin is d435i_link, coincident with the simulated
D435i IMU origin. A single initial rigid alignment maps the estimate to truth;
scale stays one and return segments are never realigned.
"""
import argparse
import csv
import hashlib
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools/debug_truth'))
sys.path.insert(0, str(ROOT / 'src/own/uav_sim'))
from evaluate_vins_motion import rotation
from evaluate_vio_quality_alignment import (
    _interpolate_position, _interpolate_quaternion, _stats, _unit_quaternion)
from uav_sim.geometry import px4_sensor_mount

STAMP_ROUNDING_TOLERANCE_NS = 2


def _jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def _rotation_vector(matrix):
    matrix = np.asarray(matrix, dtype=float)
    cosine = float(np.clip((np.trace(matrix) - 1.0) / 2.0, -1.0, 1.0))
    angle = math.acos(cosine)
    skew = np.array([matrix[2, 1] - matrix[1, 2],
                     matrix[0, 2] - matrix[2, 0],
                     matrix[1, 0] - matrix[0, 1]])
    if angle < 1e-8:
        return 0.5 * skew
    if abs(math.pi - angle) < 1e-5:
        values, vectors = np.linalg.eigh((matrix + np.eye(3)) / 2.0)
        axis = vectors[:, int(np.argmax(values))]
        return axis * angle
    return skew * (angle / (2.0 * math.sin(angle)))


def _euler_xyz(matrix):
    matrix = np.asarray(matrix, dtype=float)
    pitch = math.asin(float(np.clip(-matrix[2, 0], -1.0, 1.0)))
    if abs(math.cos(pitch)) > 1e-8:
        roll = math.atan2(matrix[2, 1], matrix[2, 2])
        yaw = math.atan2(matrix[1, 0], matrix[0, 0])
    else:
        roll = math.atan2(-matrix[1, 2], matrix[1, 1])
        yaw = 0.0
    return np.asarray([roll, pitch, yaw])


def _pose_at(stamps, positions, quaternions, query_ns, max_gap_ns):
    position, gap = _interpolate_position(stamps, positions, int(query_ns))
    if gap > max_gap_ns + STAMP_ROUNDING_TOLERANCE_NS:
        raise ValueError(f'pose bracket gap {gap / 1e9:.6f}s exceeds limit')
    quaternion = _interpolate_quaternion(stamps, quaternions, int(query_ns))
    return position, rotation(quaternion), gap


def _frame_contract(epoch, raw, truth, project_root=ROOT):
    expected_world = f'vins_{epoch}_world'
    expected_body = f'vins_{epoch}_imu'
    if any(row.get('frame') != expected_world or row.get('child_frame') != expected_body for row in raw):
        raise ValueError('raw VINS frame/epoch mismatch')
    x500 = ET.parse(project_root / 'simulation/models/x500_d435i/model.sdf').getroot().find('model')
    plugin = x500.find("plugin[@name='gz::sim::systems::OdometryPublisher']")
    if plugin is None or (plugin.findtext('odom_frame'), plugin.findtext('robot_base_frame')) != ('world', 'd435i_link'):
        raise ValueError('Gazebo truth publisher reference point changed')
    rig = ET.parse(project_root / 'simulation/models/d435i/model.sdf').getroot().find('model')
    imu = rig.find("link[@name='d435i_link']/sensor[@name='imu']")
    if imu is None:
        raise ValueError('Expected IMU mounted on d435i_link')
    pose = [float(value) for value in imu.findtext('pose').split()]
    if len(pose) != 6 or any(abs(value) > 1e-12 for value in pose):
        raise ValueError('D435i IMU no longer coincides with d435i_link; update point transform')
    generator = (project_root / 'tools/generate_vins_config.py').read_text()
    if "body_frame_id=f'vins_{epoch}_imu'" not in generator or "'body_frame': 'd435i_link'" not in (
            project_root / 'src/own/uav_sim/uav_sim/geometry.py').read_text():
        raise ValueError('VINS body-frame generation no longer matches the IMU truth origin')
    mount = px4_sensor_mount(project_root / 'simulation/models/x500_d435i/model.sdf')
    lever_flu = np.asarray(mount['translation_frd_m'], dtype=float) * [1, -1, -1]
    return {
        'vins_world_frame': expected_world, 'vins_body_frame': expected_body,
        'gazebo_truth_world_frame': 'world', 'gazebo_truth_pose_origin': 'd435i_link',
        'gazebo_truth_child_frame': 'd435i_link', 'imu_sensor_frame': imu.findtext('gz_frame_id'),
        'vins_body_and_gazebo_truth_origins_coincident': True,
        'raw_vins_to_truth_translation_m': [0.0, 0.0, 0.0],
        'base_link_to_imu_lever_arm_flu_m': lever_flu.tolist(),
        'lever_arm_note': 'The IMU-to-base lever arm is used only to audit point-velocity decomposition. It is not added to d435i_link truth a second time.'}


def _truth_velocity(stamps, positions, quaternions, stamp_ns, half_window_ns,
                    truth_gap_ns, base_to_imu_flu):
    before_ns, after_ns = stamp_ns - half_window_ns, stamp_ns + half_window_ns
    p_before, r_before, _ = _pose_at(stamps, positions, quaternions, before_ns, truth_gap_ns)
    p_after, r_after, _ = _pose_at(stamps, positions, quaternions, after_ns, truth_gap_ns)
    p_mid, r_mid, _ = _pose_at(stamps, positions, quaternions, stamp_ns, truth_gap_ns)
    duration_s = (after_ns - before_ns) / 1e9
    velocity_imu = (p_after - p_before) / duration_s
    omega_world = _rotation_vector(r_after @ r_before.T) / duration_s
    lever_world = r_mid @ base_to_imu_flu

    base_before = p_before - r_before @ base_to_imu_flu
    base_after = p_after - r_after @ base_to_imu_flu
    velocity_base = (base_after - base_before) / duration_s
    velocity_lever = np.cross(omega_world, lever_world)
    reconstructed_imu = velocity_base + velocity_lever
    return {
        'velocity_imu': velocity_imu, 'velocity_base': velocity_base,
        'omega_world': omega_world, 'velocity_lever': velocity_lever,
        'lever_reconstruction_error': reconstructed_imu - velocity_imu,
        'position_before': p_before, 'position_after': p_after,
        'orientation_mid': r_mid}


def _rpe(raw_t, raw_p, raw_q, truth_t, truth_p, truth_q,
         alignment_r, horizons_s, raw_gap_ns, truth_gap_ns):
    output = []
    detail = []
    for horizon_s in horizons_s:
        horizon_ns = int(round(horizon_s * 1e9))
        position_errors, rotation_errors, actual_durations = [], [], []
        rejected = 0
        for start_ns in raw_t:
            end_ns = int(start_ns) + horizon_ns
            try:
                ep0, eq0, _ = _pose_at(raw_t, raw_p, raw_q, int(start_ns), raw_gap_ns)
                ep1, eq1, _ = _pose_at(raw_t, raw_p, raw_q, end_ns, raw_gap_ns)
                tp0, tq0, _ = _pose_at(truth_t, truth_p, truth_q, int(start_ns), truth_gap_ns)
                tp1, tq1, _ = _pose_at(truth_t, truth_p, truth_q, end_ns, truth_gap_ns)
            except ValueError:
                rejected += 1
                continue
            eq0, eq1 = alignment_r @ eq0, alignment_r @ eq1
            delta_est_r = eq0.T @ eq1
            delta_truth_r = tq0.T @ tq1
            delta_est_p = eq0.T @ (alignment_r @ (ep1 - ep0))
            delta_truth_p = tq0.T @ (tp1 - tp0)
            rotation_error = delta_truth_r.T @ delta_est_r
            position_error = delta_est_p - delta_truth_p
            pos_norm = float(np.linalg.norm(position_error))
            angle = float(np.linalg.norm(_rotation_vector(rotation_error)))
            position_errors.append(pos_norm)
            rotation_errors.append(math.degrees(angle))
            actual_durations.append(horizon_s)
            detail.append({'window_s': horizon_s, 'start_source_ns': int(start_ns),
                           'end_source_ns': end_ns, 'translation_error_m': pos_norm,
                           'rotation_error_deg': math.degrees(angle),
                           **dict(zip(('translation_dx_m', 'translation_dy_m', 'translation_dz_m'),
                                      map(float, position_error)))})
        output.append({'target_window_s': float(horizon_s), 'supported_pairs': len(position_errors),
                       'candidate_pairs': len(raw_t), 'rejected_pairs': rejected,
                       'translation_error_m': _stats(position_errors),
                       'rotation_error_deg': _stats(rotation_errors),
                       'actual_window_s': _stats(actual_durations)})
    return output, detail


def evaluate(raw, truth, trace, stages, fixture, protocol, runtime_contract,
             truth_gap_s=0.04, raw_gap_s=0.2, velocity_half_window_s=0.1):
    epoch = fixture.get('epoch', '')
    if not re.fullmatch(r'[0-9a-f]{32}', epoch):
        raise ValueError('fixture result has no unique VINS epoch')
    raw = [row for row in raw if row.get('kind') == 'raw']
    if len(raw) < 3:
        raise ValueError('insufficient raw VINS odometry')
    frames = _frame_contract(epoch, raw, truth)
    if not trace or trace[0].get('epoch') != epoch or trace[0].get('target') != [0.0, 0.0, 0.0, 0.0]:
        raise ValueError('a stationary same-epoch fixture trace is required')
    if not stages:
        raise ValueError('fixture stages are missing')
    for stage in stages:
        if stage.get('end_sim_s', 0) < stage.get('begin_sim_s', 0):
            raise ValueError('fixture stage time is reversed')
    if protocol.get('profile') != 'drift' or protocol.get('schema_version') != 1:
        raise ValueError('run did not capture the frozen full-state drift protocol')
    if runtime_contract.get('sha256') is None:
        raise ValueError('runtime contract hash is missing')

    for row in raw:
        required = ('velocity_xyz', 'receive_sim_ns', 'receive_monotonic_ns')
        if any(key not in row for key in required):
            raise ValueError('raw VINS velocity and receive-clock fields are missing')
    raw_t = np.asarray([int(row['source_ns']) for row in raw], dtype=np.int64)
    raw_p = np.asarray([row['xyz'] for row in raw], dtype=float)
    raw_q = np.asarray([_unit_quaternion(row['q_xyzw']) for row in raw])
    raw_v = np.asarray([row['velocity_xyz'] for row in raw], dtype=float)
    raw_receive_sim = np.asarray([int(row['receive_sim_ns']) for row in raw], dtype=np.int64)
    raw_receive_wall = np.asarray([int(row['receive_monotonic_ns']) for row in raw], dtype=np.int64)
    truth_t = np.asarray([int(row['stamp_ns']) for row in truth], dtype=np.int64)
    truth_p = np.asarray([row['xyz'] for row in truth], dtype=float)
    truth_q = np.asarray([_unit_quaternion(row['q_xyzw']) for row in truth])
    if len(truth_t) < 3 or np.any(np.diff(truth_t) <= 0) or np.any(np.diff(raw_t) <= 0):
        raise ValueError('source timestamps must be strictly increasing; no sorting or repair')
    if (not np.isfinite(raw_p).all() or not np.isfinite(raw_v).all()
            or not np.isfinite(truth_p).all()):
        raise ValueError('non-finite VINS/truth state')
    if np.any(np.diff(raw_receive_wall) <= 0):
        raise ValueError('raw callback receive time must increase monotonically')

    first_stationary_ns = int(round(float(trace[0]['sim_s']) * 1e9))
    target_anchor_ns = first_stationary_ns + int(round(protocol['alignment']['anchor_after_first_stationary_trace_sim_s'] * 1e9))
    prior = np.flatnonzero(raw_t <= target_anchor_ns)
    if not len(prior) or target_anchor_ns - int(raw_t[prior[-1]]) > 150_000_000:
        raise ValueError('no fresh raw VINS pose at the initial stationary alignment point')
    anchor = int(prior[-1])
    truth_gap_ns, raw_gap_ns = int(truth_gap_s * 1e9), int(raw_gap_s * 1e9)
    half_window_ns = int(round(velocity_half_window_s * 1e9))
    p_anchor, truth_r_anchor, _ = _pose_at(truth_t, truth_p, truth_q, int(raw_t[anchor]), truth_gap_ns)
    align_r = truth_r_anchor @ rotation(raw_q[anchor]).T
    align_t = p_anchor - align_r @ raw_p[anchor]
    base_to_imu = np.asarray(frames['base_link_to_imu_lever_arm_flu_m'], dtype=float)

    curve, rejected_pose, rejected_velocity = [], [], []
    for index, row in enumerate(raw):
        stamp_ns = int(raw_t[index])
        if stamp_ns < raw_t[anchor]:
            continue
        try:
            p_truth, r_truth, _ = _pose_at(truth_t, truth_p, truth_q, stamp_ns, truth_gap_ns)
        except ValueError as exc:
            rejected_pose.append({'source_ns': stamp_ns, 'reason': str(exc)})
            continue
        p_est = align_r @ raw_p[index] + align_t
        r_est = align_r @ rotation(raw_q[index])
        position_error = p_est - p_truth
        rotation_error = r_truth.T @ r_est
        euler_error = np.degrees(_euler_xyz(rotation_error))
        angle_error = math.degrees(float(np.linalg.norm(_rotation_vector(rotation_error))))
        try:
            truth_motion = _truth_velocity(truth_t, truth_p, truth_q, stamp_ns,
                                           half_window_ns, truth_gap_ns, base_to_imu)
            v_truth = truth_motion['velocity_imu']
            v_est = align_r @ raw_v[index]
            velocity_error = v_est - v_truth
        except ValueError as exc:
            truth_motion = None
            v_truth = v_est = velocity_error = None
            rejected_velocity.append({'source_ns': stamp_ns, 'reason': str(exc)})

        source_age_s = (int(row['receive_sim_ns']) - stamp_ns) / 1e9
        result = {
            'source_ns': stamp_ns,
            'receive_sim_ns': int(row['receive_sim_ns']),
            'receive_monotonic_ns': int(row['receive_monotonic_ns']),
            'source_age_at_receipt_sim_s': source_age_s,
            'position_error_m': float(np.linalg.norm(position_error)),
            'attitude_geodesic_error_deg': angle_error,
            'roll_error_deg': float(euler_error[0]), 'pitch_error_deg': float(euler_error[1]),
            'yaw_error_deg': float(euler_error[2]),
            'truth_x_m': float(p_truth[0]), 'truth_y_m': float(p_truth[1]), 'truth_z_m': float(p_truth[2]),
            'estimate_x_m': float(p_est[0]), 'estimate_y_m': float(p_est[1]), 'estimate_z_m': float(p_est[2]),
            'dx_m': float(position_error[0]), 'dy_m': float(position_error[1]), 'dz_m': float(position_error[2]),
        }
        for name, vector in [('vins_velocity_world_m_s', align_r @ raw_v[index]),
                             ('truth_velocity_imu_world_m_s', v_truth),
                             ('velocity_error_world_m_s', velocity_error)]:
            for axis, value in zip('xyz', vector if vector is not None else [None] * 3):
                result[f'{name}_{axis}'] = None if value is None else float(value)
        if truth_motion is not None:
            result.update({
                'truth_speed_imu_m_s': float(np.linalg.norm(v_truth)),
                'truth_speed_base_m_s': float(np.linalg.norm(truth_motion['velocity_base'])),
                'truth_angular_speed_rad_s': float(np.linalg.norm(truth_motion['omega_world'])),
                'lever_arm_velocity_m_s': float(np.linalg.norm(truth_motion['velocity_lever'])),
                'lever_velocity_reconstruction_error_m_s': float(np.linalg.norm(truth_motion['lever_reconstruction_error']))})
            result['velocity_error_m_s'] = float(np.linalg.norm(velocity_error))
        else:
            result.update({'truth_speed_imu_m_s': None, 'truth_speed_base_m_s': None,
                           'truth_angular_speed_rad_s': None, 'lever_arm_velocity_m_s': None,
                           'lever_velocity_reconstruction_error_m_s': None, 'velocity_error_m_s': None})
        curve.append(result)
    if len(curve) < 3:
        raise ValueError('insufficient truth-paired raw VINS poses')

    rpe_summary, rpe_rows = _rpe(raw_t[anchor:], raw_p[anchor:], raw_q[anchor:], truth_t, truth_p, truth_q,
                                 align_r, protocol['support']['rpe_windows_sim_s'],
                                 raw_gap_ns, truth_gap_ns)
    pose_error = [row['position_error_m'] for row in curve]
    attitude_error = [row['attitude_geodesic_error_deg'] for row in curve]
    velocity_rows = [row for row in curve if row['velocity_error_m_s'] is not None]
    valid_truth_indices = [i for i, row in enumerate(curve) if row['truth_speed_imu_m_s'] is not None]
    selected_source_t = raw_t[anchor:]
    selected_receive_sim = raw_receive_sim[anchor:]
    selected_receive_wall = raw_receive_wall[anchor:]
    receipt_source_age = (selected_receive_sim - selected_source_t) / 1e9
    source_gap_s = np.diff(selected_source_t) / 1e9
    receipt_gap_s = np.diff(selected_receive_wall) / 1e9
    valid_pairs = [(curve[i-1], curve[i]) for i in range(1, len(curve))
                   if curve[i]['source_ns'] - curve[i-1]['source_ns']
                   <= raw_gap_ns + STAMP_ROUNDING_TOLERANCE_NS]
    truth_path = sum(float(np.linalg.norm(
        np.array([current[f'truth_{axis}_m'] for axis in 'xyz']) -
        np.array([previous[f'truth_{axis}_m'] for axis in 'xyz'])))
        for previous, current in valid_pairs)
    t0, t1 = int(curve[0]['source_ns']), int(curve[-1]['source_ns'])
    source_span_ns = int(raw_t[-1] - raw_t[anchor])
    motion = {
        'source_duration_sim_s': source_span_ns / 1e9,
        'paired_truth_path_length_m': truth_path,
        'truth_position_span_xyz_m': np.ptp(np.asarray([[row[f'truth_{a}_m'] for a in 'xyz'] for row in curve]), axis=0).tolist(),
        'truth_yaw_span_deg': float(np.ptp([_euler_xyz(rotation(q))[2] for q in truth_q]) * 180 / math.pi),
        'truth_roll_pitch_variation_from_level_deg': {
            'roll': float(np.ptp([_euler_xyz(rotation(q))[0] for q in truth_q]) * 180 / math.pi),
            'pitch': float(np.ptp([_euler_xyz(rotation(q))[1] for q in truth_q]) * 180 / math.pi)},
        'truth_imu_speed_m_s': _stats([curve[i]['truth_speed_imu_m_s'] for i in valid_truth_indices]),
        'truth_base_speed_m_s': _stats([curve[i]['truth_speed_base_m_s'] for i in valid_truth_indices]),
        'truth_angular_speed_rad_s': _stats([curve[i]['truth_angular_speed_rad_s'] for i in valid_truth_indices]),
        'configured_translation_m_per_leg': 1.2,
        'configured_elevation_m': 0.6,
        'configured_yaw_excursion_rad': 0.3,
        'observed_return_count': sum(stage.get('label') == 'return' for stage in stages),
        'support_note': 'Observed bounds apply only to this unarmed, slow physical-support route and this simulation model.'}
    report = {
        'schema_version': 1,
        'scope': __doc__,
        'run_id': str(fixture.get('run_id') or ''), 'epoch': epoch,
        'fixture_outcome': fixture.get('outcome'), 'fixture_error': fixture.get('error'),
        'fixture_completed_stages': len(stages), 'fixture_expected_stages': protocol.get('expected_stage_count'),
        'fixture_motion_completed': len(stages) == protocol.get('expected_stage_count'),
        'runtime_contract_sha256': runtime_contract['sha256'],
        'protocol_sha256': hashlib.sha256(json.dumps(protocol, sort_keys=True).encode()).hexdigest(),
        'coordinate_contract': frames,
        'alignment': {'method': protocol['alignment']['method'], 'reference_source_ns': int(raw_t[anchor]),
                      'target_source_ns': target_anchor_ns, 'rotation': align_r.tolist(),
                      'translation_m': align_t.tolist(), 'scale': 1,
                      'per_return_realignment': False, 'trajectory_fit': False, 'time_offset_fit': False},
        'interval': {'start_source_ns': t0, 'end_source_ns': t1,
                     'duration_sim_s': (t1 - t0) / 1e9, 'analyzed_samples': len(curve)},
        'position_ate_m': _stats(pose_error),
        'attitude_geodesic_error_deg': _stats(attitude_error),
        'roll_error_deg': _stats([row['roll_error_deg'] for row in curve]),
        'pitch_error_deg': _stats([row['pitch_error_deg'] for row in curve]),
        'yaw_error_deg': _stats([row['yaw_error_deg'] for row in curve]),
        'velocity_error_m_s': _stats([row['velocity_error_m_s'] for row in velocity_rows]),
        'velocity_error_components_m_s': {axis: _stats([row[f'velocity_error_world_m_s_{axis}'] for row in velocity_rows]) for axis in 'xyz'},
        'lever_arm_velocity_audit': {
            'reference_window_sim_s': 2 * velocity_half_window_s,
            'maximum_reconstruction_error_m_s': max((row['lever_velocity_reconstruction_error_m_s'] for row in velocity_rows), default=None),
            'method': 'Finite-difference truth at d435i_link (IMU origin); separately transform that point trajectory to base_link and reconstruct with omega cross r.'},
        'rpe': rpe_summary,
        'repeated_return_drift': 'See return-drift.json; same single alignment and source-time windows.',
        'timing': {
            'source_rate_hz': _stats((1.0 / source_gap_s).tolist()),
            'source_gap_sim_s': _stats(source_gap_s.tolist()),
            'callback_receipt_rate_wall_hz': _stats((1.0 / receipt_gap_s).tolist()),
            'callback_receipt_gap_wall_s': _stats(receipt_gap_s.tolist()),
            'source_age_at_receipt_sim_s': _stats(receipt_source_age),
            'negative_source_age_sample_count': int(np.count_nonzero(np.asarray(receipt_source_age) < 0)),
            'max_source_gap_sim_s': float(np.max(source_gap_s)) if len(source_gap_s) else None,
            'max_receipt_gap_wall_s': float(np.max(receipt_gap_s)) if len(receipt_gap_s) else None,
            'source_age_definition': 'receive_sim_ns - source_ns at callback entry; signed values retained.',
            'receipt_clock_definition': 'time.monotonic_ns at callback entry.'},
        'coverage': {
            'raw_samples_total': len(raw), 'raw_samples_at_or_after_anchor': len(selected_source_t),
            'pose_truth_pairs': len(curve), 'pose_truth_rejected': len(rejected_pose),
            'velocity_truth_pairs': len(velocity_rows), 'velocity_truth_rejected': len(rejected_velocity),
            'pose_pair_fraction': len(curve) / max(1, len(raw_t) - anchor),
            'velocity_pair_fraction': len(velocity_rows) / max(1, len(raw_t) - anchor),
            'raw_intervals_over_configured_support_limit': int(np.count_nonzero(
                np.diff(selected_source_t) > raw_gap_ns + STAMP_ROUNDING_TOLERANCE_NS)),
            'timestamp_rounding_tolerance_ns': STAMP_ROUNDING_TOLERANCE_NS,
            'rejected_pose_samples': rejected_pose, 'rejected_velocity_samples': rejected_velocity,
            'truth_interpolation_limit_sim_s': truth_gap_s,
            'raw_pose_interpolation_limit_sim_s': raw_gap_s,
            'velocity_half_window_sim_s': velocity_half_window_s},
        'motion_support': motion,
        'limitations': [
            'Three-dimensional roll/pitch excitation is not configured; their observed small variation does not qualify those axes under aggressive motion.',
            'Unarmed support motion is not free-flight qualification.',
            'Results do not qualify real D435i timing, calibration, texture, vibration, compute load, or long-range operation.',
            'No accuracy acceptance thresholds are declared by this diagnostic.' ]}
    return report, curve, rpe_rows


def evaluate_run(run, protocol_path=None, output_prefix='vio-full-state'):
    run = Path(run).resolve()
    load = lambda name: json.loads((run / name).read_text())
    protocol_file = Path(protocol_path) if protocol_path else run / 'vio-state-protocol.json'
    protocol = json.loads(protocol_file.read_text())
    fixture = load('fixture-result.json')
    fixture['run_id'] = run.name
    truth = _jsonl(run / 'fixture-truth.jsonl')
    raw = _jsonl(run / 'fixture-odometry.jsonl')
    trace = _jsonl(run / 'fixture-trace.jsonl')
    stages = load('fixture-stages.json')
    runtime = load('runtime-contract.json')
    report, curve, rpe = evaluate(raw, truth, trace, stages, fixture, protocol, runtime,
                                  truth_gap_s=protocol['truth']['maximum_truth_interpolation_gap_sim_s'],
                                  raw_gap_s=protocol['support']['maximum_raw_pose_interpolation_gap_sim_s'],
                                  velocity_half_window_s=protocol['truth']['velocity_half_window_sim_s'])
    names = ['fixture-result.json', 'fixture-odometry.jsonl', 'fixture-truth.jsonl',
             'fixture-trace.jsonl', 'fixture-stages.json', 'runtime-contract.json']
    if protocol_file.resolve() == (run / 'vio-state-protocol.json').resolve():
        names.append('vio-state-protocol.json')
    report['input_sha256'] = {name: hashlib.sha256((run / name).read_bytes()).hexdigest() for name in names}
    report['evaluator_sha256'] = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                 for path in [Path(__file__), ROOT / 'tools/evaluate_vio_quality_alignment.py',
                                              ROOT / 'tools/evaluate_vins_motion.py', ROOT / 'tools/generate_vins_config.py',
                                              ROOT / 'src/own/uav_sim/uav_sim/geometry.py',
                                              ROOT / 'src/vendor/vins_fusion/vins/src/utility/visualization.cpp']}
    csv_path = run / f'{output_prefix}-errors.csv'
    with csv_path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(curve[0]))
        writer.writeheader(); writer.writerows(curve)
    rpe_path = run / f'{output_prefix}-rpe.csv'
    with rpe_path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rpe[0]))
        writer.writeheader(); writer.writerows(rpe)
    report['output_sha256'] = {csv_path.name: hashlib.sha256(csv_path.read_bytes()).hexdigest(),
                               rpe_path.name: hashlib.sha256(rpe_path.read_bytes()).hexdigest()}
    output = run / f'{output_prefix}-report.json'
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--protocol', type=Path)
    args = parser.parse_args()
    print(json.dumps(evaluate_run(args.run, args.protocol), indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
