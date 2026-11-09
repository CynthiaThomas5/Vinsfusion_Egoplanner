#!/usr/bin/env python3
"""Use the installed ROS serializer as the independent Image CDR fixture."""
from pathlib import Path
import sys
import unittest

from rclpy.serialization import serialize_message
from sensor_msgs.msg import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src/own/uav_localization'))
from uav_localization.image_metadata import image_metadata


class MetadataTests(unittest.TestCase):
    def test_actual_ros_serialization_preserves_metadata_and_views_pixels(self):
        for frame in ('a', 'optical_frame', 'camera_b_infra1_optical_frame'):
            msg = Image()
            msg.header.frame_id = frame
            msg.header.stamp.sec, msg.header.stamp.nanosec = 123, 456789
            msg.width, msg.height, msg.step = 640, 480, 640
            msg.encoding = 'mono8'
            msg.data = bytes(640 * 480)
            raw = serialize_message(msg)
            result = image_metadata(raw)
            self.assertEqual((result.header.stamp.sec, result.header.stamp.nanosec), (123, 456789))
            self.assertEqual(result.header.frame_id, frame)
            self.assertEqual((result.width, result.height, result.step, result.encoding),
                             (640, 480, 640, 'mono8'))
            self.assertEqual(len(result.data), len(msg.data))
            self.assertIs(result.data.obj, raw)
            self.assertEqual(bytes(result.data), bytes(msg.data))

    def test_truncation_and_bad_encapsulation_fail_closed(self):
        msg = Image()
        msg.header.frame_id = 'camera_b_infra1_optical_frame'
        msg.width, msg.height, msg.step, msg.encoding = 2, 1, 2, 'mono8'
        msg.data = bytes((1, 2))
        raw = serialize_message(msg)
        for truncated in (raw[:0], raw[:3], raw[:12], raw[:-1]):
            with self.assertRaises(ValueError):
                image_metadata(truncated)
        with self.assertRaises(ValueError):
            image_metadata(b'\xff\xff\x00\x00' + raw[4:])


if __name__ == '__main__':
    unittest.main()
