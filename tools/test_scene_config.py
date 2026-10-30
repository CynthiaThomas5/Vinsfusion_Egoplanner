"""Scene selection must bind geometry/spawn/task without changing PX4 systems."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from scene_config import resolve_scene
from resolve_sim_spawn import resolve_spawn_pose
from prepare_px4_vio_bootstrap_world import generate

ROOT = Path(__file__).resolve().parents[1]
PX4 = ROOT/'external/PX4-Autopilot'


class SceneConfigTests(unittest.TestCase):
    def test_floorplan_binds_its_geometry_spawn_and_goal(self):
        scene = resolve_scene(ROOT, 'floorplan2')
        spawn = resolve_spawn_pose(ROOT, scene_name='floorplan2')
        goal = json.loads((ROOT/scene['goal_profile']).read_text())
        self.assertEqual(spawn['spawn_pose_xyzrpy'], [-8,-8,.3,0,0,0])
        self.assertEqual(goal['target_offset_enu_m'], [16,0,0])
        self.assertTrue(scene['geometry'].endswith('floorplan2_static.world'))
        self.assertEqual(resolve_scene(ROOT)['scene'], 'room')
        self.assertEqual(resolve_spawn_pose(ROOT, scene_name='room')['source'], 'config/runtime.json')

    def test_unknown_and_escaping_scene_paths_refused(self):
        with self.assertRaisesRegex(ValueError, 'unknown scene'):
            resolve_scene(ROOT, 'missing')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            p = root/'config/components/simulation/scenes.json'
            p.parent.mkdir(parents=True)
            d = json.loads((ROOT/'config/components/simulation/scenes.json').read_text())
            for bad in ('../outside.world', '/tmp/outside.world'):
                d['scenes']['floorplan2']['geometry'] = bad
                p.write_text(json.dumps(d))
                with self.assertRaisesRegex(ValueError, 'relative|escapes'):
                    resolve_scene(root, 'floorplan2')

    def test_upstream_world_and_license_are_hash_bound(self):
        d = json.loads((ROOT/'dependencies/sources.json').read_text())
        s = next(s for s in d['sources'] if s['id']=='navrl_floorplan2_world')
        self.assertEqual(hashlib.sha256((ROOT/s['target']).read_bytes()).hexdigest(),s['upstream_sha256'])
        self.assertEqual(hashlib.sha256((ROOT/s['local_license_file']).read_bytes()).hexdigest(),s['license_sha256'])
        self.assertEqual(s['reference_revision'],'3725bcc2e7c1be4ecf1455d922299ae85042603a')

    def test_floorplan_composition_retains_collisions_and_px4_timing(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)/'floorplan.sdf'
            report = generate(ROOT, PX4/'Tools/simulation/gz/worlds/default.sdf',
                              PX4/'src/modules/simulation/gz_bridge/server.config', output, 'floorplan2')
            world = ET.parse(output).find('world')
            source = ET.parse(ROOT/resolve_scene(ROOT,'floorplan2')['geometry']).find('world')
            self.assertEqual(report['scene'],'floorplan2')
            def collisions(node):
                return [ET.canonicalize(ET.tostring(c,encoding='unicode'),strip_text=True)
                        for c in node.findall('.//collision')]
            self.assertEqual(collisions(world),collisions(source))
            self.assertEqual(float(world.findtext('physics/max_step_size')), .004)
            self.assertIsNone(world.find('state'))
            self.assertIsNone(world.find('.//sensor'))
            self.assertIsNone(world.find('.//material/script'))
            self.assertIsNone(world.find('.//mesh'))
            self.assertIn('gz::sim::systems::Contact',report['world_plugins'])
            self.assertEqual({m.get('name') for m in world.findall('model')},{'ground_plane','floorplan2'})
            for visual in world.findall('.//visual'):
                self.assertIsNotNone(visual.find('material/pbr/metal/albedo_map'))

    def test_explicit_room_selection_keeps_original_world_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            a,b = Path(temp)/'a.sdf',Path(temp)/'b.sdf'
            base = PX4/'Tools/simulation/gz/worlds/default.sdf'
            server = PX4/'src/modules/simulation/gz_bridge/server.config'
            generate(ROOT,base,server,a)
            generate(ROOT,base,server,b,'room')
            self.assertEqual(a.read_bytes(), b.read_bytes())
