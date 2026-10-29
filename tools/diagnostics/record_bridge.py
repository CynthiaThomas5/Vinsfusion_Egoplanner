import sys,json,time
from pathlib import Path
import rclpy
from rclpy.qos import QoSProfile,DurabilityPolicy
from uav_interfaces.msg import Px4BridgeStatus
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from observer_window import (observation_end_metadata, safe_session_terminal_observed,
                             should_continue_observing, install_observer_stop_handlers,
                             restore_observer_stop_handlers)
run=Path(sys.argv[1]).resolve();rclpy.init();stop_request,previous_handlers=install_observer_stop_handlers();n=rclpy.create_node('bridge_alignment_readonly');start=time.monotonic();rows=[];key=None
out=(run/'bridge-alignment-timeline.jsonl').open('w')
def receive(m):
 global key
 new=(m.phase,m.reason,m.armed,m.landed,*m.frame_offset_ned,m.frame_yaw_offset_ned)
 if new==key:return
 key=new;d={'wall_s':time.monotonic()-start,'stamp_ns':m.header.stamp.sec*10**9+m.header.stamp.nanosec,'phase':m.phase,'reason':m.reason,'armed':m.armed,'landed':m.landed,'offset_ned':list(m.frame_offset_ned),'yaw_offset_ned':m.frame_yaw_offset_ned,'alignment_drift_m':m.alignment_drift_m};out.write(json.dumps(d)+'\n');out.flush()
sub=n.create_subscription(Px4BridgeStatus,'/uav_px4_bridge/status',receive,QoSProfile(depth=10))
flight_record=run/'flight.json'
while not stop_request.requested and should_continue_observing(time.monotonic()-start,safe_session_terminal_observed(run)):rclpy.spin_once(n,timeout_sec=.1)
end=observation_end_metadata(time.monotonic()-start,safe_session_terminal_observed(run),flight_record_exists=flight_record.is_file(),run_dir=run,stop_signal=stop_request.signal_name)
out.close()
(run/'bridge-observation.json').write_text(json.dumps({'scope':'Read-only PX4 bridge phase observation',**end},indent=2)+'\n')
n.destroy_node();rclpy.shutdown();restore_observer_stop_handlers(previous_handlers)
