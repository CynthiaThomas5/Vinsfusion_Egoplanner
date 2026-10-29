#!/usr/bin/env python3
"""Offline N11 scene applicability and evidence coverage; never controls flight."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

FROZEN_CONFIG_SHA = '7cf226ee4c471d49fec05f25eede1c9c127cd97fc22f0ae371ba13681d599750'
IDENTITY_KEYS = ('run_id', 'runtime_contract_sha256', 'goal_id', 'epoch', 'map_id')
STATIC_METRICS = ('raw_map_surface_geometry', 'raw_map_classification')

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load(path):
    return json.loads(Path(path).read_text())

def scene_check(path):
    world = ET.parse(path).getroot().find('world')
    if world is None:
        return False, 'world_missing'
    models = world.findall('model')
    names = [m.get('name') for m in models]
    if sorted(names) != ['blank', 'ground_plane']:
        return False, 'empty_room_models_mismatch'
    if world.findall('include') or any(m.findtext('static') not in ('true', '1') for m in models):
        return False, 'unverified_include_or_dynamic_model'
    walls = world.find("model[@name='blank']")
    if len(walls.findall('.//collision')) != 4:
        return False, 'room_wall_geometry_mismatch'
    return True, names

def evaluate(run, frozen_run, config, protocol):
    """Assess applicability without rewriting a frozen result or configuration."""
    run, frozen_run = Path(run), Path(frozen_run)
    issues, failures = [], []
    baseline = load(frozen_run / 'runtime-contract.json')
    current = load(run / 'runtime-contract.json')
    cfg = load(config)
    policy = load(protocol)
    if policy.get('schema') != 'n11-empty-scene-protocol/v1':
        failures.append('protocol_schema_mismatch')
    if policy.get('status') != 'ready_for_formal':
        issues.append('recording_and_evaluation_pipeline_not_released')
    expected_config_sha = policy.get('acceptance_config_sha256', FROZEN_CONFIG_SHA)
    if digest(config) != expected_config_sha or cfg.get('status') != 'frozen':
        failures.append('frozen_acceptance_config_mismatch')
    if baseline.get('sha256') != policy.get('frozen_runtime_contract_sha256'):
        failures.append('frozen_runtime_reference_mismatch')
    if current['files'].get('simulation/worlds/ego.sdf') != policy.get('scene_source_sha256'):
        failures.append('empty_scene_source_hash_mismatch')
    changed = [k for k in set(baseline['files']) | set(current['files'])
               if baseline['files'].get(k) != current['files'].get(k)]
    if policy.get('runtime_match_mode') == 'exact_released_runtime':
        if changed or current.get('sha256') != baseline.get('sha256'):
            failures.append('runtime_differs_from_released_baseline')
    elif changed != ['simulation/worlds/ego.sdf']:
        # Compare sets: file iteration order is not an identity property.
        if set(changed) != {'simulation/worlds/ego.sdf'}:
            failures.append('runtime_changes_exceed_declared_scene')
    scene = run / 'vio_initialization.sdf'
    provenance_path = run / 'world.json'
    provenance = load(provenance_path) if provenance_path.is_file() else {}
    if (provenance.get('project_geometry_sha256') != current['files'].get('simulation/worlds/ego.sdf')
            or not scene.is_file() or provenance.get('output_sha256') != digest(scene)):
        failures.append('active_world_provenance_mismatch')
    if not scene.is_file():
        issues.append('active_world_missing')
        empty = False
    else:
        # Generated world has the aircraft inserted at runtime, not in this SDF.
        empty, reason = scene_check(scene)
        if not empty:
            failures.append(str(reason))
    mutation_path = run / 'n11-launch-record.json'
    mutation = load(mutation_path) if mutation_path.is_file() else {}
    if not mutation_path.is_file():
        issues.append('n11_launch_record_missing')
    if mutation and (mutation.get('scenario') != 'empty_room'
                     or mutation.get('world_mutation_commands') != []
                     or mutation.get('runtime_contract_sha256') != current['sha256']
                     or mutation.get('protocol_sha256') != digest(protocol)):
        failures.append('scenario_launch_record_mismatch')
    flight_path = run / 'flight.json'
    flight = load(flight_path) if flight_path.is_file() else {}
    if not flight_path.is_file():
        issues.append('flight_missing')
    elif not flight.get('action_success') or not flight.get('landed_and_disarmed'):
        failures.append('flight_or_terminal_failed')
    expected = {'run_id': run.name, 'runtime_contract_sha256': current['sha256'],
                'goal_id': flight.get('goal_id'), 'epoch': flight.get('localization_epoch'),
                'map_id': mutation.get('map_id')}
    gui_path=run/'gui-windows.json'
    gui=load(gui_path) if gui_path.is_file() else {}
    listing=run/'gui-windows.txt'
    if (gui.get('run_id')!=run.name or gui.get('gazebo_window_present') is not True
            or gui.get('rviz_window_present') is not True or not listing.is_file()
            or gui.get('window_listing_sha256')!=digest(listing)):
        issues.append('visible_gui_evidence_missing_or_mismatched')
    safe_path=run/'safe-to-stop.json'
    safe=load(safe_path) if safe_path.is_file() else {}
    if (safe.get('safe_to_stop_project_container') is not True
            or not safe.get('checks') or not all(safe['checks'].values())
            or safe.get('expected_goal_id')!=flight.get('goal_id')
            or safe.get('expected_epoch')!=flight.get('localization_epoch')):
        issues.append('independent_safe_terminal_not_verified')
    manifest_path=run/'n09-run-manifest.json'
    manifest=load(manifest_path) if manifest_path.is_file() else {}
    launch=manifest.get('launch_manifest') or {}
    if policy.get('planner_config'):
        if (launch.get('planner_config')!=policy['planner_config']
                or current['files'].get(policy['planner_config'])!=policy.get('planner_config_sha256')
                or any(launch.get('ego_launch_arguments',{}).get(k)!=v
                       for k,v in policy.get('effective_dynamics',{}).items())):
            issues.append('effective_planner_profile_not_frozen_protocol')
    if policy.get('goal_profile_sha256'):
        if manifest.get('goal_profile_sha256')!=policy['goal_profile_sha256']:
            issues.append('goal_profile_not_frozen_protocol')
    common_path = run / 'n10-acceptance-evaluation.json'
    common = load(common_path) if common_path.is_file() else {}
    if not common:
        issues.append('frozen_common_evaluation_missing')
    if common and (common.get('runtime_contract_sha256') != current['sha256']
                   or common.get('run_id') != run.name
                   or common.get('acceptance_config_sha256') != expected_config_sha):
        failures.append('common_evaluation_identity_mismatch')
    if common.get('overall_status') == 'FAIL':
        failures.append('common_evaluation_failed')
    # A failure is never erased by an applicability override.
    raw_rows = common.get('metrics', [])
    rows = {row['id']: dict(row) for row in raw_rows}
    if len(rows) != len(raw_rows):
        failures.append('duplicate_metric_rows')
    for row in raw_rows:
        if row.get('status') == 'FAIL' or row.get('direct_safety_failure'):
            failures.append('observed_failure:' + row['id'])
    map_path = run / 'n11-static-map-evaluation.json'
    static = load(map_path) if map_path.is_file() else {}
    if not static:
        issues.append('static_wall_map_evaluation_missing')
    elif (not all(expected.values()) or static.get('run_identity') != expected
          or static.get('acceptance_config_sha256') != expected_config_sha
          or static.get('active_world_sha256') != digest(scene)):
        failures.append('static_map_identity_mismatch')
        static = {}
    for metric in STATIC_METRICS:
        replacement = (static.get('metrics') or {}).get(metric)
        if not replacement or replacement.get('status') not in ('PASS', 'FAIL', 'INSUFFICIENT'):
            issues.append(metric + ':wall_evidence_missing')
        elif replacement['status'] == 'FAIL':
            failures.append('static_map_failed:' + metric)
        else:
            # No original FAIL can be overwritten (collected above).
            rows[metric] = {'id': metric, **replacement, 'scene_source': 'static_walls'}
    dynamic = rows.get('dynamic_replanning', {})
    dynamic_applicable = not (empty and mutation_path.is_file()
            and mutation.get('scenario') == 'empty_room'
            and mutation.get('world_mutation_commands') == []
            and mutation.get('runtime_contract_sha256') == current['sha256']
            and mutation.get('protocol_sha256') == digest(protocol)
            and dynamic.get('status') != 'FAIL'
            and not dynamic.get('direct_safety_failure'))
    if not dynamic_applicable:
        rows['dynamic_replanning'] = {**dynamic, 'id': 'dynamic_replanning',
            'status': 'NOT_APPLICABLE', 'original_status': dynamic.get('status'),
            'reason': 'N11 empty-room protocol has no dynamic-obstacle event'}
    required = [name for name, value in cfg['metrics'].items() if value.get('required')
                and name != 'dynamic_replanning']
    for metric in required:
        if rows.get(metric, {}).get('status') != 'PASS':
            issues.append(metric + ':not_pass')
    if dynamic_applicable:
        issues.append('dynamic_event_non_applicability_not_established')
    status = 'FAIL' if failures else ('INSUFFICIENT' if issues else 'PASS')
    return {'schema': 'n11-scene-acceptance/v1', 'run_id': run.name,
            'runtime_contract_sha256': current['sha256'],
            'acceptance_config_sha256': digest(config), 'protocol_sha256': digest(protocol),
            'evaluator_sha256': digest(__file__), 'overall_status': status,
            'formal_count_eligible': status == 'PASS', 'changed_runtime_files': sorted(changed),
            'failures': sorted(set(failures)), 'insufficient': sorted(set(issues)),
            'metrics': list(rows.values()), 'original_metrics': raw_rows, 'control_effect': False}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--frozen-run', type=Path, required=True)
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--protocol', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    result = evaluate(a.run, a.frozen_run, a.config, a.protocol)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'status': result['overall_status'], 'formal_count_eligible': result['formal_count_eligible']}))

if __name__ == '__main__':
    main()
