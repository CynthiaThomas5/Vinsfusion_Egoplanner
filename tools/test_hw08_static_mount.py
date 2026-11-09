#!/usr/bin/env python3
"""Check that held-out static poses detect a changing mount instead of fitting it away."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).parent/'diagnostics'))
from fit_hw08_static_mount import estimate


class StaticMountTests(unittest.TestCase):
    def analyze(self, change_holdout):
        rotation=np.array([[0,0,1],[1,0,0],[0,1,0]],dtype=float)
        gravity={'baseline':[0,0,-1],'static_pitch_hold':[.5,0,-np.sqrt(.75)],
                 'static_roll_hold':[0,-.5,-np.sqrt(.75)],'static_level_hold':[0,0,-1]}
        rows=[]
        for phase,body in gravity.items():
            camera=rotation.T@body
            if change_holdout and phase=='static_roll_hold':
                # Flexible support changes only the independent third pose.
                camera=rotation.T@np.array([0,-np.sqrt(.5),-np.sqrt(.5)])
            for _ in range(40):
                rows.append(dict(kind='imu',phase=phase,data=dict(accel=camera.tolist(),gyro=[0,0,0])))
                rows.append(dict(kind='mavlink',phase=phase,data=dict(mavpackettype='HIGHRES_IMU',
                    xacc=body[0],yacc=body[1],zacc=body[2],xgyro=0,ygyro=0,zgyro=0)))
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'capture.jsonl'
            path.write_text(''.join(json.dumps(x)+'\n' for x in rows))
            return estimate(path)

    def test_known_rotation_and_independent_pose(self):
        result=self.analyze(False)
        np.testing.assert_allclose(result['R_body_imu'],[[0,0,1],[1,0,0],[0,1,0]],atol=1e-12)
        heldout=result['groups']['static_roll_hold']
        self.assertFalse(heldout['used_for_fit'])
        self.assertLess(heldout['fitted_gravity_residual_deg'],1e-5)

    def test_changing_mount_cannot_be_hidden_by_refitting_holdout(self):
        result=self.analyze(True)
        self.assertAlmostEqual(result['groups']['static_roll_hold']['fitted_gravity_residual_deg'],15.)
        self.assertLess(result['groups']['baseline']['fitted_gravity_residual_deg'],1e-5)


if __name__=='__main__':
    unittest.main()
