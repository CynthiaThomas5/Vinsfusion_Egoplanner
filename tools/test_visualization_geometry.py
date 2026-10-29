"""Curve-display checks against analytical cubic curves and bounded inputs."""
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/own/uav_navigation'))
from uav_navigation.visualization_geometry import sample_bspline


class DisplayCurveTests(unittest.TestCase):
    def test_bezier_curve_is_not_control_polygon(self):
        points = [(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)]
        curve = sample_bspline(points, [0, 0, 0, 0, 1, 1, 1, 1], 3, 0.5, 50, 100)
        self.assertEqual(curve, [(0, 0, 0), (0.5, 0.75, 0), (1, 0, 0)])

    def test_upstream_uniform_cubic_endpoints(self):
        points = [(i, i*i, 0) for i in range(6)]
        curve = sample_bspline(points, list(range(-3, 7)), 3, 0.1, 100, 100)
        for actual, expected in zip(curve[0], (1, 4/3, 0)):
            self.assertAlmostEqual(actual, expected)
        for actual, expected in zip(curve[-1], (4, 49/3, 0)):
            self.assertAlmostEqual(actual, expected)

    def test_stationary_and_sample_limit(self):
        points = [(2, -1, 3)] * 6
        curve = sample_bspline(points, [1000*t for t in range(-3, 7)], 3, 0.001, 7, 100)
        self.assertEqual(len(curve), 7)
        self.assertTrue(all(math.dist(p, (2, -1, 3)) < 1e-12 for p in curve))

    def test_invalid_inputs_rejected(self):
        points = [(0, 0, 0)] * 4
        for knots in [[0]*8, [0, 0, 0, 0, 1, 0, 1, 1], [0, 0, 0, 0, math.nan, 1, 1, 1]]:
            with self.subTest(knots=knots), self.assertRaises(ValueError):
                sample_bspline(points, knots, 3, 0.1, 50, 100)
        with self.assertRaises(ValueError):
            sample_bspline([(math.inf, 0, 0)] * 4, [0, 0, 0, 0, 1, 1, 1, 1], 3, 0.1, 50, 100)
        with self.assertRaises(ValueError):
            sample_bspline(points, [0, 0, 0, 0, 1, 1, 1, 1], 3, 0.1, 50, 3)


if __name__ == '__main__':
    unittest.main()
