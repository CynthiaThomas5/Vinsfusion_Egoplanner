"""Read-only offline evaluation input; never publishes ROS, Gazebo or control data."""
import json
from pathlib import Path
import sys
import threading
import time
from gz.transport13 import Node
from gz.msgs10.odometry_pb2 import Odometry

run=Path(sys.argv[1]).resolve();rows=[];lock=threading.Lock();node=Node();start=time.monotonic()
def receive(m):
    p=m.pose.position;q=m.pose.orientation
    with lock:rows.append({'wall_s':time.monotonic()-start,'stamp_ns':m.header.stamp.sec*10**9+m.header.stamp.nsec,'xyz':[p.x,p.y,p.z],'q_xyzw':[q.x,q.y,q.z,q.w]})
assert node.subscribe(Odometry,'/debug_truth/base_odometry',receive)
while time.monotonic()-start<380 and not (run/'flight.json').exists():time.sleep(.2)
node.unsubscribe('/debug_truth/base_odometry')
with lock:(run/'debug-truth-evaluation.json').write_text(json.dumps({'scope':__doc__,'samples':rows},indent=2)+'\n')
