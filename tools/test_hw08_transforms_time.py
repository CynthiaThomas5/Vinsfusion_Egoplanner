#!/usr/bin/env python3
"""Directed body-reference and Agent epoch tests; no ROS or flight inputs."""
import math
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src/own/uav_px4_bridge'))
from uav_px4_bridge.rigid_body import (imu_to_body_flu, mount_rotation_translation,
                                     rotation_quaternion)
from uav_px4_bridge.time_mapping import SystemClockMapper, TimeMappingError
from uav_px4_bridge.trajectory import rotate_frd_to_ned


class RigidTests(unittest.TestCase):
    def close(self, a, b):
        for x, y in zip(a, b): self.assertAlmostEqual(x, y, places=7)

    def test_optical_axes_to_body_frd(self):
        t = [0,0,1,0, 1,0,0,0, 0,1,0,0, 0,0,0,1]
        r, _ = mount_rotation_translation(t)
        for value, expected in [((0,0,1),(1,0,0)), ((-1,0,0),(0,-1,0)),
                                 ((0,-1,0),(0,0,-1))]:
            self.close([sum(r[i][j]*value[j] for j in range(3)) for i in range(3)], expected)

    def test_rotating_leverarm_velocity(self):
        t = [1,0,0,.2, 0,1,0,.01, 0,0,1,0, 0,0,0,1]
        p, q, v, w = imu_to_body_flu((.2,.01,0), (0,0,0,1), (-.01,.2,0), (0,0,1), t)
        self.close(p,(0,0,0));self.close(v,(0,0,0));self.close(w,(0,0,-1))

    def test_full_pitch_leverarm(self):
        t = [1,0,0,1, 0,1,0,0, 0,0,1,0, 0,0,0,1]
        h=math.sqrt(.5)
        p, _, _, _ = imu_to_body_flu((0,0,-1), (0,h,0,h), (0,0,0), (0,0,0), t)
        self.close(p,(0,0,0))

    def test_pi_rotations_and_bad_mount(self):
        for r in ([[1,0,0],[0,-1,0],[0,0,-1]], [[-1,0,0],[0,1,0],[0,0,-1]],
                  [[-1,0,0],[0,-1,0],[0,0,1]]):
            q=rotation_quaternion(r)
            self.close(rotate_frd_to_ned((1,2,3),(q[3],*q[:3])),
                       [sum(r[i][j]*(1,2,3)[j] for j in range(3)) for i in range(3)])
        with self.assertRaises(ValueError):
            mount_rotation_translation([1,0,0,0,0,1,0,0,0,0,-1,0,0,0,0,1])


class TimeTests(unittest.TestCase):
    def setUp(self):
        self.mapper=SystemClockMapper(.868306,.02,.05)
        self.now=1_792_374_500_000_000_000
        self.sync=NS(timestamp=self.now//1000,estimated_offset=-self.now//1000+1_000_000,
                     round_trip_time=1000,source_protocol=2)

    def map(self, **kw):
        args=dict(source_ns=self.now-50_000_000,system_ns=self.now,
                  monotonic_ns=10_000_000_000,timesync=self.sync,
                  timesync_receipt_ns=9_900_000_000,max_timesync_age_s=2.,max_rtt_us=10000)
        args.update(kw);return self.mapper.to_px4(**args)

    def test_sample_delay_without_double_offset(self):
        x=self.map();self.assertEqual(x.now_us,self.now//1000)
        self.assertEqual(x.now_us-x.sample_us,50000)
        self.assertAlmostEqual(x.sample_age_wall_s,.05)

    def test_future_stale_and_wrong_protocol(self):
        for stamp in (self.now+30_000_000,self.now-900_000_000):
            with self.assertRaises(TimeMappingError):self.map(source_ns=stamp)
        self.sync.source_protocol=1
        with self.assertRaises(TimeMappingError):self.map()

    def test_clock_step_latches(self):
        self.map()
        with self.assertRaises(TimeMappingError):
            self.map(system_ns=self.now+200_000_000,monotonic_ns=10_100_000_000)
        with self.assertRaises(TimeMappingError):self.map()

    def test_actual_hw07_timesync(self):
        import json
        path=ROOT/'artifacts/runs/hw07-usb-20261103-01/dds.jsonl'
        if not path.exists():self.skipTest('local HW07 evidence absent')
        count=0
        for line in path.read_text().splitlines():
            row=json.loads(line)
            if row['topic']!='/fmu/out/timesync_status':continue
            x=SystemClockMapper(.868306,.02,.05).to_px4(
                row['system_ns']-50_000_000,row['system_ns'],int(row['monotonic_s']*1e9),
                NS(**row['message']),int(row['monotonic_s']*1e9),2.,10000)
            self.assertEqual(x.now_us-x.sample_us,50000);count+=1
        self.assertEqual(count,60)


if __name__=='__main__':unittest.main()
