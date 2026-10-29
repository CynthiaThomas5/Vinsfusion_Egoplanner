import sys,json,time
from pathlib import Path
import rclpy
from traj_utils.msg import Bspline
from nav_msgs.msg import Odometry
from rclpy.qos import qos_profile_sensor_data
from uav_interfaces.msg import NavigationCommand,TrajectoryCancel
from rosidl_runtime_py.convert import message_to_ordereddict as asdict
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from observer_window import (observation_end_metadata, safe_session_terminal_observed,
                             should_continue_observing, install_observer_stop_handlers,
                             restore_observer_stop_handlers)
run=Path(sys.argv[1]).resolve();rclpy.init();stop_request,previous_handlers=install_observer_stop_handlers();n=rclpy.create_node('crossing_planner_readonly_observer');start=time.monotonic();rows=[]; latest_pose={}; last_write=0.0
def receive(k,m):rows.append({'wall_s':time.monotonic()-start,'type':k,'message':asdict(m)})
subs=[n.create_subscription(T,t,lambda m,k=k:receive(k,m),10) for k,T,t in [('bspline',Bspline,'/drone_0_planning/bspline'),('goal',NavigationCommand,'/navigation/ego_goal'),('cancel',TrajectoryCancel,'/navigation/trajectory_cancel')]]
def onpose(m):
 latest_pose.update(frame=m.header.frame_id,stamp_ns=m.header.stamp.sec*10**9+m.header.stamp.nanosec,xyz=[m.pose.pose.position.x,m.pose.pose.position.y,m.pose.pose.position.z],wall_s=time.monotonic()-start)
subs.append(n.create_subscription(Odometry,'/localization/optimized_imu_odom',onpose,qos_profile_sensor_data))
flight_record=run/'flight.json'
while not stop_request.requested and should_continue_observing(time.monotonic()-start,safe_session_terminal_observed(run)):
 rclpy.spin_once(n,timeout_sec=.1)
 now=time.monotonic()-start
 if now-last_write>=1:
  (run/'live-progress.json').write_text(json.dumps({'wall_s':now,'estimated_pose':latest_pose,'message_count':len(rows),'last_event':rows[-1] if rows else None})+'\n');last_write=now
end=observation_end_metadata(time.monotonic()-start,safe_session_terminal_observed(run),flight_record_exists=flight_record.is_file(),run_dir=run,stop_signal=stop_request.signal_name)
(run/'planner-observation.json').write_text(json.dumps({'scope':'Read-only live planner messages; no control, truth, or map inputs published','messages':rows,**end},indent=2)+'\n');print('messages',len(rows));n.destroy_node();rclpy.shutdown();restore_observer_stop_handlers(previous_handlers)
