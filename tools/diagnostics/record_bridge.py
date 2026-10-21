import sys,json,time
from pathlib import Path
import rclpy
from rclpy.qos import QoSProfile,DurabilityPolicy
from uav_interfaces.msg import Px4BridgeStatus
run=Path(sys.argv[1]).resolve();rclpy.init();n=rclpy.create_node('bridge_alignment_readonly');start=time.monotonic();rows=[];key=None
out=(run/'bridge-alignment-timeline.jsonl').open('w')
def receive(m):
 global key
 new=(m.phase,m.reason,m.armed,m.landed,*m.frame_offset_ned,m.frame_yaw_offset_ned)
 if new==key:return
 key=new;d={'wall_s':time.monotonic()-start,'stamp_ns':m.header.stamp.sec*10**9+m.header.stamp.nanosec,'phase':m.phase,'reason':m.reason,'armed':m.armed,'landed':m.landed,'offset_ned':list(m.frame_offset_ned),'yaw_offset_ned':m.frame_yaw_offset_ned,'alignment_drift_m':m.alignment_drift_m};out.write(json.dumps(d)+'\n');out.flush()
sub=n.create_subscription(Px4BridgeStatus,'/uav_px4_bridge/status',receive,QoSProfile(depth=10))
while time.monotonic()-start<380 and not (run/'flight.json').exists():rclpy.spin_once(n,timeout_sec=.1)
out.close();n.destroy_node();rclpy.shutdown()
