import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from tools.debug_truth.evaluate_n10_snapshot_pair import evaluate, sha256


class SnapshotPairEvaluationTests(unittest.TestCase):
    def test_same_identity_pair_compares_raw_and_inflated_cells_and_depth_roi(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / 'run-1'
            run.mkdir()
            before_dir = run / 'n10-map-snapshot-before-injection'
            after_dir = run / 'n10-map-snapshot'
            before_dir.mkdir()
            after_dir.mkdir()
            grid = np.zeros((6, 6, 6), dtype=np.int8)
            inflated = np.zeros_like(grid, dtype=np.uint8)
            before_path = before_dir / 'occupancy_snapshot.npz'
            np.savez_compressed(before_path, occupancy=grid, inflated=inflated)
            after = grid.copy()
            after_inflated = inflated.copy()
            after[2, 2, 2] = 100
            after_inflated[2, 2, 2] = 1
            after_path = after_dir / 'occupancy_snapshot.npz'
            np.savez_compressed(after_path, occupancy=after, inflated=after_inflated)
            identity = {'epoch': 'epoch-1', 'map_id': 'epoch-1-map-1',
                        'frame_id': 'odom_epoch-1'}
            common = {
                'schema': 'plan-env-voxel-snapshot/v1', **identity,
                'origin_m': [-3.0, -3.0, -3.0], 'map_size_m': [6.0, 6.0, 6.0],
                'resolution_m': 1.0, 'dimensions_xyz': [6, 6, 6],
                'data_order': 'x_major_y_mid_z_fastest',
            }
            before_meta = {**common, 'snapshot_stamp_ns': 90,
                           'last_fused_depth_source_stamp_ns': 80,
                           'last_fusion_stamp_ns': 85,
                           'archive': {'file': before_path.name,
                                       'sha256': sha256(before_path)}}
            after_meta = {**common, 'snapshot_stamp_ns': 130,
                          'last_fused_depth_source_stamp_ns': 125,
                          'last_fusion_stamp_ns': 128,
                          'snapshot_source_coverage': {'covered': True},
                          'archive': {'file': after_path.name,
                                      'sha256': sha256(after_path)}}
            (before_dir / 'metadata.json').write_text(json.dumps(before_meta))
            (after_dir / 'metadata.json').write_text(json.dumps(after_meta))
            depth = np.full((8, 8), 2.0, dtype=np.float32)
            depth_path = run / 'depth.npy'
            np.save(depth_path, depth, allow_pickle=False)
            (run / 'n10-live-obstacle-observation.json').write_text(json.dumps({
                'epoch': identity['epoch'], 'map_id_at_goal': identity['map_id'],
                'gazebo_create': {'request_sim_ns': 100},
                'obstacle': {'expected_center_odom_xyz_m': [0.0, 0.0, 0.0],
                             'size_xyz_m': [2.0, 2.0, 2.0]},
                'depth_and_color_frames': [{
                    'topic': '/sensors/d435i/depth', 'stamp_ns': 110,
                    'frame_id': 'depth_optical_frame', 'encoding': '32FC1',
                    'file': depth_path.name, 'file_sha256': sha256(depth_path)}],
            }))
            report = evaluate(run)
            self.assertEqual(report['status'], 'SUPPORTED')
            self.assertEqual(report['obstacle_roi']['transitions'][
                'voxel_cells_fully_inside_truth_obstacle']['class_transitions'][
                    'known_free->raw_occupied'], 1)
            self.assertEqual(report['depth_roi']['status'], 'SUPPORTED')
            self.assertEqual(report['depth_roi']['post_snapshot_source_covered_frame_count'], 1)
            self.assertFalse(report['control_published'])

    def test_different_map_identity_is_insufficient(self):
        # Full capture validation is covered in the positive case; mismatched
        # identities are rejected before any map transition is interpreted.
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / 'run-1'
            run.mkdir()
            before_dir = run / 'n10-map-snapshot-before-injection'
            after_dir = run / 'n10-map-snapshot'
            before_dir.mkdir(); after_dir.mkdir()
            for directory, map_id, stamp in (
                    (before_dir, 'epoch-1-map-1', 90),
                    (after_dir, 'epoch-1-map-2', 130)):
                grid = np.zeros((6, 6, 6), dtype=np.int8)
                mask = np.zeros_like(grid, dtype=np.uint8)
                archive = directory / 'occupancy_snapshot.npz'
                np.savez_compressed(archive, occupancy=grid, inflated=mask)
                metadata = {
                    'schema': 'plan-env-voxel-snapshot/v1',
                    'epoch': 'epoch-1', 'map_id': map_id, 'frame_id': 'odom_epoch-1',
                    'origin_m': [-3.0, -3.0, -3.0], 'map_size_m': [6.0, 6.0, 6.0],
                    'resolution_m': 1.0, 'dimensions_xyz': [6, 6, 6],
                    'data_order': 'x_major_y_mid_z_fastest', 'snapshot_stamp_ns': stamp,
                    'last_fused_depth_source_stamp_ns': stamp - 2,
                    'last_fusion_stamp_ns': stamp - 1,
                    'snapshot_source_coverage': {'covered': True},
                    'archive': {'file': archive.name, 'sha256': sha256(archive)},
                }
                (directory / 'metadata.json').write_text(json.dumps(metadata))
            (run / 'n10-live-obstacle-observation.json').write_text(json.dumps({
                'epoch': 'epoch-1', 'map_id_at_goal': 'epoch-1-map-1',
                'gazebo_create': {'request_sim_ns': 100},
                'obstacle': {'expected_center_odom_xyz_m': [0, 0, 0],
                             'size_xyz_m': [2, 2, 2]},
            }))
            report = evaluate(run)
            self.assertEqual(report['status'], 'INSUFFICIENT')
            self.assertFalse(report['checks']['same_run_epoch_map_frame_identity'])


if __name__ == '__main__':
    unittest.main()
