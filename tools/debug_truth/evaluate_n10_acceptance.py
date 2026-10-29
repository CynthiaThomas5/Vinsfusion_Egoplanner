#!/usr/bin/env python3
"""Apply the offline N10 acceptance configuration to an identity-bound run."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
from tools.n10_terminal_readback import summarize_terminal_readback
from tools.n10_run_identity import read_run_identity


def continuous_clearance_evidence(run_dir, minimum_clearance_m):
    """A dense sample ledger alone cannot pass an inter-sample requirement."""
    result = {'status': 'INSUFFICIENT'}
    try:
        report = json.loads((run_dir / 'n10-interval-clearance-bound.json').read_text())
        if (report.get('schema') != 'n10-model-bounded-interval-clearance/v3'
                or report.get('run_id') != run_dir.name
                or (minimum_clearance_m is not None and (
                    report.get('interval_bound_verified') is not True
                    or report.get('status') != 'AIRBORNE_MODEL_BOUND_POSITIVE_CONTACT_PHASE_SEPARATE'))
                or (minimum_clearance_m is None and report.get('status') not in (
                    'AIRBORNE_MODEL_BOUND_POSITIVE_CONTACT_PHASE_SEPARATE',
                    'INSUFFICIENT_AIRBORNE_BOUND'))):
            raise ValueError('verified_interval_bound_missing')
        tool = ROOT / 'tools/debug_truth/evaluate_n10_interval_clearance_bound.py'
        if report.get('evaluator_sha256') != sha256(tool):
            raise ValueError('interval_evaluator_identity_mismatch')
        for name in ('flight.json', 'debug-truth-evaluation.json',
                     'bridge-alignment-timeline.jsonl', 'n09-contact-observation.json',
                     'vehicle-contact-evaluation.json', 'runtime-contract.json',
                     'n10-tool-freeze-used.json', 'n09-contact-model-manifest.json',
                     'n10-px4-model-source.json'):
            if (report.get('input_sha256') or {}).get(name) != sha256(run_dir / name):
                raise ValueError(f'interval_input_hash_mismatch:{name}')
        velocity = report.get('velocity_endpoint_evidence') or {}
        if (velocity.get('status') != 'PASS'
                or velocity.get('instantaneous_endpoint_state_observed') is not True
                or velocity.get('record_sha256') != sha256(run_dir / 'debug-truth-kinematics.jsonl')):
            raise ValueError('interval_instantaneous_velocity_evidence_missing')
        flight = report.get('flight_interval') or {}
        states = report.get('solver_state_clearance') or {}
        components = report.get('collision_component_sphere_geometry') or {}
        partition = report.get('interval_partition_coverage') or {}
        contact = report.get('contact_intervals') or {}
        interval_count = finite_number(flight.get('solver_state_count'))
        state_count = finite_number(states.get('solver_state_count'))
        clearance_count = finite_number(states.get('clearance_sample_count'))
        expected_intervals = finite_number(partition.get('expected_adjacent_interval_count'))
        partition_count = finite_number(partition.get('reported_interval_count'))
        component_count = finite_number(components.get('component_count'))
        bounded_count = finite_number(partition.get('bounded_no_contact_interval_count'))
        unavailable_count = finite_number(
            partition.get('unavailable_no_contact_interval_count'))
        contact_count = finite_number(partition.get('contact_interval_count'))
        report_contact_count = finite_number(contact.get('total_interval_count'))
        report_bounded_count = finite_number((report.get('airborne_intervals') or {}).get(
            'count'))
        step_s = finite_number(flight.get('step_s'))
        maximum_gap = finite_number(flight.get('maximum_observed_step_gap_s'))
        if (states.get('status') != 'COMPLETE'
                or states.get('geometry_schema') != 'n10-sdf-collision-component-spheres/v1'
                or states.get('all_solver_states_have_clearance') is not True
                or components.get('complete_for_parsed_vehicle_models') is not True
                or component_count is None or component_count < 1
                or interval_count is None or state_count != interval_count
                or clearance_count != interval_count
                or flight.get('every_solver_step_present') is not True
                or partition.get('complete_partition') is not True
                or expected_intervals is None or partition_count != expected_intervals
                or bounded_count is None or report_bounded_count != bounded_count
                or unavailable_count is None or unavailable_count != 0
                or contact_count is None or report_contact_count != contact_count
                or bounded_count + unavailable_count + contact_count != expected_intervals
                or step_s is None or maximum_gap is None
                or maximum_gap > step_s + 2e-9
                or contact.get('prohibited_contact_interval_count') != 0):
            raise ValueError('component_clearance_or_interval_coverage_incomplete')
        lower_bound = finite_number((report.get('airborne_intervals') or {}).get(
            'min_clearance_lower_bound_m'))
        sampled_minimum = finite_number(states.get('minimum_component_clearance_m'))
        maximum_gap = finite_number(flight.get('maximum_observed_step_gap_s'))
        if lower_bound is None or sampled_minimum is None or maximum_gap is None:
            raise ValueError('interval_minimum_bound_missing')
        if lower_bound > sampled_minimum + 1e-9:
            raise ValueError('interval_lower_bound_exceeds_sampled_clearance')
        if minimum_clearance_m is not None and sampled_minimum < minimum_clearance_m:
            status = 'FAIL'
        elif minimum_clearance_m is not None and lower_bound < minimum_clearance_m:
            status = 'FAIL'
        else:
            status = 'PASS'
        result.update(status=status,
                      minimum_solver_state_component_clearance_m=sampled_minimum,
                      minimum_no_contact_interval_clearance_m=lower_bound,
                      maximum_observed_solver_step_gap_s=maximum_gap,
                      threshold_m=minimum_clearance_m,
                      numeric_limit_enabled=minimum_clearance_m is not None,
                      measurement_status="OBSERVED",
                      source_interval_report_status=report.get("status"),
                      component_count=int(component_count),
                      solver_state_count=int(interval_count),
                      adjacent_interval_partition_complete=True,
                      scope='no-contact intervals; allowed skid-contact phase separate')
    except (OSError, ValueError, TypeError, KeyError) as exc:
        result['reason'] = str(exc)
    return result


def summarize_required_metrics(config, result):
    """Keep every observation; exclude user-scoped optional gaps from coverage."""
    criteria = config.get('metrics', {})
    metrics = [{**item, 'required_for_this_scope':
                criteria.get(item['id'], {}).get('required', True) is not False}
               for item in result]
    statuses = [item['status'] for item in metrics if item['required_for_this_scope']]
    direct_failures = [item['id'] for item in metrics
                       if item['status'] == 'FAIL'
                       and item.get('evidence_status') == 'direct_goal_contract']
    observed_safety_failures = [item['id'] for item in metrics
                                if item.get('direct_safety_failure') is True]
    if config.get('status') == 'frozen' and 'FAIL' in statuses:
        overall = 'FAIL'
    elif direct_failures or observed_safety_failures:
        overall = 'FAIL'
    elif (config.get('status') != 'frozen' or not statuses or 'INSUFFICIENT' in statuses
          or (config.get('normal_navigation_policy') == 'functional_navigation_v1'
              and config.get('scene_protocol', {}).get('status') != 'ready')):
        overall = 'INSUFFICIENT'
    else:
        overall = 'PASS'
    return {'overall_status': overall, 'metrics': metrics,
            'scene_protocol': config.get('scene_protocol'),
            'excluded_from_required_calibration': [item['id'] for item in metrics
                                                   if not item['required_for_this_scope']]}


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def finite_number(value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def integer_value(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        return default


def cgroup_cpu_quota_capacity(value):
    """Return a finite cpu.max quota in cores, None for unlimited or invalid."""
    parts = str(value or '').split()
    if len(parts) != 2:
        return None
    if parts[0] == 'max':
        return None
    quota = finite_number(parts[0])
    period = finite_number(parts[1])
    return quota / period if quota is not None and period is not None and quota > 0 and period > 0 else None


def cgroup_numeric_limit(value):
    """Return a finite positive cgroup memory limit, or None for unlimited/invalid."""
    result = finite_number(value)
    return result if result is not None and result > 0 else None


def cgroup_cpu_limit_is_valid(value):
    parts = str(value or '').split()
    if len(parts) != 2:
        return False
    period = finite_number(parts[1])
    if period is None or period <= 0:
        return False
    return parts[0] == 'max' or (
        finite_number(parts[0]) is not None and finite_number(parts[0]) > 0)


def cgroup_memory_limit_is_valid(value):
    return value == 'max' or cgroup_numeric_limit(value) is not None


def numeric_summary(values):
    values = sorted(value for value in (finite_number(item) for item in values)
                    if value is not None)
    if not values:
        return {'count': 0, 'p50': None, 'p95': None, 'max': None}

    def percentile(p):
        position = (len(values) - 1) * p
        lower = int(math.floor(position))
        upper = int(math.ceil(position))
        if lower == upper:
            return values[lower]
        return values[lower] + (values[upper] - values[lower]) * (position - lower)

    return {'count': len(values), 'p50': percentile(0.5),
            'p95': percentile(0.95), 'max': values[-1]}


def gate(name, comparisons, evidence):
    """Return a result only when all numeric inputs are present and finite."""
    missing = [item['metric'] for item in comparisons
               if finite_number(item.get('value')) is None
               or finite_number(item.get('threshold')) is None]
    if missing:
        return {'id': name, 'status': 'INSUFFICIENT', 'missing': missing,
                'evidence_status': evidence}
    def violates(item):
        operator = item['operator']
        value, threshold = item['value'], item['threshold']
        if operator == '<=':
            return value > threshold
        if operator == '>=':
            return value < threshold
        if operator == '<':
            return value >= threshold
        if operator == '>':
            return value <= threshold
        if operator == '==':
            return value != threshold
        if operator == '!=':
            return value == threshold
        raise ValueError(f'unsupported acceptance comparison operator: {operator}')

    failed = [item for item in comparisons if violates(item)]
    return {
        'id': name,
        'status': 'FAIL' if failed else 'PASS',
        'evidence_status': evidence,
        'comparisons': comparisons,
    }


def compare(metric, value, threshold, operator, unit):
    value = finite_number(value)
    threshold = finite_number(threshold)
    return {'metric': metric, 'value': value, 'threshold': threshold,
            'operator': operator, 'unit': unit}


def identity_evidence(run_id, run_metrics, run_dir, functional_navigation=False):
    if functional_navigation:
        identity = read_run_identity(run_dir)
        return {
            'run_directory_matches_selected_run': run_dir.name == run_id,
            'runtime_contract_matches_calibration_record': (
                identity.get('runtime_contract_sha256')
                == run_metrics.get('runtime_contract_sha256')),
            'goal_epoch_map_identity_is_bound': (
                identity.get('complete') is True and run_dir.name == run_id),
            'run_identity': identity,
        }
    paths = {
        'runtime_contract': run_dir / 'runtime-contract.json',
        'flight': run_dir / 'flight.json',
        'observer': run_dir / 'n10-live-obstacle-observation.json',
    }
    missing = [name for name, path in paths.items() if not path.is_file()]
    report = {
        'run_directory_matches_selected_run': run_dir.name == run_id,
        'runtime_contract_matches_calibration_record': False,
        'goal_epoch_map_identity_is_bound': False,
        'missing_inputs': missing,
    }
    if missing:
        return report
    contract = json.loads(paths['runtime_contract'].read_text())
    flight = json.loads(paths['flight'].read_text())
    observer = json.loads(paths['observer'].read_text())
    goal_id = flight.get('goal_id')
    epoch = flight.get('localization_epoch')
    map_id = observer.get('map_id_at_goal')
    report.update({
        'runtime_contract_sha256': contract.get('sha256'),
        'goal_id': goal_id,
        'epoch': epoch,
        'map_id': map_id,
        'runtime_contract_matches_calibration_record': (
            contract.get('sha256') == run_metrics.get('runtime_contract_sha256')),
        'goal_epoch_map_identity_is_bound': bool(
            goal_id and epoch and map_id and map_id.startswith(epoch + '-')
            and observer.get('goal_id') == goal_id
            and observer.get('epoch') == epoch
            and observer.get('run_id') == run_id
            and run_dir.name == run_id),
    })
    return report


def archived_input_hashes(run_metrics, run_dir):
    expected = run_metrics.get('input_sha256') or {}
    checked, missing, mismatches = [], [], []
    for name, digest in expected.items():
        path = run_dir / name
        if not path.is_file():
            missing.append(name)
        elif sha256(path) != digest:
            mismatches.append(name)
        else:
            checked.append(name)
    return {'matches': bool(expected) and not missing and not mismatches,
            'checked_files': checked, 'missing_files': missing,
            'hash_mismatches': mismatches}


def tracking_clearance_budget_result(config, run_metrics, run_dir, report):
    criteria = config['metrics']['ego_tracking_clearance_budget']
    entry = {
        'id': 'ego_tracking_clearance_budget',
        'status': 'INSUFFICIENT',
        'evidence_status': criteria['evidence_status'],
        'acceptance_thresholds': criteria.get('acceptance_thresholds'),
        'runtime_gate_added': False,
    }
    if report is None:
        entry['reason'] = 'identity-bound pointwise tracking/clearance report is missing'
        return entry
    if not isinstance(report, dict):
        entry['reason'] = 'tracking/clearance report is not a JSON object'
        return entry
    if report.get('schema') != 'n10-tracking-clearance-relation/v3':
        entry['reason'] = 'tracking/clearance report schema is unsupported or lacks the pointwise budget'
        return entry

    identity = report.get('identity') or {}
    contract_path = run_dir / 'runtime-contract.json'
    flight_path = run_dir / 'flight.json'
    observer_path = run_dir / 'n10-live-obstacle-observation.json'
    identity_files_present = all(path.is_file() for path in (
        contract_path, flight_path, observer_path))
    input_paths = {
        'flight': flight_path,
        'truth': run_dir / 'debug-truth-evaluation.json',
        'runtime_contract': contract_path,
        'envelope': ROOT / 'config/components/navigation/vehicle_envelope.json',
        'world': run_dir / 'n10-dynamic-clearance-world.sdf',
        'observation': observer_path,
        'contact_model_manifest': run_dir / 'n09-contact-model-manifest.json',
        'base_collision_model': run_dir / 'n09-contact-models/x500_base/model.sdf',
        'vehicle_collision_model': run_dir / 'n09-contact-models/x500_d435i/model.sdf',
        'camera_collision_model': run_dir / 'n09-contact-models/d435i/model.sdf',
    }
    expected_inputs = report.get('input_sha256') or {}
    missing_inputs = [name for name, path in input_paths.items()
                      if not path.is_file()]
    mismatched_inputs = [name for name, path in input_paths.items()
                         if path.is_file() and expected_inputs.get(name) != sha256(path)]
    invalid_identity_files = []
    try:
        contract = json.loads(contract_path.read_text()) if contract_path.is_file() else {}
        flight = json.loads(flight_path.read_text()) if flight_path.is_file() else {}
        observer = json.loads(observer_path.read_text()) if observer_path.is_file() else {}
    except (OSError, json.JSONDecodeError):
        contract, flight, observer = {}, {}, {}
        invalid_identity_files.append('runtime-contract.json, flight.json, or n10-live-obstacle-observation.json')
    identity_matches = bool(
        identity_files_present
        and report.get('run_id') == run_dir.name
        and identity.get('run_directory_matches_selected_run') is True
        and identity.get('runtime_contract_identity_sha256') == contract.get('sha256')
        and contract.get('sha256') == run_metrics.get('runtime_contract_sha256')
        and identity.get('goal_id') == flight.get('goal_id')
        and identity.get('epoch') == flight.get('localization_epoch')
        and identity.get('map_id') == observer.get('map_id_at_goal')
        and identity.get('goal_map_identity_matches') is True
        and observer.get('run_id') == run_dir.name
        and observer.get('goal_id') == flight.get('goal_id')
        and observer.get('epoch') == flight.get('localization_epoch'))
    all_inputs_match = (not missing_inputs and not mismatched_inputs
                        and all(name in expected_inputs for name in input_paths))
    budget = report.get('translation_only_clearance_budget') or {}
    stats = budget.get('pointwise_lower_bound_m') or {}
    component_geometry = report.get('collision_component_sphere_geometry') or {}
    component_clearance = report.get('minimum_actual_body_clearance') or {}
    report_interval = report.get('interval') or {}
    geometry_checks = component_geometry.get('model_source_checks') or {}
    geometry_identity_valid = (
        component_geometry.get('schema') == 'n10-sdf-collision-component-spheres/v1'
        and finite_number(component_geometry.get('component_count')) is not None
        and finite_number(component_geometry.get('component_count')) > 0
        and set(geometry_checks) == {
            'x500_base/model.sdf', 'x500_d435i/model.sdf', 'd435i/model.sdf'}
        and all(value is True for value in geometry_checks.values()))
    matching_commands = finite_number(report_interval.get('matching_ready_commands'))
    paired_commands = finite_number(report_interval.get('paired_truth_commands'))
    maximum_bracket_gap = finite_number(
        report_interval.get('maximum_truth_bracket_gap_sim_s'))
    minimum_actual_clearance = finite_number(component_clearance.get(
        'actual_body_clearance_to_nearest_obstacle_m'))
    complete_pairing = (
        matching_commands is not None and matching_commands > 0
        and paired_commands == matching_commands
        and not report_interval.get('rejected_commands'))
    entry.update({
        'tracking_clearance_evaluator_sha256': report.get(
            'tracking_clearance_evaluator_sha256'),
        'tracking_report_identity_matches': identity_matches,
        'tracking_report_inputs_match': all_inputs_match,
        'missing_inputs': missing_inputs,
        'input_hash_mismatches': mismatched_inputs,
        'invalid_identity_files': invalid_identity_files,
        'pointwise_translation_only_lower_bound_m': stats,
        'negative_bound_sample_count': budget.get('negative_sample_count'),
        'negative_bound_sample_fraction': budget.get('negative_sample_fraction'),
        'classification': budget.get('classification'),
        'component_geometry_schema': component_geometry.get('schema'),
        'component_count': component_geometry.get('component_count'),
        'component_model_source_checks': geometry_checks,
        'component_geometry_identity_valid': geometry_identity_valid,
        'paired_ready_command_count': paired_commands,
        'matching_ready_command_count': matching_commands,
        'all_ready_commands_paired': complete_pairing,
        'maximum_truth_bracket_gap_sim_s': maximum_bracket_gap,
        'minimum_actual_component_clearance_m': minimum_actual_clearance,
        'minimum_actual_component_nearest_obstacle': component_clearance.get(
            'nearest_actual_obstacle'),
        'minimum_actual_component_nearest_component': component_clearance.get(
            'nearest_actual_component'),
        'position_tracking_error_m': report.get('tracking_error_m'),
    })
    if not identity_matches or not all_inputs_match or invalid_identity_files:
        entry['reason'] = 'tracking/clearance evidence does not match this run identity and its source hashes'
    elif not geometry_identity_valid or not complete_pairing:
        entry['reason'] = 'component geometry identity or complete command/truth pairing is missing'
    elif minimum_actual_clearance is None:
        entry['reason'] = 'finite actual component clearance observation is missing'
    else:
        thresholds = criteria.get('acceptance_thresholds') or {}
        comparisons = [
            *([compare('minimum_actual_component_clearance_m', minimum_actual_clearance,
                    thresholds['minimum_actual_component_clearance_m'], '>=', 'm')]
              if 'minimum_actual_component_clearance_m' in thresholds else []),
            compare('maximum_truth_bracket_gap_sim_s', maximum_bracket_gap,
                    thresholds.get('maximum_truth_bracket_gap_sim_s'), '<=', 'sim_s'),
        ]
        outcome = gate('ego_tracking_clearance_budget', comparisons,
                       criteria['evidence_status'])
        entry.update({
            'status': outcome['status'],
            'comparisons': comparisons,
            'translation_only_lower_bound_is_diagnostic': True,
            'clearance_numeric_limit_enabled': 'minimum_actual_component_clearance_m' in thresholds,
            'clearance_measurement_status': 'OBSERVED',
        })
        entry['reason'] = (
            'tracking samples meet the scene SDF/body-clearance criterion; scalar translation bound remains diagnostic'
            if outcome['status'] == 'PASS' else
            'observed scene geometry or source-time pairing violates the calibrated tracking criterion'
            if outcome['status'] == 'FAIL' else
            'tracking geometry metric is missing a finite measurement')
    return entry


def dynamic_replanning_result(config, run_metrics, run_dir, report,
                              tracking_report, tracking_metric, clearance_metric):
    criteria = config['metrics']['dynamic_replanning']
    entry = {
        'id': 'dynamic_replanning',
        'status': 'INSUFFICIENT',
        'evidence_status': criteria['evidence_status'],
        'acceptance_thresholds': criteria.get('acceptance_thresholds'),
        'runtime_gate_added': False,
    }
    if not isinstance(report, dict):
        entry['reason'] = 'identity-bound event-geometry replanning report is missing or unreadable'
        return entry
    if report.get('schema') != 'n10-obstacle-replan-geometry/v3':
        entry['reason'] = 'replanning report schema lacks an event-specific margin deadline'
        return entry

    flight_path = run_dir / 'flight.json'
    contract_path = run_dir / 'runtime-contract.json'
    observation_path = run_dir / 'n10-live-obstacle-observation.json'
    snapshot_path = run_dir / 'n10-box-map-snapshot-analysis.json'
    obstacle = report.get('injection', {}).get('obstacle') or {}
    paths = {
        'observation': observation_path,
        'planner': run_dir / 'planner-observation.json',
        'flight': flight_path,
        'runtime': contract_path,
        'snapshot_metadata': run_dir / 'n10-map-snapshot/metadata.json',
        'snapshot_analysis': snapshot_path,
        'body_clearance': run_dir / 'n10-clearance-evaluation.json',
        'alignment': run_dir / 'arrival-evaluation-simtime-v2.json',
        'vehicle_envelope': ROOT / 'config/components/navigation/vehicle_envelope.json',
        'injected_obstacle_sdf': run_dir / str(obstacle.get('sdf_file') or ''),
    }
    expected_hashes = report.get('inputs_sha256') or {}
    if 'map_queries' in expected_hashes:
        paths['map_queries'] = run_dir / 'n10-map-point-queries.json'
    missing_inputs = [name for name, path in paths.items() if not path.is_file()]
    mismatched_inputs = [
        name for name, path in paths.items()
        if path.is_file() and expected_hashes.get(name) != sha256(path)
    ]
    all_inputs_match = not missing_inputs and not mismatched_inputs
    try:
        contract = json.loads(contract_path.read_text())
        flight = json.loads(flight_path.read_text())
        observation = json.loads(observation_path.read_text())
        snapshot = json.loads(snapshot_path.read_text())
    except (OSError, json.JSONDecodeError):
        contract, flight, observation, snapshot = {}, {}, {}, {}

    identity = report.get('identity') or {}
    identity_matches = bool(
        report.get('run_id') == run_dir.name
        and identity.get('runtime_contract_sha256') == contract.get('sha256')
        and identity.get('runtime_contract_sha256')
        == run_metrics.get('runtime_contract_sha256')
        and identity.get('goal_id') == flight.get('goal_id')
        and identity.get('epoch') == flight.get('localization_epoch')
        and identity.get('map_id') == observation.get('map_id_at_goal')
        and identity.get('goal_id') == observation.get('goal_id')
        and identity.get('epoch') == observation.get('epoch')
        and observation.get('run_id') == run_dir.name)
    current_evaluator = ROOT / 'tools/debug_truth/evaluate_n10_replan_geometry.py'
    evaluator_matches = report.get('tool_sha256') == sha256(current_evaluator)
    live_ack = report.get('injection', {}).get('gazebo_create_acknowledged') is True
    obstacle_sdf_matches_observation = (
        paths['injected_obstacle_sdf'].is_file()
        and sha256(paths['injected_obstacle_sdf']) == obstacle.get('sdf_sha256'))

    geometry = report.get('planner_centerline_geometry') or {}
    first_cloud = (report.get('raw_occupancy_cloud_observations') or {}).get(
        'first_sample_with_points') or {}
    safe_spline = geometry.get(
        'first_trajectory_with_required_body_clearance_after_cloud') or {}
    deadline = geometry.get('replanning_deadline') or {}
    pre_cloud_command = deadline.get('latest_strictly_pre_cloud_ready_command') or {}
    pre_cloud_reference_active = (
        deadline.get('reference_trajectory_matches_latest_pre_cloud_ready_command') is True
        and integer_value(pre_cloud_command.get('trajectory_id'))
        == integer_value(deadline.get('reference_trajectory_id'), -2)
        and integer_value(pre_cloud_command.get('source_stamp_ns'), -1)
        < integer_value(first_cloud.get('stamp_ns'), 0))
    snapshot_geometry = report.get('identity_bound_raw_inflated_snapshot') or {}
    snapshot_roi = snapshot.get('snapshot_roi') or {}
    snapshot_counts = snapshot_roi.get('near_surface_raw_occupied_point_count')
    inflated_count = snapshot_roi.get('near_surface_raw_occupied_inflated_count')
    snapshot_coverage = snapshot.get('snapshot_source_coverage') or {}
    snapshot_source_ns = finite_number(snapshot_geometry.get('snapshot_source_stamp_ns'))
    safe_receipt_ns = finite_number(safe_spline.get('receipt_sim_ns'))
    cloud_stamp_ns = finite_number(first_cloud.get('stamp_ns'))
    available_s = finite_number(deadline.get('available_time_to_clearance_boundary_sim_s'))
    delay_s = finite_number(deadline.get('replacement_delay_after_first_positive_cloud_sim_s'))
    slack_s = finite_number(deadline.get('deadline_slack_after_replacement_sim_s'))
    body_margin = finite_number(safe_spline.get('minimum_centerline_body_margin_m'))
    required_body_margin = finite_number(
        criteria['acceptance_thresholds'].get('minimum_planner_centerline_body_margin_m'))
    first_positive_count = finite_number(first_cloud.get('obstacle_roi_point_count'))
    surface_raw_min = finite_number(
        criteria['acceptance_thresholds'].get(
            'minimum_identity_bound_surface_raw_occupied_count'))
    surface_inflated_min = finite_number(
        criteria['acceptance_thresholds'].get(
            'minimum_identity_bound_surface_inflated_count'))
    post_safe_splines = geometry.get('post_margin_qualified_spline_geometry') or {}
    post_safe_margin = finite_number(
        post_safe_splines.get('minimum_centerline_body_margin_m'))
    post_safe_violations = finite_number(
        post_safe_splines.get('below_required_body_clearance_count'))

    fullbody_value = next((
        item.get('value') for item in clearance_metric.get('comparisons', [])
        if item.get('metric') == 'minimum_full_body_clearance_m'),
        clearance_metric.get('minimum_received_state_clearance_m'))
    fullbody_threshold = criteria['acceptance_thresholds'].get(
        'minimum_full_body_clearance_m')
    prohibited_count = clearance_metric.get('observed_prohibited_contact_event_count')
    continuous_clearance = clearance_metric.get('continuous_interval_evidence') or {}
    interval_lower_bound = finite_number(
        continuous_clearance.get('minimum_no_contact_interval_clearance_m'))

    goal_completed_ns = integer_value(flight.get('goal_completed_source_ns'), -1)
    safe_traj_id = integer_value(safe_spline.get('traj_id'), 2**63 - 1)
    post_commands = []
    for row in flight.get('position_command_history', []):
        source_ns = integer_value(row.get('source_stamp_ns'), -1)
        traj_id = integer_value(row.get('trajectory_id'), -1)
        if (row.get('goal_id') == flight.get('goal_id')
                and row.get('epoch') == flight.get('localization_epoch')
                and integer_value(row.get('flag'), -1) == 1
                and safe_receipt_ns is not None
                and source_ns >= safe_receipt_ns
                and source_ns <= goal_completed_ns
                and traj_id >= safe_traj_id):
            post_commands.append(row)
    tracking_rows = ((tracking_report or {}).get('per_sample') or [])
    ready_command_by_stamp = Counter(
        (integer_value(row.get('source_stamp_ns'), -1),
         integer_value(row.get('trajectory_id'), -1))
        for row in post_commands if row.get('trajectory_id') is not None)
    post_tracking_rows = [
        row for row in tracking_rows
        if row.get('trajectory_id') is not None
        and safe_receipt_ns is not None
        and integer_value(row.get('source_stamp_ns'), -1) >= safe_receipt_ns
        and integer_value(row.get('source_stamp_ns'), -1) <= goal_completed_ns
        and integer_value(row.get('trajectory_id'), -1) >= safe_traj_id
    ]
    tracked_by_stamp = Counter(
        (integer_value(row.get('source_stamp_ns'), -1),
         integer_value(row.get('trajectory_id'), -1))
        for row in post_tracking_rows)
    post_tracking_complete = bool(
        ready_command_by_stamp and ready_command_by_stamp == tracked_by_stamp)
    post_tracking_clearances = [finite_number(row.get(
        'actual_body_clearance_to_nearest_obstacle_m')) for row in post_tracking_rows]
    post_tracking_geometry_complete = (
        post_tracking_complete and len(post_tracking_rows) == len(post_commands)
        and all(value is not None for value in post_tracking_clearances))
    post_tracking_min_clearance = min(
        (value for value in post_tracking_clearances if value is not None), default=None)
    post_tracking_threshold = criteria['acceptance_thresholds'].get(
        'minimum_full_body_clearance_m')
    predicted_boundary_ns = integer_value(
        deadline.get('predicted_clearance_boundary_stamp_ns'))
    first_safe_ready_command_ns = min((
        integer_value(row.get('source_stamp_ns'), -1) for row in post_commands),
        default=None)
    ready_command_deadline_slack_s = (
        (predicted_boundary_ns - first_safe_ready_command_ns) / 1e9
        if predicted_boundary_ns is not None and first_safe_ready_command_ns is not None
        else None)

    comparisons = [
        compare('safe_replacement_delay_sim_s', delay_s, available_s, '<=', 'sim_s'),
        compare('first_safe_READY_command_source_stamp_ns',
                first_safe_ready_command_ns, predicted_boundary_ns, '<', 'sim_ns'),
        compare('safe_replacement_spline_body_margin_m', body_margin,
                required_body_margin, '>=', 'm'),
        compare('minimum_post_replacement_spline_body_margin_m', post_safe_margin,
                required_body_margin, '>=', 'm'),
        compare('below_margin_post_replacement_spline_count', post_safe_violations,
                0, '<=', 'splines'),
        compare('minimum_full_body_clearance_m', fullbody_value,
                fullbody_threshold, '>=', 'm'),
        compare('minimum_airborne_interval_clearance_lower_bound_m',
                interval_lower_bound, fullbody_threshold, '>=', 'm'),
        compare('prohibited_contact_event_count', prohibited_count,
                criteria['acceptance_thresholds']['prohibited_contact_count_max'],
                '<=', 'events'),
        compare('first_positive_cloud_point_count', first_positive_count, 1, '>=', 'points'),
        compare('identity_bound_surface_raw_occupied_count', snapshot_counts,
                surface_raw_min, '>=', 'voxels'),
        compare('identity_bound_surface_inflated_count', inflated_count,
                surface_inflated_min, '>=', 'voxels'),
        compare('post_replacement_ready_command_count', len(post_commands), 1, '>=', 'commands'),
        compare('post_replacement_paired_command_count', len(post_tracking_rows),
                len(post_commands), '>=', 'commands'),
        compare('post_replacement_actual_component_clearance_m',
                post_tracking_min_clearance, post_tracking_threshold, '>=', 'm'),
    ]
    if fullbody_threshold is None:
        if (clearance_metric.get('status') == 'FAIL' or tracking_metric.get('status') == 'FAIL'
                or (prohibited_count is not None and prohibited_count >
                    criteria['acceptance_thresholds']['prohibited_contact_count_max'])):
            entry.update(status='FAIL', direct_safety_failure=True,
                         reason='observed independent contact/full-body/tracking failure')
            return entry
        numeric_clearance_names = {
            'minimum_full_body_clearance_m', 'minimum_airborne_interval_clearance_lower_bound_m',
            'post_replacement_actual_component_clearance_m'}
        if required_body_margin is None:
            numeric_clearance_names.update({'safe_replacement_spline_body_margin_m',
                'minimum_post_replacement_spline_body_margin_m',
                'below_margin_post_replacement_spline_count'})
        comparisons = [x for x in comparisons if x['metric'] not in numeric_clearance_names]
        entry['clearance_numeric_limit_enabled'] = False
        entry['clearance_measurements'] = {
            'actual_body_min_m': fullbody_value, 'interval_lower_bound_m': interval_lower_bound,
            'spline_body_margin_m': body_margin, 'post_spline_body_margin_m': post_safe_margin,
            'post_actual_body_min_m': post_tracking_min_clearance}
        if any(finite_number(v) is None for v in entry['clearance_measurements'].values()):
            entry['reason'] = 'finite replanning clearance observations missing'
            return entry
        if (geometry.get('required_full_body_clearance_m') is not None
                or deadline.get('additional_body_clearance_m') != 0.0
                or geometry.get('clearance_numeric_limit_enabled') is not False):
            entry['reason'] = 'replan geometry still uses a removed clearance-margin policy'
            return entry
    map_snapshot_order_valid = bool(
        snapshot_geometry.get('snapshot_identity_matches_live_observer') is True
        and snapshot.get('snapshot_matches_live_observer_epoch_map_frame') is True
        and snapshot_coverage.get('covered') is True
        and first_cloud and safe_spline
        and cloud_stamp_ns is not None and snapshot_source_ns is not None
        and safe_receipt_ns is not None
        and cloud_stamp_ns <= snapshot_source_ns <= safe_receipt_ns)
    tracking_status_valid = tracking_metric.get('status') == 'PASS'
    clearance_status_valid = clearance_metric.get('status') == 'PASS'
    entry.update({
        'replan_report_identity_matches': identity_matches,
        'replan_report_inputs_match': all_inputs_match,
        'missing_inputs': missing_inputs,
        'input_hash_mismatches': mismatched_inputs,
        'replan_evaluator_identity_matches': evaluator_matches,
        'obstacle_sdf_matches_observation': obstacle_sdf_matches_observation,
        'gazebo_create_acknowledged': live_ack,
        'first_positive_cloud': first_cloud or None,
        'identity_bound_map_surface': {
            'snapshot_source_stamp_ns': snapshot_source_ns,
            'raw_occupied_count': snapshot_counts,
            'inflated_count': inflated_count,
            'source_coverage': snapshot_coverage,
            'ordered_after_cloud_and_before_margin_safe_spline': map_snapshot_order_valid,
        },
        'replanning_deadline': deadline,
        'pre_cloud_deadline_reference_matches_active_ready_command': (
            pre_cloud_reference_active),
        'first_margin_qualified_spline': safe_spline or None,
        'post_margin_qualified_spline_geometry': post_safe_splines,
        'ready_commands_after_margin_qualified_spline': len(post_commands),
        'paired_commands_after_margin_qualified_spline': len(post_tracking_rows),
        'first_safe_READY_command_source_stamp_ns': first_safe_ready_command_ns,
        'first_safe_READY_command_deadline_slack_sim_s': ready_command_deadline_slack_s,
        'post_replacement_minimum_actual_component_clearance_m': post_tracking_min_clearance,
        'all_post_replacement_ready_commands_paired': post_tracking_complete,
        'post_replacement_component_clearance_complete': post_tracking_geometry_complete,
        'full_body_clearance_status': clearance_metric.get('status'),
        'minimum_airborne_interval_clearance_lower_bound_m': interval_lower_bound,
        'tracking_clearance_status': tracking_metric.get('status'),
        'comparisons': comparisons,
        'diagnostic_candidate_delay_breach': (
            delay_s is not None
            and finite_number((criteria.get('diagnostic_candidate') or {}).get(
                'first_replacement_spline_max_delay_sim_s')) is not None
            and delay_s > finite_number((criteria.get('diagnostic_candidate') or {}).get(
                'first_replacement_spline_max_delay_sim_s'))),
        'fixed_latency_candidate_is_not_an_acceptance_threshold': True,
    })
    if clearance_metric.get('status') == 'FAIL' or tracking_metric.get('status') == 'FAIL':
        entry.update({'status': 'FAIL', 'direct_safety_failure': True,
                      'reason': 'the independently evaluated full-body or tracking scene criterion failed'})
    elif not identity_matches or not all_inputs_match or not evaluator_matches:
        entry['reason'] = 'replanning report does not match run identity, current evaluator, or source hashes'
    elif not live_ack or not obstacle_sdf_matches_observation:
        entry['reason'] = 'obstacle insertion acknowledgement or injected SDF identity is missing'
    elif (not map_snapshot_order_valid or not tracking_status_valid
          or not clearance_status_valid or not post_tracking_geometry_complete
          or not pre_cloud_reference_active):
        entry['reason'] = 'map source ordering, active pre-cloud trajectory, complete command tracking, or full-body interval evidence is incomplete'
    else:
        outcome = gate('dynamic_replanning', comparisons,
                       criteria['evidence_status'])
        entry.update({'status': outcome['status'], 'missing': outcome.get('missing')})
        entry['reason'] = (
            'margin-qualified replanning occurred before the event-specific predicted clearance boundary; actual command and 4 ms full-body evidence pass'
            if outcome['status'] == 'PASS' else
            'observed replan did not meet its geometry-derived deadline or clearance criterion'
            if outcome['status'] == 'FAIL' else
            'replanning event is missing a finite timing or clearance measurement')
    return entry


def resource_and_queue_behavior_result(config, run_metrics, run_dir,
                                       platform_capacity_report):
    criteria = config['metrics']['resource_and_queue_behavior']
    entry = {
        'id': 'resource_and_queue_behavior',
        'status': 'INSUFFICIENT',
        'evidence_status': criteria['evidence_status'],
        'runtime_gate_added': False,
    }
    resource_path = run_dir / 'n10-resource-observation.json'
    if not resource_path.is_file():
        entry['safe_session_terminal_observed'] = False
        entry['reason'] = 'resource observation is missing'
        return entry
    try:
        resource = json.loads(resource_path.read_text())
        if not isinstance(resource, dict):
            raise ValueError('resource report must be an object')
    except (OSError, ValueError):
        entry['reason'] = 'resource observation is unreadable'
        return entry
    entry.update({
        'resource_report_sha256': sha256(resource_path),
        'observed_resource_samples': len(resource.get('samples', [])),
        'run_id_matches': resource.get('run_id') == run_dir.name,
        'sample_period_s': resource.get('sample_period_s'),
        'wall_duration_s': resource.get('wall_duration_s'),
        'safe_session_terminal_observed': (
            resource.get('safe_session_terminal_observed') is True),
    })
    if resource.get('safe_session_terminal_observed') is not True:
        entry['reason'] = 'resource observation did not cover a verified safe session closeout'
        return entry
    if not isinstance(platform_capacity_report, dict):
        entry['reason'] = 'bound platform-capacity report is missing'
        return entry
    platform = platform_capacity_report.get('platform') or {}
    binding = platform_capacity_report.get('run_binding') or {}
    samples = resource.get('samples') or []
    expected_capacity_inputs = {
        'resource_observation_sha256': sha256(resource_path),
        'runtime_contract_sha256': run_metrics.get('runtime_contract_sha256'),
        'run_id': run_dir.name,
    }
    platform_binding_matches = all(
        binding.get(key) == expected for key, expected in expected_capacity_inputs.items())
    try:
        runtime_contract = json.loads((run_dir / 'runtime-contract.json').read_text())
        identity = resource.get('run_identity') or {}
        identity_matches = bool(
            resource.get('run_id') == run_dir.name
            and identity.get('complete') is True
            and identity.get('run_id') == run_dir.name
            and identity.get('runtime_contract_sha256') == runtime_contract.get('sha256')
            and identity.get('runtime_contract_sha256')
            == run_metrics.get('runtime_contract_sha256')
            and identity.get('goal_id') == (json.loads((run_dir / 'flight.json').read_text()).get('goal_id'))
            and identity.get('epoch') == json.loads((run_dir / 'flight.json').read_text()).get('localization_epoch'))
    except (OSError, json.JSONDecodeError):
        identity_matches = False

    period = finite_number(resource.get('sample_period_s'))
    wall_times = [finite_number(row.get('wall_elapsed_s')) for row in samples]
    complete_wall_samples = bool(
        len(samples) >= 2 and period is not None and period > 0
        and all(value is not None for value in wall_times)
        and all(right > left for left, right in zip(wall_times, wall_times[1:])))
    max_sample_gap = (max(right - left for left, right in zip(wall_times, wall_times[1:]))
                      if complete_wall_samples else None)
    sample_period_limit = (period * criteria['thresholds'][
        'resource_sample_gap_periods_max'] if period is not None else None)
    cpu_usage_values = [finite_number(((row.get('cgroup') or {}).get(
        'cpu_stat') or {}).get('usage_usec')) for row in samples]
    cpu_usage_complete = bool(samples) and all(
        value is not None for value in cpu_usage_values)
    cpu_usage_monotonic = (cpu_usage_complete and all(
        right >= left for left, right in zip(cpu_usage_values, cpu_usage_values[1:])))
    cgroup_cpu_cores = []
    throttle_usec = []
    oom_events_by_kind = {'oom': [], 'oom_kill': [], 'oom_group_kill': []}
    memory_peaks = []
    pids_current = []
    cpu_counts = set()
    cpu_max_values = set()
    memory_max_values = set()
    for row in samples:
        cpu_counts.add(row.get('cpu_count_visible'))
        cgroup = row.get('cgroup') or {}
        cpu_max_values.add(cgroup.get('cpu_max'))
        memory_max_values.add(cgroup.get('memory_max'))
        cpu_stat = cgroup.get('cpu_stat') or {}
        throttle_usec.append(finite_number(cpu_stat.get('throttled_usec')))
        memory_events = cgroup.get('memory_events') or {}
        for key in oom_events_by_kind:
            oom_events_by_kind[key].append(finite_number(memory_events.get(key)))
        memory_peaks.append(finite_number(cgroup.get('memory_peak')))
        pids_current.append(finite_number(cgroup.get('pids_current')))
    cgroup_cpu_limit = next(iter(cpu_max_values)) if len(cpu_max_values) == 1 else None
    cgroup_memory_limit = next(iter(memory_max_values)) if len(memory_max_values) == 1 else None
    cgroup_limit_fields_complete = (
        cgroup_cpu_limit_is_valid(cgroup_cpu_limit)
        and cgroup_memory_limit_is_valid(cgroup_memory_limit))
    for left, right in zip(samples, samples[1:]):
        left_wall = finite_number(left.get('wall_elapsed_s'))
        right_wall = finite_number(right.get('wall_elapsed_s'))
        dt = (right_wall - left_wall
              if left_wall is not None and right_wall is not None else None)
        left_usage = finite_number(((left.get('cgroup') or {}).get(
            'cpu_stat') or {}).get('usage_usec'))
        right_usage = finite_number(((right.get('cgroup') or {}).get(
            'cpu_stat') or {}).get('usage_usec'))
        if dt is not None and dt > 0 and left_usage is not None and right_usage is not None:
            cgroup_cpu_cores.append((right_usage - left_usage) / 1e6 / dt)
    host_cpu_capacity = finite_number(platform.get('effective_cpu_capacity_cores'))
    host_memory_capacity = finite_number(platform.get('effective_memory_capacity_bytes'))
    visible_cpu_capacity = (finite_number(next(iter(cpu_counts)))
                            if len(cpu_counts) == 1 else None)
    cpu_quota_capacity = cgroup_cpu_quota_capacity(cgroup_cpu_limit)
    memory_cgroup_capacity = cgroup_numeric_limit(cgroup_memory_limit)
    cpu_capacity_candidates = [value for value in (
        host_cpu_capacity, visible_cpu_capacity, cpu_quota_capacity)
        if value is not None]
    memory_capacity_candidates = [value for value in (
        host_memory_capacity, memory_cgroup_capacity) if value is not None]
    cpu_capacity = min(cpu_capacity_candidates, default=None)
    memory_capacity = min(memory_capacity_candidates, default=None)
    max_cpu_cores = max(cgroup_cpu_cores, default=None)
    max_memory_peak = max((value for value in memory_peaks if value is not None), default=None)
    max_pids = max((value for value in pids_current if value is not None), default=None)
    memory_peak_monotonic = (bool(memory_peaks)
                             and all(value is not None for value in memory_peaks)
                             and all(right >= left for left, right in
                                     zip(memory_peaks, memory_peaks[1:])))

    queue_config = resource.get('configured_queue_capacities') or {}
    queue_source_hashes = queue_config.get('source_sha256') or {}
    queue_source_mismatches = [
        name for name, digest in queue_source_hashes.items()
        if not (ROOT / name).is_file() or sha256(ROOT / name) != digest
    ]
    required_queue_sources = {
        'config/components/mapping/ego_input.json',
        'src/own/uav_mapping/uav_mapping/adapter.py',
        'config/n10_capture.json',
        'src/vendor/vins_fusion/vins/src/estimator/estimator.cpp',
        'src/vendor/vins_fusion/vins/src/estimator/estimator.h',
        'dependencies/patches/vins/0020-readonly-estimator-queue-high-water.patch',
        'dependencies/sources.json',
    }
    if 'native_work_lag_budget_s' in criteria['thresholds']:
        required_queue_sources.add('dependencies/patches/vins/0021-readonly-native-work-queue.patch')
    queue_source_identity_complete = (
        required_queue_sources.issubset(queue_source_hashes)
        and not queue_source_mismatches)
    map_rows = [row.get('map_queue_counters') for row in samples
                if isinstance(row.get('map_queue_counters'), dict)]
    map_identity_ok = bool(map_rows) and all(
        item.get('epoch') == identity.get('epoch')
        and item.get('map_id') == identity.get('map_id') for item in map_rows)
    map_depth_limit = finite_number(queue_config.get('mapping_pending_depth_limit'))
    map_depth_highwater = max((finite_number(item.get('pending_depth_high_water_count'))
                               for item in map_rows
                               if finite_number(item.get('pending_depth_high_water_count')) is not None),
                              default=None)
    map_pending_max = max((finite_number(item.get('pending_depth_count'))
                           for item in map_rows
                           if finite_number(item.get('pending_depth_count')) is not None),
                          default=None)
    map_depth_drops = max((finite_number(item.get('dropped_depth_count'))
                           for item in map_rows
                           if finite_number(item.get('dropped_depth_count')) is not None),
                          default=None)
    map_keyframe_drops = max((finite_number(item.get('keyframe_dropped_count'))
                              for item in map_rows
                              if finite_number(item.get('keyframe_dropped_count')) is not None),
                             default=None)

    queue_path = run_dir / str((resource.get('vins_queue_telemetry_artifact') or {}).get(
        'path') or '')
    queue_artifact = resource.get('vins_queue_telemetry_artifact') or {}
    queue_rows = []
    queue_file_matches = False
    if queue_path.is_file():
        try:
            queue_rows = [json.loads(line) for line in queue_path.read_text().splitlines()
                          if line.strip()]
            queue_file_matches = (
                sha256(queue_path) == queue_artifact.get('sha256')
                and len(queue_rows) == queue_artifact.get('row_count'))
        except (OSError, json.JSONDecodeError):
            queue_rows = []
    queue_observation = resource.get('vins_estimator_queue_observation') or {}
    queue_sample_stamps = [finite_number(row.get('source_stamp_ns'))
                           for row in queue_rows]
    queue_metric_names = tuple(
        f'{name}_{suffix}' for name in ('acc', 'gyr', 'feature')
        for suffix in ('current_before_feature_dequeue', 'high_water'))
    queue_rows_complete = bool(queue_rows) and all(
        finite_number(row.get('source_stamp_ns')) is not None
        and finite_number(row.get('receipt_monotonic_ns')) is not None
        and (row.get('queue_metrics') or {}).get('scope') == 'estimator_process_lifetime'
        and all(finite_number((row.get('queue_metrics') or {}).get(field)) is not None
                and finite_number((row.get('queue_metrics') or {}).get(field)) >= 0
                for field in queue_metric_names)
        and all(finite_number((row.get('queue_metrics') or {}).get(
            f'{name}_high_water')) >= finite_number((row.get('queue_metrics') or {}).get(
                f'{name}_current_before_feature_dequeue'))
            for name in ('acc', 'gyr', 'feature'))
        for row in queue_rows)
    queue_stamps_monotonic = (
        bool(queue_sample_stamps)
        and all(value is not None for value in queue_sample_stamps)
        and all(right > left for left, right in zip(queue_sample_stamps,
                                                     queue_sample_stamps[1:])))
    queue_receipts = [finite_number(row.get('receipt_monotonic_ns'))
                      for row in queue_rows]
    queue_receipts_monotonic = (
        bool(queue_receipts) and all(value is not None for value in queue_receipts)
        and all(right >= left for left, right in zip(queue_receipts,
                                                     queue_receipts[1:])))
    queue_observer_clean = (
        queue_observation.get('status') == 'OBSERVED'
        and queue_observation.get('errors') == [])
    queue_identity_ok = (
        bool(queue_rows) and queue_rows_complete and queue_stamps_monotonic
        and queue_receipts_monotonic and queue_observer_clean
        and queue_observation.get('sample_count') == len(queue_rows)
        and queue_observation.get('valid_sample_count') == len(queue_rows)
        and all(row.get('epoch') == identity.get('epoch')
                for row in queue_rows))
    current_queue_stats = {}
    for name in ('acc', 'gyr', 'feature'):
        field = f'{name}_current_before_feature_dequeue'
        values = [finite_number((row.get('queue_metrics') or {}).get(field))
                  for row in queue_rows]
        values = [value for value in values if value is not None]
        slope = None
        if len(values) >= 2 and queue_stamps_monotonic:
            times = [stamp / 1e9 for stamp in queue_sample_stamps]
            mean_t = sum(times) / len(times)
            mean_v = sum(values) / len(values)
            denom = sum((item - mean_t) ** 2 for item in times)
            slope = (sum((t - mean_t) * (v - mean_v)
                         for t, v in zip(times, values)) / denom
                     if denom > 0 else None)
        current_queue_stats[name] = {
            'sample_count': len(values),
            'first_current_depth': values[0] if values else None,
            'last_current_depth': values[-1] if values else None,
            'maximum_current_depth': max(values) if values else None,
            'maximum_reported_process_high_water': max((
                finite_number((row.get('queue_metrics') or {}).get(
                    f'{name}_high_water')) for row in queue_rows
                if finite_number((row.get('queue_metrics') or {}).get(
                    f'{name}_high_water')) is not None), default=None),
            'least_squares_current_depth_slope_items_per_sim_s': slope,
        }
    max_positive_queue_slope = max((
        finite_number(item.get('least_squares_current_depth_slope_items_per_sim_s'))
        for item in current_queue_stats.values()
        if finite_number(item.get('least_squares_current_depth_slope_items_per_sim_s')) is not None),
        default=None)

    rtf_summary = numeric_summary(
        row.get('rtf_sim_over_wall') for row in samples)
    cpu_summary = numeric_summary(cgroup_cpu_cores)
    memory_summary = numeric_summary(memory_peaks)

    throttle_counters_complete = bool(samples) and all(
        value is not None for value in throttle_usec)
    throttle_counter_monotonic = (throttle_counters_complete and all(
        right >= left for left, right in zip(throttle_usec, throttle_usec[1:])))
    throttle_delta_usec = (
        throttle_usec[-1] - throttle_usec[0]
        if throttle_counter_monotonic else None)
    oom_fields_complete = bool(samples) and all(
        all(value is not None for value in values)
        for values in oom_events_by_kind.values())
    oom_counter_monotonic = oom_fields_complete and all(
        right >= left
        for values in oom_events_by_kind.values()
        for left, right in zip(values, values[1:]))
    oom_delta_by_kind = ({key: values[-1] - values[0]
                          for key, values in oom_events_by_kind.items()}
                         if oom_counter_monotonic else {})
    no_oom = (oom_counter_monotonic and bool(oom_delta_by_kind)
              and max(oom_delta_by_kind.values(), default=0)
              <= criteria['thresholds']['cgroup_oom_event_delta_max'])
    cgroup_unthrottled = (
        throttle_counter_monotonic and throttle_delta_usec is not None
        and throttle_delta_usec
        <= criteria['thresholds']['cgroup_cpu_throttling_usec_delta_max'])
    throttle_violation = (
        throttle_counter_monotonic and throttle_delta_usec is not None
        and throttle_delta_usec
        > criteria['thresholds']['cgroup_cpu_throttling_usec_delta_max'])
    oom_violation = (oom_counter_monotonic and bool(oom_delta_by_kind)
                     and max(oom_delta_by_kind.values(), default=0)
                     > criteria['thresholds']['cgroup_oom_event_delta_max'])
    max_cpu_capacity_check = compare(
        'cgroup_cpu_core_equivalent_max', max_cpu_cores, cpu_capacity, '<=', 'cores')
    max_memory_capacity_check = compare(
        'cgroup_memory_peak_bytes', max_memory_peak, memory_capacity, '<=', 'bytes')
    comparisons = [
        max_cpu_capacity_check,
        max_memory_capacity_check,
        compare('resource_sample_gap_wall_s', max_sample_gap,
                sample_period_limit, '<=', 's'),
        compare('mapping_depth_high_water', map_depth_highwater,
                map_depth_limit, '<=', 'items'),
        compare('mapping_pending_depth_max', map_pending_max,
                map_depth_limit, '<=', 'items'),

    ]
    native_work = None
    if 'native_work_lag_budget_s' in criteria['thresholds']:
        from n11_native_work_queue import evaluate_native_work
        interval = (run_metrics.get('segments') or {}).get('prestream_to_landed') or {}
        native_work = evaluate_native_work(queue_rows, criteria['thresholds'],
                                          interval.get('start_source_ns'), interval.get('end_source_ns'))
        if interval.get('start_source_ns') is None or interval.get('end_source_ns') is None:
            native_work['missing_or_inconsistent'].append('flight_source_interval_missing')
            if native_work['status'] != 'FAIL': native_work['status'] = 'INSUFFICIENT'
        entry['native_pending_work'] = native_work
        comparisons.extend([
            compare('native_work_lag_s',native_work['maximum_native_lag_s'],criteria['thresholds']['native_work_lag_budget_s'],'<=','sim_s'),
            compare('native_pending_source_span_s',native_work['maximum_pending_source_span_s'],criteria['thresholds']['native_feature_source_span_max_s'],'<=','sim_s'),
            compare('native_waiting_features',native_work['maximum_waiting_features'],criteria['thresholds']['native_waiting_features_max'],'<=','items')])
    else:
        comparisons.append(compare('vins_current_queue_depth_trend_items_per_sim_s',max_positive_queue_slope,
            criteria['thresholds']['vins_current_queue_depth_trend_max_items_per_sim_s'],'<=','items/sim_s'))
    observer_stopped_safely = resource.get('safe_session_terminal_observed') is True
    sample_fields_complete = complete_wall_samples and all(
        all(finite_number((row.get('cgroup') or {}).get(key)) is not None
            for key in ('memory_peak', 'pids_current'))
        and finite_number(((row.get('cgroup') or {}).get('cpu_stat') or {}).get(
            'usage_usec')) is not None
        for row in samples)
    sample_fields_complete = (sample_fields_complete and cpu_usage_monotonic
                              and memory_peak_monotonic)
    queue_capacity_unknown = (
        queue_config.get('vins_estimator_queue_capacity')
        == 'unbounded_by_source; no cap or drop added'
        and queue_observation.get('queue_capacity_or_runtime_limit_inferred') is False)
    platform_identity_ok = (
        platform_binding_matches
        and platform.get('logical_cpu_count') in cpu_counts
        and host_cpu_capacity is not None and host_cpu_capacity > 0
        and host_memory_capacity is not None and host_memory_capacity > 0
        and cgroup_limit_fields_complete)
    checks_complete = all((
        identity_matches, platform_identity_ok, resource.get('run_id') == run_dir.name,
        resource.get('safe_session_terminal_observed') is True,
        resource.get('terminal_flight_record_observed') is True,
        sample_fields_complete, cgroup_unthrottled, no_oom,
        cgroup_limit_fields_complete, map_identity_ok,
        queue_file_matches, queue_identity_ok, queue_rows_complete,
        queue_capacity_unknown,
        queue_observation.get('status') == 'OBSERVED', queue_source_identity_complete,
    ))
    entry.update({
        'platform_capacity_report_sha256': platform_capacity_report.get('_file_sha256'),
        'platform_capacity_binding_matches': platform_binding_matches,
        'platform_identity_matches_run_observation': platform_identity_ok,
        'resource_report_identity_matches': identity_matches,
        'resource_sample_count': len(samples),
        'sample_period_s': period,
        'maximum_sample_gap_wall_s': max_sample_gap,
        'wall_duration_s': resource.get('wall_duration_s'),
        'safe_session_terminal_observed': observer_stopped_safely,
        'cgroup_cpu_max': cgroup_cpu_limit,
        'cgroup_memory_max': cgroup_memory_limit,
        'cgroup_limit_fields_complete': cgroup_limit_fields_complete,
        'available_cpu_capacity_cores': cpu_capacity,
        'host_cpu_capacity_cores': host_cpu_capacity,
        'cgroup_cpu_quota_capacity_cores': cpu_quota_capacity,
        'maximum_observed_cpu_core_equivalent': max_cpu_cores,
        'cpu_core_equivalent_summary': cpu_summary,
        'available_memory_capacity_bytes': memory_capacity,
        'host_memory_capacity_bytes': host_memory_capacity,
        'cgroup_memory_capacity_bytes': memory_cgroup_capacity,
        'maximum_observed_cgroup_memory_peak_bytes': max_memory_peak,
        'memory_peak_summary_bytes': memory_summary,
        'rtf_sim_over_wall_summary': rtf_summary,
        'cgroup_cpu_unthrottled': cgroup_unthrottled,
        'cgroup_cpu_throttled_usec_delta': throttle_delta_usec,
        'cgroup_oom_count_zero': no_oom,
        'cgroup_oom_event_delta_by_kind': oom_delta_by_kind,
        'maximum_observed_pids': max_pids,
        'mapping_queue': {
            'identity_matches': map_identity_ok,
            'configured_pending_depth_capacity': map_depth_limit,
            'pending_depth_high_water': map_depth_highwater,
            'maximum_pending_depth': map_pending_max,
            'depth_drop_count': map_depth_drops,
            'keyframe_drop_count': map_keyframe_drops,
            'drops_are_reported_not_independently_failed': True,
        },
        'vins_queue_capacity': None,
        'vins_queue_capacity_status': 'UNKNOWN_BY_SOURCE',
        'vins_queue_telemetry_rows': len(queue_rows),
        'vins_queue_telemetry_hash_matches': queue_file_matches,
        'vins_queue_rows_complete': queue_rows_complete,
        'vins_queue_source_and_receipt_stamps_monotonic': (
            queue_stamps_monotonic and queue_receipts_monotonic),
        'vins_queue_observer_errors': queue_observation.get('errors'),
        'queue_source_identity_matches': queue_source_identity_complete,
        'queue_source_hash_mismatches': queue_source_mismatches,
        'vins_current_queue_depth_stats': current_queue_stats,
        'vins_max_positive_current_depth_slope_items_per_sim_s': max_positive_queue_slope,
        'unbounded_vins_queue_not_misrepresented_as_capped': queue_capacity_unknown,
        'formal_600_sim_second_duration_remains_n16': criteria.get(
            'formal_n16_duration_sim_s'),
        'comparisons': comparisons,
    })
    if throttle_violation or oom_violation:
        entry.update({'status': 'FAIL', 'direct_safety_failure': True,
                      'reason': 'cgroup throttling or an OOM event increased during this run'})
    elif not identity_matches or not platform_identity_ok or not platform_binding_matches:
        entry['reason'] = 'resource limits are not bound to this runtime and platform capacity'
    elif resource.get('safe_session_terminal_observed') is not True:
        entry['reason'] = 'resource observer did not cover verified safe session closeout'
    elif (not sample_fields_complete or not cgroup_limit_fields_complete
          or not throttle_counter_monotonic or not oom_counter_monotonic
          or not queue_file_matches or not queue_identity_ok):
        entry['reason'] = 'resource or VINS queue telemetry is incomplete or mismatched'
    elif not map_identity_ok or not queue_capacity_unknown:
        entry['reason'] = 'mapping or unbounded VINS queue observation lacks correct identity semantics'
    else:
        outcome = gate('resource_and_queue_behavior', comparisons,
                       criteria['evidence_status'])
        if outcome['status'] == 'PASS' and checks_complete:
            entry['status'] = 'PASS'
            entry['reason'] = (
                'observed calibration load remained within captured platform/cgroup capacity; '
                'bounded mapping queue stayed within its configured capacity; VINS queue capacity remains explicitly unknown')
        elif outcome['status'] == 'FAIL':
            entry.update({'status': 'FAIL', 'direct_safety_failure': True,
                          'reason': 'observed resource capacity, queue-depth, or sampling criterion was exceeded'})
        else:
            entry['reason'] = 'one or more required capacity or queue measurements are missing'
    if native_work is not None:
        if native_work['status'] == 'FAIL':
            entry.update(status='FAIL',direct_safety_failure=True,reason='native pending work or source-time budget exceeded')
        elif native_work['status'] != 'PASS' and entry['status'] != 'FAIL':
            entry.update(status='INSUFFICIENT',reason='native pending-work evidence is missing or incomplete')
    return entry


def observer_identity_binding_result(config, run_dir):
    """Check shared run/goal/epoch/map/runtime identity across N10 observers."""
    metric_id = 'observer_identity_binding'
    expected = read_run_identity(run_dir)
    policy = config['metrics'][metric_id]
    required_files = tuple(policy.get('required_reports', ()))
    optional_files = tuple(policy.get('optional_reports', ()))
    missing = [name for name in required_files if not (run_dir / name).is_file()]
    missing_optional = [name for name in optional_files if not (run_dir / name).is_file()]
    identities = {}
    mismatches = {}
    optional_mismatches = {}
    expected_tuple = tuple(expected.get(key, '') for key in (
        'run_id', 'runtime_contract_sha256', 'goal_id', 'epoch', 'map_id'))
    for name in required_files + optional_files:
        is_optional = name in optional_files
        destination = optional_mismatches if is_optional else mismatches
        path = run_dir / name
        if not path.is_file():
            continue
        try:
            report = json.loads(path.read_text())
        except (OSError, ValueError):
            destination[name] = 'unreadable_report'
            continue
        identity = report.get('run_identity')
        if (not isinstance(identity, dict)
                and name == 'n10-live-obstacle-observation.json'):
            identity = {
                'run_id': report.get('run_id', ''),
                'runtime_contract_sha256': report.get(
                    'runtime_contract_baseline_sha256', ''),
                'goal_id': report.get('goal_id', ''),
                'epoch': report.get('epoch', ''),
                'map_id': report.get('map_id_at_goal', ''),
                'complete': all(report.get(key) for key in (
                    'run_id', 'runtime_contract_baseline_sha256', 'goal_id',
                    'epoch', 'map_id_at_goal')),
            }
        if not isinstance(identity, dict):
            destination[name] = 'run_identity_missing'
            continue
        identities[name] = identity
        candidate = tuple(identity.get(key, '') for key in (
            'run_id', 'runtime_contract_sha256', 'goal_id', 'epoch', 'map_id'))
        if identity.get('complete') is not True:
            destination[name] = 'run_identity_incomplete'
        elif candidate != expected_tuple:
            destination[name] = 'identity_tuple_differs_from_run'
        if name == 'n10-sensor-capture-evaluation.json' and report.get('status') != 'PASS':
            destination[name] = 'sensor_payload_or_receipt_coverage_not_pass'
    status = ('PASS' if not missing and not mismatches and expected.get('complete')
              else 'INSUFFICIENT')
    return {
        'id': metric_id,
        'status': status,
        'evidence_status': config['metrics'][metric_id]['evidence_status'],
        'run_identity': expected,
        'observer_files': list(required_files),
        'optional_observer_files': list(optional_files),
        'observer_identities': identities,
        'missing_observer_reports': missing,
        'missing_optional_observer_reports': missing_optional,
        'identity_mismatches': mismatches,
        'optional_identity_mismatches': optional_mismatches,
        'observer_report_sha256': {
            name: sha256(run_dir / name) for name in required_files + optional_files
            if (run_dir / name).is_file()},
        'runtime_control_effect': False,
    }


def evaluate_run(config, run_metrics, run_dir, tracking_clearance_report=None,
                 snapshot_report_path=None, dynamic_replan_report=None,
                 platform_capacity_report=None):
    policy_config = config
    functional_navigation = config.get('normal_navigation_policy') == 'functional_navigation_v1'
    if functional_navigation:
        from tools.n13_navigation_policy import calculation_config
        config = calculation_config(config)
    def read_evidence(path):
        try:
            value = json.loads(path.read_text())
            if functional_navigation and not isinstance(value, dict):
                return {}
            return value
        except (OSError, ValueError):
            if functional_navigation:
                return {}
            raise
    criteria = config['metrics']
    result = []
    arrival = run_metrics.get('arrival') or {}
    arrival_window = arrival.get('longest_joint_tolerance_window') or {}
    arrival_thresholds = criteria['arrival_position_yaw_dwell']['thresholds']
    arrival_numeric = gate('arrival_position_yaw_dwell', [
        compare('joint_dwell_sim_s', arrival_window.get('duration_sim_s'),
                arrival_thresholds.get('continuous_dwell_min_sim_s'), '>=', 'sim_s'),
        compare('max_truth_source_gap_sim_s', arrival.get('max_truth_sample_gap_sim_s'),
                arrival_thresholds.get('maximum_truth_source_gap_sim_s'), '<=', 'sim_s'),
    ], criteria['arrival_position_yaw_dwell']['evidence_status'])
    independent_status = arrival.get('independent_goal_dwell_status')
    if independent_status == 'FAIL':
        arrival_numeric['status'] = 'FAIL'
    elif independent_status != 'PASS' and arrival_numeric['status'] == 'PASS':
        arrival_numeric['status'] = 'INSUFFICIENT'
        arrival_numeric['reason'] = 'independent arrival evaluator did not explicitly report PASS'
    result.append(arrival_numeric)

    segments = run_metrics.get('segments') or {}
    pose_thresholds = criteria['raw_vio_absolute_error']['thresholds']
    pose_segment_names = {
        'goal_motion': 'goal_motion_and_arrival_dwell',
        'active_hold': 'requested_active_hold',
        'landing': 'hold_end_to_landed',
        'full_task': 'prestream_to_landed',
    }
    pose_comparisons = []
    unsupported_pose_segments = []
    for label, segment_name in pose_segment_names.items():
        pose_segment = segments.get(segment_name) or {}
        pose = pose_segment.get('absolute_position_yaw_error') or {}
        if pose.get('supported') is not True or int(pose.get('sample_count') or 0) <= 0:
            unsupported_pose_segments.append(label)
        prefix = label + '_'
        pose_comparisons.extend([
            compare(prefix + 'position_p95_m', (pose.get('position_error_m') or {}).get('p95'),
                    pose_thresholds['position_p95_max_m'], '<=', 'm'),
            compare(prefix + 'position_sample_max_m', (pose.get('position_error_m') or {}).get('max'),
                    pose_thresholds['position_sample_max_m'], '<=', 'm'),
            compare(prefix + 'absolute_yaw_p95_deg', (pose.get('absolute_yaw_error_deg') or {}).get('p95'),
                    pose_thresholds['absolute_yaw_p95_max_deg'], '<=', 'deg'),
            compare(prefix + 'absolute_yaw_sample_max_deg', (pose.get('absolute_yaw_error_deg') or {}).get('max'),
                    pose_thresholds['absolute_yaw_sample_max_deg'], '<=', 'deg'),
        ])
    pose_result = gate('raw_vio_absolute_error', pose_comparisons,
                       criteria['raw_vio_absolute_error']['evidence_status'])
    if unsupported_pose_segments and pose_result['status'] == 'PASS':
        pose_result['status'] = 'INSUFFICIENT'
    pose_result['unsupported_segments'] = unsupported_pose_segments
    result.append(pose_result)

    rpe_thresholds = criteria['raw_vio_rpe_10s']['thresholds']
    rpe_config = criteria['raw_vio_rpe_10s']
    rpe_comparisons = []
    rpe_translation_measurements = []
    rpe_segment_status = {}
    for label, segment_name in rpe_config.get('required_comparison_segments', {}).items():
        segment = segments.get(segment_name) or {}
        rpe = (segment.get('relative_pose_error') or {}).get('10s') or {}
        supported = rpe.get('supported') is True and int(rpe.get('supported_pairs') or 0) > 0
        rpe_segment_status[label] = {
            'source_segment': segment_name,
            'status': 'OBSERVED' if supported else 'INSUFFICIENT',
            'supported_pairs': int(rpe.get('supported_pairs') or 0),
        }
        translation = finite_number((rpe.get('translation_error_m') or {}).get('p95'))
        rpe_translation_measurements.append({
            'metric': label + '_translation_p95_m', 'value': translation, 'unit': 'm',
            'status': 'OBSERVED' if supported and translation is not None else 'INSUFFICIENT',
        })
        if 'translation_p95_max_m' in rpe_thresholds:
            rpe_comparisons.append(compare(label + '_translation_p95_m', translation,
                                           rpe_thresholds['translation_p95_max_m'], '<=', 'm'))
        rpe_comparisons.append(compare(label + '_rotation_p95_deg',
                                       (rpe.get('rotation_error_deg') or {}).get('p95'),
                                       rpe_thresholds['rotation_p95_max_deg'], '<=', 'deg'))
    rpe_result = gate('raw_vio_rpe_10s', rpe_comparisons,
                      criteria['raw_vio_rpe_10s']['evidence_status'])
    rpe_result['translation_measurements'] = rpe_translation_measurements
    rpe_result['translation_numeric_limit_enabled'] = 'translation_p95_max_m' in rpe_thresholds
    if (rpe_result['status'] == 'PASS'
            and any(row['status'] != 'OBSERVED' for row in rpe_translation_measurements)):
        rpe_result['status'] = 'INSUFFICIENT'
        rpe_result['reason'] = 'required RPE measurements or source-window support missing'
    for label, segment_name in rpe_config.get('diagnostic_segments', {}).items():
        segment = segments.get(segment_name) or {}
        rpe = (segment.get('relative_pose_error') or {}).get('10s') or {}
        rpe_segment_status[label] = {
            'source_segment': segment_name,
            'status': ('OBSERVED' if rpe.get('supported') is True
                       and int(rpe.get('supported_pairs') or 0) > 0 else 'INSUFFICIENT'),
            'supported_pairs': int(rpe.get('supported_pairs') or 0),
        }
    rpe_result['segment_coverage'] = rpe_segment_status
    rpe_result['full_task_rpe_is_diagnostic_only'] = True
    result.append(rpe_result)

    full = segments.get('prestream_to_landed') or {}
    goal = segments.get('goal_motion_and_arrival_dwell') or {}
    hold = segments.get('requested_active_hold') or {}
    velocity_thresholds = criteria['raw_vio_velocity_error']['thresholds']
    goal_velocity = (goal.get('raw_velocity_error') or {}).get('velocity_error_norm_m_s') or {}
    hold_velocity = (hold.get('raw_velocity_error') or {}).get('velocity_error_norm_m_s') or {}
    velocity_result = gate('raw_vio_velocity_error', [
        compare('goal_motion_p95_m_s', goal_velocity.get('p95'),
                velocity_thresholds['goal_motion_p95_max_m_s'], '<=', 'm/s'),
        compare('goal_motion_sample_max_m_s', goal_velocity.get('max'),
                velocity_thresholds['goal_motion_sample_max_m_s'], '<=', 'm/s'),
        compare('active_hold_p95_m_s', hold_velocity.get('p95'),
                velocity_thresholds['active_hold_p95_max_m_s'], '<=', 'm/s'),
        compare('active_hold_sample_max_m_s', hold_velocity.get('max'),
                velocity_thresholds['active_hold_sample_max_m_s'], '<=', 'm/s'),
    ], criteria['raw_vio_velocity_error']['evidence_status'])
    if ((goal.get('raw_velocity_error') or {}).get('supported') is not True
            or (hold.get('raw_velocity_error') or {}).get('supported') is not True):
        if velocity_result['status'] == 'PASS':
            velocity_result['status'] = 'INSUFFICIENT'
        velocity_result['reason'] = 'goal or active-hold raw VINS velocity support is incomplete'
    result.append(velocity_result)

    age_thresholds = criteria['map_source_and_update_age']['thresholds']
    ages = full.get('map_and_source_timing') or {}
    source_age = ages.get('source_age_sim_s') or {}
    update_age = ages.get('occupancy_update_age_sim_s') or {}
    age_result = gate('map_source_and_update_age', [
        compare('offline_source_age_sample_max_sim_s', source_age.get('max'),
                age_thresholds['offline_source_age_sample_max_sim_s'], '<=', 'sim_s'),
        compare('offline_occupancy_update_age_sample_max_sim_s', update_age.get('max'),
                age_thresholds['offline_occupancy_update_age_sample_max_sim_s'], '<=', 'sim_s'),
    ], criteria['map_source_and_update_age']['evidence_status'])
    age_result['runtime_gate_added'] = False
    result.append(age_result)

    tracking = (goal.get('ego_tracking_error') or {}).get('position_error_m') or {}
    tracking_candidate = criteria['ego_tracking_error'].get('diagnostic_candidate') or {}
    tracking_checks = [
        compare('tracking_p95_m', tracking.get('p95'),
                tracking_candidate.get('position_p95_max_m'), '<=', 'm'),
        compare('tracking_sample_max_m', tracking.get('max'),
                tracking_candidate.get('position_sample_max_m'), '<=', 'm'),
    ]
    tracking_failures = [item['metric'] for item in tracking_checks
                         if item['value'] is not None and item['threshold'] is not None
                         and item['value'] > item['threshold']]
    tracking_clearance_result = tracking_clearance_budget_result(
        config, run_metrics, run_dir, tracking_clearance_report)
    result.append({
        'id': 'ego_tracking_error',
        'status': tracking_clearance_result['status'],
        'evidence_status': criteria['ego_tracking_error']['evidence_status'],
        'acceptance_thresholds': criteria['ego_tracking_error'].get(
            'acceptance_thresholds'),
        'diagnostic_candidate_comparisons': tracking_checks,
        'diagnostic_candidate_breaches': tracking_failures,
        'scalar_candidate_values_are_diagnostic_only': True,
        'scene_geometry_result': tracking_clearance_result.get('comparisons'),
        'reason': tracking_clearance_result.get('reason'),
    })
    result.append(tracking_clearance_result)

    clearance_path = run_dir / 'n10-clearance-evaluation.json'
    partial_clearance_paths = [
        run_dir / 'n10-action-physics-step-clearance-diagnostic.json',
        run_dir / 'n10-partial-hold-physics-step-clearance-diagnostic.json',
    ]
    contact_path = run_dir / 'vehicle-contact-evaluation.json'
    partial_contact_path = run_dir / 'n10-contact-evaluation-partial.json'
    clearance_result = {'id': 'full_body_clearance_and_contact',
                        'status': 'INSUFFICIENT',
                        'evidence_status': criteria['full_body_clearance_and_contact']['evidence_status']}
    clearance = (read_evidence(clearance_path)
                 if clearance_path.is_file() else None)
    interval_clearance_path = run_dir / 'n10-interval-clearance-bound.json'
    interval_clearance_report = (
        read_evidence(interval_clearance_path)
        if interval_clearance_path.is_file() else None)
    component_clearance_report = (
        interval_clearance_report
        if (interval_clearance_report or {}).get('schema')
        == 'n10-model-bounded-interval-clearance/v3' else None)
    clearance_for_acceptance = clearance
    if component_clearance_report is not None:
        solver_state = component_clearance_report.get('solver_state_clearance') or {}
        flight_interval = component_clearance_report.get('flight_interval') or {}
        clearance_for_acceptance = {
            'physics_step_sample_coverage': {
                'all_received_pose_gaps_within_one_physics_step': (
                    flight_interval.get('every_solver_step_present') is True
                    and finite_number(flight_interval.get('maximum_observed_step_gap_s'))
                    is not None
                    and finite_number(flight_interval.get('step_s')) is not None
                    and abs(finite_number(flight_interval.get('maximum_observed_step_gap_s'))
                            - finite_number(flight_interval.get('step_s'))) <= 2e-9),
                'every_consecutive_physics_state_captured': (
                    solver_state.get('all_solver_states_have_clearance') is True
                    and solver_state.get('clearance_sample_count')
                    == flight_interval.get('solver_state_count')),
                'minimum_clearance_at_all_received_states_m': solver_state.get(
                    'minimum_component_clearance_m'),
            },
            'interval': {
                'truth_max_source_gap_sim_s': flight_interval.get(
                    'maximum_observed_step_gap_s'),
            },
        }
    contact = (read_evidence(contact_path)
               if contact_path.is_file() else None)
    partial_contact = (read_evidence(partial_contact_path)
                       if partial_contact_path.is_file() else None)
    contact_record = contact or partial_contact
    contact_result = ((contact_record or {}).get('result') or contact_record or {})
    prohibited = finite_number(contact_result.get('prohibited_contact_event_count'))
    contact_topics_ready = contact_result.get('sensor_topics_ready') is True
    contact_observation_valid = contact_topics_ready and prohibited is not None
    prohibited_limit = criteria['full_body_clearance_and_contact']['thresholds'][
        'prohibited_contact_count_max']
    prohibited_contact_breach = (
        contact_observation_valid and prohibited > prohibited_limit)

    clearance_observations = []
    if clearance_for_acceptance is not None:
        coverage = clearance_for_acceptance.get('physics_step_sample_coverage') or {}
        # The clearance evaluator's v2 schema records the minimum at received
        # solver states. Accept the earlier alias too so offline replays do not
        # turn a field-name difference into missing evidence.
        clearance_value = finite_number(coverage.get(
            'minimum_clearance_at_all_received_states_m'))
        if clearance_value is None:
            clearance_value = finite_number(coverage.get(
                'minimum_clearance_at_received_states_m'))
        if clearance_value is not None:
            clearance_observations.append({
                'source': (interval_clearance_path.name
                           if component_clearance_report is not None
                           else clearance_path.name),
                'minimum_received_state_clearance_m': clearance_value,
                'geometry': ('per SDF collision-component circumscribed spheres'
                             if component_clearance_report is not None
                             else 'legacy whole-vehicle cylinder'),
                'every_consecutive_physics_state_captured': (
                    coverage.get('every_consecutive_physics_state_captured') is True),
            })
    for path in partial_clearance_paths:
        if not path.is_file():
            continue
        report = read_evidence(path)
        minimum = finite_number(
            (report.get('minimum_received_state') or {}).get('clearance_m'))
        if minimum is None:
            minimum = finite_number(
                (report.get('clearance') or {}).get('minimum_clearance_m'))
        if minimum is not None:
            coverage = report.get('physics_step_coverage') or {}
            clearance_observations.append({
                'source': path.name,
                'minimum_received_state_clearance_m': minimum,
                'every_consecutive_physics_state_captured': (
                    coverage.get('every_consecutive_physics_state_captured') is True),
            })

    if clearance_for_acceptance is not None and contact is not None:
        coverage = clearance_for_acceptance.get('physics_step_sample_coverage') or {}
        clearance_value = finite_number(
            coverage.get('minimum_clearance_at_all_received_states_m'))
        if clearance_value is None:
            clearance_value = finite_number(
                coverage.get('minimum_clearance_at_received_states_m'))
        gap = finite_number(clearance_for_acceptance.get('interval', {}).get(
            'truth_max_source_gap_sim_s'))
        if (coverage.get('all_received_pose_gaps_within_one_physics_step') is True
                and coverage.get('every_consecutive_physics_state_captured') is True
                and clearance_value is not None and gap is not None
                and contact_observation_valid):
            thresholds = criteria['full_body_clearance_and_contact']['thresholds']
            clearance_result['comparisons'] = [
                *([compare('minimum_full_body_clearance_m', clearance_value,
                        thresholds['minimum_full_body_clearance_m'], '>=', 'm')]
                  if 'minimum_full_body_clearance_m' in thresholds else []),
                compare('truth_max_source_gap_sim_s', gap,
                        thresholds['maximum_truth_gap_sim_s'], '<=', 'sim_s'),
                compare('prohibited_contact_event_count', prohibited,
                        prohibited_limit, '<=', 'events'),
            ]
            clearance_result['status'] = gate(
                'full_body_clearance_and_contact',
                clearance_result['comparisons'],
                clearance_result['evidence_status'])['status']
            clearance_result['minimum_received_state_clearance_m'] = clearance_value
            clearance_result['clearance_numeric_limit_enabled'] = 'minimum_full_body_clearance_m' in thresholds
            clearance_result['clearance_measurement_status'] = 'OBSERVED'
            clearance_result['contact_observation_complete'] = contact_observation_valid
            clearance_result['classification'] = (
                ('discrete Gazebo solver-state per-component collision-sphere clearance '
                 'plus contact record; interval bound is checked separately'
                 if component_clearance_report is not None else
                 'discrete legacy vehicle-envelope clearance plus contact record; '
                 'not a continuous-time or real-aircraft bound'))
            clearance_result['observed_prohibited_contact_event_count'] = prohibited
            if component_clearance_report is not None:
                clearance_result['clearance_geometry'] = (
                    'per-SDF-collision-component circumscribed spheres')
                clearance_result['legacy_clearance_report_is_diagnostic_only'] = True
                clearance_result['interval_report_sha256'] = sha256(interval_clearance_path)
            if prohibited_contact_breach:
                clearance_result['direct_safety_failure'] = True
    else:
        clearance_result['reason'] = (
            'complete mission-wide physics-step and contact coverage are required for PASS')
        clearance_result['partial_clearance_observations'] = clearance_observations
        clearance_result['contact_observation_complete'] = contact_observation_valid
        clearance_result['observed_prohibited_contact_event_count'] = prohibited
        if prohibited_contact_breach:
            clearance_result['status'] = 'FAIL'
            clearance_result['direct_safety_failure'] = True
            clearance_result['reason'] = 'observed prohibited vehicle contact'
        else:
            threshold = criteria['full_body_clearance_and_contact']['thresholds'].get(
                'minimum_full_body_clearance_m')
            if threshold is not None and any(row['minimum_received_state_clearance_m'] < threshold
                   for row in clearance_observations):
                clearance_result['status'] = 'FAIL'
                clearance_result['reason'] = (
                    'observed partial-interval body clearance below the configured candidate')
    interval_evidence = continuous_clearance_evidence(run_dir,
        criteria['full_body_clearance_and_contact']['thresholds'].get('minimum_full_body_clearance_m'))
    clearance_result['continuous_interval_evidence'] = interval_evidence
    if clearance_result['status'] == 'PASS':
        clearance_result['status'] = interval_evidence['status']
        clearance_result['classification'] = (
            'solver-state and identity-bound no-contact interval clearance; '
            'allowed skid-contact phase separately evaluated')
    result.append(clearance_result)

    snapshot_path = (Path(snapshot_report_path) if snapshot_report_path else
                     run_dir / 'n10-box-map-snapshot-analysis.json')
    snapshot_result = {'id': 'raw_map_surface_geometry',
                       'status': 'INSUFFICIENT',
                       'evidence_status': criteria['raw_map_surface_geometry']['evidence_status']}
    if snapshot_path.is_file():
        snapshot = read_evidence(snapshot_path)
        source_coverage = snapshot.get('snapshot_source_coverage') or {}
        source_covered = source_coverage.get('covered') is True
        if snapshot.get('snapshot_matches_live_observer_epoch_map_frame') is True:
            faces = (snapshot.get('snapshot_roi') or {}).get(
                'surface_face_samples', {})
            observed_faces = {
                face: finite_number(row.get('surface_center_error_max_m'))
                for face, row in faces.items()
                if int(row.get('surface_center_error_sample_count') or 0) > 0
                and finite_number(row.get('surface_center_error_max_m')) is not None
            }
            observed = list(observed_faces.values())
            required_faces = {'x_negative', 'x_positive', 'y_negative',
                              'y_positive', 'z_negative', 'z_positive'}
            point_queries = snapshot.get('point_query_archive') or {}
            if observed:
                from tools.map_surface_policy import surface_error_result
                policy = surface_error_result(observed, criteria['raw_map_surface_geometry']['thresholds'])
                snapshot_result = {'id': 'raw_map_surface_geometry', **policy,
                    'evidence_status': criteria['raw_map_surface_geometry']['evidence_status']}
                snapshot_result.update({
                    'evaluation_scope': 'occupied surface cells on observed faces only',
                    'observed_faces': sorted(observed_faces),
                    'unobserved_faces': sorted(required_faces - set(observed_faces)),
                    'per_face_surface_center_error_max_m': observed_faces,
                    'point_query_capture': point_queries or None,
                    'point_queries_are_optional_diagnostics': True,
                    'array_source': 'one identity-bound raw/inflated occupancy snapshot',
                })
            else:
                snapshot_result.update({
                    'reason': 'no occupied surface voxels were supported on any measured face',
                    'observed_faces': [],
                    'unobserved_faces': sorted(required_faces),
                    'point_query_capture': point_queries or None,
                    'point_queries_are_optional_diagnostics': True,
                })
        else:
            snapshot_result['reason'] = 'snapshot does not match the live observer identity'
        snapshot_result['snapshot_source_coverage'] = source_coverage or None
        if snapshot_result.get('status') == 'PASS' and not source_covered:
            snapshot_result['status'] = 'INSUFFICIENT'
            snapshot_result['reason'] = (
                'snapshot source timestamp does not cover the latest recorded positive obstacle-ROI cloud')
    result.append(snapshot_result)

    classification = {'id': 'raw_map_classification', 'status': 'INSUFFICIENT',
                      'evidence_status': criteria['raw_map_classification']['evidence_status'],
                      'reason': 'identity-bound occupancy class counts are not present'}
    if snapshot_path.is_file():
        snapshot = read_evidence(snapshot_path)
        source_coverage = snapshot.get('snapshot_source_coverage') or {}
        source_covered = source_coverage.get('covered') is True
        counts = ((snapshot.get('snapshot_roi') or {})
                  .get('inside_box_voxel_counts_by_raw_class') or {})
        truth_occluded_free = (snapshot.get('snapshot_roi') or {}).get(
            'truth_occluded_known_free_voxel_count')
        cell_geometry = (snapshot.get('snapshot_roi') or {}).get(
            'voxel_cell_geometry') or {}
        contained_by_class = cell_geometry.get(
            'all_corners_inside_box_counts_by_raw_class') or {}
        if (snapshot.get('snapshot_matches_live_observer_epoch_map_frame') is True
                and all(key in counts for key in ('unknown', 'known_free', 'raw_occupied'))):
            threshold = criteria['raw_map_classification']['thresholds'][
                'truth_occluded_raw_free_count_max']
            classification['class_counts'] = counts
            classification['known_free_voxels_inside_box_observed'] = counts.get('known_free')
            cell_geometry = (snapshot.get('snapshot_roi') or {}).get(
                'voxel_cell_geometry') or {}
            contained = cell_geometry.get(
                'all_corners_inside_box_counts_by_raw_class') or {}
            boundary = cell_geometry.get(
                'center_inside_but_cell_not_fully_contained_counts_by_raw_class') or {}
            if 'known_free' in contained and 'known_free' in boundary:
                classification['known_free_voxel_geometry'] = {
                    'center_inside_count': counts.get('known_free'),
                    'fully_contained_cell_count': contained['known_free'],
                    'center_inside_not_fully_contained_cell_count': boundary['known_free'],
                    'qualification': cell_geometry.get('qualification'),
                }
            if truth_occluded_free is None:
                if 'known_free' in contained_by_class:
                    truth_occluded_free = contained_by_class['known_free']
                    classification = gate('raw_map_classification', [
                        compare('truth_occluded_known_free_voxel_count',
                                truth_occluded_free, threshold, '<=', 'voxels')],
                        criteria['raw_map_classification']['evidence_status'])
                    classification['class_counts'] = counts
                    classification['known_free_voxels_inside_box_observed'] = counts.get('known_free')
                    classification['truth_occluded_known_free_voxel_count'] = truth_occluded_free
                    classification['truth_occluded_count_method'] = (
                        'count known-free cells only when all eight transformed voxel corners lie inside the solid truth box')
                    classification['voxel_geometry_qualification'] = cell_geometry.get(
                        'qualification')
                else:
                    classification['reason'] = (
                        'total known-free voxel count is present, but fully contained and surface-intersecting cells are not distinguished')
            else:
                classification = gate('raw_map_classification', [
                    compare('truth_occluded_known_free_voxel_count', truth_occluded_free,
                            threshold, '<=', 'voxels')],
                    criteria['raw_map_classification']['evidence_status'])
                classification['class_counts'] = counts
                classification['known_free_voxels_inside_box_observed'] = counts.get('known_free')
                classification['truth_occluded_known_free_voxel_count'] = truth_occluded_free
        classification['snapshot_source_coverage'] = source_coverage or None
        if classification.get('status') == 'PASS' and not source_covered:
            classification['status'] = 'INSUFFICIENT'
            classification['reason'] = (
                'snapshot source timestamp does not cover the latest recorded positive obstacle-ROI cloud')
        elif classification.get('status') == 'FAIL' and not source_covered:
            classification['temporal_source_coverage_warning'] = (
                'The recorded snapshot violates the candidate threshold, but its source timestamp does not cover the latest recorded positive obstacle-ROI cloud.')
    result.append(classification)

    for metric_id in ('dynamic_replanning', 'fault_exit_to_terminal_px4_state',
                      'resource_and_queue_behavior'):
        entry = {'id': metric_id, 'status': 'INSUFFICIENT',
                 'evidence_status': criteria[metric_id]['evidence_status'],
                 'reason': 'calibration inputs or a frozen numeric basis are not yet present'}
        if metric_id == 'dynamic_replanning':
            entry = dynamic_replanning_result(
                config, run_metrics, run_dir, dynamic_replan_report,
                tracking_clearance_report, tracking_clearance_result,
                clearance_result)
        elif metric_id == 'resource_and_queue_behavior':
            entry = resource_and_queue_behavior_result(
                config, run_metrics, run_dir, platform_capacity_report)
        elif metric_id == 'fault_exit_to_terminal_px4_state':
            readback_path = run_dir / 'postflight-px4-bridge-readback.json'
            readback = (read_evidence(readback_path)
                        if readback_path.is_file() else {})
            emergency_path = run_dir / 'emergency-disarm-safe-terminal.json'
            emergency_record = (read_evidence(emergency_path)
                                if emergency_path.is_file() else None)
            latest = readback.get('latest') or {}
            bridge = latest.get('bridge') or {}
            px4 = latest.get('px4_status') or {}
            reason = str(bridge.get('reason') or readback.get('reason') or '')
            fault_observed = (
                'planner_fault:' in reason
                or 'fault' in reason.lower()
                or bool((readback.get('fault_events') or [])))
            terminal_summary = summarize_terminal_readback(
                readback, emergency_record)
            terminal_reached = terminal_summary[
                'native_terminal_evidence_complete']
            entry.update({
                'observed_fault_reason': reason or None,
                'observed_bridge_terminal': {
                    'phase': bridge.get('phase'),
                    'landed': bridge.get('landed'),
                    'armed': bridge.get('armed'),
                    'control_enabled': bridge.get('control_enabled'),
                    'px4_failsafe': (px4.get('failsafe')
                                     if isinstance(px4, dict) else None),
                    'px4_nav_state': (px4.get('nav_state')
                                      if isinstance(px4, dict) else None),
                },
                'fault_observed': fault_observed,
                'required_terminal_readback_complete': terminal_reached,
                'terminal_readback': terminal_summary,
            })
            if fault_observed and terminal_summary['emergency_closeout_used']:
                entry['status'] = 'FAIL'
                entry['direct_safety_failure'] = True
                entry['reason'] = (
                    'terminal state followed an authorized emergency disarm; '
                    'this does not qualify the native fault landing path')
            elif fault_observed and terminal_summary['observed_state_failures']:
                entry['status'] = 'FAIL'
                entry['direct_safety_failure'] = True
                entry['reason'] = (
                    'observed fault ended with an unsafe independent PX4/bridge state')
            elif fault_observed and terminal_summary['post_terminal_failures']:
                entry['status'] = 'FAIL'
                entry['direct_safety_failure'] = True
                entry['reason'] = (
                    'control or an old goal/trajectory remained active after terminal readback')
            elif fault_observed and terminal_summary['missing_evidence']:
                entry['reason'] = (
                    'fault observed, but terminal readback is incomplete: '
                    + ', '.join(terminal_summary['missing_evidence']))
        result.append(entry)

    result.append(observer_identity_binding_result(config, run_dir))
    if functional_navigation:
        from tools.n13_navigation_policy import project_results
        result = project_results(policy_config, result, run_dir)
    return summarize_required_metrics(policy_config, result)


def truth_reference_evidence(run_metrics, run_dir, tracking_clearance_report=None,
                             functional_navigation=False):
    """Prevent mixed old/new numeric reports from being accepted offline."""
    from truth_reference import model_to_imu_contract, require_same_truth_reference
    try:
        contract = model_to_imu_contract(run_dir)
        require_same_truth_reference(run_metrics, contract)
    except (OSError, ValueError, KeyError) as exc:
        return {'status': 'INSUFFICIENT', 'reason': str(exc)}
    mismatches = {}
    report_names = ('arrival-evaluation-simtime-v2.json', 'odometry-evaluation.json',
                    'n10-vins-velocity-evaluation.json', 'n10-tracking-clearance-relation.json',
                    'n10-clearance-evaluation.json', 'n10-interval-clearance-bound.json')
    if functional_navigation:
        report_names = ('arrival-evaluation-simtime-v2.json',)
    for name in report_names:
        try:
            if name == 'n10-tracking-clearance-relation.json' and tracking_clearance_report is not None:
                report = tracking_clearance_report
            else:
                report = json.loads((Path(run_dir) / name).read_text())
            require_same_truth_reference(report, contract)
        except (OSError, ValueError, KeyError) as exc:
            mismatches[name] = str(exc)
    return {'status': 'PASS' if not mismatches else 'INSUFFICIENT',
            'contract': contract, 'report_mismatches': mismatches}


def evaluate(config_path, calibration_path, run_dir, run_id,
             tracking_clearance_path=None, snapshot_report_path=None,
             snapshot_pair_path=None, dynamic_replan_path=None,
             platform_capacity_path=None):
    config_path = Path(config_path).resolve()
    calibration_path = Path(calibration_path).resolve()
    run_dir = Path(run_dir).resolve()
    config = json.loads(config_path.read_text())
    calibration = json.loads(calibration_path.read_text())
    if config.get('schema') != 'uav-n10-acceptance/v1':
        raise ValueError('unsupported N10 acceptance configuration schema')
    if calibration.get('schema') != 'n10-cross-run-calibration-pair/v1':
        raise ValueError('unsupported cross-run calibration schema')
    matches = [row for row in calibration.get('runs', []) if row.get('run_id') == run_id]
    if len(matches) != 1:
        raise ValueError(f'expected exactly one calibrated run record for {run_id}')
    run_metrics = matches[0]
    functional_navigation = config.get('normal_navigation_policy') == 'functional_navigation_v1'
    identity = identity_evidence(run_id, run_metrics, run_dir, functional_navigation)
    identity_match = (identity['runtime_contract_matches_calibration_record']
                      and identity['goal_epoch_map_identity_is_bound'])
    hash_metrics = run_metrics
    diagnostic_source_hashes = None
    if functional_navigation:
        diagnostic_names = set(config.get('diagnostic_input_reports', ()))
        hashes = run_metrics.get('input_sha256') or {}
        hash_metrics = {**run_metrics, 'input_sha256': {
            name: value for name, value in hashes.items() if name not in diagnostic_names}}
        diagnostic_source_hashes = archived_input_hashes({
            'input_sha256': {name: value for name, value in hashes.items()
                             if name in diagnostic_names}}, run_dir)
    source_hashes = archived_input_hashes(hash_metrics, run_dir)
    if tracking_clearance_path is None:
        candidates = (
            run_dir / 'n10-tracking-clearance-relation.json',
            run_dir / 'n10-tracking-clearance-diagnostic.json',
        )
        tracking_clearance_path = next(
            (path for path in candidates if path.is_file()), None)
    tracking_clearance_report = None
    if tracking_clearance_path is not None and Path(tracking_clearance_path).is_file():
        try:
            tracking_clearance_report = json.loads(Path(tracking_clearance_path).read_text())
        except (OSError, json.JSONDecodeError):
            tracking_clearance_report = {'load_error': 'tracking clearance JSON is unreadable'}
    reference_evidence = truth_reference_evidence(
        run_metrics, run_dir, tracking_clearance_report, functional_navigation)
    if dynamic_replan_path is None:
        candidate = run_dir / 'n10-obstacle-replan-timing-analysis.json'
        dynamic_replan_path = candidate if candidate.is_file() else None
    dynamic_replan_report = None
    if dynamic_replan_path is not None and Path(dynamic_replan_path).is_file():
        try:
            dynamic_replan_report = json.loads(Path(dynamic_replan_path).read_text())
        except (OSError, json.JSONDecodeError):
            dynamic_replan_report = {'load_error': 'event-geometry report is unreadable'}
    if platform_capacity_path is None:
        candidate = run_dir / 'n10-platform-capacity.json'
        platform_capacity_path = candidate if candidate.is_file() else None
    platform_capacity_report = None
    if platform_capacity_path is not None and Path(platform_capacity_path).is_file():
        try:
            platform_capacity_report = json.loads(Path(platform_capacity_path).read_text())
            platform_capacity_report['_file_sha256'] = sha256(
                Path(platform_capacity_path).resolve())
        except (OSError, json.JSONDecodeError):
            platform_capacity_report = {'load_error': 'platform-capacity report is unreadable'}
    evaluated = evaluate_run(
        config, run_metrics, run_dir, tracking_clearance_report,
        snapshot_report_path, dynamic_replan_report, platform_capacity_report)
    if snapshot_pair_path is None:
        candidate = run_dir / 'n10-map-snapshot-pair-analysis.json'
        snapshot_pair_path = candidate if candidate.is_file() else None
    snapshot_pair_context = {'classification': 'offline diagnostic context only',
                             'changes_acceptance_metric_status': False}
    if snapshot_pair_path is not None and Path(snapshot_pair_path).is_file():
        snapshot_pair_path = Path(snapshot_pair_path).resolve()
        try:
            pair_report = json.loads(snapshot_pair_path.read_text())
            snapshot_pair_context.update({
                'path': str(snapshot_pair_path),
                'sha256': sha256(snapshot_pair_path),
                'status': pair_report.get('status', 'INSUFFICIENT'),
                'checks': pair_report.get('checks', {}),
                'obstacle_roi': pair_report.get('obstacle_roi'),
                'depth_roi': pair_report.get('depth_roi'),
            })
        except (OSError, json.JSONDecodeError):
            snapshot_pair_context.update({
                'path': str(snapshot_pair_path), 'status': 'INSUFFICIENT',
                'load_error': 'snapshot-pair report is unreadable',
            })
    else:
        snapshot_pair_context.update({'status': 'INSUFFICIENT', 'path': None})
    if not identity_match or not source_hashes['matches'] or reference_evidence['status'] != 'PASS':
        direct_failure_preserved = any(
            row.get('status') == 'FAIL'
            and (row.get('direct_safety_failure') is True
                 or row.get('evidence_status') == 'direct_goal_contract')
            for row in evaluated['metrics'])
        evaluated['overall_status'] = (
            'FAIL' if direct_failure_preserved else 'INSUFFICIENT')
        evaluated['metrics'].append({
            'id': 'runtime_identity', 'status': 'INSUFFICIENT',
            'reason': 'runtime, goal/epoch/map identity, truth-reference provenance, or archived input hashes do not match; any independently observed direct failure is retained',
        })
    return {
        'schema': 'n10-acceptance-evaluation/v1',
        'classification': 'offline acceptance evaluation; cannot change runtime behavior or formal test counts',
        'run_id': run_id,
        'acceptance_config_status': config.get('status'),
        'acceptance_config_sha256': sha256(config_path),
        'calibration_report_sha256': sha256(calibration_path),
        'runtime_contract_sha256': run_metrics.get('runtime_contract_sha256'),
        'selected_run_input_sha256': run_metrics.get('input_sha256'),
        'diagnostic_archived_input_verification': diagnostic_source_hashes,
        'tracking_clearance_report_path': (
            str(Path(tracking_clearance_path).resolve())
            if tracking_clearance_path is not None else None),
        'tracking_clearance_report_sha256': (
            sha256(Path(tracking_clearance_path).resolve())
            if tracking_clearance_path is not None and Path(tracking_clearance_path).is_file()
            else None),
        'dynamic_replan_report_path': (
            str(Path(dynamic_replan_path).resolve())
            if dynamic_replan_path is not None else None),
        'dynamic_replan_report_sha256': (
            sha256(Path(dynamic_replan_path).resolve())
            if dynamic_replan_path is not None and Path(dynamic_replan_path).is_file()
            else None),
        'platform_capacity_report_path': (
            str(Path(platform_capacity_path).resolve())
            if platform_capacity_path is not None else None),
        'platform_capacity_report_sha256': (
            sha256(Path(platform_capacity_path).resolve())
            if platform_capacity_path is not None and Path(platform_capacity_path).is_file()
            else None),
        'snapshot_report_path': (
            str(Path(snapshot_report_path).resolve())
            if snapshot_report_path is not None else str(
                (run_dir / 'n10-box-map-snapshot-analysis.json').resolve())),
        'snapshot_report_sha256': (
            sha256(Path(snapshot_report_path).resolve())
            if snapshot_report_path is not None and Path(snapshot_report_path).is_file()
            else (sha256(run_dir / 'n10-box-map-snapshot-analysis.json')
                  if (run_dir / 'n10-box-map-snapshot-analysis.json').is_file()
                  else None)),
        'snapshot_pair_context': snapshot_pair_context,
        'truth_reference_evidence': reference_evidence,
        'runtime_identity_matches': identity_match,
        'identity_evidence': identity,
        'archived_source_hashes': source_hashes,
        'no_runtime_gate_added': True,
        **evaluated,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Path('config/acceptance.json'))
    parser.add_argument('--calibration-report', type=Path, required=True)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--tracking-clearance-report', type=Path,
                        help='identity-bound tracking/clearance report; optional and offline-only')
    parser.add_argument('--dynamic-replan-report', type=Path,
                        help='identity-bound event-geometry replan report; optional and offline-only')
    parser.add_argument('--platform-capacity-report', type=Path,
                        help='platform capacity bound to the selected resource observation')
    parser.add_argument('--snapshot-report', type=Path,
                        help='optional versioned offline box/map geometry report')
    parser.add_argument('--snapshot-pair-report', type=Path,
                        help='optional same-identity before/after map diagnostic context')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = evaluate(args.config, args.calibration_report, args.run_dir, args.run_id,
                      args.tracking_clearance_report, args.snapshot_report,
                      args.snapshot_pair_report, args.dynamic_replan_report,
                      args.platform_capacity_report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'overall_status': report['overall_status'],
                      'run_id': report['run_id'],
                      'metric_count': len(report['metrics'])}))


if __name__ == '__main__':
    main()
