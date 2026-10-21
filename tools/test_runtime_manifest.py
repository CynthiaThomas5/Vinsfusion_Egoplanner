import json
import tempfile
import unittest
from pathlib import Path
from runtime_manifest import snapshot


class RuntimeManifestTest(unittest.TestCase):
    def test_actual_runtime_and_configuration_changes_are_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {'config/runtime.json': json.dumps({'px4_build': 'external/build'}),
                     'config/flight.json': '{}', 'src/own/node.py': 'control',
                     'install/pkg/lib/vins_node': 'binary', 'external/build/bin/px4': 'px4',
                     'dependencies/sources.json': '{}', 'config/local/private.json': 'private',
                     'src/own/__pycache__/cache.pyc': 'cache'}
            for rel, content in files.items():
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            first = snapshot(root)
            self.assertNotIn('config/local/private.json', first['files'])
            self.assertEqual(first, snapshot(root))
            binary = root / 'install/pkg/lib/vins_node'
            binary.write_text('changed binary')
            self.assertNotEqual(first['sha256'], snapshot(root)['sha256'])
            binary.write_text('binary')
            (root / 'config/flight.json').write_text('{"speed": 1}')
            self.assertNotEqual(first['sha256'], snapshot(root)['sha256'])


if __name__ == '__main__':
    unittest.main()
