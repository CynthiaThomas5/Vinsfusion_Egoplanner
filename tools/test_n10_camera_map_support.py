import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent/'debug_truth'))
from evaluate_n10_camera_map_support import cylinder_hits,box_hits,camera_grid

class CameraSupportTests(unittest.TestCase):
    def test_cylinder_front_back_and_cap(self):
        c={'center_xyz_m':[3,0,0],'radius_m':.5,'z_min_m':-1,'z_max_m':1}
        hit=cylinder_hits([0,0,0],[[1,0,0],[-1,0,0],[0,1,0]],c,.2,10)
        self.assertAlmostEqual(hit[0],2.5);self.assertTrue(np.isinf(hit[1:]).all())
        self.assertAlmostEqual(cylinder_hits([3,0,3],[[0,0,-1]],c,.2,10)[0],2)

    def test_box_parallel_slab_and_range_clip(self):
        box={'center_xyz_m':[2,0,0],'size_xyz_m':[1,1,1],'yaw_rad':0}
        self.assertAlmostEqual(box_hits([0,0,0],[[1,0,0]],box,.2,10)[0],1.5)
        self.assertTrue(np.isinf(box_hits([0,2,0],[[1,0,0]],box,.2,10)[0]))
        self.assertTrue(np.isinf(box_hits([0,0,0],[[1,0,0]],box,.2,1)[0]))

    def test_pixel_margin_skip_and_optical_forward_axis(self):
        camera={'width':8,'height':6,'K':[4,0,4,0,4,3,0,0,1]}
        u,v,r=camera_grid(camera,1,2)
        self.assertEqual(len(r),6);self.assertEqual(set(u),{1,3,5})
        self.assertEqual(set(v),{1,3});self.assertTrue(np.all(r[:,2]==1))

if __name__=='__main__':unittest.main()
