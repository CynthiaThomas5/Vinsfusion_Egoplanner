import json
from pathlib import Path
import tempfile
import unittest
from tools.n13_navigation_policy import scene_navigation
from tools.n14_navigation_policy import scene_navigation as corridor_scene
ROOT=Path(__file__).resolve().parents[1]

class CorridorBindingTests(unittest.TestCase):
    def config(self):return json.loads((ROOT/'config/acceptance_n14.json').read_text())

    def test_missing_release_cannot_pass(self):
        with tempfile.TemporaryDirectory() as p:
            r=scene_navigation(self.config(),Path(p))
            self.assertEqual(r['id'],'n14_scene_navigation')
            self.assertEqual(r['status'],'INSUFFICIENT')

    def test_wrong_world_cannot_reuse_n13(self):
        with tempfile.TemporaryDirectory() as p:
            c=self.config();c['scene_protocol']['status']='ready'
            (Path(p)/'world.json').write_text(json.dumps({'project_geometry_sha256':'wrong'}))
            r=corridor_scene(c,Path(p));self.assertFalse(r['checks']['world_matches_release'])
            self.assertEqual(r['status'],'INSUFFICIENT')

    def test_matching_hash_without_real_scene_does_not_pass(self):
        with tempfile.TemporaryDirectory() as p:
            c=self.config();c['scene_protocol']['status']='ready'
            (Path(p)/'world.json').write_text(json.dumps({'project_geometry_sha256':c['scene_protocol']['world_geometry_sha256']}))
            r=corridor_scene(c,Path(p));self.assertTrue(all(r['checks'].values()))
            self.assertEqual(r['status'],'INSUFFICIENT')
