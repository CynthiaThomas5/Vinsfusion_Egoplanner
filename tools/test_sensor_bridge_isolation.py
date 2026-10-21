#!/usr/bin/env python3
"""Keep online D435i sensor bridging separate from debug-truth odometry."""

from pathlib import Path
import sys
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class SensorBridgeIsolationTests(unittest.TestCase):
    def test_sensor_bridge_has_no_truth_topic(self):
        config = yaml.safe_load(
            (ROOT / 'config/components/simulation/d435i_bridge.yaml').read_text())
        topics = {entry['ros_topic_name'] for entry in config}
        self.assertIn('/clock', topics)
        self.assertIn('/sensors/d435i/imu', topics)
        self.assertIn('/sensors/d435i/infra1/image_rect', topics)
        self.assertIn('/sensors/d435i/infra2/image_rect', topics)
        self.assertFalse(any('debug_truth' in topic for topic in topics))

    def test_truth_bridge_is_loaded_only_by_debug_truth_launch(self):
        config = yaml.safe_load(
            (ROOT / 'config/components/simulation/debug_truth_bridge.yaml').read_text())
        self.assertEqual([entry['ros_topic_name'] for entry in config],
                         ['/debug_truth/base_odometry'])
        debug_launch = (ROOT / 'src/own/uav_sim/launch/debug_truth.launch.py').read_text()
        vio_launch = (ROOT / 'src/own/uav_px4_bridge/launch/vio_closed_loop_px4.launch.py').read_text()
        self.assertIn('debug_truth_bridge.yaml', debug_launch)
        self.assertIn('d435i_bridge.yaml', vio_launch)
        self.assertNotIn('debug_truth_bridge.yaml', vio_launch)
        self.assertNotIn('/debug_truth/', vio_launch)


if __name__ == '__main__':
    sys.exit(unittest.main())
