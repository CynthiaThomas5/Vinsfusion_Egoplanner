"""Observer configuration checks; fixture resources are not runtime evidence."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from run_loop_observer import resolve

ROOT = Path(__file__).resolve().parents[1]


class LoopObserverTests(unittest.TestCase):
    def fixture(self, root):
        prefix = root/'install/loop_fusion'
        executable = prefix/'lib/loop_fusion/loop_fusion_node'
        executable.parent.mkdir(parents=True)
        executable.write_text('fixture, never executed')
        executable.chmod(0o755)
        cfg = root/'config/components/localization'
        cfg.mkdir(parents=True)
        for name in ['vins_sim.json', 'loop_observer.json']:
            (cfg/name).write_bytes((ROOT/'config/components/localization'/name).read_bytes())
        model = root/'simulation/models/d435i/model.sdf'
        model.parent.mkdir(parents=True)
        model.write_bytes((ROOT/'simulation/models/d435i/model.sdf').read_bytes())
        sources = {'id': 'vins_fusion', 'patched_files_sha256': {}}
        resources = prefix/'share/loop_fusion/support_files'
        resources.mkdir(parents=True)
        for name in ['brief_k10L6.bin', 'brief_pattern.yml']:
            (resources/name).write_text('unit fixture')
            sources['patched_files_sha256']['support_files/'+name] = hashlib.sha256((resources/name).read_bytes()).hexdigest()
        (root/'dependencies').mkdir()
        (root/'dependencies/sources.json').write_text(json.dumps({'sources': [sources]}))
        session = root/'artifacts/runs/test-run-stack/session'
        session.mkdir(parents=True)
        (root/'artifacts/runs/test-run').mkdir()
        (session/'vins.yaml').write_text('unit fixture')
        epoch = 'a'*32
        (session/'session.json').write_text(json.dumps({
            'epoch': epoch, 'namespace': '/vins_raw/s_'+epoch,
            'files_sha256': {'vins.yaml': hashlib.sha256((session/'vins.yaml').read_bytes()).hexdigest()},
            'settings_sha256': hashlib.sha256((cfg/'vins_sim.json').read_bytes()).hexdigest(),
            'model_sha256': hashlib.sha256(model.read_bytes()).hexdigest()}))
        return prefix, session

    def test_command_only_reads_raw_session_and_outputs_in_separate_namespace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); prefix, _ = self.fixture(root)
            _, command, manifest = resolve(root, 'test-run', prefix)
            self.assertIn('__ns:=/loop_observer/s_'+'a'*32, command)
            self.assertIn('keyframe_point:=/vins_raw/s_'+'a'*32+'/keyframe_point', command)
            self.assertFalse(any('/fmu/' in x or '/localization/' in x or '/debug_truth/' in x for x in command))
            self.assertFalse(manifest['control_or_tf_outputs'])
            self.assertEqual(manifest['limits']['queue_limit'], 64)

    def test_changed_calibration_or_session_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); prefix, session = self.fixture(root)
            (session/'vins.yaml').write_text('changed')
            with self.assertRaisesRegex(ValueError, 'Session file hash'):
                resolve(root, 'test-run', prefix)

    def test_explicit_diagnostic_sampling_does_not_replace_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); prefix, _ = self.fixture(root)
            relative='config/components/localization/loop_observer_local_revisit.json'
            (root/relative).write_bytes((ROOT/relative).read_bytes())
            _, default, _ = resolve(root,'test-run',prefix)
            _, selected, manifest = resolve(root,'test-run',prefix,relative)
            self.assertIn('minimum_distance_m:=0.2',default)
            self.assertIn('minimum_distance_m:=0.1',selected)
            self.assertEqual(manifest['configuration_source'],relative)
            with self.assertRaises(ValueError):resolve(root,'test-run',prefix,'../outside.json')

    def test_installed_resource_is_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); prefix, _ = self.fixture(root)
            (prefix/'share/loop_fusion/support_files/brief_pattern.yml').write_text('bad')
            with self.assertRaisesRegex(ValueError, 'resource hash'):
                resolve(root, 'test-run', prefix)

    def test_invalid_limits_and_modes_fail_before_start(self):
        for key, value in [('mode', 'control'), ('queue_limit', 0), ('max_keyframes', True),
                           ('minimum_distance_m', float('nan'))]:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); prefix, _ = self.fixture(root)
                p = root/'config/components/localization/loop_observer.json'
                cfg = json.loads(p.read_text()); cfg[key] = value; p.write_text(json.dumps(cfg))
                with self.assertRaisesRegex(ValueError, 'mode/resource'):
                    resolve(root, 'test-run', prefix)

    def test_bad_run_id_and_missing_real_binary_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); prefix, _ = self.fixture(root)
            with self.assertRaisesRegex(ValueError, 'run id'):
                resolve(root, '../unsafe', prefix)
            os.chmod(prefix/'lib/loop_fusion/loop_fusion_node', 0o644)
            with self.assertRaises(FileNotFoundError):
                resolve(root, 'test-run', prefix)

    def test_online_extrinsic_estimation_is_not_treated_as_fixed_calibration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); prefix, session = self.fixture(root)
            p = root/'config/components/localization/vins_sim.json'
            settings = json.loads(p.read_text()); settings['estimate_extrinsic'] = 1
            p.write_text(json.dumps(settings))
            manifest_path = session/'session.json'
            manifest = json.loads(manifest_path.read_text())
            manifest['settings_sha256'] = hashlib.sha256(p.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'fresh stereo-IMU'):
                resolve(root, 'test-run', prefix)


if __name__ == '__main__':
    unittest.main()
