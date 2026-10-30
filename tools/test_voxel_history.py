"""History retains old observations, deduplicates and enforces physical bounds."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src/own/uav_mapping'))
from uav_mapping.voxel_history import VoxelHistory


class VoxelHistoryTests(unittest.TestCase):
    def test_disjoint_local_clouds_retain_previously_seen_voxels(self):
        history = VoxelHistory(.15, (-20, -20, -1), (40, 40, 6), 100)
        history.add([(-7.99, 0, 1), (-7.98, 0, 1)])
        self.assertEqual(len(history.voxels), 1)
        history.add([(8, 0, 1)])
        self.assertEqual(len(history.voxels), 2)
        self.assertTrue(any(p[0] < -7 for p in history.centers()))
        self.assertTrue(any(p[0] > 7 for p in history.centers()))

    def test_capacity_does_not_evict_old_voxels_and_clear_releases_it(self):
        history = VoxelHistory(1, (0, 0, 0), (10, 10, 10), 2)
        history.add([(0, 0, 0), (1, 0, 0), (2, 0, 0), (0, 0, 0)])
        self.assertEqual(history.centers(), [(.5, .5, .5), (1.5, .5, .5)])
        self.assertEqual(history.rejected_new_voxels, 1)
        history.clear()
        self.assertEqual(history.centers(), [])
        self.assertEqual(history.rejected_new_voxels, 0)
        history.add([(2, 0, 0)])
        self.assertEqual(history.centers(), [(2.5, .5, .5)])

    def test_invalid_and_out_of_map_points_do_not_enter_history(self):
        history = VoxelHistory(.1, (-1, -1, -1), (2, 2, 2), 10)
        history.add([(float('nan'), 0, 0), (float('inf'), 0, 0), (1, 0, 0), (-1.01, 0, 0)])
        self.assertEqual(history.centers(), [])
        history.add([(-1, -1, -1)])
        self.assertEqual(len(history.centers()), 1)

    def test_invalid_grid_is_rejected(self):
        for resolution in (0, -1, float('nan')):
            with self.assertRaises(ValueError):
                VoxelHistory(resolution, (0, 0, 0), (2, 2, 2), 10)
