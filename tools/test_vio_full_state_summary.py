"""Checks that N01 aggregation requires independent, complete same-protocol epochs."""
import hashlib
import json
import sys
import tempfile
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent / 'debug_truth'))
from summarize_vio_full_state import summarize


def _report(epoch):
    report = {
        'epoch': epoch, 'fixture_outcome': 'unarmed_support_drift_completed',
        'fixture_motion_completed': True, 'runtime_contract_sha256': 'runtime',
        'fixture_completed_stages': 23, 'fixture_expected_stages': 23,
        'protocol_sha256': 'protocol', 'position_ate_m': {'rmse': 0.1, 'p95': 0.2, 'max': 0.3},
        'attitude_geodesic_error_deg': {'rmse': 1.0}, 'roll_error_deg': {'rmse': 0.1},
        'pitch_error_deg': {'rmse': 0.2}, 'yaw_error_deg': {'rmse': 0.3},
        'velocity_error_m_s': {'rmse': 0.4},
        'timing': {'source_age_at_receipt_sim_s': {'p95': 0.05},
                   'max_source_gap_sim_s': 0.1, 'max_receipt_gap_wall_s': 0.2},
        'coverage': {'velocity_truth_pairs': 100, 'pose_pair_fraction': 1.0,
                     'velocity_pair_fraction': 0.9,
                     'raw_intervals_over_configured_support_limit': 0},
        'motion_support': {'source_duration_sim_s': 300, 'paired_truth_path_length_m': 8,
                           'truth_imu_speed_m_s': {'max': 0.2},
                           'truth_angular_speed_rad_s': {'max': 0.1},
                           'truth_yaw_span_deg': 20,
                           'truth_roll_pitch_variation_from_level_deg': {'roll': 1, 'pitch': 2}},
        'rpe': [{'target_window_s': window, 'candidate_pairs': 12,
                 'supported_pairs': 10, 'rejected_pairs': 2,
                 'translation_error_m': {'rmse': 0.01}, 'rotation_error_deg': {'rmse': 0.02}}
                for window in (1.0, 5.0, 10.0)],
        'input_sha256': {}, 'output_sha256': {}}
    returns = {'measurement_completed': True, 'returns': 3,
               'input_sha256': {}, 'checkpoints': [
                   {'label': 'reference', 'cycle': None},
                   *[{'label': 'return', 'cycle': cycle, 'drift_since_reference_m': cycle * 0.01,
                      'yaw_drift_since_reference_deg': cycle * 0.1,
                      'truth_return_distance_m': 0.001} for cycle in (1, 2, 3)]]}
    return report, returns


def _write_cleanup_audit(run, report, fixture_present=False, disarmed=True, landed=True):
    source_names = ('fixture-result.json', 'fixture-stages.json', 'fixture-trace.jsonl',
                    'runtime-contract.json', 'vio-state-protocol.json')
    for name in source_names:
        (run / name).write_text(name + '\n')
    audit = {
        'schema_version': 1, 'run_id': run.name,
        'probe_outcome': report['fixture_outcome'], 'probe_error': report['fixture_error'],
        'completed_stages': report['fixture_completed_stages'],
        'expected_stages': report['fixture_expected_stages'],
        'attachment_states': ['attached', 'detached'], 'fixture_may_remain_attached': False,
        'fixture_present_in_gazebo_pose_info': fixture_present,
        'fixture_models': ['preflight_scan_fixture'] if fixture_present else [],
        'px4_disarmed': disarmed, 'px4_arming_state': 1 if disarmed else 2,
        'vehicle_landed': landed,
        'input_sha256': {name: hashlib.sha256((run / name).read_bytes()).hexdigest()
                         for name in source_names}}
    (run / 'fixture-cleanup-audit.json').write_text(json.dumps(audit))


class VioFullStateSummaryTests(unittest.TestCase):
    def test_requires_three_unique_complete_epochs_with_matching_hashes(self):
        with tempfile.TemporaryDirectory() as root:
            runs = []
            for index, epoch in enumerate(('a' * 32, 'b' * 32, 'c' * 32)):
                run = Path(root) / str(index)
                run.mkdir()
                report, returns = _report(epoch)
                (run / 'vio-full-state-report.json').write_text(json.dumps(report))
                (run / 'return-drift.json').write_text(json.dumps(returns))
                runs.append(run)
            result = summarize(runs)
            self.assertEqual(result['complete_fresh_epoch_count'], 3)
            self.assertEqual(result['repeated_return_drift']['cycle_3']['position_drift_m']['median'], 0.03)
            report, returns = _report('a' * 32)
            (runs[2] / 'vio-full-state-report.json').write_text(json.dumps(report))
            (runs[2] / 'return-drift.json').write_text(json.dumps(returns))
            with self.assertRaisesRegex(ValueError, 'different VINS epoch'):
                summarize(runs)

    def test_rejects_incomplete_epoch(self):
        with tempfile.TemporaryDirectory() as root:
            runs = []
            for index, epoch in enumerate(('a' * 32, 'b' * 32, 'c' * 32)):
                run = Path(root) / str(index)
                run.mkdir()
                report, returns = _report(epoch)
                if index == 1:
                    report['fixture_motion_completed'] = False
                (run / 'vio-full-state-report.json').write_text(json.dumps(report))
                (run / 'return-drift.json').write_text(json.dumps(returns))
                runs.append(run)
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                summarize(runs)

    def test_reports_raw_source_gaps_over_frozen_interpolation_support(self):
        with tempfile.TemporaryDirectory() as root:
            runs = []
            for index, epoch in enumerate(('a' * 32, 'b' * 32, 'c' * 32)):
                run = Path(root) / str(index)
                run.mkdir()
                report, returns = _report(epoch)
                if index == 1:
                    report['coverage']['raw_intervals_over_configured_support_limit'] = 1
                (run / 'vio-full-state-report.json').write_text(json.dumps(report))
                (run / 'return-drift.json').write_text(json.dumps(returns))
                runs.append(run)
            result = summarize(runs)
            self.assertEqual(result['complete_fresh_epoch_count'], 3)
            gaps = result['cross_epoch_metrics']['raw_intervals_over_configured_support_limit']
            self.assertEqual((gaps['min'], gaps['median'], gaps['max']), (0.0, 0.0, 1.0))

    def test_accepts_removal_ack_failure_only_with_independent_cleanup_audit(self):
        with tempfile.TemporaryDirectory() as root:
            runs = []
            for index, epoch in enumerate(('a' * 32, 'b' * 32, 'c' * 32)):
                run = Path(root) / str(index)
                run.mkdir()
                report, returns = _report(epoch)
                if index == 1:
                    report['fixture_outcome'] = 'failed'
                    report['fixture_error'] = 'detached fixture removal was not acknowledged'
                    _write_cleanup_audit(run, report)
                (run / 'vio-full-state-report.json').write_text(json.dumps(report))
                (run / 'return-drift.json').write_text(json.dumps(returns))
                runs.append(run)
            result = summarize(runs)
            self.assertEqual(result['complete_fresh_epoch_count'], 3)
            self.assertEqual(result['epochs'][1]['completion_basis'],
                             'all_motion_stages_complete_and_postdetach_cleanup_independently_verified')

    def test_rejects_postdetach_audit_if_fixture_remains_or_is_not_landed(self):
        with tempfile.TemporaryDirectory() as root:
            runs = []
            for index, epoch in enumerate(('a' * 32, 'b' * 32, 'c' * 32)):
                run = Path(root) / str(index)
                run.mkdir()
                report, returns = _report(epoch)
                if index == 1:
                    report['fixture_outcome'] = 'failed'
                    report['fixture_error'] = 'detached fixture removal was not acknowledged'
                    _write_cleanup_audit(run, report, fixture_present=True, landed=False)
                (run / 'vio-full-state-report.json').write_text(json.dumps(report))
                (run / 'return-drift.json').write_text(json.dumps(returns))
                runs.append(run)
            with self.assertRaisesRegex(ValueError, 'cleanup audit does not independently verify'):
                summarize(runs)


if __name__ == '__main__':
    unittest.main()
