"""Read-only, full-attitude evidence for source-time alignment analysis."""
import sys,json,time
from pathlib import Path
import rclpy
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry
from px4_msgs.msg import VehicleLocalPosition,VehicleAttitude
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from observer_window import (observation_end_metadata, safe_session_terminal_observed,
                             should_continue_observing, install_observer_stop_handlers,
                             restore_observer_stop_handlers)
run=Path(sys.argv[1]).resolve()
session=json.loads((run.parent/(run.name+'-stack')/'session/session.json').read_text())
rclpy.init();stop_request,previous_handlers=install_observer_stop_handlers();n=rclpy.create_node('alignment_readonly_recorder');start=time.monotonic();rows=[]
def onodom(m,kind='odom'):
    p=m.pose.pose.position;q=m.pose.pose.orientation;t=m.header.stamp
    row={'kind':kind,'wall_s':time.monotonic()-start,'source_ns':t.sec*10**9+t.nanosec,'frame_id':m.header.frame_id,'child_frame_id':m.child_frame_id,'xyz':[p.x,p.y,p.z],'q_xyzw':[q.x,q.y,q.z,q.w]}
    if kind=='raw_odom':
        v=m.twist.twist.linear
        row['linear_velocity_world_m_s']=[v.x,v.y,v.z]
    rows.append(row)
def onlocal(m):rows.append({'kind':'local','wall_s':time.monotonic()-start,'timestamp_us':m.timestamp,'sample_us':m.timestamp_sample,'xyz':[m.x,m.y,m.z],'v':[m.vx,m.vy,m.vz],'heading':m.heading})
def onattitude(m):rows.append({'kind':'attitude','wall_s':time.monotonic()-start,'timestamp_us':m.timestamp,'sample_us':m.timestamp_sample,'q_wxyz':[float(v) for v in m.q]})
subs=[n.create_subscription(T,t,cb,qos_profile_sensor_data) for T,t,cb in [(Odometry,'/localization/optimized_imu_odom',onodom),(VehicleLocalPosition,'/fmu/out/vehicle_local_position_v1',onlocal),(VehicleAttitude,'/fmu/out/vehicle_attitude',onattitude)]]
subs.append(n.create_subscription(Odometry,session['namespace']+'/odometry',lambda m:onodom(m,'raw_odom'),qos_profile_sensor_data))
flight_record=run/'flight.json'
while not stop_request.requested and should_continue_observing(time.monotonic()-start,safe_session_terminal_observed(run)):rclpy.spin_once(n,timeout_sec=.1)
end=observation_end_metadata(time.monotonic()-start,safe_session_terminal_observed(run),flight_record_exists=flight_record.is_file(),run_dir=run,stop_signal=stop_request.signal_name)
(run/'alignment-observation.json').write_text(json.dumps({'scope':'Read-only estimated states, no control or truth inputs published','raw_velocity_semantics':'For raw_odom, twist.twist.linear copies VINS estimator.Vs published in WORLD_FRAME_ID; no body-frame transform is applied by this recorder.','epoch':session['epoch'],'raw_topic':session['namespace']+'/odometry','samples':rows,**end},indent=2)+'\n');n.destroy_node();rclpy.shutdown();restore_observer_stop_handlers(previous_handlers)
