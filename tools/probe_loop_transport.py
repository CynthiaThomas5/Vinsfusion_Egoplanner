#!/usr/bin/env python3
"""Synthetic isolated ROS transport/failure probe, never flight/SLAM accuracy evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import signal
import subprocess
import time
import uuid

import rclpy
from rclpy.qos import qos_profile_sensor_data, QoSProfile, DurabilityPolicy
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image
from std_msgs.msg import String
from ament_index_python.packages import get_package_prefix


def until(node, predicate, timeout=8):
    deadline = time.monotonic()+timeout
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=.05)
        if predicate():
            return
    raise RuntimeError('Synthetic loop transport probe timed out')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    session = json.loads((args.session/'session.json').read_text())
    # The caller must isolate this process and its child from the flight domain.
    import os
    if os.environ.get('ROS_DOMAIN_ID') == '84' or not os.environ.get('ROS_DOMAIN_ID'):
        raise RuntimeError('Run this synthetic probe in an explicit, separate ROS domain')
    results = []
    rclpy.init()
    executable = Path(get_package_prefix('loop_fusion'))/'lib/loop_fusion/loop_fusion_node'
    executable_hash = hashlib.sha256(executable.read_bytes()).hexdigest()
    for case in ['bounded_buffers_and_time_rewind', 'wrong_frame', 'graceful_sigint']:
        namespace = '/loop_probe/s_'+uuid.uuid4().hex
        node = rclpy.create_node('loop_transport_probe')
        states, odometry = [], []
        latched = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        subscriptions = [node.create_subscription(String, namespace+'/status', lambda m: states.append(json.loads(m.data)), latched),
                         node.create_subscription(Odometry, namespace+'/odometry_rect', lambda m: odometry.append(m), qos_profile_sensor_data)]
        pose_pub = node.create_publisher(Odometry, namespace+'/odometry', 10)
        image_pub = node.create_publisher(Image, namespace+'/image', 10)
        log = args.output.parent/('probe-'+case+'.log')
        command = [str(executable), str(args.session/'vins.yaml'), '--ros-args', '-r', '__ns:='+namespace,
                   '-r', '/sensors/d435i/infra1/image_rect:='+namespace+'/image', '-p', 'queue_limit:=16']
        with log.open('w') as out:
            process = subprocess.Popen(command, stdout=out, stderr=subprocess.STDOUT)
            try:
                until(node, lambda: bool(states))
                if case == 'bounded_buffers_and_time_rewind':
                    import cv2
                    fs = cv2.FileStorage(str(args.session/'vins.yaml'), cv2.FILE_STORAGE_READ)
                    image = Image(); image.height = int(fs.getNode('image_height').real())
                    image.width = int(fs.getNode('image_width').real()); fs.release()
                    image.encoding = 'mono8'; image.step = image.width
                    image.data = bytes(image.height*image.width)
                    for k in range(80):
                        ns = 1_000_000_000+k*68_000_000
                        image.header.stamp.sec, image.header.stamp.nanosec = divmod(ns, 10**9)
                        image_pub.publish(image)
                        for _ in range(3):
                            rclpy.spin_once(node, timeout_sec=.01)
                    until(node, lambda: bool(states) and states[-1]['dropped_buffer'] > 0)
                    assert max(p['image_buffer'] for p in states) <= 16
                    msg = Odometry(); msg.header.frame_id = 'vins_'+session['epoch']+'_world'
                    msg.pose.pose.orientation.w = 1.0; msg.header.stamp.sec = 20
                    pose_pub.publish(msg)
                    until(node, lambda: bool(odometry))
                    msg.header.stamp.sec = 19; pose_pub.publish(msg)
                    until(node, lambda: process.poll() is not None)
                    assert process.returncode == 2
                elif case == 'wrong_frame':
                    msg = Odometry(); msg.header.frame_id = 'another_epoch'
                    msg.pose.pose.orientation.w = 1.0; msg.header.stamp.sec = 20
                    pose_pub.publish(msg)
                    until(node, lambda: process.poll() is not None)
                    assert process.returncode == 2
                else:
                    process.send_signal(signal.SIGINT)
                    until(node, lambda: process.poll() is not None)
                    assert process.returncode == 0
                results.append({'case': case, 'exit': process.returncode, 'last_status': states[-1], 'passed': True})
            finally:
                if process.poll() is None:
                    process.send_signal(signal.SIGINT)
                    process.wait(timeout=5)
                node.destroy_node()
    rclpy.shutdown()
    assert hashlib.sha256(executable.read_bytes()).hexdigest() == executable_hash
    args.output.write_text(json.dumps({'scope': __doc__, 'executable_sha256': executable_hash,
                                     'ros_domain_id': os.environ['ROS_DOMAIN_ID'],
                                     'cases': results, 'passed': True}, indent=2)+'\n')
    print('PASS: bounded image storage, time rewind/frame rejection and orderly SIGINT exit')


if __name__ == '__main__':
    main()
