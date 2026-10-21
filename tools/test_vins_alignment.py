#!/usr/bin/env python3
import unittest
import numpy as np
from evaluate_vins_motion import rigid_alignment,rotation,evaluate


class AlignmentTest(unittest.TestCase):
    def test_single_rigid_transform_recovered(self):
        estimated=np.array([[0,0,0],[1,0,0],[0,2,0],[0,0,3],[1,2,3]],dtype=float)
        expected=rotation([0,0,np.sin(.3),np.cos(.3)])
        reference=(expected@estimated.T).T+[2,-3,4]
        r,t=rigid_alignment(estimated,reference)
        np.testing.assert_allclose(r,expected,atol=1e-12)
        np.testing.assert_allclose(t,[2,-3,4],atol=1e-12)

    def test_scale_and_reflection_cannot_be_fitted_away(self):
        x=np.array([[0,0,0],[1,0,0],[0,2,0],[0,0,3]],dtype=float)
        for reference in [2*x,x*[1,1,-1]]:
            r,t=rigid_alignment(x,reference)
            self.assertAlmostEqual(np.linalg.det(r),1)
            self.assertGreater(np.linalg.norm((r@x.T).T+t-reference),.5)

    def test_invalid_truth_stamps_rejected(self):
        truth=[{'stamp':0, 'position':[0,0,0], 'quaternion':[0,0,0,1]} for _ in range(20)]
        states=[{'stamp_ns':i*10000000, 'position':[0,0,0], 'quaternion':[0,0,0,1]} for i in range(20)]
        with self.assertRaises(ValueError):
            evaluate({'truth':truth,'imu':[]},{'optimized':states})


if __name__=='__main__':
    unittest.main()
