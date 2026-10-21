"""Read-only, full-attitude evidence for source-time alignment analysis."""
import sys,json,time
from pathlib import Path
import rclpy
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry
from px4_msgs.msg import VehicleLocalPosition,VehicleAttitude
run=Path(sys.argv[1]).resolve()
rclpy.init();n=rclpy.create_node('alignment_readonly_recorder');start=time.monotonic();rows=[]
def onodom(m):
 p=m.pose.pose.position;q=m.pose.pose.orientation;t=m.header.stamp
 rows.append({'kind':'odom','wall_s':time.monotonic()-start,'source_ns':t.sec*10**9+t.nanosec,'xyz':[p.x,p.y,p.z],'q_xyzw':[q.x,q.y,q.z,q.w]})
def onlocal(m):rows.append({'kind':'local','wall_s':time.monotonic()-start,'timestamp_us':m.timestamp,'sample_us':m.timestamp_sample,'xyz':[m.x,m.y,m.z],'v':[m.vx,m.vy,m.vz],'heading':m.heading})
def onattitude(m):rows.append({'kind':'attitude','wall_s':time.monotonic()-start,'timestamp_us':m.timestamp,'sample_us':m.timestamp_sample,'q_wxyz':[float(v) for v in m.q]})
subs=[n.create_subscription(T,t,cb,qos_profile_sensor_data) for T,t,cb in [(Odometry,'/localization/optimized_imu_odom',onodom),(VehicleLocalPosition,'/fmu/out/vehicle_local_position_v1',onlocal),(VehicleAttitude,'/fmu/out/vehicle_attitude',onattitude)]]
while time.monotonic()-start<380 and not (run/'flight.json').exists():rclpy.spin_once(n,timeout_sec=.1)
(run/'alignment-observation.json').write_text(json.dumps({'scope':'Read-only estimated states, no control or truth inputs published','samples':rows},indent=2)+'\n');n.destroy_node();rclpy.shutdown()
