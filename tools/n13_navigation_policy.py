"""Offline N13 policy projection; never publishes control or grants formal credit."""
import copy
import hashlib
import json
from pathlib import Path

from tools.n09_contact_evaluation import evaluate_contacts
from tools.n10_run_identity import read_run_identity
from tools.n10_terminal_readback import summarize_terminal_readback


def calculation_config(config):
    """Supply old numeric references solely to existing diagnostic calculators."""
    result = copy.deepcopy(config)
    for metric in result['metrics'].values():
        for key in ('thresholds', 'acceptance_thresholds'):
            reference = metric.get('diagnostic_reference_' + key)
            if reference is not None:
                metric[key] = {**reference, **(metric.get(key) or {})}
    return result


def _read(path):
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def contact_and_terminal(run_dir):
    """Reclassify raw contacts; do not trust a cached zero-contact conclusion."""
    run_dir = Path(run_dir)
    row = {'id': 'full_body_clearance_and_contact', 'status': 'INSUFFICIENT',
           'evidence_status': 'direct_navigation_contract',
           'runtime_control_effect': False}
    names = ('n09-contact-observation.json', 'n09-contact-model-manifest.json',
             'flight.json', 'bridge-alignment-timeline.jsonl',
             'postflight-px4-bridge-readback.json', 'safe-to-stop.json')
    row['input_sha256'] = {
        name: hashlib.sha256((run_dir / name).read_bytes()).hexdigest()
        for name in names if (run_dir / name).is_file()}
    observation = _read(run_dir / names[0])
    manifest = _read(run_dir / names[1])
    flight = _read(run_dir / 'flight.json')
    readback = _read(run_dir / 'postflight-px4-bridge-readback.json')
    safe = _read(run_dir / 'safe-to-stop.json')
    emergency = _read(run_dir / 'emergency-disarm-safe-terminal.json')
    expected = read_run_identity(run_dir)
    observed = observation.get('run_identity') or {}
    fields = ('run_id', 'runtime_contract_sha256', 'goal_id', 'epoch', 'map_id')
    identity_ok = (expected.get('complete') is True
                   and observed.get('complete') is True
                   and all(expected.get(k) == observed.get(k) for k in fields))
    phases = []
    try:
        phases = [json.loads(line) for line in
                  (run_dir / 'bridge-alignment-timeline.jsonl').read_text().splitlines()
                  if line.strip()]
        if not all(isinstance(phase, dict) for phase in phases):
            raise ValueError('invalid phase record')
        goal_stamp = int(flight['goal']['source_ns'])
        contact = evaluate_contacts(observation, manifest, phases, goal_stamp)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        contact = {}
    terminal = summarize_terminal_readback(readback, emergency)
    safe_identity = (safe.get('expected_goal_id') == expected.get('goal_id')
                     and safe.get('expected_epoch') == expected.get('epoch'))
    readback_identity = (readback.get('expected_goal_id') == expected.get('goal_id')
                         and readback.get('expected_epoch') == expected.get('epoch'))
    checks = {
        'same_run_contact_identity': identity_ok,
        'contact_sensors_ready': contact.get('sensor_topics_ready') is True,
        'contact_record_through_terminal': (
            observation.get('terminal_flight_record_observed') is True
            and observation.get('safe_session_terminal_observed') is True),
        'phase_timeline_present': bool(phases),
        'landing_contact_observed': contact.get('landing_ground_contact_observed') is True,
        'normal_terminal_readback': terminal['native_terminal_evidence_complete'],
        'same_goal_epoch_terminal_readback': readback_identity,
        'same_goal_epoch_safe_terminal': safe_identity,
        'safe_terminal_observed': safe.get('safe_to_stop_project_container') is True,
        'no_emergency_closeout': safe.get('emergency_disarm_used') is False,
        'action_succeeded': flight.get('action_success') is True,
        'landed_and_disarmed': flight.get('landed_and_disarmed') is True,
    }
    row.update(checks=checks, contact=contact, terminal_readback=terminal)
    # A genuinely observed collision/action/terminal failure survives missing
    # optional geometry and incomplete other core evidence.
    failures = []
    if identity_ok and contact.get('prohibited_contact_event_count', 0) > 0:
        failures.append('observed_prohibited_contact')
    if flight.get('action_goal_sent') is True and flight.get('action_success') is False:
        failures.append('action_failed')
    if (readback_identity and (terminal['emergency_closeout_used']
            or terminal['observed_state_failures']
            or terminal['post_terminal_failures'])) or (
            safe_identity and safe.get('emergency_disarm_used') is True):
        failures.append('normal_terminal_failed')
    if failures:
        row.update(status='FAIL', direct_safety_failure=True, failures=failures)
    elif all(checks.values()):
        row['status'] = 'PASS'
    else:
        row['missing_evidence'] = [key for key, value in checks.items() if not value]
    return row


def project_results(config, rows, run_dir):
    result = []
    for row in rows:
        policy = config['metrics'].get(row['id'], {})
        if row['id'] == 'full_body_clearance_and_contact':
            core = contact_and_terminal(run_dir)
            core['optional_dense_geometry_diagnostic'] = row
            result.append(core)
        elif policy.get('assessment_role') == 'diagnostic':
            result.append({
                'id': row['id'], 'status': 'DIAGNOSTIC',
                'evidence_status': 'diagnostic_only',
                'diagnostic_status': row['status'], 'observation': row,
                'runtime_control_effect': False,
                'affects_functional_acceptance': False})
        else:
            result.append(row)
    result.append(scene_navigation(config, run_dir))
    return result


def scene_navigation(config, run_dir):
    """Recompute scene proof from this archive, bound to released code/world."""
    if config.get('scene_protocol', {}).get('kind') == 'n14_corridor':
        from tools.n14_navigation_policy import scene_navigation as evaluate_scene
        return evaluate_scene(config, run_dir)
    from tools.debug_truth.evaluate_n13_route import evaluate
    run_dir = Path(run_dir)
    root = Path(__file__).resolve().parents[1]
    policy = config.get('scene_protocol') or {}
    row = {'id': 'n13_scene_navigation', 'status': 'INSUFFICIENT',
           'runtime_control_effect': False, 'evidence_status': 'direct_navigation_contract'}
    evaluator = root / 'tools/debug_truth/evaluate_n13_route.py'
    world = _read(run_dir / 'world.json')
    checks = {
        'released_protocol': policy.get('status') == 'ready',
        'evaluator_matches_release': policy.get('evaluator_sha256') == hashlib.sha256(evaluator.read_bytes()).hexdigest(),
        'world_matches_release': bool(policy.get('world_geometry_sha256')) and
            world.get('project_geometry_sha256') == policy.get('world_geometry_sha256'),
    }
    row['checks'] = checks
    if not all(checks.values()):
        row['missing_evidence'] = [key for key, value in checks.items() if not value]
        return row
    # The route calculator currently only reads diagnostic reference settings;
    # all scene decisions come from measured geometry and identity-bound files.
    report = evaluate(run_dir, root / 'config/acceptance_n13.json')
    names = ('flight.json', 'runtime-contract.json', 'arrival-evaluation.json',
             'n11-static-map-observation.json', 'n11-launch-record.json',
             'vio_initialization.sdf', 'n10-tracking-clearance-relation.json',
             'planner-observation.json', 'world.json')
    row['input_sha256'] = {name: hashlib.sha256((run_dir / name).read_bytes()).hexdigest()
                           for name in names if (run_dir / name).is_file()}
    row.update(status=report['status'], route=report)
    if report['status'] == 'FAIL':
        row['direct_safety_failure'] = True
    return row
