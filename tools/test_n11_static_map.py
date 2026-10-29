"""Geometric counterexamples for the offline N11 static map evaluator."""
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent/'debug_truth'))
from evaluate_n11_static_map import wall_measurements, visibility_measurements

class GeometryTests(unittest.TestCase):
    def setUp(self):
        self.wall={'name':'wall','yaw_rad':0,'center_xyz_m':[2.,0.,1.],'size_xyz_m':[.2,4.,2.],'kind':'vertical_box'}
        self.raw=np.full((40,10,10),-1)
        self.raw[10,5,5]=0
        self.camera={'near':.01,'far':10,'width':640,'height':480,'K':[300,0,320,0,300,240,0,0,1]}
        self.optical=np.array([[0,0,1],[-1,0,0],[0,-1,0]])
    def measure(self):
        return visibility_measurements(self.raw,[0,-.5,.5],.1,np.eye(3),np.zeros(3),[self.wall],np.array([0.,0.,1.]),self.optical,self.camera)
    def test_visible_free_controls(self): self.assertEqual(self.measure()['visible_free_control_count'],1)
    def test_occluded_unknown_support(self):
        r=self.measure();self.assertGreater(r['fully_occluded_roi_cell_count'],0);self.assertEqual(r['fully_occluded_raw_free_count'],0)
    def test_behind_wall_free_is_detected(self):
        self.raw[30,5,5]=0;self.assertGreater(self.measure()['fully_occluded_raw_free_count'],0)
    def test_camera_looking_away_has_no_visible_free_control(self):
        self.optical=-self.optical;self.assertEqual(self.measure()['visible_free_control_count'],0)
    def test_out_of_range_is_not_visible(self):
        self.camera['far']=.5;self.assertEqual(self.measure()['visible_free_control_count'],0)
    def test_solid_cell_not_just_center(self):
        wall={**self.wall,'center_xyz_m':[0,0,0],'size_xyz_m':[.4,2,2]}
        raw=np.array([[[100]],[[0]],[[100]]]);r=wall_measurements(raw,np.ones_like(raw),[-.15,-.05,-.05],.1,np.eye(3),np.zeros(3),[wall])
        self.assertEqual(r[0]['solid_free_cell_count'],1)
    def test_invalid_resolution_rejected(self):
        with self.assertRaises(ValueError):wall_measurements(self.raw,self.raw,[0,0,0],0,np.eye(3),np.zeros(3),[self.wall])
    def test_invalid_codes_rejected(self):
        with self.assertRaises(ValueError):wall_measurements(np.array([[[2]]]),np.array([[[0]]]),[0,0,0],.1,np.eye(3),np.zeros(3),[self.wall])

if __name__=='__main__':unittest.main()
