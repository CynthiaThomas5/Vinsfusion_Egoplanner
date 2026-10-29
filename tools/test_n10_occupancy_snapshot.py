import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np

from tools.debug_truth.evaluate_n10_occupancy_snapshot import (
    box_local,
    point_classification,
    point_to_cell,
    signed_box_surface_distance,
    voxel_centers,
    voxel_cells_fully_inside_box,
    evaluate,
)


class N10OccupancySnapshotGeometryTest(unittest.TestCase):
    def test_point_to_cell_uses_lower_origin_and_half_open_voxels(self):
        self.assertEqual(point_to_cell([0.15, 0.25, 0.35], [0, 0, 0], 0.1, (4, 4, 4)),
                         (1, 2, 3))
        self.assertIsNone(point_to_cell([0.4, 0.1, 0.1], [0, 0, 0], 0.1, (4, 4, 4)))
        self.assertIsNone(point_to_cell([-0.001, 0.1, 0.1], [0, 0, 0], 0.1, (4, 4, 4)))

    def test_voxel_centers_follow_xyz_array_index(self):
        actual = voxel_centers([[0, 0, 0], [1, 2, 3]], [1, -1, 0.5], 0.1)
        np.testing.assert_allclose(actual, [[1.05, -0.95, 0.55], [1.15, -0.75, 0.85]])

    def test_cell_containment_distinguishes_surface_center_from_full_volume(self):
        args = ([[0, 0, 0]], [0, 0, 0], 0.1, np.eye(3), [0, 0, 0],
                [0.05, 0.05, 0.05])
        self.assertFalse(voxel_cells_fully_inside_box(
            *args, [0.08, 0.08, 0.08], 0.0)[0])
        self.assertTrue(voxel_cells_fully_inside_box(
            *args, [0.10, 0.10, 0.10], 0.0)[0])

    def test_box_local_coordinates_apply_yaw_inverse(self):
        points = np.asarray([[0.0, 1.0, 0.0]])
        local = box_local(points, [0, 0, 0], np.pi / 2.0)
        np.testing.assert_allclose(local, [[1.0, 0.0, 0.0]], atol=1e-12)

    def test_signed_box_distance_separates_interior_surface_and_exterior(self):
        points = np.asarray([[0, 0, 0], [0.5, 0, 0], [0.7, 0, 0], [0.6, 0.6, 0]])
        actual = signed_box_surface_distance(points, [1.0, 1.0, 1.0])
        np.testing.assert_allclose(actual, [0.5, 0.0, 0.2, np.sqrt(0.02)])

    def test_snapshot_point_classification_returns_raw_and_inflated(self):
        occupancy = np.zeros((2, 2, 2), dtype=np.int8)
        inflated = np.zeros((2, 2, 2), dtype=np.uint8)
        occupancy[1, 0, 1] = 100
        inflated[1, 0, 1] = 1
        result = point_classification(
            [1.15, -0.95, 0.65], np.eye(3), [0, 0, 0],
            [1.0, -1.0, 0.5], 0.1, occupancy, inflated)
        self.assertEqual(result["cell_index_xyz"], [1, 0, 1])
        self.assertEqual(result["raw_code"], 100)
        self.assertTrue(result["inflated"])

    def test_full_snapshot_evaluation_binds_box_to_snapshot_identity(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run = Path(temp_dir) / "n10-20261027-test"
            snapshot_dir = run / "n10-map-snapshot"
            snapshot_dir.mkdir(parents=True)
            observation = {
                "epoch": "a" * 32,
                "map_id_at_goal": "a" * 32 + "-map1",
                "obstacle": {
                    "model_name": "box",
                    "pose_world_xyz_m": [1.0, 1.0, 1.0],
                    "size_xyz_m": [0.4, 0.4, 0.4],
                    "yaw_rad": 0.0,
                },
            }
            (run / "n10-live-obstacle-observation.json").write_text(
                json.dumps(observation))
            (run / "arrival-evaluation-simtime-v2.json").write_text(json.dumps({
                "ground_rotation": np.eye(3).tolist(),
                "ground_translation": [0.0, 0.0, 0.0],
            }))
            occupancy = np.zeros((20, 20, 20), dtype=np.int8)
            inflated = np.zeros((20, 20, 20), dtype=np.uint8)
            occupancy[8, 10, 10] = 100
            occupancy[10, 10, 10] = 100
            occupancy[11, 11, 11] = -1
            inflated[8, 10, 10] = 1
            archive_path = snapshot_dir / "occupancy_snapshot.npz"
            np.savez_compressed(archive_path, occupancy=occupancy, inflated=inflated)
            digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
            metadata = {
                "schema": "plan-env-voxel-snapshot/v1",
                "epoch": observation["epoch"],
                "map_id": observation["map_id_at_goal"],
                "frame_id": "odom_" + observation["epoch"],
                "snapshot_stamp_ns": 100,
                "last_fused_depth_source_stamp_ns": 90,
                "last_fusion_stamp_ns": 95,
                "origin_m": [0.0, 0.0, 0.0],
                "resolution_m": 0.1,
                "dimensions_xyz": [20, 20, 20],
                "data_order": "x_major_y_mid_z_fastest",
                "archive": {"sha256": digest},
            }
            (snapshot_dir / "metadata.json").write_text(json.dumps(metadata))
            contract = {'schema': 'synthetic-imu-reference', 'output_pose_reference': 'd435i_imu',
                        'model_origin_to_imu_m': [0, 0, 0], 'source_sha256': {}}
            alignment_path = run / "arrival-evaluation-simtime-v2.json"
            alignment = json.loads(alignment_path.read_text())
            alignment['truth_reference_contract'] = contract
            alignment_path.write_text(json.dumps(alignment))
            with mock.patch('tools.debug_truth.evaluate_n10_occupancy_snapshot.model_to_imu_contract',
                            return_value=contract):
                report, output = evaluate(run)
            self.assertTrue(report["snapshot_matches_live_observer_epoch_map_frame"])
            self.assertEqual(report["snapshot_roi"]["inside_box_voxel_counts_by_raw_class"], {
                "unknown": 1, "known_free": 61, "raw_occupied": 2,
            })
            geometry = report["snapshot_roi"]["voxel_cell_geometry"]
            self.assertEqual(
                geometry["all_corners_inside_box_counts_by_raw_class"]["known_free"], 61)
            self.assertEqual(
                geometry["center_inside_but_cell_not_fully_contained_counts_by_raw_class"]["known_free"], 0)
            self.assertIn("cannot be directly visible", geometry["qualification"])
            self.assertEqual(report["snapshot_roi"]["raw_occupied_point_archive_count"], 2)
            self.assertTrue(output.is_file())
            self.assertTrue((snapshot_dir / "box_roi_raw_occupied_points.jsonl").is_file())


if __name__ == "__main__":
    unittest.main()
