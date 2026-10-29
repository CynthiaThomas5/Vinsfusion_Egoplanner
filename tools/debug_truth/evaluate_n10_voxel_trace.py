#!/usr/bin/env python3
"""Offline audit of N10 per-fusion voxel updates against raw map snapshots.

This diagnostic never publishes control or changes acceptance/admission. Missing
source traces are reported as INSUFFICIENT rather than treated as a flight gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text())


def resolve_root_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def iter_jsonl(path: Path):
    with path.open(encoding='utf-8') as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                yield line_number, json.loads(line), None
            except json.JSONDecodeError as exc:
                yield line_number, None, f'{type(exc).__name__}: {exc}'


def snapshot_files(observation: dict, label: str):
    row = observation.get('map_snapshots', {}).get(label)
    if not isinstance(row, dict) or row.get('accepted') is not True:
        return None, None
    metadata_path = resolve_root_path(row.get('metadata_file', ''))
    if not metadata_path.is_file():
        return None, None
    metadata = read_json(metadata_path)
    archive = metadata_path.parent / metadata.get('archive', {}).get('file', '')
    if not archive.is_file():
        return metadata, None
    return metadata, archive


def status_for_source(covered, trace_complete):
    if covered is False:
        return 'INSUFFICIENT'
    if trace_complete is False:
        return 'INSUFFICIENT'
    if covered is True and trace_complete is True:
        return 'PASS'
    return 'INSUFFICIENT'


def decode_voxel_update(row: dict, update) -> dict:
    """Normalize verbose v1 objects and compact v2 arrays to one offline shape."""
    schema = row.get('schema')
    if schema == 'n10-voxel-update-trace/v1':
        return {
            'index': update['index'],
            'hit_votes': update['hit_votes'],
            'miss_votes': update['miss_votes'],
            'selected_vote': update['selected_vote'],
            'pre_class': update['pre_class'],
            'post_class': update['post_class'],
        }
    if schema == 'n10-voxel-update-trace/v2':
        expected_fields = [
            'ix', 'iy', 'iz', 'hit_votes', 'miss_votes', 'pre_log_odds',
            'post_log_odds', 'pre_class_code', 'post_class_code',
        ]
        if row.get('update_fields') != expected_fields:
            raise ValueError('unsupported compact voxel update field order')
        if not isinstance(update, list) or len(update) != len(expected_fields):
            raise ValueError('compact voxel update must contain nine values')
        class_names = {0: 'unknown', 1: 'free', 2: 'occupied'}
        hit_votes, miss_votes = int(update[3]), int(update[4])
        pre_code, post_code = int(update[7]), int(update[8])
        if pre_code not in class_names or post_code not in class_names:
            raise ValueError('compact voxel update has an unknown occupancy class code')
        return {
            'index': update[:3],
            'hit_votes': hit_votes,
            'miss_votes': miss_votes,
            'selected_vote': 'hit' if hit_votes >= miss_votes else 'miss',
            'pre_class': class_names[pre_code],
            'post_class': class_names[post_code],
        }
    raise ValueError(f'unsupported voxel update schema: {schema!r}')


def evaluate(run: Path) -> dict:
    report_path = run / 'n10-live-obstacle-observation.json'
    output_path = run / 'n10-voxel-trace-evaluation.json'
    if not report_path.is_file():
        result = {
            'schema': 'n10-voxel-trace-evaluation/v1',
            'diagnostic_only': True,
            'status': 'INSUFFICIENT',
            'reason': 'live-obstacle observation report is missing',
            'run_dir': str(run),
        }
        output_path.write_text(json.dumps(result, indent=2) + '\n')
        return result

    observation = read_json(report_path)
    trace_streams = observation.get('mapping_trace_streams', {})
    trace_errors = observation.get('mapping_trace_parse_errors', [])
    before, before_archive = snapshot_files(observation, 'before_injection')
    after, after_archive = snapshot_files(observation, 'after_injection')
    freeze_path = run / 'n10-tool-freeze-used.json'
    freeze = read_json(freeze_path) if freeze_path.is_file() else {}
    planner_path = resolve_root_path(freeze.get('planner_config_path', '')) if freeze else None
    planner = read_json(planner_path) if planner_path and planner_path.is_file() else {}
    expected_trace = planner.get('n10_voxel_update_trace', {})
    expected_center = expected_trace.get('roi_center_odom_m')
    expected_half = expected_trace.get('roi_half_extents_m')

    base = {
        'schema': 'n10-voxel-trace-evaluation/v1',
        'diagnostic_only': True,
        'runtime_control_effect': False,
        'acceptance_or_admission_effect': False,
        'run_id': observation.get('run_id'),
        'run_dir': str(run),
        'observation_report_sha256': sha256(report_path),
        'protocol_json_sha256': observation.get('protocol_json_sha256'),
        'trace_parse_error_count': len(trace_errors),
        'before_snapshot_present': before is not None and before_archive is not None,
        'after_snapshot_present': after is not None and after_archive is not None,
        'expected_roi_center_odom_m': expected_center,
        'expected_roi_half_extents_m': expected_half,
    }

    stream_rows = {}
    stream_files = {}
    parse_errors = []
    for kind in ('depth_fusion', 'voxel_update'):
        meta = trace_streams.get(kind, {})
        path_value = meta.get('file') if isinstance(meta, dict) else None
        path = resolve_root_path(path_value) if path_value else None
        if not path or not path.is_file():
            stream_rows[kind] = []
            stream_files[kind] = {
                'path': path_value,
                'present': False,
                'declared_row_count': meta.get('row_count') if isinstance(meta, dict) else None,
                'observed_row_count': 0,
                'sha256': None,
            }
            continue
        rows = []
        local_parse_errors = []
        for line_number, row, error in iter_jsonl(path):
            if error:
                local_parse_errors.append({'line': line_number, 'error': error})
            else:
                rows.append(row)
        stream_rows[kind] = rows
        stream_files[kind] = {
            'path': path_value,
            'present': True,
            'declared_row_count': meta.get('row_count'),
            'observed_row_count': len(rows),
            'bytes': path.stat().st_size,
            'sha256': sha256(path),
            'parse_error_count': len(local_parse_errors),
        }
        parse_errors.extend({'kind': kind, **item} for item in local_parse_errors)

    identity_ok = bool(before and after and before_archive and after_archive
                       and before.get('epoch') == after.get('epoch')
                       and before.get('map_id') == after.get('map_id')
                       and before.get('frame_id') == after.get('frame_id')
                       and before.get('data_order') == 'x_major_y_mid_z_fastest'
                       and after.get('data_order') == 'x_major_y_mid_z_fastest')
    after_source_ns = (int(after.get('last_fused_depth_source_stamp_ns'))
                       if after and after.get('last_fused_depth_source_stamp_ns') is not None
                       else None)
    before_source_ns = (int(before.get('last_fused_depth_source_stamp_ns'))
                        if before and before.get('last_fused_depth_source_stamp_ns') is not None
                        else None)
    watermark = after.get('snapshot_roi_cloud_watermark') if after else None
    coverage = after.get('snapshot_source_coverage') if after else None
    coverage_status = (coverage or {}).get('status')
    source_covered = bool(coverage and coverage.get('covered') is True
                          and watermark is not None and after_source_ns is not None)

    map_epoch = str(after.get('epoch')) if after else None
    map_id = str(after.get('map_id')) if after else None
    fusion_rows = [row for row in stream_rows['depth_fusion']
                   if row.get('phase') == 'fused'
                   and str(row.get('epoch')) == map_epoch
                   and str(row.get('map_id')) == map_id]
    voxel_rows = [row for row in stream_rows['voxel_update']
                  if str(row.get('epoch')) == map_epoch
                  and str(row.get('map_id')) == map_id]
    if before_source_ns is not None and after_source_ns is not None:
        fusion_rows = [row for row in fusion_rows
                       if before_source_ns <= int(row.get('pose_source_stamp_ns', -1))
                       <= after_source_ns]
        voxel_rows = [row for row in voxel_rows
                      if before_source_ns <= int(row.get('pose_source_stamp_ns', -1))
                      <= after_source_ns]

    def event_key(row):
        return (str(row.get('epoch')), str(row.get('map_id')),
                int(row.get('fused_count', -1)))

    fusion_keys = [event_key(row) for row in fusion_rows]
    voxel_keys = [event_key(row) for row in voxel_rows]
    fusion_key_counts = {}
    voxel_key_counts = {}
    for key in fusion_keys:
        fusion_key_counts[key] = fusion_key_counts.get(key, 0) + 1
    for key in voxel_keys:
        voxel_key_counts[key] = voxel_key_counts.get(key, 0) + 1
    missing_voxel_keys = sorted(set(fusion_key_counts) - set(voxel_key_counts), key=lambda row: row[2])
    extra_voxel_keys = sorted(set(voxel_key_counts) - set(fusion_key_counts), key=lambda row: row[2])
    duplicate_fusion_keys = [list(key) for key, count in fusion_key_counts.items() if count > 1]
    duplicate_voxel_keys = [list(key) for key, count in voxel_key_counts.items() if count > 1]
    correlation_complete = bool(
        identity_ok and fusion_rows and voxel_rows and not missing_voxel_keys
        and not extra_voxel_keys and not duplicate_fusion_keys
        and not duplicate_voxel_keys and not parse_errors and not trace_errors)

    all_roi_updates = []
    malformed_updates = []
    roi_identity_mismatches = []
    for row in voxel_rows:
        if (expected_center is not None and row.get('roi_center_m') != expected_center):
            # C++ serializes doubles with 17 significant digits; compare numerically below.
            try:
                if not np.allclose(row.get('roi_center_m'), expected_center, atol=1e-12, rtol=0):
                    roi_identity_mismatches.append({'fused_count': row.get('fused_count'),
                                                    'field': 'roi_center_m'})
            except (TypeError, ValueError):
                roi_identity_mismatches.append({'fused_count': row.get('fused_count'),
                                                'field': 'roi_center_m'})
        if (expected_half is not None and row.get('roi_half_extents_m') != expected_half):
            try:
                if not np.allclose(row.get('roi_half_extents_m'), expected_half, atol=1e-12, rtol=0):
                    roi_identity_mismatches.append({'fused_count': row.get('fused_count'),
                                                    'field': 'roi_half_extents_m'})
            except (TypeError, ValueError):
                roi_identity_mismatches.append({'fused_count': row.get('fused_count'),
                                                'field': 'roi_half_extents_m'})
        updates = row.get('updates')
        if not isinstance(updates, list) or int(row.get('voxel_count', -1)) != len(updates):
            malformed_updates.append({'fused_count': row.get('fused_count'),
                                      'declared': row.get('voxel_count'),
                                      'observed': len(updates) if isinstance(updates, list) else None})
            continue
        all_roi_updates.extend((row, update) for update in updates)

    index_final_trace = {}
    vote_counts = {'hit': 0, 'miss': 0}
    transition_counts = {}
    touched_voxels = set()
    for row, update in all_roi_updates:
        try:
            normalized = decode_voxel_update(row, update)
            index = tuple(int(value) for value in normalized['index'])
            fused_count = int(row['fused_count'])
            selected = str(normalized['selected_vote'])
            pre_class = str(normalized['pre_class'])
            post_class = str(normalized['post_class'])
        except (KeyError, TypeError, ValueError):
            malformed_updates.append({'fused_count': row.get('fused_count'), 'reason': 'invalid voxel fields'})
            continue
        if selected in vote_counts:
            vote_counts[selected] += 1
        transition = pre_class + '->' + post_class
        transition_counts[transition] = transition_counts.get(transition, 0) + 1
        touched_voxels.add(index)
        prior = index_final_trace.get(index)
        if prior is None or fused_count > prior[0]:
            index_final_trace[index] = (fused_count, post_class)

    snapshot_comparison = {
        'status': 'INSUFFICIENT',
        'compared_voxel_count': 0,
        'class_match_count': 0,
        'class_mismatch_count': 0,
        'mismatch_examples': [],
    }
    if identity_ok and after_source_ns is not None and after_archive is not None:
        with np.load(after_archive, allow_pickle=False) as snapshot:
            occupancy = snapshot['occupancy']
        matches, mismatches = [], []
        for index, (fused_count, trace_class) in index_final_trace.items():
            if any(part < 0 or part >= occupancy.shape[axis] for axis, part in enumerate(index)):
                mismatches.append({'index': list(index), 'reason': 'index outside snapshot'})
                continue
            code = int(occupancy[index])
            map_class = {-1: 'unknown', 0: 'free', 100: 'occupied'}.get(code)
            if map_class == trace_class:
                matches.append(index)
            else:
                mismatches.append({'index': list(index), 'fused_count': fused_count,
                                   'trace_post_class': trace_class,
                                   'snapshot_class': map_class, 'snapshot_code': code})
        if correlation_complete and not roi_identity_mismatches and not malformed_updates:
            snapshot_comparison['status'] = 'PASS' if not mismatches else 'FAIL'
        snapshot_comparison.update({
            'compared_voxel_count': len(matches) + len(mismatches),
            'class_match_count': len(matches),
            'class_mismatch_count': len(mismatches),
            'mismatch_examples': mismatches[:40],
        })

    trace_complete_status = (True if correlation_complete and not roi_identity_mismatches
                             and not malformed_updates else False if stream_rows['voxel_update'] else None)
    source_link_status = status_for_source(source_covered, trace_complete_status)
    result = {
        **base,
        'status': 'INSUFFICIENT',
        'snapshot_identity_matches': identity_ok,
        'map_identity': {'epoch': map_epoch, 'map_id': map_id,
                         'before_frame_id': before.get('frame_id') if before else None,
                         'after_frame_id': after.get('frame_id') if after else None},
        'source_interval': {'before_snapshot_source_stamp_ns': before_source_ns,
                            'after_snapshot_source_stamp_ns': after_source_ns,
                            'raw_occupancy_cloud_watermark': watermark,
                            'snapshot_source_coverage': coverage,
                            'coverage_status': coverage_status,
                            'source_covered': source_covered},
        'trace_streams': stream_files,
        'trace_interval_fusion_row_count': len(fusion_rows),
        'trace_interval_voxel_frame_count': len(voxel_rows),
        'trace_interval_roi_update_count': len(all_roi_updates),
        'trace_interval_unique_voxel_count': len(touched_voxels),
        'depth_fusion_to_voxel_trace': {
            'status': 'PASS' if correlation_complete else 'INSUFFICIENT',
            'matched_fused_event_count': len(set(fusion_keys) & set(voxel_keys)),
            'missing_voxel_fused_event_count': len(missing_voxel_keys),
            'extra_voxel_fused_event_count': len(extra_voxel_keys),
            'duplicate_fusion_event_count': len(duplicate_fusion_keys),
            'duplicate_voxel_event_count': len(duplicate_voxel_keys),
            'missing_fused_counts_examples': [key[2] for key in missing_voxel_keys[:40]],
            'roi_identity_mismatch_count': len(roi_identity_mismatches),
            'malformed_update_frame_count': len(malformed_updates),
            'trace_parse_error_count': len(parse_errors) + len(trace_errors),
        },
        'per_voxel_vote_summary': {
            'hit_selected_updates': vote_counts['hit'],
            'miss_selected_updates': vote_counts['miss'],
            'pre_to_post_class_transitions': transition_counts,
        },
        'last_trace_class_vs_after_snapshot': snapshot_comparison,
        'source_link_status': source_link_status,
        'offline_evaluator_sha256': sha256(Path(__file__)),
        'parse_errors': parse_errors[:40],
        'limitations': [
            'The trace is emitted before later clear/inflate map post-processing; class mismatches expose that downstream difference.',
            'Cloud points and mapping traces are observation-only and do not alter navigation or acceptance decisions.',
            'A PASS here establishes only source/event consistency and trace-to-snapshot class agreement for recorded ROI cells; it is not GOAL C or collision qualification.',
        ],
    }
    if not identity_ok or not stream_rows['voxel_update'] or not stream_rows['depth_fusion']:
        result['reason'] = 'same-identity snapshots or mapping trace streams are missing'
    elif not source_covered:
        result['reason'] = 'after-snapshot source watermark does not cover a positive ROI raw occupancy cloud'
    elif not correlation_complete:
        result['reason'] = 'depth-fusion and voxel-update event streams are incomplete or inconsistent'
    elif roi_identity_mismatches or malformed_updates:
        result['reason'] = 'trace ROI identity or per-frame voxel update payload is inconsistent'
    elif snapshot_comparison['status'] == 'FAIL':
        result['reason'] = 'traced last raw voxel classes differ from the same-identity after snapshot'
    elif snapshot_comparison['status'] == 'PASS':
        result['status'] = 'PASS'
        result['reason'] = 'source watermark is covered and ROI voxel trace matches the raw snapshot for touched cells'
    output_path.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir', type=Path)
    args = parser.parse_args()
    run = args.run_dir if args.run_dir.is_absolute() else ROOT / args.run_dir
    result = evaluate(run.resolve())
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
