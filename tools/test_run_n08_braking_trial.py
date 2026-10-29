import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent))
from action_msgs.msg import GoalStatus
from run_n08_braking_trial import (bspline_time_window,
                                  is_caller_cancel_action_result,
                                  px4_sample_inside_stop_gate,
                                  terminal_reference_command,
                                  validate_trial_source_fingerprints)


class CallerCancelResultTests(unittest.TestCase):
    def test_cancel_outcome_and_reason_are_checked_in_their_own_fields(self):
        self.assertTrue(is_caller_cancel_action_result(
            GoalStatus.STATUS_CANCELED, 'canceled', 'caller_cancel'))
        self.assertFalse(is_caller_cancel_action_result(
            GoalStatus.STATUS_CANCELED, 'caller_cancel', 'canceled'))

    def test_wrong_terminal_status_or_cancel_reason_is_rejected(self):
        self.assertFalse(is_caller_cancel_action_result(
            GoalStatus.STATUS_ABORTED, 'canceled', 'caller_cancel'))
        self.assertFalse(is_caller_cancel_action_result(
            GoalStatus.STATUS_CANCELED, 'canceled', 'map_identity_changed'))


class TrialBuildFingerprintTests(unittest.TestCase):
    def test_runtime_goal_config_is_authenticated_by_current_launch_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            runner=root/'tools/run_n08_braking_trial.py'
            helper=root/'tools/n08_trial_gate.py'
            profile=root/'config/components/navigation/n08_forward_braking_trial_goal.json'
            for path,data in ((runner,b'runner'),(helper,b'gate'),(profile,b'updated-runtime-profile')):
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(data)
            hashes={rel:hashlib.sha256(path.read_bytes()).hexdigest() for rel,path in (
                ('tools/run_n08_braking_trial.py',runner),
                ('tools/n08_trial_gate.py',helper),
                ('config/components/navigation/n08_forward_braking_trial_goal.json',profile))}
            validate_trial_source_fingerprints(
                root,
                {'tools/run_n08_braking_trial.py':'legacy-runner-build-hash',
                 'tools/n08_trial_gate.py':'legacy-helper-build-hash',
                 'config/components/navigation/n08_forward_braking_trial_goal.json':'old-build-profile-hash'},
                hashes)
            hashes['config/components/navigation/n08_forward_braking_trial_goal.json']='wrong-manifest-hash'
            with self.assertRaisesRegex(ValueError,'run_trial_runtime_fingerprint_mismatch'):
                validate_trial_source_fingerprints(
                    root,{},hashes)

    def test_python_runner_uses_cold_run_manifest_not_legacy_build_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runner = root / 'tools/run_n08_braking_trial.py'
            runner.parent.mkdir(parents=True)
            runner.write_bytes(b'updated-python-runner')
            helper = root / 'tools/n08_trial_gate.py'
            helper.write_bytes(b'updated-python-geometry-gate')
            current = hashlib.sha256(runner.read_bytes()).hexdigest()
            helper_current = hashlib.sha256(helper.read_bytes()).hexdigest()
            validate_trial_source_fingerprints(
                root,
                {'tools/run_n08_braking_trial.py': 'legacy-build-list-hash',
                 'tools/n08_trial_gate.py': 'legacy-gate-build-list-hash'},
                {'tools/run_n08_braking_trial.py': current,
                 'tools/n08_trial_gate.py': helper_current})

    def test_python_runner_must_match_cold_run_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runner = root / 'tools/run_n08_braking_trial.py'
            runner.parent.mkdir(parents=True)
            runner.write_bytes(b'updated-python-runner')
            helper = root / 'tools/n08_trial_gate.py'
            helper.write_bytes(b'updated-python-geometry-gate')
            helper_hash = hashlib.sha256(helper.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, 'run_trial_runner_fingerprint_mismatch'):
                validate_trial_source_fingerprints(
                    root,
                    {'tools/run_n08_braking_trial.py': 'legacy-build-list-hash'},
                    {'tools/n08_trial_gate.py': helper_hash})

    def test_python_runner_is_required_in_manifest_even_if_build_list_omits_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runner = root / 'tools/run_n08_braking_trial.py'
            runner.parent.mkdir(parents=True)
            runner.write_bytes(b'updated-python-runner')
            helper = root / 'tools/n08_trial_gate.py'
            helper.write_bytes(b'updated-python-geometry-gate')
            helper_hash = hashlib.sha256(helper.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, 'run_trial_runner_fingerprint_mismatch'):
                validate_trial_source_fingerprints(
                    root, {}, {'tools/n08_trial_gate.py': helper_hash})

    def test_compiled_source_mismatch_still_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runner = root / 'tools/run_n08_braking_trial.py'
            runner.parent.mkdir(parents=True)
            runner.write_bytes(b'python-runner')
            runner_hash = hashlib.sha256(runner.read_bytes()).hexdigest()
            helper = root / 'tools/n08_trial_gate.py'
            helper.write_bytes(b'python-geometry-gate')
            helper_hash = hashlib.sha256(helper.read_bytes()).hexdigest()
            source = root / 'src/vendor/ego.cpp'
            source.parent.mkdir(parents=True)
            source.write_bytes(b'changed-compiled-source')
            with self.assertRaisesRegex(ValueError, 'trial_source_fingerprint_mismatch'):
                validate_trial_source_fingerprints(
                    root,
                    {'tools/run_n08_braking_trial.py': 'legacy-build-list-hash',
                     'tools/n08_trial_gate.py': 'legacy-gate-build-list-hash',
                     'src/vendor/ego.cpp': 'build-source-hash'},
                    {'tools/run_n08_braking_trial.py': runner_hash,
                     'tools/n08_trial_gate.py': helper_hash})

    def test_geometry_gate_must_match_current_run_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runner = root / 'tools/run_n08_braking_trial.py'
            helper = root / 'tools/n08_trial_gate.py'
            runner.parent.mkdir(parents=True)
            runner.write_bytes(b'python-runner')
            helper.write_bytes(b'python-geometry-gate')
            runner_hash = hashlib.sha256(runner.read_bytes()).hexdigest()
            with self.assertRaisesRegex(
                    ValueError, 'run_trial_runtime_fingerprint_mismatch'):
                validate_trial_source_fingerprints(
                    root, {}, {'tools/run_n08_braking_trial.py': runner_hash})


class CancelStopCompletionTests(unittest.TestCase):
    def test_b_spline_active_domain_matches_traj_server_time_span(self):
        msg=NS(order=3,pos_pts=[None]*6,knots=list(map(float,range(10))),
               start_time=NS(sec=100,nanosec=250))
        self.assertEqual(bspline_time_window(msg),{
            'start_sim_ns':100_000_000_250,'duration_sim_s':3.0,
            'end_sim_ns':103_000_000_250})

    def test_ready_flag_at_domain_end_is_a_terminal_hold_after_stable_zero_derivatives(self):
        def row(stamp):
            return {'goal_id':'g','epoch':'e','trajectory_id':2,'flag':1,
                    'source_stamp_ns':stamp,'position_enu':[1.,2.,3.],
                    'velocity_enu_m_s':[0.,0.,0.],
                    'acceleration_enu_m_s2':[0.,0.,0.]}
        rows=[row(4_000_000_000),row(4_060_000_000)]
        self.assertIs(terminal_reference_command(rows,'g','e',2,4_000_000_000),rows[-1])

    def test_terminal_hold_accepts_high_rate_commands_after_a_stable_50ms_window(self):
        def row(stamp,position=(1.,2.,3.),velocity=(0.,0.,0.)):
            return {'goal_id':'g','epoch':'e','trajectory_id':2,'flag':1,
                    'source_stamp_ns':stamp,'position_enu':list(position),
                    'velocity_enu_m_s':list(velocity),
                    'acceleration_enu_m_s2':[0.,0.,0.]}
        rows=[row(4_000_000_000+i*8_000_000) for i in range(8)]
        self.assertIs(terminal_reference_command(rows,'g','e',2,4_000_000_000),rows[-1])

    def test_terminal_hold_rejects_motion_anywhere_in_recent_50ms_window(self):
        def row(stamp,position=(1.,2.,3.),velocity=(0.,0.,0.)):
            return {'goal_id':'g','epoch':'e','trajectory_id':2,'flag':1,
                    'source_stamp_ns':stamp,'position_enu':list(position),
                    'velocity_enu_m_s':list(velocity),
                    'acceleration_enu_m_s2':[0.,0.,0.]}
        rows=[row(4_000_000_000+i*8_000_000) for i in range(8)]
        rows[-3]=row(rows[-3]['source_stamp_ns'],velocity=(0.001,0.,0.))
        self.assertIsNone(terminal_reference_command(rows,'g','e',2,4_000_000_000))

    def test_terminal_reference_requires_end_time_zero_derivatives_and_stable_position(self):
        base={'goal_id':'g','epoch':'e','trajectory_id':2,'flag':1,
              'position_enu':[1.,2.,3.],'velocity_enu_m_s':[0.,0.,0.],
              'acceleration_enu_m_s2':[0.,0.,0.]}
        early=[dict(base,source_stamp_ns=3_900_000_000),
               dict(base,source_stamp_ns=3_960_000_000)]
        self.assertIsNone(terminal_reference_command(early,'g','e',2,4_000_000_000))
        moving=[dict(base,source_stamp_ns=4_000_000_000),
                dict(base,source_stamp_ns=4_060_000_000,
                     velocity_enu_m_s=[.001,0.,0.])]
        self.assertIsNone(terminal_reference_command(moving,'g','e',2,4_000_000_000))

    def test_measured_px4_stop_gate_uses_existing_horizontal_and_vertical_bounds(self):
        self.assertTrue(px4_sample_inside_stop_gate({'vx':.03,'vy':0.,'vz':.05}))
        self.assertFalse(px4_sample_inside_stop_gate({'vx':.0301,'vy':0.,'vz':0.}))
        self.assertFalse(px4_sample_inside_stop_gate({'vx':0.,'vy':0.,'vz':-.0501}))


class TrialRuntimeManifestTests(unittest.TestCase):
    def test_runtime_python_evaluator_is_checked_against_cold_run_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            expected={}
            runtime={}
            for relative,content in (
                    ('tools/run_n08_braking_trial.py',b'runner'),
                    ('tools/n08_trial_gate.py',b'gate'),
                    ('tools/debug_truth/evaluate_n08_braking.py',b'evaluator')):
                path=root/relative;path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes(content)
                expected[relative]=hashlib.sha256(content).hexdigest()
                runtime[relative]=expected[relative]
            validate_trial_source_fingerprints(root,expected,runtime)
            runtime['tools/debug_truth/evaluate_n08_braking.py']='stale-evaluator'
            with self.assertRaisesRegex(ValueError,'run_trial_runtime_fingerprint_mismatch'):
                validate_trial_source_fingerprints(root,expected,runtime)


if __name__ == '__main__':
    unittest.main()
