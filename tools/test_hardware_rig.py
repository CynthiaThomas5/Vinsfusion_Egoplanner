#!/usr/bin/env python3
"""Focused HW03 rig/session contracts; no ROS runtime or device access."""
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/own/uav_sim'))
sys.path.insert(0, str(ROOT / 'src/own/uav_px4_bridge'))
sys.path.insert(0, str(ROOT / 'tools'))

from uav_sim.geometry import load_rig, load_session_rig  # noqa: E402
from generate_vins_config import generate  # noqa: E402
from uav_px4_bridge.vio_ego_bringup import resolve_vio_ego_configuration  # noqa: E402


def multiply(a, b):
    return [sum(a[row*4+k] * b[k*4+column] for k in range(4))
            for row in range(4) for column in range(4)]


def inverse_rigid(transform):
    rotation = [transform[row*4+column]
                for row in range(3) for column in range(3)]
    translation = [transform[3], transform[7], transform[11]]
    inverse = [rotation[column*3+row]
               for row in range(3) for column in range(3)]
    inverse_translation = [-sum(inverse[row*3+column] * translation[column]
                                for column in range(3)) for row in range(3)]
    return [inverse[0], inverse[1], inverse[2], inverse_translation[0],
            inverse[3], inverse[4], inverse[5], inverse_translation[1],
            inverse[6], inverse[7], inverse[8], inverse_translation[2],
            0.0, 0.0, 0.0, 1.0]


class HardwareRigTests(unittest.TestCase):
    def test_current_serial_rig_geometry_and_provisional_mount(self):
        path = ROOT / 'config/hardware/rig.json'
        raw = json.loads(path.read_text())
        rig = load_rig(path)
        self.assertEqual(raw['identity']['api_serial'], '243622073269')
        self.assertEqual(rig['source_kind'], 'hardware_json')
        self.assertAlmostEqual(rig['stereo_baseline_m'], 0.04991940408945083, places=9)
        right = raw['cameras']['infra2']
        self.assertAlmostEqual(-right['P'][3] / right['K'][0],
                               rig['stereo_baseline_m'], delta=1e-8)
        self.assertEqual(raw['cameras']['infra1']['image_frame'],
                         raw['cameras']['infra2']['image_frame'])
        self.assertFalse(rig['rgb_enabled'])
        self.assertFalse(rig['airframe_mount']['control_usable'])
        self.assertIsNone(rig['airframe_mount']['T_airframe_imu'])

        left_t = rig['cameras']['infra1']['T_imu_optical']
        right_t = rig['cameras']['infra2']['T_imu_optical']
        identity = multiply(left_t, inverse_rigid(left_t))
        for actual, expected in zip(identity, [1, 0, 0, 0, 0, 1, 0, 0,
                                                0, 0, 1, 0, 0, 0, 0, 1]):
            self.assertAlmostEqual(actual, expected, places=8)
        left_to_right = multiply(inverse_rigid(left_t), right_t)
        baseline = (sum(left_to_right[index] ** 2 for index in (3, 7, 11)) ** 0.5)
        self.assertAlmostEqual(baseline, rig['stereo_baseline_m'], places=8)
        forward = [rig['cameras']['infra1']['R_body_optical'][index]
                   for index in (2, 5, 8)]
        self.assertGreater(forward[2], 0.999)

    def test_hardware_session_hashes_outputs_and_zero_bias_policy(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'hardware-session'
            manifest = generate(ROOT, output, epoch='a' * 32,
                                rig_config='config/hardware/rig.json')
            self.assertEqual(manifest['rig_config'], 'config/hardware/rig.json')
            self.assertEqual(manifest['settings_config'],
                             'config/components/localization/vins_hardware.json')
            self.assertEqual(manifest['health_config'],
                             'config/components/localization/health_hardware.json')
            self.assertEqual(manifest['health_sha256'], hashlib.sha256(
                (ROOT / manifest['health_config']).read_bytes()).hexdigest())
            self.assertEqual(manifest['calibration_id'], manifest['rig_sha256'])
            self.assertEqual(manifest['rig_sha256'], hashlib.sha256(
                (ROOT / manifest['rig_config']).read_bytes()).hexdigest())
            self.assertEqual(load_session_rig(ROOT, manifest)['calibration_sha256'],
                             manifest['calibration_id'])
            mismatched = dict(manifest, rig_sha256='0' * 64)
            with self.assertRaisesRegex(ValueError, 'rig hash mismatch'):
                load_session_rig(ROOT, mismatched)
            with self.assertRaisesRegex(ValueError, 'differs from the VINS session'):
                load_session_rig(ROOT, manifest, 'simulation/models/d435i/model.sdf')
            self.assertEqual(manifest['settings_sha256'], hashlib.sha256(
                (ROOT / manifest['settings_config']).read_bytes()).hexdigest())
            for name, digest in manifest['files_sha256'].items():
                self.assertEqual(digest, hashlib.sha256((output / name).read_bytes()).hexdigest())
                self.assertIn(manifest['rig_sha256'], (output / name).read_text())
            vins = (output / 'vins.yaml').read_text()
            self.assertTrue(vins.startswith('%YAML:1.0\n---\n'))
            self.assertIn('known_zero_gyro_bias: 0', vins)
            self.assertNotIn('opencv_threads:', vins)
            self.assertEqual(manifest['runtime']['opencv_threads'], 2)
            self.assertIn('/sensors/d435i/infra1/image_rect_raw', vins)
            self.assertIn('td: -0.009338100822726176', vins)
            rig = json.loads((ROOT / 'config/hardware/rig.json').read_text())
            for index, name in enumerate(('infra1', 'infra2')):
                match = re.search(r'body_T_cam{}:.*?data: (\[[^\]]+\])'.format(index),
                                  vins, re.S)
                actual = json.loads(match.group(1))
                expected = rig['cameras'][name]['T_imu_optical']
                for value, expected_value in zip(actual, expected):
                    self.assertAlmostEqual(value, expected_value, places=10)
    def test_planner_and_bridge_resolve_hardware_intrinsics_without_mount_eligibility(self):
        resolved = resolve_vio_ego_configuration(
            ROOT, rig_config='config/hardware/rig.json')
        k = resolved['rig']['cameras']['depth']['K']
        args = resolved['ego_launch_arguments']
        self.assertEqual([args['fx'], args['fy'], args['cx'], args['cy']],
                         [k[0], k[4], k[2], k[5]])
        self.assertFalse(resolved['bridge_installation']['control_usable'])
        self.assertIn('config/hardware/rig.json', resolved['source_files'])
        self.assertIn('config/components/localization/vins_hardware.json',
                      resolved['source_files'])
        self.assertNotIn('simulation/models/d435i/model.sdf', resolved['source_files'])

    def test_simulation_generator_keeps_its_sdf_source(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'simulation-session'
            manifest = generate(ROOT, output, epoch='b' * 32)
            model_hash = hashlib.sha256(
                (ROOT / 'simulation/models/d435i/model.sdf').read_bytes()).hexdigest()
            self.assertEqual(manifest['rig_config'], 'simulation/models/d435i/model.sdf')
            self.assertEqual(manifest['settings_config'],
                             'config/components/localization/vins_sim.json')
            self.assertEqual(manifest['model_sha256'], model_hash)
            self.assertEqual(manifest['rig_sha256'], model_hash)
            self.assertEqual(load_session_rig(ROOT, manifest)['calibration_sha256'], model_hash)


if __name__ == '__main__':
    unittest.main()
