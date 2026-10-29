"""Functional policy regression: diagnostics cannot hide real failures or gaps."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.debug_truth.evaluate_n10_acceptance import (
    evaluate_run, identity_evidence, summarize_required_metrics)
from tools.n13_navigation_policy import contact_and_terminal, project_results
from tools import test_n10_acceptance as fixtures

ROOT = Path(__file__).resolve().parents[1]


def write(run, name, data):
    path = run / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def core_fixture(run):
    identity = {'run_id': run.name, 'runtime_contract_sha256': 'runtime',
                'goal_id': 'goal', 'epoch': 'epoch', 'map_id': 'epoch-map',
                'complete': True}
    write(run, 'n10-run-manifest.json', identity)
    write(run, 'runtime-contract.json', {'sha256': 'runtime'})
    write(run, 'n10-map-snapshot/metadata.json', {'epoch': 'epoch', 'map_id': 'epoch-map'})
    write(run, 'flight.json', {'goal': {'source_ns': 10}, 'goal_id': 'goal',
          'localization_epoch': 'epoch', 'action_goal_sent': True,
          'action_success': True, 'landed_and_disarmed': True})
    write(run, 'n09-contact-model-manifest.json', {'sensor_topics': ['sensor']})
    write(run, 'n09-contact-observation.json', {
        'run_identity': identity, 'ready': True, 'expected_topics': ['sensor'],
        'advertised_topics': ['sensor'], 'terminal_flight_record_observed': True,
        'safe_session_terminal_observed': True, 'events': [
            {'stamp_ns': 20, 'topic': 'sensor', 'pairs': [
                {'collision1': 'body', 'collision2': 'ground_plane'}]}]})
    (run / 'bridge-alignment-timeline.jsonl').write_text(
        json.dumps({'stamp_ns': 15, 'phase': 'LANDING'}) + '\n')
    write(run, 'postflight-px4-bridge-readback.json', {
        'expected_goal_id': 'goal', 'expected_epoch': 'epoch',
        'latest': {'bridge': {'phase': 'LANDED', 'landed': True,
                             'armed': False, 'control_enabled': False},
                   'px4_status': {'arming_state': 1},
                   'land_detected': {'landed': True}},
        'zero_control_after_terminal': True, 'no_old_epoch_goal_or_trajectory': True})
    write(run, 'safe-to-stop.json', {'safe_to_stop_project_container': True,
          'expected_goal_id': 'goal', 'expected_epoch': 'epoch',
          'emergency_disarm_used': False})


class N13NavigationPolicyTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / 'config/acceptance_n13.json').read_text())

    def mutate(self, run, name, change):
        data = json.loads((run / name).read_text())
        change(data)
        write(run, name, data)

    def test_all_independent_numeric_budgets_are_diagnostic(self):
        diag = [m for m in self.config['metrics'].values()
                if m.get('assessment_role') == 'diagnostic']
        self.assertEqual(len(diag), 10)
        self.assertTrue(all(m['required'] is False for m in diag))
        self.assertTrue(all('thresholds' not in m and 'acceptance_thresholds' not in m
                            for m in diag))

    def test_diagnostic_failures_preserved_without_failing_core(self):
        c = copy.deepcopy(self.config)
        c['scene_protocol']['status'] = 'ready'  # synthetic summary-only test
        rows = [{'id': k, 'status': 'PASS'} for k in c['metrics']]
        for row in rows:
            if c['metrics'][row['id']].get('assessment_role') == 'diagnostic':
                row.update(status='FAIL', direct_safety_failure=True)
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp); core_fixture(run)
            with patch('tools.n13_navigation_policy.scene_navigation', return_value={
                    'id': 'n13_scene_navigation', 'status': 'PASS'}):
                result = summarize_required_metrics(c, project_results(c, rows, run))
        self.assertEqual(result['overall_status'], 'PASS')
        diagnostics = [m for m in result['metrics'] if m['status'] == 'DIAGNOSTIC']
        self.assertEqual(len(diagnostics), 10)
        self.assertTrue(all(m['diagnostic_status'] == 'FAIL' for m in diagnostics))

    def test_pending_scene_cannot_receive_n12_retrospective_credit(self):
        self.config['scene_protocol']['status'] = 'pending'
        rows = [{'id': k, 'status': 'PASS'} for k in self.config['metrics']]
        self.assertEqual(summarize_required_metrics(self.config, rows)['overall_status'],
                         'INSUFFICIENT')

    def test_missing_optional_diagnostics_and_dense_geometry_do_not_fail_contact(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp); core_fixture(run)
            self.assertEqual(contact_and_terminal(run)['status'], 'PASS')

    def test_each_missing_core_input_is_insufficient(self):
        for name in ('n09-contact-observation.json', 'n09-contact-model-manifest.json',
                     'bridge-alignment-timeline.jsonl', 'postflight-px4-bridge-readback.json',
                     'safe-to-stop.json', 'flight.json'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                run = Path(tmp); core_fixture(run); (run / name).unlink()
                self.assertEqual(contact_and_terminal(run)['status'], 'INSUFFICIENT')

    def test_raw_obstacle_contact_fails_without_any_dense_geometry(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp); core_fixture(run)
            self.mutate(run, 'n09-contact-observation.json', lambda d:
                        d['events'][0]['pairs'][0].update(collision2='obstacle'))
            self.assertEqual(contact_and_terminal(run)['status'], 'FAIL')

    def test_partial_observer_cannot_claim_zero_contacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp); core_fixture(run)
            self.mutate(run, 'n09-contact-observation.json', lambda d:
                        d.update(safe_session_terminal_observed=False))
            self.assertEqual(contact_and_terminal(run)['status'], 'INSUFFICIENT')

    def test_other_goal_terminal_cannot_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp); core_fixture(run)
            self.mutate(run, 'postflight-px4-bridge-readback.json', lambda d:
                        d.update(expected_goal_id='other'))
            self.assertEqual(contact_and_terminal(run)['status'], 'INSUFFICIENT')

    def test_other_epoch_contacts_cannot_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp); core_fixture(run)
            self.mutate(run, 'n09-contact-observation.json', lambda d:
                        d['run_identity'].update(epoch='other'))
            self.assertEqual(contact_and_terminal(run)['status'], 'INSUFFICIENT')

    def test_real_action_failure_still_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp); core_fixture(run)
            self.mutate(run, 'flight.json', lambda d: d.update(action_success=False))
            self.assertEqual(contact_and_terminal(run)['status'], 'FAIL')

    def test_emergency_disarm_cannot_pass_normal_terminal(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp); core_fixture(run)
            self.mutate(run, 'safe-to-stop.json', lambda d:
                        d.update(emergency_disarm_used=True))
            self.assertEqual(contact_and_terminal(run)['status'], 'FAIL')

    def test_nonzero_terminal_controls_still_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp); core_fixture(run)
            self.mutate(run, 'postflight-px4-bridge-readback.json', lambda d:
                        d.update(zero_control_after_terminal=False))
            self.assertEqual(contact_and_terminal(run)['status'], 'FAIL')

    def test_identity_no_longer_requires_legacy_injected_box(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp); core_fixture(run)
            self.assertTrue(identity_evidence(run.name,
                {'runtime_contract_sha256': 'runtime'}, run, True)
                ['goal_epoch_map_identity_is_bound'])

    def test_arrival_failure_survives_pending_scene(self):
        self.assertEqual(summarize_required_metrics(self.config, [{
            'id': 'arrival_position_yaw_dwell', 'status': 'FAIL',
            'evidence_status': 'direct_goal_contract'}])['overall_status'], 'FAIL')

    def test_unreadable_optional_reports_do_not_abort_evaluation(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp); core_fixture(run)
            for name in ('n10-clearance-evaluation.json', 'n10-interval-clearance-bound.json',
                         'n10-box-map-snapshot-analysis.json', 'n10-resource-observation.json'):
                (run / name).write_text('broken recorder output')
            result = evaluate_run(self.config, fixtures._metrics(), run)
            body = next(m for m in result['metrics'] if m['id'] == 'full_body_clearance_and_contact')
            self.assertEqual(body['status'], 'PASS')
            self.assertEqual(result['overall_status'], 'INSUFFICIENT')


if __name__ == '__main__':
    unittest.main()
