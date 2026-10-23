import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent/'debug_truth'))
from evaluate_loop_revisit import relative_error


class RelativeLoopGeometryTests(unittest.TestCase):
    def test_translation_is_in_old_imu_frame(self):
        r=np.array([[0,-1,0],[1,0,0],[0,0,1]])
        te,re=relative_error(np.zeros(3),r,np.array([0,2,0]),r,[2,0,0],[0,0,0,1])
        self.assertAlmostEqual(te,0);self.assertAlmostEqual(re,0)
        te,re=relative_error(np.zeros(3),r,np.array([0,2,0]),r,[0,2,0],[0,0,0,1])
        self.assertGreater(te,2)

    def test_wrong_rotation_is_measured(self):
        te,re=relative_error(np.zeros(3),np.eye(3),np.zeros(3),np.eye(3),[0,0,0],[0,0,1,0])
        self.assertEqual(te,0);self.assertAlmostEqual(re,180)
