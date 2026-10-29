#!/usr/bin/env python3
"""Contract tests for config-derived no-truth VIO/EGO launch inputs."""
import json
import hashlib
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/own/uav_px4_bridge'))
sys.path.insert(0, str(ROOT / 'src/own/uav_sim'))

from uav_px4_bridge.vio_ego_bringup import (  # noqa: E402
    bridge_position_command_remappings,
    prepare_vio_ego_run,
    resolve_vio_ego_configuration,
)


class VioEgoBringupConfigTests(unittest.TestCase):
    def test_n08_compute_only_remaps_only_the_bridge_trajectory_input(self):
        self.assertEqual(bridge_position_command_remappings(False), [])
        self.assertEqual(
            bridge_position_command_remappings(True),
            [('/position_cmd', '/n08/compute_only_position_cmd')])
        with self.assertRaisesRegex(ValueError, 'must be boolean'):
            bridge_position_command_remappings('true')

    def test_launch_values_follow_project_config_and_sdf(self):
        resolved = resolve_vio_ego_configuration(ROOT)
        args = resolved['ego_launch_arguments']
        planner = resolved['planner']
        k = resolved['rig']['cameras']['depth']['K']
        self.assertEqual(args['drone_id'], planner['drone_id'])
        self.assertEqual(args['map_size_x_'], planner['map_size_m'][0])
        self.assertEqual(args['max_vel'], planner['max_velocity_m_s'])
        self.assertEqual(args['max_acc'], planner['max_acceleration_m_s2'])
        self.assertEqual(args['obstacles_inflation'], planner['obstacles_inflation_m'])
        envelope = json.loads((ROOT / 'config/components/navigation/vehicle_envelope.json').read_text())
        self.assertEqual(args['obstacles_inflation'],
                         envelope['spatial_budget']['body_reference_clearance_radius_m'])
        self.assertTrue(args['official_ego_collision_policy'])
        self.assertEqual(args['terminal_hold_neighborhood'], 0.0)
        self.assertFalse(args['n10_voxel_trace_enabled'])
        self.assertEqual([args[f'n10_voxel_trace_center_{axis}'] for axis in 'xyz'],
                         [0.0, 0.0, 0.0])
        self.assertEqual([args[f'n10_voxel_trace_half_{axis}'] for axis in 'xyz'],
                         [0.0, 0.0, 0.0])
        self.assertEqual(args['ground_height'], planner['ground_height_m'])
        self.assertLessEqual(args['ground_height'],
                             envelope['map_policy']['required_map_bottom_m'])
        self.assertEqual(args['cx'], k[2])
        self.assertEqual(args['cy'], k[5])
        self.assertEqual(args['fx'], k[0])
        self.assertEqual(args['fy'], k[4])
        self.assertEqual(args['odometry_topic'], '/localization/optimized_imu_odom')
        self.assertEqual(args['camera_pose_topic'], 'camera_pose')
        self.assertEqual(args['depth_topic'], 'depth_image')

    def test_mismatched_drone_topics_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self._copy_runtime_inputs(Path(temp))
            path = root / 'config/components/mapping/ego_planner.json'
            config = json.loads(path.read_text())
            config['drone_id'] = 1
            path.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError, 'drone ids differ'):
                resolve_vio_ego_configuration(root)

    def test_profile_rejects_online_truth_or_gps(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self._copy_runtime_inputs(Path(temp))
            path = root / 'config/profiles/vio_closed_loop.json'
            config = json.loads(path.read_text())
            config['gps_position_aiding_allowed'] = True
            path.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError, 'prohibited online position'):
                resolve_vio_ego_configuration(root)

    def test_selected_planner_config_drives_launch_and_manifest_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self._copy_runtime_inputs(Path(temp))
            relative = 'config/components/mapping/ego_planner_slow_probe.json'
            config = json.loads((root / 'config/components/mapping/ego_planner.json').read_text())
            config['max_velocity_m_s'] = 0.25
            config['max_acceleration_m_s2'] = 0.4
            (root / relative).write_text(json.dumps(config))

            resolved = resolve_vio_ego_configuration(root, relative)
            self.assertEqual(resolved['ego_launch_arguments']['max_vel'], 0.25)
            self.assertEqual(resolved['ego_launch_arguments']['max_acc'], 0.4)
            self.assertEqual(resolved['ego_launch_arguments']['obstacles_inflation'],
                             config['obstacles_inflation_m'])
            self.assertIn(relative, resolved['source_files'])
            self.assertNotIn('config/components/mapping/ego_planner.json',
                             resolved['source_files'])

            run = prepare_vio_ego_run(root, 'vio-ego-slow-probe-001', relative)
            manifest = json.loads((run['run_directory'] / 'launch-manifest.json').read_text())
            self.assertEqual(manifest['planner_config'], relative)
            self.assertEqual(manifest['source_sha256'][relative],
                             hashlib.sha256((root / relative).read_bytes()).hexdigest())

    def test_n10_voxel_trace_config_is_read_only_launch_diagnostic(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self._copy_runtime_inputs(Path(temp))
            relative = 'config/components/mapping/ego_planner_trace_probe.json'
            config = json.loads((root / 'config/components/mapping/ego_planner.json').read_text())
            config['n10_voxel_update_trace'] = {
                'enabled': True,
                'roi_center_odom_m': [8.0, 0.0, 1.1],
                'roi_half_extents_m': [0.6, 0.6, 1.6],
            }
            (root / relative).write_text(json.dumps(config))
            resolved = resolve_vio_ego_configuration(root, relative)
            args = resolved['ego_launch_arguments']
            self.assertTrue(args['n10_voxel_trace_enabled'])
            self.assertEqual([args[f'n10_voxel_trace_center_{axis}'] for axis in 'xyz'],
                             [8.0, 0.0, 1.1])
            self.assertEqual([args[f'n10_voxel_trace_half_{axis}'] for axis in 'xyz'],
                             [0.6, 0.6, 1.6])
            self.assertIn(relative, resolved['source_files'])

    def test_planner_config_must_be_inside_project(self):
        with self.assertRaisesRegex(ValueError, 'inside the project root'):
            resolve_vio_ego_configuration(ROOT, '../outside.json')

    def test_negative_obstacle_inflation_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self._copy_runtime_inputs(Path(temp))
            path = root / 'config/components/mapping/ego_planner.json'
            config = json.loads(path.read_text())
            config['obstacles_inflation_m'] = -0.1
            path.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError, 'finite non-negative number'):
                resolve_vio_ego_configuration(root)

    def test_custom_n05_geometry_consistency_refusals_are_not_applied(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self._copy_runtime_inputs(Path(temp))
            planner_path = root / 'config/components/mapping/ego_planner.json'
            config = json.loads(planner_path.read_text())
            config['obstacles_inflation_m'] = 0.5
            config['ground_height_m'] = -0.8
            planner_path.write_text(json.dumps(config))

            envelope_path = root / 'config/components/navigation/vehicle_envelope.json'
            envelope = json.loads(envelope_path.read_text())
            envelope['geometry']['orientation_invariant_rotor_sweep_radius_m'] = 0.2
            envelope['spatial_budget']['combined_uncertainty_margin_m'] = 0.3
            envelope['spatial_budget']['body_reference_clearance_radius_m'] = 0.9
            envelope['map_policy']['terminal_hold_neighborhood_radius_m'] = 1.25
            envelope['map_policy']['required_map_bottom_m'] = -0.1
            envelope_path.write_text(json.dumps(envelope))

            resolved = resolve_vio_ego_configuration(root)
            args = resolved['ego_launch_arguments']
            self.assertEqual(args['obstacles_inflation'], 0.5)
            self.assertEqual(args['ground_height'], -0.8)
            self.assertEqual(args['terminal_hold_neighborhood'], 0.0)

    def test_terminal_hold_radius_above_project_cap_is_passed_through(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self._copy_runtime_inputs(Path(temp))
            nav_path = root / 'config/components/navigation/task_supervisor.json'
            navigation = json.loads(nav_path.read_text())
            navigation['collision_policy'] = 'known_free'
            nav_path.write_text(json.dumps(navigation))

            envelope_path = root / 'config/components/navigation/vehicle_envelope.json'
            envelope = json.loads(envelope_path.read_text())
            envelope['map_policy']['terminal_hold_neighborhood_radius_m'] = 1.25
            envelope_path.write_text(json.dumps(envelope))

            resolved = resolve_vio_ego_configuration(root)
            self.assertEqual(resolved['ego_launch_arguments']['terminal_hold_neighborhood'], 1.25)

    def test_prepare_creates_fresh_hashed_session_and_refuses_reuse(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self._copy_runtime_inputs(Path(temp))
            run = prepare_vio_ego_run(root, 'vio-ego-test-001')
            manifest = json.loads((run['run_directory'] / 'launch-manifest.json').read_text())
            session = json.loads(run['session_manifest'].read_text())
            self.assertEqual(manifest['run_id'], 'vio-ego-test-001')
            self.assertEqual(manifest['model_sha256'], session['model_sha256'])
            self.assertTrue((run['session_directory'] / 'vins.yaml').is_file())
            with self.assertRaises(FileExistsError):
                prepare_vio_ego_run(root, 'vio-ego-test-001')

    @staticmethod
    def _copy_runtime_inputs(destination):
        shutil.copytree(ROOT / 'config', destination / 'config')
        (destination / 'simulation/models/d435i').mkdir(parents=True)
        (destination / 'simulation/models/d435i/model.sdf').symlink_to(
            ROOT / 'simulation/models/d435i/model.sdf')
        (destination / 'src/own').mkdir(parents=True)
        (destination / 'src/own/uav_sim').symlink_to(ROOT / 'src/own/uav_sim')
        (destination / 'tools').mkdir()
        (destination / 'tools/generate_vins_config.py').symlink_to(
            ROOT / 'tools/generate_vins_config.py')
        return destination


if __name__ == '__main__':
    unittest.main()
