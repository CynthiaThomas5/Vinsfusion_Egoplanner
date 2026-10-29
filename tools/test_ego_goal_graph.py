import unittest
from check_ego_goal_graph import check_graph

def graph(publishers,subscribers):
    return '\n'.join(f'Node name: {name}\nEndpoint type: {kind}\n' for names,kind in [(publishers,'PUBLISHER'),(subscribers,'SUBSCRIPTION')] for name in names)

class EgoGoalGraphTests(unittest.TestCase):
    def test_required_control_endpoints_with_observers(self):
        self.assertTrue(check_graph(graph(['uav_navigation'],['uav_px4_bridge','drone_0_ego_planner_node','navigation_visualization','crossing_planner_readonly_observer'])))
    def test_extra_publisher_or_missing_control_subscriber_rejected(self):
        self.assertFalse(check_graph(graph(['uav_navigation','foreign'],['uav_px4_bridge','drone_0_ego_planner_node'])))
        self.assertFalse(check_graph(graph(['uav_navigation'],['drone_0_ego_planner_node','readonly'])))
    def test_missing_graph_not_accepted(self):
        self.assertFalse(check_graph('Publisher count: 1\nSubscription count: 4\n'))
