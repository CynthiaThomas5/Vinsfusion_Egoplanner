#!/usr/bin/env python3
"""Read-only map/reference display through SSH; custom DDS stays on the Nano."""
import argparse
import base64
import json
import math
from pathlib import Path
import queue
import shlex
import signal
import subprocess
import sys
import threading
import time
import zlib

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from rclpy.serialization import serialize_message, deserialize_message
from sensor_msgs.msg import PointCloud2
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Path as PathMessage
from visualization_msgs.msg import Marker


def decode_cloud(row, epoch, stamp):
    if row['epoch'] != epoch or row['kind'] not in ('map', 'inflated'):
        raise ValueError('Map epoch/kind mismatch')
    if len(row['payload']) > 16*1024*1024:
        raise ValueError('Oversized map packet')
    decoder = zlib.decompressobj()
    data = decoder.decompress(base64.b64decode(row['payload'], validate=True), 8*1024*1024+1)
    if len(data) > 8*1024*1024 or not decoder.eof or decoder.unused_data:
        raise ValueError('Invalid compressed map packet')
    msg = deserialize_message(data, PointCloud2)
    if msg.header.frame_id != 'odom_'+epoch:
        raise ValueError('Map source frame mismatch')
    # Coordinates remain in the current VINS world; arrival time is display-only.
    msg.header.frame_id = 'hardware_display'
    msg.header.stamp = stamp
    return msg


def relay(args):
    from uav_interfaces.msg import LocalizationStatus, PositionCommand
    epoch = json.loads((Path(args.run)/'session/session.json').read_text())['epoch']
    node = Node('groundstation_map_readonly_relay')
    latest = {}
    def cloud(kind, msg):
        if msg.header.frame_id == 'odom_'+epoch:
            latest[kind] = {'kind':kind, 'epoch':epoch,
                           'payload':base64.b64encode(zlib.compress(serialize_message(msg), 1)).decode()}
    def status(msg):
        latest['status'] = {'kind':'status', 'epoch':msg.epoch, 'valid':msg.valid, 'reason':msg.reason}
    def reference(msg):
        if msg.epoch == epoch and msg.header.frame_id == 'odom_'+epoch:
            latest['reference'] = {'kind':'reference', 'epoch':epoch, 'id':msg.trajectory_id,
                                   'ready':msg.trajectory_flag == msg.TRAJECTORY_STATUS_READY,
                                   'point':[msg.position.x,msg.position.y,msg.position.z]}
    qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT)
    subscriptions = [
        node.create_subscription(PointCloud2, '/grid_map/occupancy', lambda m:cloud('map',m), qos),
        node.create_subscription(PointCloud2, '/hardware_map_only/occupancy_inflate', lambda m:cloud('inflated',m), qos),
        node.create_subscription(PositionCommand, '/position_cmd', reference, qos),
        node.create_subscription(LocalizationStatus, '/localization/status', status,
            QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)),
    ]
    def send():
        for kind in list(latest):
            print(json.dumps(latest.pop(kind), separators=(',',':')), flush=True)
    node.create_timer(.5, send)
    stopping = threading.Event()
    def watch_connection():
        sys.stdin.buffer.read()
        stopping.set()
    threading.Thread(target=watch_connection,daemon=True).start()
    try:
        while rclpy.ok() and not stopping.is_set():
            rclpy.spin_once(node,timeout_sec=.2)
    finally:
        node.destroy_node()


def view(args):
    node = Node('groundstation_map_display_only')
    epoch = json.loads(subprocess.check_output(['ssh',args.host,
        'cat '+shlex.quote(args.run+'/session/session.json')], text=True))['epoch']
    command = ('cd '+shlex.quote(args.root)+'; source tools/hardware-env.bash; '
               'export ROS_DOMAIN_ID='+str(args.relay_domain)+'; '
               'export FASTRTPS_DEFAULT_PROFILES_FILE="$PWD/config/hardware/vins_fastdds_udp_rxbuf4m.xml"; '
               'exec python3 tools/diagnostics/groundstation_map.py relay --run '+shlex.quote(args.run))
    child = subprocess.Popen(['ssh','-o','BatchMode=yes',args.host,command],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
    pending = queue.Queue(maxsize=12)
    def read():
        for line in child.stdout:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if pending.full():
                try: pending.get_nowait()
                except queue.Empty: pass
            pending.put(row)
    threading.Thread(target=read,daemon=True).start()
    pubs = {kind:node.create_publisher(PointCloud2,'/groundstation/'+kind,1) for kind in ('map','inflated')}
    path_pub = node.create_publisher(PathMessage,'/groundstation/reference_samples',1)
    label_pub = node.create_publisher(Marker,'/groundstation/status',1)
    path = PathMessage(); path.header.frame_id = 'hardware_display'
    valid = False; received = 0.; trajectory = None
    last_cloud = {}; counts = {}; reason = 'WAITING FOR NANO LOCALIZATION / MAP'
    def clear():
        path.poses.clear(); path_pub.publish(path)
        for kind,pub in pubs.items():
            if kind not in last_cloud: continue
            old = last_cloud[kind]
            msg = PointCloud2(); msg.header.frame_id = 'hardware_display'
            msg.fields = old.fields; msg.point_step = old.point_step; msg.height = 1
            pub.publish(msg)
    def tick():
        nonlocal valid,received,trajectory,reason
        while not pending.empty():
            row = pending.get()
            if row['epoch'] != epoch:
                valid = False; clear(); continue
            if row['kind'] == 'status':
                valid = row['valid']; received = time.monotonic()
                reason = row['reason']
                if not valid: clear()
            elif valid and time.monotonic()-received < 3:
                if row['kind'] in pubs:
                    kind = row['kind']
                    msg = decode_cloud(row,epoch,node.get_clock().now().to_msg())
                    last_cloud[kind] = msg; counts[kind] = counts.get(kind,0)+1
                    pubs[kind].publish(msg)
                elif row['kind'] == 'reference':
                    if trajectory != row['id'] or not row['ready']:
                        path.poses.clear(); trajectory = row['id']
                    if row['ready'] and all(math.isfinite(x) for x in row['point']):
                        pose = PoseStamped(); pose.header = path.header; pose.pose.orientation.w = 1.
                        pose.pose.position.x,pose.pose.position.y,pose.pose.position.z = row['point']
                        path.poses.append(pose); path.poses = path.poses[-600:]
                    path.header.stamp = node.get_clock().now().to_msg(); path_pub.publish(path)
        if time.monotonic()-received > 3:
            valid = False; clear()
        label = Marker(); label.header.frame_id = 'hardware_display'
        label.type = Marker.TEXT_VIEW_FACING; label.pose.orientation.w = 1.
        label.pose.position.z = 1.; label.scale.z = .15
        label.color.a = 1.; label.color.r = 0.2 if valid else 1.; label.color.g = 0.8
        label.text = ('LOCALIZATION VALID' if valid else 'INVALID / NO LIVE DATA')+'\n'+reason+'\nmap packets '+str(counts)
        label_pub.publish(label)
    node.create_timer(.2,tick)
    try:
        rclpy.spin(node)
    finally:
        child.stdin.close()
        try: child.wait(timeout=3)
        except subprocess.TimeoutExpired:
            child.terminate()
            try: child.wait(timeout=3)
            except subprocess.TimeoutExpired: child.kill(); child.wait()
        node.destroy_node()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('relay','view'))
    parser.add_argument('--run', required=True)
    parser.add_argument('--host')
    parser.add_argument('--root')
    parser.add_argument('--relay-domain',type=int,default=0)
    args = parser.parse_args()
    if not 0 <= args.relay_domain <= 232:
        parser.error('Invalid relay ROS domain')
    signal.signal(signal.SIGTERM,signal.default_int_handler)
    rclpy.init()
    try:
        (relay if args.mode == 'relay' else view)(args)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok(): rclpy.shutdown()


if __name__ == '__main__':
    main()
