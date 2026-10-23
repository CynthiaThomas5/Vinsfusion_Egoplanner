"""Read-only loop transport observation; no image storage, truth or controls."""
import json
import argparse
import os
from pathlib import Path
import sys
import time

import rclpy
from rclpy.qos import QoSProfile, DurabilityPolicy, qos_profile_sensor_data
from nav_msgs.msg import Odometry, Path as PathMessage
from sensor_msgs.msg import PointCloud
from std_msgs.msg import String
from visualization_msgs.msg import MarkerArray

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('run', type=Path)
parser.add_argument('--end-marker', default='flight.json')
parser.add_argument('--max-wall-s', type=float, default=380)
args = parser.parse_args()
if not 1 <= args.max_wall_s <= 1800:
    parser.error('max-wall-s must be in [1,1800]')
run = args.run.resolve()
session = json.loads((run.parent/(run.name+'-stack')/'session/session.json').read_text())
namespace = '/loop_observer/s_'+session['epoch']
rclpy.init()
node = rclpy.create_node('loop_readonly_recorder')
start = time.monotonic()
report = {'scope': __doc__, 'epoch': session['epoch'], 'namespace': namespace,
          'status': [], 'paths': [], 'clouds': [], 'odometry': [], 'last_path': None,
          'last_cloud': None, 'last_markers': None, 'graph_revisions': [],
          'candidate_diagnostics': []}
report['process_resources'] = []
report['cpu_ticks_per_second'] = os.sysconf('SC_CLK_TCK')
live_status = (run/'loop-status.jsonl').open('x', buffering=1)


def stamp(header):
    return header.stamp.sec*10**9+header.stamp.nanosec


def pose(p):
    return {'xyz': [p.position.x, p.position.y, p.position.z],
            'q_xyzw': [p.orientation.x, p.orientation.y, p.orientation.z, p.orientation.w]}


def onpath(m):
    report['paths'].append({'wall_s': time.monotonic()-start, 'source_ns': stamp(m.header),
                            'frame': m.header.frame_id, 'count': len(m.poses)})
    report['last_path'] = {'frame': m.header.frame_id, 'poses': [
        {'source_ns': stamp(p.header), **pose(p.pose)} for p in m.poses]}


def oncloud(m):
    report['clouds'].append({'source_ns': stamp(m.header), 'frame': m.header.frame_id, 'count': len(m.points)})
    report['last_cloud'] = {'source_ns': stamp(m.header), 'frame': m.header.frame_id,
                            'xyz': [[p.x, p.y, p.z] for p in m.points]}


def onmarkers(m):
    report['last_markers'] = [{'namespace': p.ns, 'id': p.id, 'frame': p.header.frame_id,
                               'type': p.type, 'xyz': [[v.x, v.y, v.z] for v in p.points]} for p in m.markers]


def onstatus(m):
    status = json.loads(m.data)
    graph = status.pop('graph', None)
    candidate_batch = status.get('candidate_diagnostics', {})
    if isinstance(candidate_batch, dict):
        report['candidate_diagnostics'].extend(candidate_batch.get('events', []))
    wall = time.monotonic()-start
    if graph is not None:
        revision = [status['keyframes'], status['verified_loops'], status['optimizations']]
        if not report['graph_revisions'] or report['graph_revisions'][-1]['revision'] != revision:
            report['graph_revisions'].append({'wall_s': wall, 'revision': revision, 'graph': graph})
    report['status'].append({'wall_s': wall, **status})
    live_status.write(json.dumps({'wall_s': wall, **status})+'\n')
    pid = int((run/'loop-observer.pid').read_text())
    process = Path('/proc')/str(pid)
    fields = (process/'stat').read_text().rsplit(')', 1)[1].split()
    values = dict(line.split(':', 1) for line in (process/'status').read_text().splitlines() if ':' in line)
    report['process_resources'].append({'wall_s': time.monotonic()-start,
        'cpu_ticks': int(fields[11])+int(fields[12]),
        'rss_kib': int(values['VmRSS'].split()[0]), 'hwm_kib': int(values['VmHWM'].split()[0]),
        'threads': int(values['Threads'])})


def onodom(m):
    report['odometry'].append({'source_ns': stamp(m.header), 'frame': m.header.frame_id, **pose(m.pose.pose)})


latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
subs = [node.create_subscription(T, namespace+'/'+topic, callback, qos)
        for T, topic, callback, qos in [(PathMessage, 'pose_graph_path', onpath, latched),
                                       (MarkerArray, 'pose_graph', onmarkers, latched),
                                       (String, 'status', onstatus, latched),
                                       (PointCloud, 'point_cloud_loop_rect', oncloud, qos_profile_sensor_data),
                                       (Odometry, 'odometry_rect', onodom, qos_profile_sensor_data)]]
after_flight = None
while time.monotonic()-start < args.max_wall_s:
    rclpy.spin_once(node, timeout_sec=.1)
    if (run/args.end_marker).exists():
        after_flight = after_flight or time.monotonic()
        if time.monotonic()-after_flight >= 2:
            break
report['observer_node_publishers'] = node.get_publisher_names_and_types_by_node('loop_fusion', namespace)
report['observer_node_subscriptions'] = node.get_subscriber_names_and_types_by_node('loop_fusion', namespace)
(run/'loop-observation.json').write_text(json.dumps(report, indent=2)+'\n')
live_status.close()
node.destroy_node()
rclpy.shutdown()
