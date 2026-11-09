#!/usr/bin/env python3
import sys
from pathlib import Path
import unittest
import json
import tempfile
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent/'diagnostics'))
from record_hw08_board import timesync_pair
from analyze_hw08_board import analyze, fit_rotation


class BoardClockTests(unittest.TestCase):
    def test_fc_tc1_with_echoed_host_ts1(self):
        epoch = 1_792_374_500_000_000_000
        result = timesync_pair(epoch, 1_000_000_000, 1_002_000_000, 100_001_000_000)
        self.assertEqual(result['rtt_ns'], 2_000_000)
        self.assertEqual(result['host_minus_fc_ns'], epoch-100_000_000_000)

    def test_invalid_clock_reply(self):
        for args in ((1,2,1,3),(1,2,3,0)):
            with self.assertRaises(ValueError): timesync_pair(*args)

    def test_rigid_rotation_fit_has_correct_direction(self):
        expected=np.array([[0.,0.,1.],[1.,0.,0.],[0.,1.,0.]])
        camera=np.eye(3)
        rotation,singular=fit_rotation(camera,camera @ expected.T)
        np.testing.assert_allclose(rotation,expected,atol=1e-12)
        self.assertTrue(np.all(singular>0))

    def test_clock_mapping_and_axis_comparison(self):
        epoch=1_792_374_500_000_000_000
        rows=[]
        def put(kind,phase,data):rows.append(dict(kind=kind,phase=phase,data=data))
        for index in range(100):
            put('imu','baseline',dict(stamp_ns=epoch+index*5_000_000,gyro=[.01,.02,.03]))
        for index in range(30):
            put('mavlink','baseline',dict(mavpackettype='HIGHRES_IMU',
                time_usec=1_000_000+index*10_000,xgyro=.001,ygyro=.002,zgyro=.003))
        for index in range(100):
            put('imu','yaw_left_return',dict(stamp_ns=epoch+1_000_000_000+index*10_000_000,
                                           gyro=[.01,-.08,.03]))
            put('mavlink','yaw_left_return',dict(mavpackettype='HIGHRES_IMU',
                time_usec=2_000_000+index*10_000,xgyro=.001,ygyro=.002,zgyro=-.097))
        for delta in (0,2_000_000_000):
            put('timesync_pair','baseline',dict(rtt_ns=1_000_000,
                fc_hrt_ns=1_000_000_000+delta,host_midpoint_system_ns=epoch+delta))
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'board.jsonl'
            path.write_text(''.join(json.dumps(x)+'\n' for x in rows))
            result=analyze(path)
        yaw=result['phases']['yaw_left_return']
        self.assertGreaterEqual(yaw['moving_samples'],90)
        self.assertEqual(yaw['dominant_fc_axis'],2)
        self.assertEqual(yaw['dominant_camera_mapped_axis'],2)
        self.assertAlmostEqual(yaw['direction_cos_median'],1.)
        self.assertLess(yaw['gyro_rmse_vector_rad_s'],1e-8)
        self.assertNotIn('rotation_estimate',result)


if __name__=='__main__': unittest.main()
