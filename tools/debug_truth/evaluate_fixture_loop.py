#!/usr/bin/env python3
"""Independently verify real loop edges in an unarmed fixture session."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

from evaluate_loop_revisit import relative_error
from evaluate_odometry import pose_arrays, rotation, _interpolate_position, _interpolate_quaternion

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src/own/uav_sim'))
from uav_sim.geometry import px4_sensor_mount


def geometry(graph, truth, lever):
    tt, tp, tq = pose_arrays(truth, 'stamp_ns')
    indices = [p['index'] for p in graph]
    if len(set(indices)) != len(indices):
        raise ValueError('duplicate graph indices')
    if any(b['source_ns'] <= a['source_ns'] for a, b in zip(graph, graph[1:])):
        raise ValueError('nonmonotonic graph source times')
    by_index = {p['index']: p for p in graph}

    def pose(stamp):
        point, gap = _interpolate_position(tt, tp, stamp)
        if gap > 40_000_000:
            raise ValueError('truth interpolation gap exceeds 40ms')
        attitude = rotation(_interpolate_quaternion(tt, tq, stamp))
        return point + attitude @ lever, attitude

    edges = []
    for current in graph:
        old_index = current['loop_index']
        if old_index < 0:
            continue
        if old_index not in by_index or current['index'] - old_index < 50:
            raise ValueError('missing or temporally adjacent loop endpoint')
        old = by_index[old_index]
        op, ori = pose(old['source_ns'])
        cp, cri = pose(current['source_ns'])
        te, re = relative_error(op, ori, cp, cri, current['loop_relative_t'],
                                current['loop_relative_q_xyzw'])
        if not np.isfinite([te, re]).all():
            raise ValueError('nonfinite loop geometry')
        edges.append({'old_index': old_index, 'current_index': current['index'],
                      'old_source_ns': old['source_ns'], 'current_source_ns': current['source_ns'],
                      'separation_sim_s': (current['source_ns'] - old['source_ns'])/1e9,
                      'actual_imu_separation_m': float(np.linalg.norm(cp-op)),
                      'translation_error_m': te, 'rotation_error_deg': re})
    return edges


def evaluate(run):
    load = lambda name: json.loads((run/name).read_text())
    fixture, manifest, observation = [load(name) for name in
        ['fixture-result.json', 'loop-observer-manifest.json', 'loop-observation.json']]
    if fixture['epoch'] != manifest['epoch'] or fixture['epoch'] != observation['epoch']:
        raise ValueError('epoch mismatch; no session stitching')
    if not observation['status'] or not observation['graph_revisions']:
        raise ValueError('missing actual backend status/graph')
    status = observation['status'][-1]
    graph = observation['graph_revisions'][-1]['graph']
    truth = [json.loads(line) for line in (run/'fixture-truth.jsonl').open()]
    mount = px4_sensor_mount(ROOT/'simulation/models/x500_d435i/model.sdf')
    lever = np.asarray(mount['translation_frd_m'])*[1,-1,-1]
    edges = geometry(graph, truth, lever)
    namespace = manifest['namespace']
    publishers = [name for name, _ in observation['observer_node_publishers']]
    subscribers = [name for name, _ in observation['observer_node_subscriptions']]
    # Independent diagnostic bounds are inherited from #059, not PnP thresholds.
    limits = {'translation_m': .25, 'rotation_deg': 5}
    exit_file = run/'loop-backend-exit-code'
    exit_code = int(exit_file.read_text()) if exit_file.exists() else None
    finite_graph = bool(graph) and all(np.isfinite(p[name]).all() for p in graph
                                     for name in ['xyz','vio_xyz','q_xyzw','vio_q_xyzw'])
    pose_update = max((float(np.linalg.norm(np.asarray(p['xyz'])-p['vio_xyz'])) for p in graph), default=0)
    checks = {'actual_candidate': status['loop_candidates'] > 0,
              'actual_verified_loop': status['verified_loops'] > 0 and len(edges) == status['verified_loops'],
              'actual_graph_optimization': status['optimizations'] > 0,
              'finite_graph_solution': finite_graph,
              'observed_graph_pose_update': pose_update > 1e-6,
              'independent_edge_geometry': bool(edges) and all(e['translation_error_m'] <= limits['translation_m']
                                                        and e['rotation_error_deg'] <= limits['rotation_deg'] for e in edges),
              'normal_backend_exit': exit_code == 0,
              'consistent_output_frame': bool(observation['odometry']) and all(p['frame'] == manifest['map_frame'] for p in observation['odometry']),
              'no_control_or_tf_outputs': bool(publishers) and all(p.startswith(namespace+'/')
                                              or p in ['/rosout', '/parameter_events'] for p in publishers),
              'no_truth_input_to_backend': not any('truth' in p for p in subscribers),
              'raw_session_inputs': all(manifest['session']['namespace']+'/'+name in subscribers
                                       for name in ['odometry','keyframe_pose','keyframe_point','extrinsic']),
              'same_camera_exposure': status['max_image_pose_gap_ns'] <= 2,
              'bounded_queues': all(max(s['image_buffer'],s['pose_buffer'],s['point_buffer']) <= manifest['limits']['queue_limit']
                                   for s in observation['status'])}
    return {'scope': __doc__, 'run_id': run.name, 'epoch': fixture['epoch'],
            'small_goal_2_passed': all(checks.values()), 'checks': checks,
            'keyframes': status['keyframes'], 'loop_candidates': status['loop_candidates'],
            'verified_loops': status['verified_loops'], 'optimizations': status['optimizations'],
            'edges': edges, 'diagnostic_geometry_limits': limits,
            'maximum_graph_position_update_m': pose_update,
            'backend_exit_code': exit_code,
            'fixture_outcome': fixture['outcome'], 'fixture_error': fixture['error'],
            'limitations': ['A geometrically valid optimized loop does not prove lower odometry error.',
                            'No corrected state is routed to navigation or PX4.',
                            'One repeated local scene is not general loop-detection robustness.'],
            'input_sha256': {name: hashlib.sha256((run/name).read_bytes()).hexdigest() for name in
                ['fixture-result.json','loop-observer-manifest.json','loop-observation.json',
                 'fixture-truth.jsonl'] + (['loop-backend-exit-code'] if exit_file.exists() else [])}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    report = evaluate(args.run)
    (args.run/'real-loop-evaluation.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))
