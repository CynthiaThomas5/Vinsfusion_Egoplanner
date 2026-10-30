import json
from pathlib import Path
import unittest
from audit_vehicle_envelope import audit, box_corners
from n05_entry import collision_primitives


ROOT = Path(__file__).resolve().parents[1]


class VehicleEnvelopeTests(unittest.TestCase):
    def test_mount_geometry_is_relative_to_declared_base_link_mount(self):
        primitives = {item['name']: item for item in collision_primitives()}
        self.assertAlmostEqual(primitives['base_link_collision_3']['center_imu_m'][2],
                               -0.18975)
        self.assertAlmostEqual(primitives['base_link_collision_4']['center_imu_m'][2],
                               -0.18975)
        self.assertEqual(primitives['d435i_housing_collision']['center_imu_m'],
                         [0.0, 0.0, 0.0])

    def test_rotor_sweep_is_included_in_current_model_envelope(self):
        result = audit()
        self.assertEqual(len(result['rotor_sweeps']), 4)
        self.assertGreaterEqual(result['configured_obstacle_inflation_m'],
                                1.5 * result['max_horizontal_radius_level_all_rotor_angles_m'])
        self.assertEqual(result['inflation_steps'], 2)
        self.assertEqual(result['d435i_housing_collision_count'], 1)
        self.assertAlmostEqual(result['max_orientation_invariant_radius_all_rotor_angles_m'],
                               0.21497339951724262)
        self.assertGreater(result['max_horizontal_radius_level_all_rotor_angles_m'],
                           0.19)
        planner = json.loads((ROOT/'config/components/mapping/ego_planner.json').read_text())
        policy = json.loads((ROOT/'config/components/navigation/vehicle_envelope.json').read_text())
        subground = policy['ground_contact']['subground_voxel_exclusion']
        self.assertTrue(subground['enabled'])
        self.assertEqual(set(subground['phases']),
                         {'TAKEOFF_CONTACT', 'ASCENT', 'DESCENT', 'LANDING_CONTACT'})
        self.assertNotIn('HOLD', subground['phases'])
        self.assertAlmostEqual(subground['surface_voxel_boundary_allowance_fraction'], 0.5)
        self.assertAlmostEqual(planner['obstacles_inflation_m'],
                               policy['spatial_budget']['body_reference_clearance_radius_m'])
        self.assertLessEqual(planner['ground_height_m'],
                             policy['map_policy']['required_map_bottom_m'])
        self.assertLessEqual(policy['map_policy']['required_map_bottom_m'],
                             -(policy['spatial_budget']['body_reference_clearance_radius_m']
                               + policy['map_policy']['terminal_hold_neighborhood_radius_m']))

    def test_box_corner_transform(self):
        corners = list(box_corners((2, 3, 4, 0, 0, 0), (2, 4, 6)))
        self.assertEqual(len(set(corners)), 8)
        self.assertIn((1, 1, 1), corners)
        self.assertIn((3, 5, 7), corners)


if __name__ == '__main__':
    unittest.main()
