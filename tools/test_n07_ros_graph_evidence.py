import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'diagnostics'))
from n07_ros_graph_evidence import CONTROL_TOPICS, qualify_report


def endpoint(name, gid):
    return {'node_name': name, 'node_namespace': '/', 'endpoint_gid': gid}


def snapshot(label, names, truth_topics=None):
    return {
        'label': label,
        'publishers': {topic: [endpoint(names.get(topic, 'uav_px4_bridge'), topic + '-gid')]
                       for topic in CONTROL_TOPICS},
        'truth_named_ros_topics': truth_topics or [],
        'truth_named_ros_nodes': [],
        'checks': {'no_ros_truth_topic_or_node': not truth_topics,
                   'one_uav_px4_bridge_publisher_per_px4_control_topic': True},
    }


class N07RosGraphEvidenceTest(unittest.TestCase):
    def test_delayed_dds_names_resolve_only_by_stable_endpoint_gid(self):
        first = snapshot('pre_enable', {topic: '_NODE_NAME_UNKNOWN_' for topic in CONTROL_TOPICS})
        active = snapshot('airborne', {})
        report = qualify_report({'control_topics': list(CONTROL_TOPICS),
                                 'snapshots': [first, active], 'checks_passed': False})
        self.assertTrue(report['checks_passed'])
        self.assertFalse(report['raw_capture_checks_passed'])
        self.assertEqual(
            report['control_owner_reconciliation']['snapshot_results'][0]['topics'][CONTROL_TOPICS[0]]['resolved_by'],
            'same_endpoint_gid_later_named_uav_px4_bridge')

    def test_unresolved_endpoint_without_matching_bridge_gid_fails(self):
        first = snapshot('pre_enable', {topic: '_NODE_NAME_UNKNOWN_' for topic in CONTROL_TOPICS})
        active = snapshot('airborne', {})
        active['publishers'][CONTROL_TOPICS[0]][0]['endpoint_gid'] = 'different-gid'
        report = qualify_report({'control_topics': list(CONTROL_TOPICS),
                                 'snapshots': [first, active]})
        self.assertFalse(report['checks_passed'])

    def test_duplicate_publisher_fails(self):
        active = snapshot('airborne', {})
        active['publishers'][CONTROL_TOPICS[0]].append(endpoint('intruder', 'second-gid'))
        report = qualify_report({'control_topics': list(CONTROL_TOPICS), 'snapshots': [active]})
        self.assertFalse(report['checks_passed'])

    def test_truth_topic_fails(self):
        active = snapshot('airborne', {}, truth_topics=['/debug_truth/pose'])
        report = qualify_report({'control_topics': list(CONTROL_TOPICS), 'snapshots': [active]})
        self.assertFalse(report['checks_passed'])


if __name__ == '__main__':
    unittest.main()
