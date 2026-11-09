#!/usr/bin/env python3
"""Read-only latest-frame relay; image and geometry use independent SSH streams."""
import argparse
import base64
import json
import os
from pathlib import Path
import signal
import threading
import time
import zlib

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import Image, PointCloud
from nav_msgs.msg import Odometry
from visualization_msgs.msg import MarkerArray
from rosidl_runtime_py.convert import message_to_ordereddict


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',required=True)
    parser.add_argument('--channel',choices=('geometry','image'),required=True)
    args=parser.parse_args();run=Path(args.run);manifest=run/'session/session.json'
    if args.channel=='image':
        import cv2
        import numpy as np
        cv2.setNumThreads(1)
    deadline=time.monotonic()+120
    while not manifest.exists():
        if time.monotonic()>deadline:raise RuntimeError('Session manifest did not appear')
        time.sleep(.2)
    session=json.loads(manifest.read_text());epoch=session['epoch'];namespace='/vins_raw/s_'+epoch
    assert session['namespace']==namespace
    signal.signal(signal.SIGINT,signal.default_int_handler)
    rclpy.init();node=Node('vins_visual_relay_'+args.channel)
    counts={};last={};total_bytes=0;pending={};lock=threading.Lock();wake=threading.Event();stopping=threading.Event()
    def send():
        nonlocal total_bytes
        try:
            while not stopping.is_set():
                wake.wait(.2);wake.clear()
                with lock:batch=dict(pending);pending.clear()
                for kind,(data,received_wall) in batch.items():
                    if kind=='stats':row=data
                    else:
                        msg=data if kind=='camera' else deserialize_message(data,types[kind])
                        header=msg.markers[0].header if kind=='camera' else msg.header
                        source_stamp=header.stamp.sec+header.stamp.nanosec*1e-9
                        frame=header.frame_id
                        if kind=='image':
                            if msg.encoding!='bgr8':raise ValueError('Expected VINS bgr8 image')
                            image=np.frombuffer(msg.data,dtype=np.uint8).reshape(msg.height,msg.step)[:,:msg.width*3].reshape(msg.height,msg.width,3)
                            image=cv2.resize(image,(640,240),interpolation=cv2.INTER_AREA)
                            ok,jpeg=cv2.imencode('.jpg',image,[cv2.IMWRITE_JPEG_QUALITY,65])
                            if not ok:raise RuntimeError('JPEG encoding failed')
                            payload=jpeg.tobytes();fmt='jpeg'
                        else:
                            payload=json.dumps(message_to_ordereddict(msg),separators=(',',':')).encode() if kind=='camera' else bytes(data)
                            payload=zlib.compress(payload,1);fmt='marker_json' if kind=='camera' else 'cdr'
                        row={'kind':kind,'epoch':epoch,'format':fmt,'payload':base64.b64encode(payload).decode(),
                             'source_stamp_s':source_stamp,'source_frame':frame,'received_wall_s':received_wall,'sent_wall_s':time.time()}
                        counts[kind]=counts.get(kind,0)+1
                    line=json.dumps(row,separators=(',',':'))+'\n';total_bytes+=len(line)
                    print(line,end='',flush=True)
        except Exception as exc:
            stopping.set()
            # Let main stop even if SSH closes without a signal.
            node.get_logger().error(str(exc))
    def callback(kind,data,period):
        now=time.monotonic()
        if now-last.get(kind,-1e9)<period:return
        last[kind]=now
        with lock:pending[kind]=(data,time.time())
        wake.set()
    types={'camera':MarkerArray,'points':PointCloud,'history':PointCloud,'image':Image,'body':Odometry}
    specs=[('image','image_track',.2)] if args.channel=='image' else [
        ('camera','camera_pose_visual',.1),('points','point_cloud',.1),('history','margin_cloud',.5),('body','imu_propagate',.05)]
    qos=QoSProfile(depth=1,reliability=ReliabilityPolicy.BEST_EFFORT)
    subscriptions=[node.create_subscription(types[k],namespace+'/'+topic,
        lambda data,k=k,p=period:callback(k,data,p),qos,raw=k!='camera') for k,topic,period in specs]
    def stats():
        row={'kind':'stats','epoch':epoch,'pid':os.getpid(),'counts':dict(counts),'wire_bytes':total_bytes,'monotonic_s':time.monotonic()}
        (run/('viz-'+args.channel+'-stats.json')).write_text(json.dumps(row,indent=2))
        with lock:pending['stats']=(row,time.time())
        wake.set()
        if stopping.is_set():raise RuntimeError('Visualization sender exited')
    node.create_timer(1.,stats)
    threading.Thread(target=send,daemon=True).start()
    (run/('viz-'+args.channel+'-ready.json')).write_text(json.dumps({'epoch':epoch,'pid':os.getpid()}))
    try:rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:
        stopping.set();wake.set();node.destroy_node()
        if rclpy.ok():rclpy.shutdown()


if __name__=='__main__':main()
