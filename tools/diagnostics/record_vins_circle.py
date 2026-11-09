#!/usr/bin/env python3
"""Record new, unique poses from the local groundstation VINS Path display."""
import argparse
import json
import signal
import time
from pathlib import Path

import rclpy
from nav_msgs.msg import Path as ROSPath


def pose_row(message, receipt):
    stamp=message.header.stamp
    p=message.pose.position
    q=message.pose.orientation
    return {'stamp_ns':stamp.sec*1_000_000_000+stamp.nanosec,
            'receipt_monotonic_s':receipt,
            'position_m':[p.x,p.y,p.z],
            'orientation_xyzw':[q.x,q.y,q.z,q.w]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();baseline=[];last_stamp=0;rows=0;last_row=None;max_gap=0.
    stream=(args.output/'circle-poses.jsonl').open('x',buffering=1)
    rclpy.init();node=rclpy.create_node('groundstation_vins_circle_recorder')

    def receive(message):
        nonlocal baseline,last_stamp,rows,last_row,max_gap
        receipt=time.monotonic()
        new=[]
        for stamped in message.poses:
            row=pose_row(stamped,receipt)
            if row['stamp_ns']>last_stamp:
                new.append(row);last_stamp=row['stamp_ns']
        if not baseline and len(message.poses)>=20:
            baseline=[pose_row(x,receipt) for x in message.poses[-20:]]
            start=baseline[-1]
            (args.output/'circle-start.json').write_text(json.dumps(
                {'baseline':baseline,'start':start,'path_frame':message.header.frame_id},indent=2)+'\n')
            (args.output/'circle-ready.json').write_text(json.dumps(
                {'poses':len(baseline),'receipt_monotonic_s':receipt},indent=2)+'\n')
            new=[x for x in new if x['stamp_ns']>baseline[-1]['stamp_ns']]
        if not baseline:return
        for row in new:
            if last_row:
                max_gap=max(max_gap,row['receipt_monotonic_s']-last_row['receipt_monotonic_s'])
            stream.write(json.dumps(row,separators=(',',':'))+'\n');rows+=1;last_row=row

    node.create_subscription(ROSPath,'/hardware_view/vins_path',receive,10)
    running=True
    def stop(_signum,_frame):
        nonlocal running
        running=False
    signal.signal(signal.SIGINT,stop);signal.signal(signal.SIGTERM,stop)
    try:
        while running and rclpy.ok():rclpy.spin_once(node,timeout_sec=.2)
    finally:
        stream.close()
        (args.output/'circle-end.json').write_text(json.dumps(
            {'last_pose':last_row,'recorded_poses':rows,'baseline_ready':bool(baseline)},indent=2)+'\n')
        (args.output/'recorder-summary.json').write_text(json.dumps(
            {'baseline_ready':bool(baseline),'recorded_poses':rows,
             'duration_s':time.monotonic()-started,'max_receipt_gap_s':max_gap},indent=2)+'\n')
        node.destroy_node()
        if rclpy.ok():rclpy.shutdown()


if __name__=='__main__':main()
