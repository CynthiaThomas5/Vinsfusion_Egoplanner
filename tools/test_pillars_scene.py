"""The NavRL visual-only field must become real static obstacles, not a mock map."""
from pathlib import Path
import hashlib
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from prepare_px4_vio_bootstrap_world import generate
from scene_config import resolve_scene

ROOT = Path(__file__).resolve().parents[1]
PX4 = ROOT/'external/PX4-Autopilot'


class PillarsSceneTests(unittest.TestCase):
    def test_visual_primitives_gain_matching_collisions_and_natural_materials(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)/'pillars.sdf'
            report = generate(ROOT,PX4/'Tools/simulation/gz/worlds/default.sdf',
                              PX4/'src/modules/simulation/gz_bridge/server.config',output,'pillars')
            source = ET.parse(ROOT/resolve_scene(ROOT,'pillars')['geometry']).find('world')
            world = ET.parse(output).find('world')
            self.assertEqual(len(world.findall('model')),61)
            self.assertEqual(len(report['collisions_added_from_visuals']),60)
            for model in source.findall('model'):
                if model.get('name')=='ground_plane':continue
                target = world.find(f"model[@name='{model.get('name')}']")
                self.assertEqual(target.findtext('pose'),model.findtext('pose'))
                for link in model.findall('link'):
                    self.assertEqual(len(link.findall('collision')),0)
                    visual=link.find('visual')
                    physical=target.find(f"link[@name='{link.get('name')}']/collision")
                    normalize=lambda e:ET.canonicalize(ET.tostring(e,encoding='unicode'),strip_text=True)
                    self.assertEqual(normalize(physical.find('geometry')),normalize(visual.find('geometry')))
            self.assertEqual(len(world.findall('.//collision/geometry/cylinder')),30)
            self.assertEqual(len(world.findall('.//collision/geometry/box')),30)
            self.assertEqual(len(world.findall('.//collision/geometry/plane')),1)
            self.assertEqual(float(world.findtext('physics/max_step_size')),.004)
            self.assertFalse(world.findall('.//sensor'))
            self.assertFalse(world.findall('.//material/script'))
            text=output.read_text()
            self.assertNotIn('obstacles.png',text)
            self.assertNotIn('/textures/floor.png',text)
            self.assertIn('natural_terrazzo.png',text)
            self.assertEqual(report['material_profile']['profile'],'natural')
            floor=world.find("model[@name='ground_plane']/link")
            self.assertEqual(len(floor.findall('collision')),1)
            self.assertEqual(len(floor.findall('visual')),26)
            colors={v.findtext('material/diffuse') for m in world.findall('model')
                    if m.get('name')!='ground_plane' for v in m.findall('link/visual')}
            self.assertGreaterEqual(len(colors),4)

    def test_asset_and_upstream_bytes_are_hash_bound(self):
        d=json.loads((ROOT/'dependencies/sources.json').read_text())
        s=next(s for s in d['sources'] if s['id']=='navrl_pillars_world')
        self.assertEqual(hashlib.sha256((ROOT/s['target']).read_bytes()).hexdigest(),s['upstream_sha256'])
        texture=json.loads((ROOT/'simulation/textures/natural_terrazzo.json').read_text())
        self.assertEqual(hashlib.sha256((ROOT/texture['asset']).read_bytes()).hexdigest(),texture['sha256'])
