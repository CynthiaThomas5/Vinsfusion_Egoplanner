import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.debug_truth.kinematics_evidence import instantaneous_endpoints


class EndpointEvidenceTests(unittest.TestCase):
    def fixture(self, run):
        identity = {'complete': True, 'run_id': run.name}
        row = {'schema': 'uav-model-kinematics/v1', 'pose_reference': 'model_origin',
               'model_name': 'x500', 'stamp_ns': 4_000_000, 'xyz': [0, 0, 1],
               'q_xyzw': [0, 0, 0, 1], 'linear_velocity_world_m_s': [0, 0, -.0392],
               'angular_velocity_world_rad_s': [0, 0, 0]}
        plugin = {'enabled': True, 'plugin_filename': 'libuav_truth_kinematics.so',
                  'plugin_class': 'uav::debug_truth::ModelKinematics',
                  'topic': '/debug_truth/model_kinematics', 'pose_reference': 'model_origin',
                  'velocity_frame': 'world', 'velocity_kind': 'instantaneous_physics_components',
                  'plugin_binary_sha256': 'a'*64, 'plugin_source_sha256': 'b'*64}
        overlay_model = run/'n09-contact-models/x500_d435i/model.sdf'
        overlay_model.parent.mkdir(parents=True)
        model_sdf = (b'<sdf version="1.9"><model name="x500_d435i">'
                     b'<plugin filename="libuav_truth_kinematics.so" '
                     b'name="uav::debug_truth::ModelKinematics"/></model></sdf>')
        overlay_model.write_bytes(model_sdf)
        model_sha = hashlib.sha256(model_sdf).hexdigest()
        files = {'install/uav_debug_truth/lib/libuav_truth_kinematics.so': 'a'*64,
                 'src/own/uav_debug_truth/src/model_kinematics.cpp': 'b'*64}
        (run/'runtime-contract.json').write_text(json.dumps({'files': files}))
        overlay_root = f'/workspace/artifacts/runs/{run.name}/n09-contact-models'
        (run/'n09-contact-model-manifest.json').write_text(json.dumps({
            'kinematics_observer':plugin,
            'overlay_root':overlay_root,
            'generated_model_sha256':{'x500_d435i/model.sdf':model_sha},
        }))
        (run/'n10-px4-model-source.json').write_text(json.dumps({
            'schema':'n10-px4-gazebo-model-source/v1',
            'model_name':'x500_d435i',
            'px4_gz_models':overlay_root,
            'selected_model_sdf':overlay_root+'/x500_d435i/model.sdf',
            'selected_model_sdf_sha256':model_sha,
            'kinematics_requested':True,
            'kinematics_plugin_entries':1,
            'kinematics_plugin_source_present':True,
        }))
        report = {'schema': 'uav-kinematics-observation/v1', 'enabled': True,
                  'metadata_validated': True, 'error_count': 0, 'subscribe_ok': True,
                  'safe_session_terminal_observed': True, 'terminal_flight_record_observed': True,
                  'run_identity': identity, 'record_count': 1}
        return identity, row, report

    def test_valid_binding_and_rejection_cases(self):
        for mutation in ('valid', 'hash', 'missing', 'pose', 'reference', 'identity',
                         'binary', 'duplicate', 'model_source_missing',
                         'model_source_sha', 'model_source_path'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                run = Path(temporary)
                identity, row, report = self.fixture(run)
                truth = {'stamp_ns': row['stamp_ns'], 'xyz': list(row['xyz']), 'q_xyzw': list(row['q_xyzw'])}
                if mutation == 'missing': truth['stamp_ns'] += 4_000_000
                if mutation == 'pose': row['xyz'][0] = .24
                if mutation == 'reference': row['pose_reference'] = 'base_link'
                if mutation == 'identity': report['run_identity'] = {'complete': False}
                if mutation == 'binary': (run/'runtime-contract.json').write_text('{"files": {}}')
                payload = json.dumps(row)+'\n'
                if mutation == 'duplicate': payload += payload; report['record_count'] = 2
                if mutation == 'model_source_missing':
                    (run/'n10-px4-model-source.json').unlink()
                elif mutation == 'model_source_sha':
                    source_path = run/'n10-px4-model-source.json'
                    source_report = json.loads(source_path.read_text())
                    source_report['selected_model_sdf_sha256'] = 'c'*64
                    source_path.write_text(json.dumps(source_report))
                elif mutation == 'model_source_path':
                    source_path = run/'n10-px4-model-source.json'
                    source_report = json.loads(source_path.read_text())
                    source_report['selected_model_sdf'] = '/workspace/simulation/models/x500_d435i/model.sdf'
                    source_path.write_text(json.dumps(source_report))
                (run/'debug-truth-kinematics.jsonl').write_text(payload)
                report['record_sha256'] = hashlib.sha256(payload.encode()).hexdigest()
                if mutation == 'hash': report['record_sha256'] = 'c'*64
                (run/'debug-truth-kinematics-observation.json').write_text(json.dumps(report))
                with patch('tools.debug_truth.kinematics_evidence.read_run_identity', return_value=identity):
                    converted, evidence = instantaneous_endpoints(run, [truth])
                self.assertEqual(evidence['status'], 'PASS' if mutation == 'valid' else 'INSUFFICIENT')
                if mutation == 'valid':
                    self.assertEqual(converted[0]['linear_velocity_xyz_m_s'], [0,0,-.0392])
                    self.assertNotIn('linear_velocity_xyz_m_s', truth)
                else: self.assertIsNone(converted)

    def test_missing_observer_is_insufficient(self):
        with tempfile.TemporaryDirectory() as temporary:
            rows, evidence = instantaneous_endpoints(Path(temporary), [])
        self.assertIsNone(rows)
        self.assertEqual(evidence['status'], 'INSUFFICIENT')
