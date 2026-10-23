"""Target certificate validation, independent of ROS runtime."""
import copy
from pathlib import Path
import sys
import subprocess
import tempfile
from types import SimpleNamespace as NS
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/own/uav_navigation'))
from uav_navigation.admission import query_rejection


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.request = NS(expected_epoch='e', expected_map_id='m', frame_id='odom_e',
                          center=NS(x=1., y=2., z=3.), radius_m=.5)
        stamp = NS(sec=10, nanosec=0)
        self.response = NS(accepted=True, free=True, reason='free', epoch='e', map_id='m',
                           header=NS(frame_id='odom_e', stamp=stamp),
                           last_depth_source_stamp=stamp, last_fusion_stamp=stamp,
                           center=NS(x=1., y=2., z=3.), radius_m=.5,
                           unknown_count=0, occupied_count=0, free_count=10)

    def check(self):
        return query_rejection(self.response, self.request, 10.1, .4)

    def test_free(self):
        self.assertEqual(self.check(), '')

    def test_verdicts(self):
        for reason in ('unknown', 'occupied', 'outside_map', 'depth_source_stale'):
            self.response.reason = reason
            self.response.free = False
            self.assertEqual(self.check(), 'map_query_' + reason)
        self.response.reason = 'free'
        self.response.free = True
        self.response.accepted = False
        self.assertTrue(self.check())

    def test_identity(self):
        original = copy.deepcopy(self.response)
        for field in ('epoch', 'map_id'):
            self.response = copy.deepcopy(original)
            setattr(self.response, field, 'other')
            self.assertEqual(self.check(), 'map_query_identity_mismatch')
        self.response = original
        self.response.header.frame_id = 'world'
        self.assertEqual(self.check(), 'map_query_identity_mismatch')

    def test_geometry_and_counts(self):
        self.response.radius_m = .1
        self.assertEqual(self.check(), 'map_query_geometry_mismatch')
        self.response.radius_m = .5
        self.response.center.z = float('nan')
        self.assertEqual(self.check(), 'map_query_geometry_mismatch')
        self.response.center.z = 3.
        for key in ('unknown_count', 'occupied_count', 'free_count'):
            setattr(self.response, key, 0 if key == 'free_count' else 1)
            self.assertEqual(self.check(), 'map_query_inconsistent_counts')
            setattr(self.response, key, 10 if key == 'free_count' else 0)

    def test_each_stamp_stale_future_zero(self):
        for field in ('last_depth_source_stamp', 'last_fusion_stamp'):
            for sec in (0, 9, 11):
                original = getattr(self.response, field)
                setattr(self.response, field, NS(sec=sec, nanosec=0))
                self.assertEqual(self.check(), 'map_query_stale')
                setattr(self.response, field, original)
        self.response.header.stamp = NS(sec=9, nanosec=0)
        self.assertEqual(self.check(), 'map_query_stale')

    def test_production_cpp_sphere_query(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            binary = str(Path(tmp)/'sphere-query')
            subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-I',
                            str(root/'src/vendor/ego_planner/planner/plan_env/include'),
                            str(root/'tools/probe_sphere_query.cpp'), '-o', binary], check=True)
            subprocess.run([binary], check=True)

    def test_production_depth_raycast(self):
        root = Path(__file__).resolve().parents[1]
        vendor = root/'src/vendor/ego_planner/planner/plan_env'
        with tempfile.TemporaryDirectory() as tmp:
            binary = str(Path(tmp)/'depth-rays')
            subprocess.run(['c++', '-std=c++17', '-I/usr/include/eigen3', '-I',
                            str(vendor/'include'), str(root/'tools/probe_depth_raycast.cpp'),
                            str(vendor/'src/raycast.cpp'), '-o', binary], check=True)
            subprocess.run([binary], check=True)

    def test_production_curve_cover(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            binary = str(Path(tmp)/'curve-cover')
            subprocess.run(['c++', '-std=c++17', '-I/usr/include/eigen3', '-I',
                            str(root/'src/vendor/ego_planner/planner/plan_env/include'), '-I',
                            str(root/'src/vendor/ego_planner/planner/bspline_opt/include'),
                            str(root/'tools/probe_swept_curve.cpp'),
                            str(root/'src/vendor/ego_planner/planner/bspline_opt/src/uniform_bspline.cpp'),
                            '-o', binary], check=True)
            subprocess.run([binary], check=True)

    def test_radius_covers_nominal_model(self):
        import json
        from audit_vehicle_envelope import audit
        root = Path(__file__).resolve().parents[1]
        radius = json.loads((root/'config/components/mapping/ego_planner.json').read_text())['obstacles_inflation_m']
        self.assertGreaterEqual(radius, audit()['max_orientation_invariant_radius_all_rotor_angles_m'])


if __name__ == '__main__':
    unittest.main()
