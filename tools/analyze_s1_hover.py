#!/usr/bin/env python3
"""Offline S1 checks for a no-goal hover run and its PX4 ULog."""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from pyulog import ULog


def stats(values):
    x = np.asarray(values, dtype=float)
    if not len(x):
        return {'count': 0, 'rmse': None, 'p95': None, 'max': None}
    return {
        'count': int(len(x)),
        'rmse': float(np.sqrt(np.mean(x ** 2))),
        'p95': float(np.percentile(x, 95)),
        'max': float(np.max(x)),
    }


def rotation(q_wxyz):
    q = np.asarray(q_wxyz, dtype=float)
    norm = np.linalg.norm(q)
    if q.shape != (4,) or not np.isfinite(norm) or norm < 1e-9:
        raise ValueError('invalid ULog quaternion')
    w, x, y, z = q / norm
    return np.array([
        [1 - 2 * (y*y + z*z), 2 * (x*y - z*w), 2 * (x*z + y*w)],
        [2 * (x*y + z*w), 1 - 2 * (x*x + z*z), 2 * (y*z - x*w)],
        [2 * (x*z - y*w), 2 * (y*z + x*w), 1 - 2 * (x*x + y*y)],
    ])


def interpolate(stamps, values, query):
    right = int(np.searchsorted(stamps, query, side='left'))
    if right < len(stamps) and stamps[right] == query:
        return values[right].copy(), 0
    if right == 0 or right >= len(stamps):
        raise ValueError('requested ULog time outside sample coverage')
    left = right - 1
    gap = int(stamps[right] - stamps[left])
    ratio = (query - stamps[left]) / gap
    return values[left] + ratio * (values[right] - values[left]), gap


def clock_fit(rows, start_wall=None, end_wall=None):
    selected = [r for r in rows if
                (start_wall is None or r['wall_elapsed_s'] >= start_wall) and
                (end_wall is None or r['wall_elapsed_s'] <= end_wall)]
    if len(selected) < 3:
        return {'sample_count': len(selected), 'rtf_sim_s_per_wall_s': None,
                'residual_p95_s': None, 'residual_max_s': None}
    wall = np.asarray([r['wall_elapsed_s'] for r in selected], dtype=float)
    sim = np.asarray([r['sim_time_ns'] for r in selected], dtype=float) / 1e9
    if np.any(np.diff(wall) <= 0) or np.any(np.diff(sim) < 0):
        raise ValueError('clock receipt samples are non-monotonic')
    slope, intercept = np.polyfit(wall - wall[0], sim, 1)
    residual = sim - (slope * (wall - wall[0]) + intercept)
    return {
        'sample_count': len(selected),
        'rtf_sim_s_per_wall_s': float(slope),
        'residual_p95_s': float(np.percentile(np.abs(residual), 95)),
        'residual_max_s': float(np.max(np.abs(residual))),
        'fit_wall_span_s': float(wall[-1] - wall[0]),
        'fit_sim_span_s': float(sim[-1] - sim[0]),
    }


def dataset(ulog, name):
    return next((item.data for item in ulog.data_list if item.name == name), None)


def _finite_pose_rows(data, stamp_name, position_names, quaternion_names):
    stamps = np.asarray(data[stamp_name], dtype=np.int64)
    positions = np.column_stack([data[name] for name in position_names]).astype(float)
    quaternions = np.column_stack([data[name] for name in quaternion_names]).astype(float)
    valid = (np.isfinite(stamps) & np.isfinite(positions).all(axis=1)
             & np.isfinite(quaternions).all(axis=1))
    stamps, positions, quaternions = stamps[valid], positions[valid], quaternions[valid]
    order = np.argsort(stamps, kind='stable')
    stamps, positions, quaternions = stamps[order], positions[order], quaternions[order]
    unique = np.concatenate(([True], np.diff(stamps) > 0))
    return stamps[unique], positions[unique], quaternions[unique]


def vio_error(ulog, hover_start_us, hover_end_us):
    truth_pos = dataset(ulog, 'vehicle_local_position_groundtruth')
    truth_att = dataset(ulog, 'vehicle_attitude_groundtruth')
    vio = dataset(ulog, 'vehicle_visual_odometry')
    if truth_pos is None or truth_att is None or vio is None:
        raise ValueError('ULog lacks VIO or isolated ground-truth datasets')
    truth_t = np.asarray(truth_pos['timestamp_sample'], dtype=np.int64)
    truth_p = np.column_stack([truth_pos['x'], truth_pos['y'], truth_pos['z']]).astype(float)
    att_t = np.asarray(truth_att['timestamp_sample'], dtype=np.int64)
    truth_q = np.column_stack([truth_att[f'q[{i}]'] for i in range(4)]).astype(float)
    vio_t, vio_p, vio_q = _finite_pose_rows(
        vio, 'timestamp_sample', ['position[0]', 'position[1]', 'position[2]'],
        [f'q[{i}]' for i in range(4)])
    truth_valid = np.isfinite(truth_p).all(axis=1)
    truth_t, truth_p = truth_t[truth_valid], truth_p[truth_valid]
    att_valid = np.isfinite(truth_q).all(axis=1)
    att_t, truth_q = att_t[att_valid], truth_q[att_valid]
    if len(truth_t) < 3 or len(att_t) < 3 or len(vio_t) < 3:
        raise ValueError('insufficient ULog pose samples')

    paired_vio, paired_truth, paired_truth_q, interpolation_gaps = [], [], [], []
    for stamp, pos, q in zip(vio_t, vio_p, vio_q):
        if stamp < max(truth_t[0], att_t[0]) or stamp > min(truth_t[-1], att_t[-1]):
            continue
        gt_pos, pos_gap = interpolate(truth_t, truth_p, int(stamp))
        gt_q, att_gap = interpolate(att_t, truth_q, int(stamp))
        paired_vio.append((int(stamp), pos, q))
        paired_truth.append(gt_pos)
        paired_truth_q.append(gt_q)
        interpolation_gaps.append(max(pos_gap, att_gap))
    if len(paired_vio) < 20:
        raise ValueError('insufficient time-aligned VIO and truth samples')

    # One rigid alignment at the first source-synchronized sample; no scale or segment refit.
    first_rotation = rotation(paired_truth_q[0]) @ rotation(paired_vio[0][2]).T
    first_translation = paired_truth[0] - first_rotation @ paired_vio[0][1]
    errors, sample_stamps = [], []
    for (stamp, pos, _), gt_pos in zip(paired_vio, paired_truth):
        if hover_start_us <= stamp <= hover_end_us:
            aligned = first_rotation @ pos + first_translation
            errors.append(float(np.linalg.norm(aligned - gt_pos)))
            sample_stamps.append(stamp)
    if not errors:
        raise ValueError('no VIO samples overlap the hover clock interval')
    return {
        'alignment': 'one fixed SE(3) at first source-synchronized VIO/truth sample; scale=1; no refit',
        'alignment_stamp_us': int(paired_vio[0][0]),
        'hold_interval_position_error_m': stats(errors),
        'max_truth_interpolation_gap_s': float(max(interpolation_gaps, default=0) / 1e6),
        'hold_sample_stamp_start_us': int(min(sample_stamps)),
        'hold_sample_stamp_end_us': int(max(sample_stamps)),
    }


def hold_errors(ulog, start_us, end_us):
    local = dataset(ulog, 'vehicle_local_position')
    truth = dataset(ulog, 'vehicle_local_position_groundtruth')
    setpoint = dataset(ulog, 'trajectory_setpoint')
    if local is None or truth is None or setpoint is None:
        raise ValueError('ULog lacks local position, truth, or offboard setpoint data')
    local_t = np.asarray(local['timestamp_sample'], dtype=np.int64)
    local_p = np.column_stack([local['x'], local['y'], local['z']]).astype(float)
    good_local = (np.isfinite(local_p).all(axis=1) & (local_t >= start_us) & (local_t <= end_us))
    local_t, local_p = local_t[good_local], local_p[good_local]

    sp_t = np.asarray(setpoint['timestamp'], dtype=np.int64)
    sp_p = np.column_stack([setpoint[f'position[{i}]'] for i in range(3)]).astype(float)
    good_sp = np.isfinite(sp_p).all(axis=1)
    sp_t, sp_p = sp_t[good_sp], sp_p[good_sp]
    sort = np.argsort(sp_t, kind='stable')
    sp_t, sp_p = sp_t[sort], sp_p[sort]
    unique = np.concatenate(([True], np.diff(sp_t) > 0))
    sp_t, sp_p = sp_t[unique], sp_p[unique]
    mask = (local_t >= sp_t[0]) & (local_t <= sp_t[-1])
    local_t, local_p = local_t[mask], local_p[mask]
    if len(local_t) < 20 or len(sp_t) < 3:
        raise ValueError('insufficient hold position/setpoint samples')
    interpolated = np.column_stack([
        np.interp(local_t, sp_t, sp_p[:, axis]) for axis in range(3)])
    tracking_error = np.linalg.norm(local_p - interpolated, axis=1)
    hover_sp = sp_p[(sp_t >= start_us) & (sp_t <= end_us)]
    if len(hover_sp) < 3:
        raise ValueError('insufficient offboard setpoints during hover')
    setpoint_motion = np.linalg.norm(hover_sp - hover_sp[0], axis=1)

    truth_t = np.asarray(truth['timestamp_sample'], dtype=np.int64)
    truth_p = np.column_stack([truth['x'], truth['y'], truth['z']]).astype(float)
    valid = np.isfinite(truth_p).all(axis=1)
    truth_t, truth_p = truth_t[valid], truth_p[valid]
    in_hold = (truth_t >= start_us) & (truth_t <= end_us)
    hold_t, hold_p = truth_t[in_hold], truth_p[in_hold]
    if len(hold_t) < 20:
        raise ValueError('insufficient ground-truth samples during hover')
    displacement = np.linalg.norm(hold_p - hold_p[0], axis=1)
    return {
        'px4_local_position_to_offboard_hold_setpoint_m': stats(tracking_error),
        'hold_reference_motion_m': stats(setpoint_motion),
        'hold_reference_first_ned_m': hover_sp[0].tolist(),
        'hold_reference_last_ned_m': hover_sp[-1].tolist(),
        'truth_displacement_from_hover_start_m': stats(displacement),
        'truth_reference_stamp_us': int(hold_t[0]),
    }


def evaluate(run_dir):
    run_dir = Path(run_dir)
    report = json.loads((run_dir / 'vio-ego-flight-report.json').read_text())
    inputs = json.loads((run_dir / 'runtime-inputs.json').read_text())
    host = json.loads((run_dir / 'host-launch.json').read_text())
    requested = float(host['requested_hover_sim_s'])
    start_ns, end_ns = int(report['hover_start_sim_time_ns']), int(report['hover_end_sim_time_ns'])
    start_us, end_us = start_ns // 1000, end_ns // 1000
    logs = sorted((run_dir / 'px4_sitl_default' / 'log').rglob('*.ulg'))
    if len(logs) != 1:
        raise ValueError(f'expected one closed PX4 ULog, found {len(logs)}')
    ulog_path = logs[0]
    ulog = ULog(str(ulog_path))
    reasons = []

    if report.get('result') != 'PASS': reasons.append('hover_probe_not_pass')
    if report.get('action_goal_sent'): reasons.append('navigation_goal_sent')
    if report.get('hover_duration_sim_s', 0) < requested: reasons.append('hover_sim_duration_short')
    if not report.get('landed_and_disarmed'): reasons.append('not_landed_disarmed')
    if report.get('clock_regressions', report.get('simulation_clock_regressions', 0)) != 0:
        reasons.append('simulation_clock_regressed')
    if report.get('hover_clock_stalled'): reasons.append('simulation_clock_stalled')

    hold_wall_start = float(report['hover_start_wall_elapsed_s'])
    hold_wall_end = float(report['hover_end_wall_elapsed_s'])
    clock_rows = report.get('simulation_clock_history', [])
    rtf = {
        'full_observation': clock_fit(clock_rows),
        'hover_interval': clock_fit(clock_rows, hold_wall_start, hold_wall_end),
    }
    if rtf['hover_interval']['rtf_sim_s_per_wall_s'] is None:
        reasons.append('insufficient_clock_fit_samples')

    health = [r for r in report.get('localization_quality_history', [])
              if start_ns <= int(r['stamp_ns']) <= end_ns]
    invalid_health = [r for r in health if not r.get('valid') or int(r.get('state', -1)) != 1]
    if not health or invalid_health:
        reasons.append('localization_not_tracking_during_hover')

    details = [r for r in report.get('bridge_detail_history', [])
               if hold_wall_start <= float(r['wall_elapsed_s']) <= hold_wall_end]
    bad_time = [r for r in details if not r.get('detail', {}).get('px4_time_domain_valid')
                or r.get('detail', {}).get('px4_timestamp_error')
                or r.get('detail', {}).get('odometry_time_error')]
    if not details or bad_time:
        reasons.append('px4_time_mapping_invalid_during_hover')
    freshness = defaultdict(lambda: {'source_age_sim_s': [], 'receipt_age_wall_s': [],
                                     'source_stamp_us': []})
    for row in details:
        for source, sample in row.get('detail', {}).get('px4_telemetry_freshness', {}).items():
            for field in ('source_age_sim_s', 'receipt_age_wall_s', 'source_stamp_us'):
                value = sample.get(field)
                if value is not None:
                    freshness[source][field].append(float(value))
    freshness_summary = {
        source: {
            field: ({'count': len(values), 'min': min(values), 'max': max(values)} if values else None)
            for field, values in fields.items()
        }
        for source, fields in sorted(freshness.items())
    }

    statuses = [r for r in report.get('vehicle_status_history', [])
                if hold_wall_start <= float(r['wall_elapsed_s']) <= hold_wall_end]
    if not statuses or any(r.get('failsafe') or int(r.get('nav_state', -1)) != 14
                           or int(r.get('arming_state', -1)) != 2 for r in statuses):
        reasons.append('px4_offboard_or_armed_status_lost_during_hover')

    pubs = report.get('publisher_counts', {})
    control_topics = ['/fmu/in/offboard_control_mode', '/fmu/in/trajectory_setpoint',
                      '/fmu/in/vehicle_command']
    if any(int(pubs.get(topic, 0)) != 1 for topic in control_topics):
        reasons.append('control_publisher_count_not_unique')
    bridge_info = (run_dir / 'px4-bridge-node-info.txt').read_text(errors='replace')
    if 'debug_truth' in bridge_info:
        reasons.append('debug_truth_subscription_present')
    graph_topics = [run_dir / f'control-topic-{i}.txt' for i in range(1, 4)]
    for topic_file in graph_topics:
        if not topic_file.exists():
            reasons.append('control_topic_graph_evidence_missing')
            break
        content = topic_file.read_text(errors='replace')
        if 'Publisher count: 1' not in content or 'uav_px4_bridge' not in content:
            reasons.append('control_publisher_not_unique_bridge')

    try:
        params = ulog.initial_parameters
        gps_ctrl = int(params.get('EKF2_GPS_CTRL', -1))
        ev_ctrl = int(params.get('EKF2_EV_CTRL', -1))
    except Exception:
        gps_ctrl, ev_ctrl = -1, -1
    if gps_ctrl != 0 or ev_ctrl == 0:
        reasons.append('px4_gps_or_visual_odom_parameter_mismatch')

    flags = dataset(ulog, 'estimator_status_flags')
    if flags is None:
        raise ValueError('ULog has no estimator_status_flags')
    flag_t = np.asarray(flags['timestamp_sample'], dtype=np.int64)
    flag_hold = (flag_t >= start_us) & (flag_t <= end_us)
    aid = {}
    for name in ('cs_ev_pos', 'cs_ev_yaw', 'cs_ev_hgt', 'cs_ev_vel',
                 'cs_gnss_pos', 'cs_gnss_vel', 'cs_gnss_hgt', 'cs_gnss_yaw'):
        values = np.asarray(flags[name])[flag_hold]
        aid[name] = {'samples': int(len(values)), 'active_count': int(np.count_nonzero(values))}
    ev_ok = all(aid[name]['active_count'] > 0 for name in ('cs_ev_pos', 'cs_ev_yaw'))
    gnss_ok = all(aid[name]['active_count'] == 0 for name in
                  ('cs_gnss_pos', 'cs_gnss_vel', 'cs_gnss_hgt', 'cs_gnss_yaw'))
    if not ev_ok: reasons.append('ekf2_visual_position_yaw_fusion_not_observed')
    if not gnss_ok: reasons.append('gnss_aiding_observed')

    runtime_topics = report.get('stream_diagnostics', {})
    if runtime_topics.get('raw_depth', {}).get('count', 0) <= 0:
        reasons.append('raw_camera_depth_not_observed')
    if runtime_topics.get('ego_depth', {}).get('count', 0) <= 0:
        reasons.append('ego_depth_not_observed')

    position = hold_errors(ulog, start_us, end_us)
    vio = vio_error(ulog, start_us, end_us)
    renderer = json.loads((run_dir / 'gpu-renderer-runtime.json').read_text())
    if not renderer.get('nvidia_backend'):
        reasons.append('nvidia_renderer_not_confirmed')
    world_text = (run_dir / 'vio_initialization.sdf').read_text(errors='replace')
    if '<render_engine>ogre2</render_engine>' not in world_text:
        reasons.append('gazebo_world_not_configured_for_ogre2')
    renderer['gazebo_sensor_render_engine'] = 'ogre2' if '<render_engine>ogre2</render_engine>' in world_text else None
    renderer['active_depth_output_counts'] = {
        name: int(runtime_topics.get(name, {}).get('count', 0))
        for name in ('raw_depth', 'ego_depth')
    }
    if 'debug_truth' in (run_dir / 'ros-topics.txt').read_text(errors='replace'):
        reasons.append('debug_truth_topic_present')
    gpu_samples = []
    for line in (run_dir / 'container-gpu-samples.csv').read_text(errors='replace').splitlines():
        try:
            gpu_samples.append(float(line.split(',')[1].strip().rstrip('%')))
        except (IndexError, ValueError):
            pass
    if not gpu_samples or max(gpu_samples) <= 0:
        reasons.append('gpu_utilization_not_observed')

    output = {
        'schema_version': 1,
        'run_id': host['run_id'],
        'classification': 'S1_SINGLE_RUN_PASS' if not reasons else 'S1_SINGLE_RUN_FAIL',
        'result': 'PASS' if not reasons else 'FAIL',
        'failure_reasons': reasons,
        'fixed_inputs': inputs,
        'container': {'image': host['image'], 'image_id': host['image_id'],
                      'gpu_utilization_samples': len(gpu_samples),
                      'gpu_utilization_percent_max': max(gpu_samples, default=None)},
        'renderer': renderer,
        'hover': {
            'requested_sim_s': requested,
            'observed_sim_s': report.get('hover_duration_sim_s'),
            'observed_wall_s': report.get('hover_duration_wall_s'),
            'sim_start_ns': start_ns,
            'sim_end_ns': end_ns,
            'no_navigation_goal': not bool(report.get('action_goal_sent')),
            'landed_disarmed': bool(report.get('landed_and_disarmed')),
            'localization_samples': len(health),
            'bridge_detail_samples': len(details),
            'px4_status_samples': len(statuses),
        },
        'rtf_and_clock_fit': rtf,
        'localization_health': {'invalid_samples': len(invalid_health), 'valid_samples': len(health)},
        'time_mapping': {'invalid_samples': len(bad_time), 'valid_samples': len(details)},
        'px4_source_and_receipt_freshness': freshness_summary,
        'ekf2': {'EKF2_EV_CTRL': ev_ctrl, 'EKF2_GPS_CTRL': gps_ctrl, 'aid_flags_during_hold': aid},
        'control_publishers': {topic: pubs.get(topic) for topic in control_topics},
        'position_and_vio_error': {'hold': position, 'vio_to_truth': vio},
        'px4_ulog': {
            'path': str(ulog_path.relative_to(run_dir)),
            'sha256': hashlib.sha256(ulog_path.read_bytes()).hexdigest(),
        },
        'limitations': [
            'Truth is read only from the PX4 ULog after the simulation; no project ROS node subscribes to truth.',
            'The fixed SE(3) pose alignment is diagnostic and does not freeze formal acceptance thresholds.',
            'GPU validation applies only to the recorded RTX 3060 and fixed container image.',
        ],
    }
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = evaluate(args.run_dir)
    output = args.output or (args.run_dir / 'run-analysis.json')
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({k: result[k] for k in
                      ('run_id', 'classification', 'failure_reasons', 'hover', 'position_and_vio_error')},
                     indent=2, ensure_ascii=False))
    if result['result'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
