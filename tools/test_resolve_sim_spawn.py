import json
from pathlib import Path
import tempfile
import unittest

from resolve_sim_spawn import resolve_spawn_pose


class ResolveSimSpawnTest(unittest.TestCase):
    def _root(self, parent):
        root = Path(parent)
        (root / 'config').mkdir()
        (root / 'config/runtime.json').write_text(json.dumps({
            'spawn_pose': '-6.5,0,0.3,0,0,0'}))
        return root

    def test_default_runtime_pose_is_recorded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._root(directory)
            record = resolve_spawn_pose(root)
            self.assertEqual(record['source'], 'config/runtime.json')
            self.assertEqual(record['spawn_pose_xyzrpy'], [-6.5, 0, 0.3, 0, 0, 0])
            self.assertEqual(len(record['source_sha256']), 64)

    def test_project_relative_profile_overrides_only_for_this_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._root(directory)
            profile = root / 'config/n10-spawn.json'
            profile.write_text(json.dumps({'spawn_pose_xyzrpy': [-8, 0, .3, 0, 0, 0]}))
            record = resolve_spawn_pose(root, 'config/n10-spawn.json')
            self.assertEqual(record['source'], 'config/n10-spawn.json')
            self.assertEqual(record['spawn_pose_xyzrpy'], [-8, 0, .3, 0, 0, 0])

    def test_rejects_absolute_and_out_of_project_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._root(directory)
            with self.assertRaisesRegex(ValueError, 'project-relative'):
                resolve_spawn_pose(root, '/tmp/spawn.json')
            with self.assertRaisesRegex(ValueError, 'existing project-relative'):
                resolve_spawn_pose(root, '../outside.json')

    def test_rejects_wrong_length_and_nonfinite_poses(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self._root(directory)
            profile = root / 'config/bad.json'
            for pose in ([0, 0, 0], [0, 0, 0, 0, 0, float('nan')]):
                profile.write_text(json.dumps({'spawn_pose_xyzrpy': pose}))
                with self.assertRaises(ValueError):
                    resolve_spawn_pose(root, 'config/bad.json')

    def test_runtime_invokes_resolver_with_workspace_absolute_path(self):
        runtime = Path(__file__).resolve().with_name('sim_runtime.sh')
        source = runtime.read_text(encoding='utf-8')
        self.assertIn('python3 /workspace/tools/resolve_sim_spawn.py', source)


if __name__ == '__main__':
    unittest.main()
