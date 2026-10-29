import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from n05_entry import (  # noqa: E402
    check_entry_schedule,
    check_pose,
    collision_primitives,
    check_candidate_landing_schedule,
    fit_ground_plane,
    load_policy,
    make_candidate_landing_schedule,
    make_entry_schedule,
)
from evaluate_n05_entry import n05_results_match  # noqa: E402


class N05EntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load_policy()
        cls.primitives = collision_primitives()

    def make_snapshot(self):
        occupancy = np.zeros((100, 100, 80), dtype=np.int8)
        return {
            'occupancy': occupancy,
            'origin_m': [-5.0, -5.0, -4.0],
            'resolution_m': 0.1,
            'dimensions_xyz': occupancy.shape,
        }

    def test_replay_match_ignores_only_float_roundoff(self):
        online = {
            'accepted': False,
            'reason': 'TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope',
            'ground_plane': {'z_at_center_m': -0.35000000000000003},
            'phases': {'HOLD': {'maximum_unknown_cells': 3}},
        }
        replay = {
            'accepted': False,
            'reason': 'TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope',
            'ground_plane': {'z_at_center_m': -0.3500000000000001},
            'phases': {'HOLD': {'maximum_unknown_cells': 3}},
        }
        self.assertTrue(n05_results_match(replay, online))
        replay['phases']['HOLD']['maximum_unknown_cells'] = 4
        self.assertFalse(n05_results_match(replay, online))

    def test_sdf_geometry_and_budget_are_locked(self):
        self.assertEqual(len(self.primitives), 10)
        self.assertEqual(sum(p['name'] in ('base_link_collision_3', 'base_link_collision_4')
                             for p in self.primitives), 2)
        self.assertAlmostEqual(
            self.policy['spatial_budget']['body_reference_clearance_radius_m'],
            self.policy['geometry']['orientation_invariant_rotor_sweep_radius_m']
            + self.policy['spatial_budget']['combined_uncertainty_margin_m'])

    def test_raw_free_hull_passes_but_unknown_and_occupied_refuse(self):
        snapshot = self.make_snapshot()
        pose = {'center_xyz_m': [0.0, 0.0, 1.0], 'yaw_rad': 0.0}
        self.assertTrue(check_pose(snapshot, pose, 'HOLD', self.policy,
                                   self.primitives)['accepted'])
        snapshot['occupancy'][50, 50, 50] = -1
        self.assertEqual(check_pose(snapshot, pose, 'HOLD', self.policy,
                                    self.primitives)['reason'],
                         'raw_unknown_in_expanded_vehicle_envelope')
        snapshot['occupancy'][50, 50, 50] = 100
        self.assertEqual(check_pose(snapshot, pose, 'HOLD', self.policy,
                                    self.primitives)['reason'],
                         'raw_occupied_in_expanded_vehicle_envelope')

    def test_ground_plane_exception_is_phase_and_state_limited(self):
        snapshot = self.make_snapshot()
        occ = snapshot['occupancy']
        occ[42:59, 42:59, 40] = 100
        center = [0.0, 0.0, 0.32]
        plane = fit_ground_plane(occ, snapshot['origin_m'], 0.1, center, self.policy)
        self.assertTrue(plane['valid'], plane)
        pose = {'center_xyz_m': center, 'yaw_rad': 0.0}
        accepted = check_pose(snapshot, pose, 'TAKEOFF_CONTACT', self.policy,
                              self.primitives, plane, ground_confirmed=True)
        self.assertTrue(accepted['accepted'], accepted)
        refused = check_pose(snapshot, pose, 'TAKEOFF_CONTACT', self.policy,
                             self.primitives, plane, ground_confirmed=False)
        self.assertEqual(refused['reason'], 'ground_contact_not_confirmed')
        refused = check_pose(snapshot, pose, 'HOLD', self.policy,
                             self.primitives, plane, ground_confirmed=True)
        self.assertEqual(refused['reason'], 'raw_occupied_in_expanded_vehicle_envelope')

    def test_ground_plane_includes_voxels_intersecting_height_boundary(self):
        snapshot = self.make_snapshot()
        # The body-relative search limit falls inside this occupied floor voxel.
        snapshot['occupancy'][42:59, 42:59, 39] = 100
        center = [0.0, 0.0, 0.021]
        plane = fit_ground_plane(snapshot['occupancy'], snapshot['origin_m'],
                                 0.1, center, self.policy)
        self.assertTrue(plane['valid'], plane)
        self.assertEqual(plane['raw_occupied_voxel_count'], 289)

    def test_early_refusal_keeps_schedule_parameters_for_replay(self):
        snapshot = self.make_snapshot()
        result = check_entry_schedule(
            snapshot, {'center_xyz_m': [0.0, 0.0, 1.0], 'yaw_rad': 0.0},
            ground_confirmed=True, policy=self.policy, primitives=self.primitives)
        self.assertEqual(result['reason'], 'ground_plane_insufficient_raw_occupied_voxels')
        self.assertEqual(result['hold_height_m'], 1.0)
        self.assertEqual(result['sample_step_m'], 0.05)

    def test_unknown_is_never_cleared_by_contact_exception(self):
        snapshot = self.make_snapshot()
        snapshot['occupancy'][42:59, 42:59, 40] = 100
        snapshot['occupancy'][50, 50, 41] = -1
        plane = fit_ground_plane(snapshot['occupancy'], snapshot['origin_m'],
                                 0.1, [0.0, 0.0, 0.32], self.policy)
        result = check_pose(snapshot,
                            {'center_xyz_m': [0.0, 0.0, 0.32], 'yaw_rad': 0.0},
                            'TAKEOFF_CONTACT', self.policy, self.primitives,
                            plane, ground_confirmed=True)
        self.assertEqual(result['reason'], 'raw_unknown_in_expanded_vehicle_envelope')

    def test_whole_subground_voxels_are_excluded_only_with_confirmed_ground(self):
        snapshot = self.make_snapshot()
        plane = {
            'valid': True,
            'coefficients_ax_by_c_m': [0.0, 0.0, 0.0],
            'residual_p95_m': 0.0,
        }
        pose = {'center_xyz_m': [0.0, 0.0, 0.0], 'yaw_rad': 0.0}
        snapshot['occupancy'][50, 50, 38] = -1  # centre z=-0.15; full cell below boundary
        accepted = check_pose(snapshot, pose, 'TAKEOFF_CONTACT', self.policy,
                              self.primitives, plane, ground_confirmed=True)
        self.assertTrue(accepted['accepted'], accepted)
        self.assertGreater(accepted['counts']['subground_excluded_cells'], 0)
        refused = check_pose(snapshot, pose, 'ASCENT', self.policy,
                             self.primitives, plane, ground_confirmed=False)
        self.assertEqual(refused['reason'], 'raw_unknown_in_expanded_vehicle_envelope')
        held = check_pose(snapshot, pose, 'HOLD', self.policy,
                          self.primitives, plane, ground_confirmed=True)
        self.assertEqual(held['reason'], 'raw_unknown_in_expanded_vehicle_envelope')

    def test_unknown_touching_or_above_ground_boundary_still_refuses(self):
        plane = {
            'valid': True,
            'coefficients_ax_by_c_m': [0.0, 0.0, 0.0],
            'residual_p95_m': 0.0,
        }
        pose = {'center_xyz_m': [0.0, 0.0, 0.0], 'yaw_rad': 0.0}
        for z_index in (39, 40):  # cells touch the ground plane or extend above it
            snapshot = self.make_snapshot()
            snapshot['occupancy'][50, 50, z_index] = -1
            result = check_pose(snapshot, pose, 'TAKEOFF_CONTACT', self.policy,
                                self.primitives, plane, ground_confirmed=True)
            self.assertEqual(result['reason'], 'raw_unknown_in_expanded_vehicle_envelope')

    def test_map_boundary_and_attitude_fail_closed(self):
        snapshot = self.make_snapshot()
        outside = check_pose(snapshot, {'center_xyz_m': [0.0, 0.0, 5.8], 'yaw_rad': 0.0},
                             'HOLD', self.policy, self.primitives)
        self.assertEqual(outside['reason'], 'outside_map')
        tilted = check_pose(snapshot,
                            {'center_xyz_m': [0.0, 0.0, 1.0], 'yaw_rad': 0.0,
                             'pitch_rad': 0.2},
                            'HOLD', self.policy, self.primitives)
        self.assertEqual(tilted['reason'], 'body_attitude_outside_level_entry_scope')

    def test_vertical_schedule_has_no_start_pose_exemption(self):
        snapshot = self.make_snapshot()
        pose = {'center_xyz_m': [0.0, 0.0, 1.0], 'yaw_rad': 0.0}
        schedule = make_entry_schedule(pose)
        self.assertEqual(schedule[0][0], 'TAKEOFF_CONTACT')
        self.assertEqual(schedule[-1][0], 'LANDING_CONTACT')
        snapshot['occupancy'][50, 50, 50] = -1
        result = check_entry_schedule(snapshot, pose, ground_confirmed=True,
                                      policy=self.policy, ground_plane={
                                          'valid': True,
                                          'coefficients_ax_by_c_m': [0.0, 0.0, 0.0],
                                      }, primitives=self.primitives)
        self.assertFalse(result['accepted'])
        self.assertIn('raw_unknown_in_expanded_vehicle_envelope', result['reason'])

    def make_candidate_landing_snapshot(self):
        snapshot = self.make_snapshot()
        # A spatially supported raw floor plane at voxel centers z=0.05 m.
        snapshot['occupancy'][40:61, 40:61, 40] = 100
        return snapshot

    def test_candidate_landing_geometry_does_not_claim_actual_ground_contact(self):
        snapshot = self.make_candidate_landing_snapshot()
        pose = {'center_xyz_m': [0.0, 0.0, 0.32], 'yaw_rad': 0.0}
        result = check_candidate_landing_schedule(
            snapshot, pose, policy=self.policy, primitives=self.primitives)
        self.assertTrue(result['accepted'], result)
        self.assertFalse(result['ground_confirmed'])
        self.assertTrue(result['candidate_ground_contact_authorized'])
        self.assertEqual(result['sample_count'], 21)
        self.assertEqual(result['scope'].split(';')[0],
                         'prospective landing geometry only')
        schedule = make_candidate_landing_schedule(pose)
        self.assertEqual(schedule[0][0], 'HOLD')
        self.assertEqual(schedule[-1][0], 'LANDING_CONTACT')
        self.assertNotIn('TAKEOFF_CONTACT', [phase for phase, _ in schedule])

    def test_candidate_landing_refuses_unknown_or_occupied_air_volume(self):
        for value in (-1, 100):
            snapshot = self.make_candidate_landing_snapshot()
            snapshot['occupancy'][50, 50, 54] = value
            result = check_candidate_landing_schedule(
                snapshot, {'center_xyz_m': [0.0, 0.0, 0.32], 'yaw_rad': 0.0},
                policy=self.policy, primitives=self.primitives)
            self.assertFalse(result['accepted'])
            self.assertIn('raw_' + ('unknown' if value == -1 else 'occupied'),
                          result['reason'])

    def test_candidate_landing_uses_raw_support_and_refuses_missing_plane(self):
        snapshot = self.make_snapshot()
        pose = {'center_xyz_m': [0.0, 0.0, 0.32], 'yaw_rad': 0.0}
        result = check_candidate_landing_schedule(
            snapshot, pose, policy=self.policy, primitives=self.primitives)
        self.assertFalse(result['accepted'])
        self.assertFalse(result['ground_confirmed'])
        self.assertEqual(result['reason'], 'ground_plane_insufficient_raw_occupied_voxels')


if __name__ == '__main__':
    unittest.main()
