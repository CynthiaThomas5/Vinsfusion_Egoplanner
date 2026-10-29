"""Resolve read-only N07 ROS graph publisher ownership evidence."""

CONTROL_TOPICS = (
    '/fmu/in/vehicle_visual_odometry',
    '/fmu/in/offboard_control_mode',
    '/fmu/in/trajectory_setpoint',
    '/fmu/in/vehicle_command',
)
UNKNOWN_PUBLISHER_NAMES = {'', '_NODE_NAME_UNKNOWN_'}


def qualify_report(report):
    """Qualify unique control publishers, resolving delayed DDS node names by GID.

    A publisher first seen with an unresolved DDS node name is accepted only if
    its topic has exactly one publisher and the same endpoint GID is later
    reported as ``uav_px4_bridge``. Duplicate or mismatched endpoints fail.
    Raw per-snapshot checks remain intact in the returned document.
    """
    snapshots = report.get('snapshots') or []
    topics = report.get('control_topics') or list(CONTROL_TOPICS)
    bridge_gids = {topic: set() for topic in topics}
    for snapshot in snapshots:
        publishers = snapshot.get('publishers') or {}
        for topic in topics:
            endpoints = publishers.get(topic) or []
            if len(endpoints) == 1 and endpoints[0].get('node_name') == 'uav_px4_bridge':
                gid = endpoints[0].get('endpoint_gid')
                if gid:
                    bridge_gids[topic].add(gid)

    snapshot_results = []
    for snapshot in snapshots:
        publishers = snapshot.get('publishers') or {}
        topic_results = {}
        for topic in topics:
            endpoints = publishers.get(topic) or []
            if len(endpoints) != 1:
                topic_results[topic] = {
                    'passed': False,
                    'reason': 'publisher_count_not_one',
                    'publisher_count': len(endpoints),
                }
                continue
            endpoint = endpoints[0]
            name = endpoint.get('node_name', '')
            gid = endpoint.get('endpoint_gid', '')
            if name == 'uav_px4_bridge':
                topic_results[topic] = {'passed': True, 'resolved_by': 'node_name', 'endpoint_gid': gid}
            elif name in UNKNOWN_PUBLISHER_NAMES and gid and gid in bridge_gids[topic]:
                topic_results[topic] = {
                    'passed': True,
                    'resolved_by': 'same_endpoint_gid_later_named_uav_px4_bridge',
                    'endpoint_gid': gid,
                }
            else:
                topic_results[topic] = {
                    'passed': False,
                    'reason': 'publisher_not_identified_as_uav_px4_bridge',
                    'node_name': name,
                    'endpoint_gid': gid,
                }
        no_truth = (not snapshot.get('truth_named_ros_topics')
                    and not snapshot.get('truth_named_ros_nodes'))
        snapshot_results.append({
            'label': snapshot.get('label'),
            'one_uav_px4_bridge_publisher_per_control_topic': all(
                item['passed'] for item in topic_results.values()),
            'no_ros_truth_topic_or_node': no_truth,
            'topics': topic_results,
        })

    raw_check = report.get('checks_passed')
    qualified = bool(snapshot_results) and all(
        row['one_uav_px4_bridge_publisher_per_control_topic']
        and row['no_ros_truth_topic_or_node'] for row in snapshot_results)
    result = dict(report)
    result['raw_capture_checks_passed'] = raw_check
    result['checks_passed'] = qualified
    result['control_owner_reconciliation'] = {
        'method': 'exactly one publisher per control topic in each snapshot; unresolved startup DDS names are resolved only by the same endpoint GID later identified as uav_px4_bridge',
        'snapshot_results': snapshot_results,
        'passed': qualified,
    }
    return result
