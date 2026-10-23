#!/usr/bin/env python3
"""Read-only, source-stamped Gazebo truth for an unarmed fixture diagnostic."""
import argparse
import json
from pathlib import Path
import threading
import time


def main():
    from gz.transport13 import Node
    from gz.msgs10.odometry_pb2 import Odometry
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--end-marker', default='fixture-result.json')
    parser.add_argument('--output', default='fixture-truth.jsonl')
    parser.add_argument('--max-wall-s', type=float, default=650)
    args = parser.parse_args()
    if not 1 <= args.max_wall_s <= 1800:
        parser.error('max-wall-s must be in [1,1800]')
    node = Node()
    lock = threading.Lock()
    path = args.run / args.output
    with path.open('x') as stream:
        active = True
        def receive(message):
            p, q, t = message.pose.position, message.pose.orientation, message.header.stamp
            row = {'stamp_ns': t.sec * 10**9 + t.nsec, 'xyz': [p.x, p.y, p.z],
                   'q_xyzw': [q.x, q.y, q.z, q.w],
                   'receive_monotonic_ns': time.monotonic_ns()}
            with lock:
                if active:
                    stream.write(json.dumps(row) + '\n')

        if not node.subscribe(Odometry, '/debug_truth/base_odometry', receive):
            raise RuntimeError('truth subscription rejected')
        deadline = time.monotonic() + args.max_wall_s
        while time.monotonic() < deadline and not (args.run / args.end_marker).exists():
            time.sleep(.2)
        node.unsubscribe('/debug_truth/base_odometry')
        # Serialize stream closing against an in-flight transport callback.
        with lock:
            active = False
            stream.flush()


if __name__ == '__main__':
    main()
