"""Display follow frame follows valid motion without crossing sessions."""
from collections import deque
import math
from types import SimpleNamespace
import unittest

from nav_msgs.msg import Odometry
from uav_navigation.visualization import NavigationVisualization


class FollowViewTests(unittest.TestCase):
    def test_motion_heading_and_session_filter(self):
        sent = []
        observer = SimpleNamespace(
            ready=True, frame='odom_test', follow_frame='visualization_follow_test',
            last_stamp=None, poses=deque(), policy={'path_min_distance_m': 0.01,
                                                  'path_max_interval_s': 1.0},
            follow_tf=SimpleNamespace(sendTransform=sent.append))
        msg = Odometry()
        msg.header.frame_id = observer.frame
        msg.header.stamp.sec = 1
        msg.pose.pose.position.x = 1.0
        msg.pose.pose.orientation.w = 1.0
        NavigationVisualization.on_odometry(observer, msg)
        msg.header.stamp.sec = 2
        msg.pose.pose.position.x = 4.0
        msg.pose.pose.orientation.z = math.sqrt(0.5)
        msg.pose.pose.orientation.w = math.sqrt(0.5)
        NavigationVisualization.on_odometry(observer, msg)
        self.assertEqual([t.transform.translation.x for t in sent], [1.0, 4.0])
        self.assertEqual(sent[-1].child_frame_id, observer.follow_frame)
        self.assertAlmostEqual(sent[-1].transform.rotation.z, math.sqrt(0.5))
        self.assertEqual(sent[-1].transform.rotation.x, 0.0)
        self.assertEqual(sent[-1].transform.rotation.y, 0.0)
        msg.header.frame_id = 'odom_old'
        NavigationVisualization.on_odometry(observer, msg)
        observer.ready = False
        msg.header.frame_id = observer.frame
        NavigationVisualization.on_odometry(observer, msg)
        self.assertEqual(len(sent), 2)


if __name__ == '__main__':
    unittest.main()
