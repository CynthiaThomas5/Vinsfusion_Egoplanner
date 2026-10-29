#!/usr/bin/env python3
"""Run in the Gazebo Python environment."""
import math
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import numpy as np
from prepare_motion_world import prepare
from run_sensor_motion import motion
from probe_n06_live_layout import raw_line_sweep, raw_sphere_query


class MotionTest(unittest.TestCase):
    def test_explicit_phase_durations_reach_target_and_stop_at_rest(self):
        acceleration = .0045
        retreat_duration = math.sqrt(3.2/acceleration)
        return_duration = math.sqrt(2.4/acceleration)
        profile = {
            'initial_hold_seconds': 5.0,
            'phase_seconds': 25.0,
            'phase_durations_seconds': [retreat_duration, retreat_duration,
                                       return_duration, return_duration],
            'world_acceleration_and_angular_acceleration': [
                acceleration, 0.0, 0.0, 0.0, 0.0, 0.0],
            'phase_signs': [
                [-1, 0, 0, 0, 0, 0],
                [1, 0, 0, 0, 0, 0],
                [1, 0, 0, 0, 0, 0],
                [-1, 0, 0, 0, 0, 0],
            ],
        }
        velocity = 0.0
        position = 0.0
        elapsed = profile['initial_hold_seconds']
        for duration in profile['phase_durations_seconds']:
            ax = motion(elapsed + duration/2, profile)[0]
            position += velocity*duration + .5*ax*duration*duration
            velocity += ax*duration
            elapsed += duration
        self.assertAlmostEqual(position, -.8, places=10)
        self.assertAlmostEqual(velocity, 0.0, places=10)
        self.assertAlmostEqual(acceleration*retreat_duration, .12, places=10)
        self.assertEqual(motion(elapsed, profile), [0.0]*6)

    def test_explicit_phase_duration_count_must_match(self):
        profile = {
            'initial_hold_seconds': 0.0,
            'phase_durations_seconds': [1.0],
            'phase_signs': [[1.0, 0.0, 0.0, 0.0],
                            [-1.0, 0.0, 0.0, 0.0]],
            'world_acceleration_and_yaw_acceleration': [1.0, 0.0, 0.0, 0.0],
        }
        with self.assertRaises(ValueError):
            motion(0.5, profile)

    def test_excitation_is_bounded_and_stops(self):
        for t in [0,4,21,23,25]:
            self.assertEqual(motion(t),[0.,0.,0.,0.])
        values=[motion(t/100) for t in range(500,2301)]
        for axis,bound in enumerate([.06,.04,.03,.10]):
            self.assertTrue(all(math.isfinite(v[axis]) and abs(v[axis])<=bound for v in values))
            self.assertGreater(max(abs(v[axis]) for v in values),bound/3)

    def test_ideal_phase_integrals_return_to_rest(self):
        velocity=[0.]*4
        position=[0.]*4
        for i in range(8):
            acceleration=motion(5+i*2+.1)
            for axis in range(4):
                position[axis]+=2*velocity[axis]+2*acceleration[axis]
                velocity[axis]+=2*acceleration[axis]
        for value in velocity+position:
            self.assertAlmostEqual(value,0,places=12)

    def test_generated_world_has_one_rigid_sensor_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'motion.sdf'
            prepare(p)
            fixture=ET.parse(p).find('world/model[@name="sensor_fixture"]')
            self.assertEqual(len(fixture.findall('link')),1)
            self.assertEqual(len(fixture.findall('link/sensor')),5)
            self.assertEqual(fixture.findtext('link/gravity'),'false')
            self.assertIsNone(fixture.find('joint'))
            self.assertIsNone(fixture.find('plugin[@name="gz::sim::systems::VelocityControl"]'))
            self.assertIsNotNone(ET.parse(p).find('world/plugin[@name="gz::sim::systems::ApplyLinkWrench"]'))
            with self.assertRaises(FileExistsError):
                prepare(p)


class RawSnapshotCertificateTest(unittest.TestCase):
    def setUp(self):
        self.snapshot = {
            'occupancy': np.zeros((80, 80, 40), dtype=np.int8),
            'origin_m': [-4.0, -4.0, -2.0],
            'resolution_m': 0.1,
        }

    def test_sphere_rejects_unknown_voxel(self):
        self.snapshot['occupancy'][40, 40, 20] = -1
        result = raw_sphere_query(self.snapshot, [0.0, 0.0, 0.0], 0.2)
        self.assertTrue(result['accepted'])
        self.assertEqual(result['reason'], 'unknown')
        self.assertGreater(result['unknown_count'], 0)

    def test_continuous_sweep_rejects_unknown_between_endpoints(self):
        self.snapshot['occupancy'][42, 40, 20] = -1
        result = raw_line_sweep(self.snapshot, [0.0, 0.0, 0.0],
                                [0.5, 0.0, 0.0], 0.1, 0.5)
        self.assertFalse(result['free'])
        self.assertEqual(result['reason'], 'unknown')
        self.assertEqual(result['first_failure']['reason'], 'unknown')


if __name__ == '__main__':
    unittest.main()
