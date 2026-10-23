#!/usr/bin/env python3
"""Validate read-only prior telemetry; no calibration or flight qualification."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

from evaluate_residual_transition import decompose


def validate(metric):
    grouped = decompose(metric)
    details = metric['cost_components']['prior_details']
    tracks = details['window_tracks']
    if len({t[0] for t in tracks}) != len(tracks):
        raise ValueError('duplicate window feature IDs')
    if any(len(t) != 4 or min(t) < 0 or t[2] < 1 or t[3] > t[2] for t in tracks):
        raise ValueError('invalid window track span')
    # Fixed stereo configuration: one 2D left factor after the anchor and a
    # 2D stereo factor for every available right observation, including anchor.
    predicted_visual = sum(2 * (n - 1 + stereo) for _, _, n, stereo in tracks if n >= 4)
    actual_visual = grouped['groups']['visual']['residual_components']
    if predicted_visual > actual_visual or (not details['window_tracks_truncated'] and predicted_visual != actual_visual):
        raise ValueError('window tracks do not reproduce visual residual count')
    if details['next_marginalization_branch'] not in ('oldest', 'second_newest'):
        raise ValueError('invalid marginalization branch')
    if details['available']:
        if not details['evaluation_ok'] or not details['spectrum_ok']:
            raise ValueError('prior evaluation/spectrum failed')
        names = ['r0_squared_norm', 'current_squared_norm', 'Jdx_squared_norm',
                 'twice_r0_dot_Jdx', 'information_min_positive', 'information_max']
        if any(not math.isfinite(details[n]) for n in names):
            raise ValueError('nonfinite prior diagnostic')
        actual = details['current_squared_norm']
        reconstructed = sum(details[n] for n in
                            ['r0_squared_norm', 'Jdx_squared_norm', 'twice_r0_dot_Jdx'])
        cost = grouped['groups']['marginalization']['cost']
        if not math.isclose(actual, reconstructed, rel_tol=1e-8, abs_tol=1e-8):
            raise ValueError('r0+Jdx identity failed')
        if not math.isclose(actual, 2 * cost, rel_tol=1e-8, abs_tol=1e-8):
            raise ValueError('prior cost does not match residual norm')
        if not 0 < details['information_rank'] <= details['retained_dimension']:
            raise ValueError('invalid prior rank')
    return grouped


def evaluate(path):
    metrics = [json.loads(line) for line in path.open()]
    solves = [m for m in metrics if m.get('solve_current')]
    if any(b['stamp_ns'] <= a['stamp_ns'] for a, b in zip(solves, solves[1:])):
        raise ValueError('nonmonotonic solve stamps; no session stitching')
    selected = [m for m in solves if m.get('cost_components') is not None]
    if not selected:
        raise ValueError('no prior diagnostics')
    for metric in selected:
        validate(metric)
    prior = [m for m in selected if m['cost_components']['prior_details']['available']]
    maximum = max(selected, key=lambda m: 2 * m['final_cost'] / m['residual_components'])
    timings = [m['cost_components']['evaluation_seconds'] for m in selected]
    return {'scope': __doc__, 'input_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'solve_frames': len(solves), 'diagnostic_frames': len(selected),
            'prior_frames': len(prior), 'all_recorded_identities_valid': True,
            'prior_norm_identity_checks': len(prior), 'group_total_checks': len(selected),
            'complete_visual_count_checks': sum(not m['cost_components']['prior_details']['window_tracks_truncated']
                                                for m in selected),
            'truncated_visual_lower_bound_checks': sum(m['cost_components']['prior_details']['window_tracks_truncated']
                                                       for m in selected),
            'branch_counts': dict(Counter(m['cost_components']['prior_details']['next_marginalization_branch']
                                         for m in selected)),
            'evaluation_s': {'mean': sum(timings)/len(timings), 'maximum': max(timings)},
            'maximum_q_frame': maximum,
            'crossing_frames': sum(2*m['final_cost']/m['residual_components'] > 1 for m in selected),
            'limitations': ['Window span is not total tracker lifetime.',
                            'Truncated window lists only validate a lower bound, not full visual-count reconstruction.',
                            'Spectrum uses mixed state units and absolute rank epsilon; not a calibrated health criterion.',
                            'Diagnostic identities do not prove correct estimates or harmless marginalization.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('telemetry', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = evaluate(args.telemetry)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'maximum_q_frame'}, indent=2))
