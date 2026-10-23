#!/usr/bin/env python3
"""Offline transport/isolation check, not a claim of correct loops or drift removal."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def evaluate(run):
    load = lambda name: json.loads((run/name).read_text())
    observation = load('loop-observation.json')
    manifest = load('loop-observer-manifest.json')
    qualification = load('qualification.json')
    namespace, frame = manifest['namespace'], manifest['map_frame']
    states, paths, clouds = (observation[k] for k in ['status', 'paths', 'clouds'])
    if not states or not paths or not clouds or not observation['odometry']:
        raise ValueError('Missing actual loop outputs; no synthetic success fallback')
    last = states[-1]
    poses = observation['last_path']['poses']
    stamps = np.array([p['source_ns'] for p in poses], dtype=np.int64)
    xyz = np.array([p['xyz'] for p in poses])
    all_frames = [x['frame'] for x in paths+clouds+observation['odometry']]
    all_frames += [m['frame'] for m in observation['last_markers']]
    outputs = [name for name, _ in observation['observer_node_publishers']]
    inputs = [name for name, _ in observation['observer_node_subscriptions']]
    expected_inputs = {manifest['session']['namespace']+'/'+name for name in [
        'odometry', 'keyframe_pose', 'keyframe_point', 'extrinsic']}
    raw = {p['source_ns']: p for p in load('alignment-observation.json')['samples'] if p['kind'] == 'raw_odom'}
    comparisons = [np.linalg.norm(np.asarray(p['xyz'])-raw[p['source_ns']]['xyz'])
                   for p in observation['odometry'] if p['source_ns'] in raw]
    checks = {
        'identity': observation['epoch'] == manifest['epoch'],
        'backend_normal_exit': int((run/'loop-backend-exit-code').read_text()) == 0,
        'keyframe_graph_progress': len(poses) >= 10 and len(poses) == last['keyframes'] and np.ptp(xyz[:, 0]) > 5,
        'monotonic_keyframe_source_time': bool(np.all(np.diff(stamps) > 0)),
        'finite_graph_and_current_features': bool(np.isfinite(xyz).all() and observation['last_cloud']['xyz']
                                                and np.isfinite(observation['last_cloud']['xyz']).all()),
        'sequential_graph_edges_present': len(observation['last_markers']) >= len(poses)-1,
        'separate_consistent_output_frame': all(f == frame for f in all_frames),
        'no_control_or_tf_publications': all(t.startswith(namespace+'/') or t in ['/rosout', '/parameter_events'] for t in outputs),
        'raw_session_inputs': expected_inputs.issubset(inputs) and not any('truth' in t for t in inputs),
        'bounded_queues': all(max(s['image_buffer'], s['pose_buffer'], s['point_buffer']) <= manifest['limits']['queue_limit'] for s in states),
        'bounded_keyframes': last['keyframes'] <= manifest['limits']['max_keyframes'],
        'same_camera_exposure': max(s['max_image_pose_gap_ns'] for s in states) <= 2,
        'normal_navigation_and_landing': qualification['passed'] and load('flight.json')['landed_and_disarmed'],
        'real_corrected_pose_overlap': len(comparisons) >= 100,
    }
    if last['verified_loops'] == 0:
        checks['no_correction_without_verified_loop'] = bool(comparisons and max(comparisons) < 1e-9)
    checks = {name: bool(value) for name, value in checks.items()}
    resources = observation['process_resources']
    cpu = [(b['cpu_ticks']-a['cpu_ticks'])/observation['cpu_ticks_per_second']/(b['wall_s']-a['wall_s'])*100
           for a, b in zip(resources, resources[1:]) if b['wall_s']-a['wall_s'] > .5]
    return {'scope': __doc__, 'run_id': run.name, 'passed': all(checks.values()), 'checks': checks,
            'epoch': manifest['epoch'], 'namespace': namespace, 'map_frame': frame,
            'keyframes': len(poses), 'loop_candidates': last['loop_candidates'],
            'verified_loops': last['verified_loops'], 'optimizations': last['optimizations'],
            'keyframe_xyz_span_m': np.ptp(xyz, axis=0).tolist(),
            'last_keyframe_feature_count': len(observation['last_cloud']['xyz']),
            'maximum_keyframe_feature_count': max(p['count'] for p in clouds),
            'last_graph_marker_count': len(observation['last_markers']),
            'corrected_pose_raw_overlap': len(comparisons),
            'max_corrected_vs_raw_position_difference_m': max(comparisons, default=None),
            'last_status': last,
            'resources_on_x86_server': {'peak_rss_mib': max(p['hwm_kib'] for p in resources)/1024,
                                      'mean_cpu_one_core_percent': float(np.mean(cpu)) if cpu else None,
                                      'max_sample_cpu_one_core_percent': max(cpu, default=None)},
            'runtime_contract_sha256': qualification['runtime_contract_sha256'],
            'executable_sha256': manifest['executable_sha256'],
            'input_sha256': {p: hashlib.sha256((run/p).read_bytes()).hexdigest() for p in [
                'loop-observation.json', 'loop-observer-manifest.json', 'qualification.json', 'flight.json',
                'alignment-observation.json']},
            'limitations': ['Transport/graph observation only; loop edge correctness and drift improvement are unqualified.',
                            'Current keyframe cloud is not a persistent globally optimized landmark map.',
                            'No map-to-odom transform, flight feedback, saved-map loading or Nano benchmark.',
                            'One forward route does not establish successful revisit detection.']}


def plot(run):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    data = json.loads((run/'loop-observation.json').read_text())
    path = np.array([p['xyz'] for p in data['last_path']['poses']])
    cloud = np.array(data['last_cloud']['xyz'])
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.scatter(cloud[:, 0], cloud[:, 1], s=12, c='#b28400', alpha=.6, label='Latest keyframe sparse features (not whole map)')
    for marker in data['last_markers']:
        p = np.array(marker['xyz'])
        if len(p):
            ax.plot(p[:, 0], p[:, 1], c='red' if marker['type'] == 4 else '#2677b8', alpha=.3, lw=.7)
    ax.plot(path[:, 0], path[:, 1], '.-', c='#145da0', ms=4, label=f'Actual pose graph: {len(path)} keyframes')
    ax.scatter(path[[0, -1], 0], path[[0, -1], 1], c=['green', 'red'], s=60, zorder=5)
    ax.set(xlabel='Loop-map X (m)', ylabel='Loop-map Y (m)',
           title='Observed VINS pose graph and current sparse features — XY projection')
    ax.set_aspect('equal', adjustable='datalim')
    ax.grid(alpha=.2); ax.legend(); fig.tight_layout()
    fig.savefig(run/'loop-graph.png', dpi=160); plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--plot', action='store_true')
    args = parser.parse_args()
    report = evaluate(args.run)
    (args.run/'loop-qualification.json').write_text(json.dumps(report, indent=2)+'\n')
    if args.plot:
        plot(args.run)
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report['passed'] else 1)
