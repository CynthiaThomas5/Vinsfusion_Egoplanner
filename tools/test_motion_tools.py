#!/usr/bin/env python3
"""Run in the Gazebo Python environment."""
import math
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from prepare_motion_world import prepare
from run_sensor_motion import motion


class MotionTest(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
