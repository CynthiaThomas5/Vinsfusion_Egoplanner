import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from tools.debug_truth.evaluate_n10_clearance import quaternion_rotation
from tools.debug_truth.evaluate_n10_interval_clearance_bound import (
    DEFAULTS,
    _body_point_radius_from_model_origin,
    _classify_dynamics_bound,
    _contact_step_classes,
    _collision_component_spheres,
    _interval_dynamics_bound,
    _parse_model_physics,
    _physics_endpoint_rows,
    _quaternion_from_rotation,
    _sample_component_sphere_clearances,
    _sample_clearances,
    interval_motion_allowance,
)


class N10IntervalMotionAllowanceTests(unittest.TestCase):
    def test_bound_includes_translation_rotation_and_half_interval(self):
        report = interval_motion_allowance(
            0.004, 0.5, 0.2, 10.0, 20.0, 0.6
        )
        self.assertAlmostEqual(report["within_step_speed_bound_m_s"], 0.54)
        self.assertAlmostEqual(report["within_step_angular_rate_bound_rad_s"], 0.28)
        self.assertAlmostEqual(report["body_point_speed_bound_m_s"], 0.708)
        self.assertAlmostEqual(report["maximum_nearest_endpoint_motion_m"], 0.001416)

    def test_rejects_nonfinite_or_negative_inputs(self):
        for values in (
            (0.004, float("nan"), 0.2, 10.0, 20.0, 0.6),
            (0.004, 0.5, 0.2, -1.0, 20.0, 0.6),
            (0.0, 0.5, 0.2, 10.0, 20.0, 0.6),
        ):
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    interval_motion_allowance(*values)

    def test_sample_clearances_uses_provided_identity_bound_rows(self):
        row = {
            "stamp_ns": 1,
            "xyz": [0.0, 0.0, 0.0],
            "q_xyzw": [0.0, 0.0, 0.0, 1.0],
        }
        geometry = {
            "collision_bounds_xyz_m": [[-0.1, 0.1], [-0.1, 0.1], [-0.1, 0.1]],
            "orientation_invariant_rotor_sweep_radius_m": 0.2,
        }
        with patch(
            "tools.debug_truth.evaluate_n10_interval_clearance_bound.vehicle_vertical_cylinder",
            return_value=(0.2, -0.1, 0.1, None),
        ), patch(
            "tools.debug_truth.evaluate_n10_interval_clearance_bound.distance_to_obstacle",
            return_value=0.5,
        ):
            result = _sample_clearances(
                [row], geometry, [{}], [0.0, 0.0, 0.0], np.eye(3)
            )
        self.assertEqual(result[0], [0.5])

    def test_physics_endpoint_reader_receives_run_identity_and_preserves_missing_rows(self):
        run = Path("/offline/run")
        row = {
            "stamp_ns": 1,
            "xyz": [0.0, 0.0, 0.0],
            "q_xyzw": [0.0, 0.0, 0.0, 1.0],
        }
        with patch(
            "tools.debug_truth.evaluate_n10_interval_clearance_bound.instantaneous_endpoints",
            return_value=(None, {"status": "INSUFFICIENT"}),
        ) as endpoints:
            rows, exact_rows, evidence = _physics_endpoint_rows(run, [row])
        endpoints.assert_called_once_with(run, [row])
        self.assertEqual(rows, [row])
        self.assertIsNone(exact_rows)
        self.assertEqual(evidence["status"], "INSUFFICIENT")


class N10ModelFrameBoundTests(unittest.TestCase):
    def setUp(self):
        # Physics parser needs a world step/gravity, not an unshipped flight archive.
        self.fixture_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.fixture_dir.cleanup)
        self.physics_world = Path(self.fixture_dir.name) / 'physics.sdf'
        self.physics_world.write_text('<sdf version="1.9"><world name="test"><gravity>0 0 -9.8</gravity><physics name="test" type="ignored"><max_step_size>0.004</max_step_size></physics></world></sdf>')

    def test_locked_x500_model_pose_maps_truth_origin_to_base_link(self):
        world_step = _parse_model_physics(
            self.physics_world,
            DEFAULTS["base_model"],
            DEFAULTS["airframe_model"],
            DEFAULTS["world_model"],
            DEFAULTS["camera_model"],
        )
        self.assertEqual(
            world_step["truth_model_to_base_link_position_m"], [0.0, 0.0, 0.12]
        )
        self.assertGreater(world_step["model_origin_to_com_radius_m"], 0.1)
        self.assertEqual(world_step["physics_step_s"], 0.004)

    def test_body_radius_is_measured_from_truth_model_origin(self):
        radius = _body_point_radius_from_model_origin(
            0.481935870666,
            -0.307,
            0.0125,
            [0.0, 0.0, 0.24],
            np.eye(3),
        )
        expected = math.hypot(
            0.481935870666,
            max(abs(0.24 - 0.307), abs(0.24 + 0.0125)),
        )
        self.assertAlmostEqual(radius, expected)
        self.assertGreater(radius, 0.54)

    def test_quaternion_rotation_round_trip_preserves_base_pose(self):
        yaw = math.radians(37.0)
        rotation = np.array([
            [math.cos(yaw), -math.sin(yaw), 0.0],
            [math.sin(yaw), math.cos(yaw), 0.0],
            [0.0, 0.0, 1.0],
        ])
        reconstructed = quaternion_rotation(_quaternion_from_rotation(rotation))
        np.testing.assert_allclose(reconstructed, rotation, atol=1e-12)

    def test_model_derived_step_dynamics_are_self_consistent(self):
        world_step = _parse_model_physics(
            self.physics_world,
            DEFAULTS["base_model"],
            DEFAULTS["airframe_model"],
            DEFAULTS["world_model"],
            DEFAULTS["camera_model"],
        )
        bound = _interval_dynamics_bound(0.75, 0.09, 0.004, world_step)
        self.assertTrue(bound["self_consistent"])
        self.assertGreater(bound["alpha_bound_rad_s2"], 0.0)
        self.assertGreaterEqual(
            bound["model_origin_acceleration_bound_m_s2"],
            bound["com_acceleration_bound_m_s2"],
        )
        for tau_up, tau_down, delta, speed in zip(
            world_step["rotor_speed_time_constant_up_s"],
            world_step["rotor_speed_time_constant_down_s"],
            world_step["rotor_speed_max_change_per_step_rad_s"],
            world_step["rotor_speed_max_rad_s"],
        ):
            expected = speed * max(
                1.0 - math.exp(-world_step["physics_step_s"] / tau_up),
                1.0 - math.exp(-world_step["physics_step_s"] / tau_down),
            )
            self.assertAlmostEqual(delta, expected)
            self.assertLess(delta, speed)

    def test_collision_spheres_cover_all_vehicle_collision_boxes_and_rotors(self):
        components = _collision_component_spheres(
            DEFAULTS["base_model"], DEFAULTS["world_model"], DEFAULTS["camera_model"]
        )
        self.assertEqual(len(components), 10)
        rotor_components = [item for item in components if "/rotor_" in item["name"]]
        self.assertEqual(len(rotor_components), 4)
        for component in components:
            self.assertEqual(
                component["source_geometry"], "SDF collision box circumscribed sphere"
            )
            self.assertEqual(len(component["center_model_origin_m"]), 3)
            self.assertTrue(all(math.isfinite(value)
                                for value in component["center_model_origin_m"]))
            self.assertGreater(component["enclosing_sphere_radius_m"], 0.0)

    def test_component_sphere_clearance_uses_actual_obstacle_surface_gap(self):
        row = {
            "stamp_ns": 4,
            "xyz": [0.0, 0.0, 0.0],
            "q_xyzw": [0.0, 0.0, 0.0, 1.0],
        }
        component = {
            "name": "rotor_0",
            "center_model_origin_m": [0.0, 0.0, 0.0],
            "enclosing_sphere_radius_m": 0.1,
        }
        obstacle = {
            "name": "test_cylinder",
            "kind": "vertical_cylinder",
            "center_xyz_m": [1.0, 0.0, 0.0],
            "radius_m": 0.2,
            "z_min_m": -1.0,
            "z_max_m": 1.0,
        }
        clearances, details = _sample_component_sphere_clearances(
            [row], [component], [obstacle]
        )
        self.assertAlmostEqual(clearances[0], 0.7)
        self.assertEqual(details[0]["component"], "rotor_0")
        self.assertEqual(details[0]["obstacle"], "test_cylinder")

    def test_nonconvergent_interval_is_reported_as_insufficient(self):
        world_step = _parse_model_physics(
            self.physics_world,
            DEFAULTS["base_model"],
            DEFAULTS["airframe_model"],
            DEFAULTS["world_model"],
            DEFAULTS["camera_model"],
        )
        result = _classify_dynamics_bound(6.8, 0.2, 0.02, world_step)
        self.assertEqual(result["classification"], "dynamics_bound_unavailable")
        self.assertEqual(result["reason"], "linear_speed_bound_did_not_converge")


class N10ContactClassificationTests(unittest.TestCase):
    def test_only_configured_skids_against_ground_are_allowed(self):
        report = {
            "events": [
                {
                    "stamp_ns": 10,
                    "pairs": [
                        {
                            "collision1": "x500::base_link::base_link_collision_3",
                            "collision2": "ground_plane::link::collision",
                        },
                        {
                            "collision1": "x500::base_link::base_link_collision_4",
                            "collision2": "ground_plane::link::collision",
                        },
                    ],
                },
                {
                    "stamp_ns": 20,
                    "pairs": [{
                        "collision1": "x500::base_link::base_link_collision_0",
                        "collision2": "ground_plane::link::collision",
                    }],
                },
                {
                    "stamp_ns": 30,
                    "pairs": [{
                        "collision1": "x500::rotor_0::collision",
                        "collision2": "blank::Wall_0_Collision",
                    }],
                },
                {"stamp_ns": 40, "pairs": []},
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "contacts.json"
            path.write_text(json.dumps(report))
            classified, _, count = _contact_step_classes(
                path, 10, 40, {"base_link_collision_3", "base_link_collision_4"}
            )
        self.assertEqual(count, 4)
        self.assertEqual(classified[10], "allowed_ground")
        self.assertEqual(classified[20], "prohibited")
        self.assertEqual(classified[30], "prohibited")
        self.assertEqual(classified[40], "prohibited")


if __name__ == "__main__":
    unittest.main()
