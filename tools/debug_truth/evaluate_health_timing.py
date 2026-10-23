#!/usr/bin/env python3
"""Offline correlation of localization health events with telemetry and truth."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

from evaluate_fixture_odometry import compare


def normalized_cost(metrics):
    if not isinstance(metrics, dict):
        return None
    cost = metrics.get('final_cost')
    components = metrics.get('residual_components')
    if (not isinstance(cost, (int, float)) or not math.isfinite(cost) or cost < 0
            or not isinstance(components, (int, float)) or components <= 0):
        return None
    return math.sqrt(2.0 * cost / components)


def associate_telemetry(status_event, telemetry_events):
    """Return the telemetry sample most likely to have supplied this status cost."""
    latest = status_event.get('latest_telemetry_at_callback')
    if isinstance(latest, dict):
        source_ns = latest.get('source_stamp_ns')
        matching = [event for event in telemetry_events
                    if event.get('source_stamp_ns') == source_ns]
        if matching:
            receive_ns = latest.get('receive_monotonic_ns')
            return min(matching, key=lambda event: abs(
                event.get('receive_monotonic_ns', 0) - (receive_ns or 0))), 'status_callback_context'

    status_receive_ns = status_event.get('receive_monotonic_ns')
    if isinstance(status_receive_ns, int):
        preceding = [event for event in telemetry_events
                     if isinstance(event.get('receive_monotonic_ns'), int)
                     and event['receive_monotonic_ns'] <= status_receive_ns]
        if preceding:
            return max(preceding, key=lambda event: event['receive_monotonic_ns']), 'last_telemetry_received_before_status'
    return None, 'unmatched'


def latest_input_stamps(telemetry_event):
    """Normalize compact snapshots and prior event logs to one sample/topic."""
    snapshot = telemetry_event.get('latest_input_stamps')
    if snapshot is None:
        snapshot = telemetry_event.get('recent_input_stamps', {})
    if not isinstance(snapshot, dict):
        return {}
    return {
        topic: (samples[-1] if isinstance(samples, list) and samples else samples)
        for topic, samples in snapshot.items()
    }


def _load_jsonl(path):
    with Path(path).open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def _pose_error_at(run, source_stamp_ns):
    odometry = _load_jsonl(run / 'fixture-odometry.jsonl')
    optimized = [row for row in odometry if row.get('kind') == 'optimized']
    truth = _load_jsonl(run / 'fixture-truth.jsonl')
    baseline = json.loads((run / 'fixture-odometry-errors.json').read_text(encoding='utf-8'))
    _, rows = compare(optimized, truth, int(baseline['anchor_ns']), [0.0, 0.0, 0.0])
    exact = [row for row in rows if row['source_ns'] == source_stamp_ns]
    if not exact:
        return None
    row = exact[0]
    return {key: row[key] for key in (
        'source_ns', 'position_error_m', 'yaw_error_deg',
        'dx_m', 'dy_m', 'dz_m')}


def evaluate(run):
    run = Path(run)
    event_path = run / 'vio-stream-events.jsonl'
    summary_path = run / 'vio-stream-summary.json'
    events = _load_jsonl(event_path)
    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    statuses = [event for event in events if event.get('topic') == '/localization/status']
    telemetry = [event for event in events
                 if event.get('topic', '').endswith('/estimator_telemetry')]
    if not statuses or not telemetry:
        raise ValueError('event stream must contain health status and estimator telemetry')

    threshold = json.loads(
        Path(__file__).resolve().parents[2]
        .joinpath('config/components/localization/health.json').read_text(encoding='utf-8')
    )['max_normalized_cost']
    associations = []
    for status in statuses:
        sample, method = associate_telemetry(status, telemetry)
        q = None if sample is None else normalized_cost(sample.get('telemetry'))
        reported = status.get('normalized_cost')
        associations.append({
            'status_receive_monotonic_ns': status.get('receive_monotonic_ns'),
            'status_header_stamp_ns': status.get(
                'status_header_stamp_ns', status.get('clock_stamp_ns_at_receipt')),
            'propagated_source_stamp_ns': status.get(
                'propagated_source_stamp_ns', status.get('source_stamp_ns')),
            'reported_normalized_cost': reported,
            'telemetry_source_stamp_ns': None if sample is None else sample.get('source_stamp_ns'),
            'telemetry_receive_monotonic_ns': None if sample is None else sample.get('receive_monotonic_ns'),
            'telemetry_normalized_cost': q,
            'cost_match': (q is not None and isinstance(reported, (int, float))
                           and abs(q - reported) <= 1e-9),
            'association_method': method,
        })
    max_status = max(statuses, key=lambda event: float(event.get('normalized_cost', 0.0)))
    max_association = min(
        associations,
        key=lambda row: abs((row['status_receive_monotonic_ns'] or 0)
                            - (max_status.get('receive_monotonic_ns') or 0)))
    max_telemetry = next((event for event in telemetry
                          if event.get('source_stamp_ns') == max_association['telemetry_source_stamp_ns']), None)
    if max_telemetry is None:
        raise ValueError('maximum health status has no associated telemetry sample')

    metrics = max_telemetry.get('telemetry', {})
    q_source_ns = max_telemetry.get('source_stamp_ns')
    pose_error = _pose_error_at(run, q_source_ns) if isinstance(q_source_ns, int) else None
    input_snapshot = latest_input_stamps(max_telemetry)
    topics = summary.get('topics', {})
    timing_names = (
        '/sensors/d435i/infra1/image_rect',
        '/sensors/d435i/infra2/image_rect',
        '/sensors/d435i/imu',
        '/localization/status',
        '/localization/optimized_imu_odom',
        '/localization/imu_odom',
    )
    timing = {name: {
        key: topics.get(name, {}).get(key)
        for key in ('count', 'max_source_gap_s', 'source_gap_p95_s',
                    'max_receipt_gap_s', 'receipt_gap_p95_s', 'max_clock_age_s',
                    'last_receipt_age_s')
    } for name in timing_names}
    source_files = (
        'fixture-result.json', 'fixture-stages.json', 'fixture-trace.jsonl',
        'fixture-vins.jsonl', 'fixture-odometry.jsonl', 'fixture-truth.jsonl',
        'fixture-odometry-errors.json', 'vio-stream-summary.json',
        'vio-stream-events.jsonl', 'runtime-contract.json', 'gpu-request.json',
    )
    hashes = {}
    for name in source_files:
        path = run / name
        if path.is_file():
            hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    matches = [row for row in associations if row['cost_match']]
    return {
        'schema_version': 2,
        'scope': 'Read-only correlation; does not prove estimator accuracy or flight safety.',
        'run_id': run.name,
        'epoch': json.loads((run / 'fixture-result.json').read_text(encoding='utf-8')).get('epoch'),
        'event_stream': {
            'event_count': len(events),
            'status_count': len(statuses),
            'telemetry_count': len(telemetry),
            'observer_stop_reason': summary.get('stop_reason'),
            'post_end_observation_s': summary.get('post_end_observation_s'),
            'status_telemetry_cost_matches': len(matches),
            'status_telemetry_cost_match_fraction': len(matches) / len(statuses),
        },
        'health_gate': {
            'configured_max_normalized_cost': threshold,
            'max_reported_normalized_cost': max_status.get('normalized_cost'),
            'status_threshold_crossing_count': sum(
                float(event.get('normalized_cost', 0.0)) > threshold for event in statuses),
            'status_states': sorted({(
                event.get('state'), event.get('valid'), event.get('reason')) for event in statuses}),
            'maximum_cost_association': max_association,
            'maximum_cost_telemetry': {
                key: metrics.get(key) for key in (
                    'stamp_ns', 'input_features', 'stereo_features', 'long_tracks',
                    'final_cost', 'residual_components', 'solve_seconds',
                    'state_finite', 'solve_current', 'solver_usable', 'cost_components')
            },
            'maximum_cost_input_stamps': input_snapshot,
            'same_source_independent_pose_error': pose_error,
        },
        'timing': timing,
        'input_sha256': hashes,
        'limitations': [
            'A q threshold crossing identifies the health guard decision, not the upstream cause of increased VINS residuals.',
            'Status.source_stamp is a propagated-odometry stamp; normalized_cost is computed from estimator telemetry.',
            'Only source-matched telemetry and independent offline truth support the associated measurements.',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = evaluate(args.run)
    output = args.output or (args.run / 'health-timing-analysis.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
