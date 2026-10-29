import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from tools.n13_navigation_policy import scene_navigation

ROOT = Path(__file__).resolve().parents[1]


class SceneBindingTests(unittest.TestCase):
    def config(self):
        return {'scene_protocol': {'status':'ready', 'world_geometry_sha256':'world',
            'evaluator_sha256':hashlib.sha256((ROOT/'tools/debug_truth/evaluate_n13_route.py').read_bytes()).hexdigest()}}

    def test_missing_world_insufficient(self):
        with tempfile.TemporaryDirectory() as p:
            r=scene_navigation(self.config(),Path(p))
            self.assertEqual(r['status'],'INSUFFICIENT')
            self.assertFalse(r['checks']['world_matches_release'])

    def test_wrong_evaluator_insufficient(self):
        with tempfile.TemporaryDirectory() as p:
            c=self.config();c['scene_protocol']['evaluator_sha256']='other'
            r=scene_navigation(c,Path(p))
            self.assertFalse(r['checks']['evaluator_matches_release'])
            self.assertEqual(r['status'],'INSUFFICIENT')

    def test_valid_binding_without_observation_never_passes(self):
        with tempfile.TemporaryDirectory() as p:
            (Path(p)/'world.json').write_text(json.dumps({'project_geometry_sha256':'world'}))
            r=scene_navigation(self.config(),Path(p))
            self.assertTrue(all(r['checks'].values()))
            self.assertEqual(r['status'],'INSUFFICIENT')

    def test_draft_never_passes(self):
        with tempfile.TemporaryDirectory() as p:
            c=self.config();c['scene_protocol']['status']='pending'
            r=scene_navigation(c,Path(p))
            self.assertFalse(r['checks']['released_protocol'])
