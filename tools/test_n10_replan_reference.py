import math,unittest
import numpy as np
from tools.debug_truth.evaluate_n10_replan_geometry import sample_centerline_to_box

class ReplanReferenceTests(unittest.TestCase):
    def test_box_distance_is_invariant_under_shared_rigid_world_transform(self):
        spline={'message':{'order':1,'knots':[0,0,1,1],
                           'pos_pts':[{'x':0,'y':0,'z':0},{'x':1,'y':0,'z':0}]}}
        center=np.array([.5,2,0]);size=np.ones(3)
        baseline=sample_centerline_to_box(spline,center,size)
        rot=np.array([[0,-1,0],[1,0,0],[0,0,1]]);translation=np.array([10,20,0])
        shifted=sample_centerline_to_box(spline,rot@center+translation,size,rot,translation,math.pi/2)
        self.assertAlmostEqual(baseline['min_centerline_to_box_m'],1.5)
        self.assertAlmostEqual(shifted['min_centerline_to_box_m'],1.5)
        np.testing.assert_allclose(np.array(shifted['closest_centerline_point_world_m']),
                                   rot@np.array(shifted['closest_centerline_point_odom_m'])+translation)

    def test_clearance_boundary_uses_vehicle_radius_plus_scene_margin(self):
        spline={'message':{'order':1,'knots':[0,0,1,1],
                           'pos_pts':[{'x':0,'y':0,'z':0},{'x':2,'y':0,'z':0}]}}
        result=sample_centerline_to_box(
            spline, np.array([1.0,0,0]), np.array([0.2,0.2,0.2]),
            body_radius_m=0.3, required_body_clearance_m=0.1)
        self.assertAlmostEqual(result['minimum_centerline_body_margin_m'], -0.3, places=6)
        self.assertAlmostEqual(
            result['first_required_clearance_crossing_offset_sim_s'], 0.25, delta=0.003)
        self.assertGreater(result['sample_time_resolution_max_s'], 0)
        self.assertIn('not a continuous-time', result['method'])

if __name__=='__main__':unittest.main()
