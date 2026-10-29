#!/usr/bin/env python3
"""Check that the N10 fault path isolates only the D435i depth image input."""
from pathlib import Path
import unittest

import yaml

from fault_relay import TOPICS


ROOT = Path(__file__).resolve().parents[1]


class N10DepthFaultRouteTest(unittest.TestCase):
    def test_gazebo_depth_enters_relay_while_stereo_and_imu_stay_direct(self):
        entries = yaml.safe_load(
            (ROOT / 'config/components/simulation/n03_depth_fault_bridge.yaml').read_text())
        routes = {entry['ros_topic_name']: entry['gz_topic_name'] for entry in entries}
        self.assertEqual(routes['/fault/input/depth'], '/sensors/d435i/depth')
        self.assertNotIn('/sensors/d435i/depth', routes)
        self.assertEqual(routes['/sensors/d435i/infra1/image_rect'],
                         '/sensors/d435i/infra1/image_rect')
        self.assertEqual(routes['/sensors/d435i/infra2/image_rect'],
                         '/sensors/d435i/infra2/image_rect')
        self.assertEqual(routes['/sensors/d435i/imu'], '/sensors/d435i/imu')

    def test_relay_has_only_depth_as_the_faulted_sensor_stream(self):
        name, message_type, source, output = TOPICS['depth'][0]
        self.assertEqual((name, message_type.__name__, source, output),
                         ('depth', 'Image', '/fault/input/depth', '/sensors/d435i/depth'))

    def test_injector_is_opt_in_and_starts_before_vio_bridge(self):
        runtime = (ROOT / 'tools/sim_runtime.sh').read_text()
        self.assertIn('N10_DEPTH_FAULT=${D435I_N10_DEPTH_FAULT:-0}', runtime)
        self.assertIn('start n10-depth-fault-relay python3 tools/fault_relay.py', runtime)
        self.assertLess(runtime.index('start n10-depth-fault-relay'),
                        runtime.index('start vio ros2 launch'))
        self.assertIn('n03_depth_fault_bridge.yaml', runtime)


if __name__ == '__main__':
    unittest.main()
