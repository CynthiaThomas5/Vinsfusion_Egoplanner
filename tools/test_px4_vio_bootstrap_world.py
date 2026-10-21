#!/usr/bin/env python3
"""Check imported scenery matches physical obstacles and preserves PX4 systems."""

from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from prepare_px4_vio_bootstrap_world import generate  # noqa: E402


class Px4VioBootstrapWorldTests(unittest.TestCase):
    def test_scene_cannot_add_dynamic_obstacles_or_another_sensor(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            scene = temp / 'simulation/worlds/ego.sdf'
            scene.parent.mkdir(parents=True)
            base = temp / 'px4.sdf'
            base.write_text('<sdf version="1.9"><world name="default"/></sdf>')
            for fault in ('dynamic', 'sensor'):
                with self.subTest(fault=fault):
                    tree = ET.parse(ROOT / 'simulation/worlds/ego.sdf')
                    if fault == 'dynamic':
                        tree.find('world/model/static').text = 'false'
                    else:
                        ET.SubElement(tree.find('world/model/link'), 'sensor',
                                      name='unexpected_camera', type='camera')
                    tree.write(scene)
                    output = temp / f'{fault}.sdf'
                    with self.assertRaisesRegex(ValueError, 'static models|must not add sensors'):
                        generate(temp, base, temp / 'unused-server.config', output)
                    self.assertFalse(output.exists())

    def test_imported_world_matches_recorded_source_hash(self):
        sources = json.loads((ROOT / 'dependencies/sources.json').read_text())
        entry = next(source for source in sources['sources'] if source['id'] == 'ego_world')
        self.assertEqual(hashlib.sha256((ROOT / entry['target']).read_bytes()).hexdigest(),
                         entry['target_sha256'])
        for patch in entry['patches']:
            self.assertEqual(hashlib.sha256((ROOT / patch).read_bytes()).hexdigest(),
                             entry['patch_sha256'][patch])

    def test_merges_project_scene_with_px4_environment_and_world_systems(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            base = temp / 'px4-default.sdf'
            base.write_text('''<?xml version="1.0"?>
<sdf version="1.9"><world name="default">
  <physics name="px4-physics" type="ignored"><max_step_size>0.004</max_step_size></physics>
  <gravity>0 0 -9.8</gravity>
  <magnetic_field>6e-06 2.3e-05 -4.2e-05</magnetic_field>
  <atmosphere type="adiabatic"/>
  <spherical_coordinates><latitude_deg>47.4</latitude_deg></spherical_coordinates>
  <model name="ground_plane"><static>true</static><link name="ground"/></model>
</world></sdf>\n''')
            server = temp / 'server.config'
            server.write_text('''<server_config><plugins>
  <plugin entity_name="*" entity_type="world" filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
  <plugin entity_name="*" entity_type="world" filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
  <plugin entity_name="*" entity_type="world" filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
  <plugin entity_name="*" entity_type="world" filename="gz-sim-imu-system" name="gz::sim::systems::Imu"/>
  <plugin entity_name="*" entity_type="world" filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors"><render_engine>ogre2</render_engine></plugin>
  <plugin entity_name="*" entity_type="world" filename="gz-sim-air-pressure-system" name="gz::sim::systems::AirPressure"/>
  <plugin entity_name="*" entity_type="world" filename="gz-sim-magnetometer-system" name="gz::sim::systems::Magnetometer"/>
</plugins></server_config>\n''')
            output = temp / 'vio_initialization.sdf'
            report = generate(ROOT, base, server, output)
            world = ET.parse(output).getroot().find('world')
            model_names = {model.get('name') for model in world.findall('model')}
            room = world.find('model[@name="blank"]')
            plugins = {plugin.get('name') for plugin in world.findall('plugin')}
            text = output.read_text()
            self.assertEqual(report['world'], 'vio_initialization')
            self.assertEqual(len(model_names), 21)
            self.assertIn('ground_plane', model_names)
            self.assertEqual(len(room.findall('link')), 4)
            self.assertIsNone(world.find('model[@name="calibration_wall"]'))
            self.assertTrue(report['project_geometry_source'].endswith('worlds/ego.sdf'))
            for model in world.findall('model'):
                self.assertEqual(model.findtext('static'), 'true')
            for cylinder in (m for m in world.findall('model')
                             if m.get('name').startswith('unit_cylinder')):
                link = cylinder.find('link')
                for dimension in ('radius', 'length'):
                    visual = link.findtext(f'visual/geometry/cylinder/{dimension}')
                    collision = link.findtext(f'collision/geometry/cylinder/{dimension}')
                    self.assertEqual(visual, collision)
            self.assertEqual(world.findtext('model[@name="unit_cylinder_0"]/pose'),
                             '-1.47322 3.48874 0.5 0 -0 1e-06')
            self.assertIsNone(world.find('state'))
            self.assertIsNone(world.find('.//sensor'))
            self.assertIsNone(world.find('.//material/script'))
            self.assertIsNone(world.find('.//uri'))
            self.assertIn('gz::sim::systems::SceneBroadcaster', plugins)
            self.assertIn('gz::sim::systems::UserCommands', plugins)
            self.assertIn('gz::sim::systems::Sensors', plugins)
            self.assertIn('gz::sim::systems::AirPressure', plugins)
            self.assertIn('gz::sim::systems::Magnetometer', plugins)
            self.assertEqual(len(plugins), len(world.findall('plugin')))
            self.assertEqual(world.find('physics/max_step_size').text, '0.004')
            self.assertIsNotNone(world.find('magnetic_field'))
            self.assertIsNotNone(world.find('atmosphere'))
            self.assertIsNotNone(world.find('spherical_coordinates'))
            self.assertNotIn('/debug_truth/', text)
            self.assertNotIn('OdometryPublisher', text)
            self.assertNotIn('sensor_fixture', text)


if __name__ == '__main__':
    sys.exit(unittest.main())
