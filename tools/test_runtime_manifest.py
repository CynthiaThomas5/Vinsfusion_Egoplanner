import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from runtime_manifest import snapshot


class RuntimeManifestTests(unittest.TestCase):
    def test_navigation_supervisor_launcher_is_fingerprinted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            launcher = (root / 'install/uav_navigation/lib/uav_navigation'
                        / 'navigation_supervisor')
            launcher.parent.mkdir(parents=True)
            launcher.write_bytes(b'navigation-supervisor-entrypoint')

            px4 = root / 'external/PX4-Autopilot/build/px4_sitl_default/bin/px4'
            px4.parent.mkdir(parents=True)
            px4.write_bytes(b'px4')
            (root / 'config').mkdir()
            (root / 'config/runtime.json').write_text(json.dumps({
                'px4_build': 'external/PX4-Autopilot/build/px4_sitl_default',
            }))
            (root / 'dependencies').mkdir()
            (root / 'dependencies/sources.json').write_text('{}')

            files = snapshot(root)['files']
            path = 'install/uav_navigation/lib/uav_navigation/navigation_supervisor'
            self.assertEqual(files[path],
                             hashlib.sha256(b'navigation-supervisor-entrypoint').hexdigest())

    def test_runtime_tool_sources_are_fingerprinted_but_tests_are_not(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            runner = root / 'tools/run_n08_braking_trial.py'
            helper = root / 'tools/n08_trial_gate.py'
            shell = root / 'tools/mission_runtime.sh'
            test_script = root / 'tools/test_runtime_manifest.py'
            runner.parent.mkdir(parents=True)
            runner.write_bytes(b'n08-runtime-runner')
            helper.write_bytes(b'n08-runtime-geometry-gate')
            shell.write_bytes(b'n08-runtime-shell')
            test_script.write_bytes(b'development-only-test')

            px4 = root / 'external/PX4-Autopilot/build/px4_sitl_default/bin/px4'
            px4.parent.mkdir(parents=True)
            px4.write_bytes(b'px4')
            (root / 'config').mkdir()
            (root / 'config/runtime.json').write_text(json.dumps({
                'px4_build': 'external/PX4-Autopilot/build/px4_sitl_default',
            }))
            (root / 'dependencies').mkdir()
            (root / 'dependencies/sources.json').write_text('{}')

            files = snapshot(root)['files']
            self.assertEqual(
                files['tools/run_n08_braking_trial.py'],
                hashlib.sha256(b'n08-runtime-runner').hexdigest())
            self.assertEqual(
                files['tools/n08_trial_gate.py'],
                hashlib.sha256(b'n08-runtime-geometry-gate').hexdigest())
            self.assertEqual(
                files['tools/mission_runtime.sh'],
                hashlib.sha256(b'n08-runtime-shell').hexdigest())
            self.assertNotIn('tools/test_runtime_manifest.py', files)


if __name__ == '__main__':
    unittest.main()
