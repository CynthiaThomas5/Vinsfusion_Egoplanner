#!/usr/bin/env python3
"""Offline loop-edge geometry and correction errors; no ROS or control outputs."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
sys.path.insert(0, str(ROOT/'tools/debug_truth'))
sys.path.insert(0, str(ROOT/'src/own/uav_sim'))
from evaluate_odometry import pose_arrays
from evaluate_vins_motion import rotation
from evaluate_vio_quality_alignment import _interpolate_position, _interpolate_quaternion
from uav_sim.geometry import px4_sensor_mount


def relative_error(old_p, old_r, current_p, current_r, measured_t, measured_q):
    translation = old_r.T @ (current_p-old_p)
    relative_r = old_r.T @ current_r
    delta_r = rotation(measured_q).T @ relative_r
    angle = np.degrees(np.arccos(np.clip((np.trace(delta_r)-1)/2, -1, 1)))
    return float(np.linalg.norm(translation-measured_t)), float(angle)


def stats(values):
    a = np.asarray(values)
    return {'samples': len(a), 'rmse_m': float(np.sqrt(np.mean(a*a))),
            'maximum_m': float(a.max()), 'last_m': float(a[-1])} if len(a) else None


def evaluate(run):
    load = lambda n: json.loads((run/n).read_text())
    observed = load('loop-observation.json')
    raw_report = load('odometry-evaluation.json')
    epoch = raw_report['epoch']
    if observed['epoch'] != epoch:
        raise ValueError('Epoch mismatch; cannot stitch sessions')
    tt, tp, tq = pose_arrays(load('debug-truth-evaluation.json')['samples'], 'stamp_ns')
    mount = px4_sensor_mount(ROOT/'simulation/models/x500_d435i/model.sdf')
    lever = np.asarray(mount['translation_frd_m'])*[1,-1,-1]
    def truth(stamp):
        p, gap = _interpolate_position(tt, tp, stamp)
        if gap > 40_000_000:
            raise ValueError('Truth support exceeds 40ms')
        r = rotation(_interpolate_quaternion(tt, tq, stamp))
        return p+r@lever, r
    ar = np.asarray(raw_report['alignment']['rotation'])
    at = np.asarray(raw_report['alignment']['translation_m'])
    graph = observed['graph_revisions'][-1]['graph']
    by_index = {p['index']: p for p in graph}
    edges = []
    for cur in graph:
        if cur['loop_index'] < 0:
            continue
        old = by_index[cur['loop_index']]
        op, ori = truth(old['source_ns']); cp, cri = truth(cur['source_ns'])
        te, re = relative_error(op, ori, cp, cri, cur['loop_relative_t'], cur['loop_relative_q_xyzw'])
        edges.append({'from_index': old['index'], 'to_index': cur['index'],
                      'old_source_ns': old['source_ns'], 'current_source_ns': cur['source_ns'],
                      'time_separation_sim_s': (cur['source_ns']-old['source_ns'])/1e9,
                      'actual_pose_separation_m': float(np.linalg.norm(cp-op)),
                      'relative_translation_error_m': te, 'relative_rotation_error_deg': re})
    raw = {p['source_ns']: p for p in load('alignment-observation.json')['samples'] if p['kind']=='raw_odom'}
    pairs = []
    start = raw_report['interval']['start_source_ns']; end = raw_report['interval']['end_source_ns']
    for corrected in observed['odometry']:
        stamp = corrected['source_ns']
        if not start <= stamp <= end or stamp not in raw:
            continue
        if corrected['frame'] != 'loop_'+epoch+'_map':
            raise ValueError('Unexpected corrected pose frame')
        actual, _ = truth(stamp)
        rp = np.asarray(raw[stamp]['xyz']); cp = np.asarray(corrected['xyz'])
        pairs.append({'source_ns': stamp, 'elapsed_sim_s': (stamp-start)/1e9,
                      'raw_error_m': float(np.linalg.norm(ar@rp+at-actual)),
                      'corrected_error_m': float(np.linalg.norm(ar@cp+at-actual)),
                      'correction_m': float(np.linalg.norm(cp-rp))})
    changed = [p for p in pairs if p['correction_m'] > 1e-6]
    after = [p for p in pairs if changed and p['source_ns'] >= changed[0]['source_ns']]
    status = observed['status'][-1]
    # Fixed diagnostic bounds, not PnP thresholds or a general localization guarantee.
    geometry_ok = bool(edges) and all(e['relative_translation_error_m'] <= .25
                                      and e['relative_rotation_error_deg'] <= 5 for e in edges)
    qualification = load('qualification.json') if (run/'qualification.json').exists() else {'passed': False}
    checks = {'actual_verified_loop': status['verified_loops'] > 0 and len(edges)==status['verified_loops'],
              'actual_graph_optimization': status['optimizations'] > 0,
              'independent_loop_geometry': geometry_ok,
              'nonzero_observed_pose_correction': bool(changed),
              'native_mission_and_landing': qualification['passed'] and load('flight.json').get('landed_and_disarmed',False)}
    report = {'scope': __doc__, 'run_id': run.name, 'epoch': epoch, 'checks': checks,
              'passed': all(checks.values()), 'navigation_qualification_available': (run/'qualification.json').exists(), 'diagnostic_geometry_limits': {'translation_m': .25, 'rotation_deg': 5},
              'verified_loops': status['verified_loops'], 'optimizations': status['optimizations'],
              'edges': edges, 'single_raw_preflight_alignment': raw_report['alignment'],
              'paired_raw_error_m': stats([p['raw_error_m'] for p in pairs]),
              'paired_corrected_error_m': stats([p['corrected_error_m'] for p in pairs]),
              'after_first_correction_raw_error_m': stats([p['raw_error_m'] for p in after]),
              'after_first_correction_corrected_error_m': stats([p['corrected_error_m'] for p in after]),
              'maximum_observed_correction_m': max((p['correction_m'] for p in pairs), default=None),
              'limitations': ['A successful loop need not improve already small odometry error.',
                              'One room/run is not robustness, map reuse or real-flight qualification.',
                              'Fixed initial alignment; no trajectory fit, scale fit or post-loop realignment.']}
    return report, pairs


def plot(run, pairs):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    t = [p['elapsed_sim_s'] for p in pairs]
    for key, label in [('raw_error_m','Raw VINS'), ('corrected_error_m','Loop corrected')]:
        axes[0].plot(t, [p[key] for p in pairs], label=label)
    axes[0].set_ylabel('Position error (m)'); axes[0].legend()
    axes[1].plot(t, [p['correction_m'] for p in pairs]); axes[1].set(xlabel='Flight simulation time (s)', ylabel='Correction (m)')
    for ax in axes: ax.grid(alpha=.25)
    fig.tight_layout(); fig.savefig(run/'loop-correction.png', dpi=160); plt.close(fig)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--plot',action='store_true');args=p.parse_args()
    report, pairs=evaluate(args.run)
    (args.run/'loop-revisit-evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
    (args.run/'loop-error-pairs.json').write_text(json.dumps(pairs)+'\n')
    if args.plot: plot(args.run,pairs)
    print(json.dumps(report,indent=2));sys.exit(0 if report['passed'] else 1)
