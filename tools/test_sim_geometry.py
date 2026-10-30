#!/usr/bin/env python3
import math
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/own/uav_sim'))
from uav_sim.geometry import calibration, px4_sensor_mount, robot_description


class GeometryTest(unittest.TestCase):
    def test_flight_imu_samples_every_room_physics_tick(self):
        model = ET.parse(ROOT / 'simulation/models/d435i/model.sdf')
        world = ET.parse(ROOT / 'simulation/worlds/ego.sdf')
        rate = float(model.findtext("model/link/sensor[@name='imu']/update_rate"))
        step = float(world.findtext('world/physics/max_step_size'))
        self.assertAlmostEqual(rate * step, 1.0)

    def test_intensity_images_keep_near_floor_texture(self):
        model = ET.parse(ROOT / 'simulation/models/d435i/model.sdf')
        sensors = {s.get('name'): s for s in model.findall('model/link/sensor')}
        for name in ('infra1', 'infra2', 'color'):
            camera = sensors[name].find('camera')
            height = int(camera.findtext('image/height'))
            width = int(camera.findtext('image/width'))
            focal = width / (2 * math.tan(float(camera.findtext('horizontal_fov')) / 2))
            # At 5 cm optical height, the bottom pixel still sees real floor.
            nearest_floor_x = .05 * focal / (height - 1 - height / 2)
            self.assertLess(float(camera.findtext('clip/near')), nearest_floor_x)
        self.assertEqual(float(sensors['depth'].findtext('camera/clip/near')), .2)

    def test_rigid_stereo_and_optical_axes(self):
        model = ROOT / 'simulation/models/d435i/model.sdf'
        rig = calibration(model)
        self.assertAlmostEqual(rig['stereo_baseline_m'], .05)
        self.assertEqual(rig['cameras']['depth']['translation'], rig['cameras']['infra1']['translation'])
        rotation = rig['cameras']['infra1']['R_body_optical']
        self.assertEqual(rotation[2::3], [1, 0, 0])  # optical forward is body forward
        self.assertEqual(rotation[0::3], [0, -1, 0])  # optical right is body right
        robot = ET.fromstring(robot_description(model))
        self.assertEqual(len(robot.findall('joint')), 5)
        for joint in robot.findall('joint'):
            rpy = [float(v) for v in joint.find('origin').get('rpy').split()]
            if joint.find('child').get('link') != 'd435i_imu_frame':
                self.assertEqual(rpy, [-math.pi/2, 0, -math.pi/2])

    def test_rotated_mount_rejected(self):
        model = ET.parse(ROOT / 'simulation/models/d435i/model.sdf')
        model.find('model/link/sensor/pose').text = '0 0 0 0 0 0.1'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'model.sdf'
            model.write(path)
            with self.assertRaises(ValueError):
                calibration(path)

    def test_px4_leverarm_is_derived_from_x500_d435i_sdf(self):
        wrapper = ET.parse(ROOT / 'simulation/models/x500_d435i/model.sdf').getroot().find('model')
        include = wrapper.find("include[uri='model://d435i']")
        joint = wrapper.find("joint[@name='d435i_mount']")
        self.assertEqual(include.find('pose').get('relative_to'), 'base_link')
        self.assertEqual(joint.find('pose').get('relative_to'), 'base_link')
        self.assertEqual(include.findtext('pose'), joint.findtext('pose'))
        mount = px4_sensor_mount(ROOT / 'simulation/models/x500_d435i/model.sdf')
        self.assertEqual(mount['parent_frame'], 'base_link')
        self.assertEqual(mount['sensor_frame'], 'd435i_imu')
        self.assertEqual(mount['translation_frd_m'], [0.0, 0.0, -0.08])
        self.assertEqual(len(mount['model_sha256']), 64)


if __name__ == '__main__':
    unittest.main()
