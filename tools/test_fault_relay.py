#!/usr/bin/env python3
"""Unit checks for source-timestamp scheduled sensor-drop boundaries."""
import unittest

from fault_relay import TOPICS, should_drop_source


class FaultWindowTests(unittest.TestCase):
    def test_drop_window_is_half_open_and_source_aligned(self):
        origin = 8_100_000_000
        self.assertFalse(should_drop_source(origin+9_999_999_999, origin, 10.0, 4.0))
        self.assertTrue(should_drop_source(origin+10_000_000_000, origin, 10.0, 4.0))
        self.assertTrue(should_drop_source(origin+13_999_999_999, origin, 10.0, 4.0))
        self.assertFalse(should_drop_source(origin+14_000_000_000, origin, 10.0, 4.0))

    def test_depth_fault_uses_the_mapped_d435i_stream(self):
        name, message_type, source, output = TOPICS['depth'][0]
        self.assertEqual((name, message_type.__name__, source, output),
                         ('depth', 'Image', '/fault/input/depth', '/sensors/d435i/depth'))


if __name__ == '__main__':
    unittest.main()
