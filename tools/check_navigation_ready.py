"""Read-only room-crossing preflight under canonical freshness limits."""
import json,math,time,sys
from pathlib import Path
from collections import Counter
import rclpy
from rclpy.qos import qos_profile_sensor_data,QoSProfile,DurabilityPolicy
from rosidl_runtime_py.convert import message_to_ordereddict as asdict
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock
from std_msgs.msg import String
from uav_interfaces.msg import LocalizationStatus,MapStatus,Px4BridgeStatus
root=Path(__file__).resolve().parents[1];run=Path(sys.argv[1]).resolve()
nav=json.loads((root/'config/components/navigation/task_supervisor.json').read_text())
rclpy.init();n=rclpy.create_node('room_crossing_preflight');latest={};receipt={};history=[];odoms=[];clocks=[];started=time.monotonic(); metrics=[]; metric_subscriptions=[]
def receive(k,m):
 latest[k]=m;receipt[k]=time.monotonic()
 if k=='localization' and m.epoch and not metric_subscriptions:
  def onmetric(msg):
   try: value=json.loads(msg.data)
   except ValueError:return
   metrics.append({'wall_s':time.monotonic()-started,'value':value})
  metric_subscriptions.append(n.create_subscription(String,'/vins_raw/s_'+m.epoch+'/estimator_telemetry',onmetric,qos_profile_sensor_data))
 if k=='odom':odoms.append({'wall_s':receipt[k]-started,'stamp_ns':m.header.stamp.sec*10**9+m.header.stamp.nanosec})
 if k=='clock':clocks.append({'wall_s':receipt[k]-started,'sim_ns':m.clock.sec*10**9+m.clock.nanosec})
q=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL)
subs=[n.create_subscription(T,t,lambda m,k=k:receive(k,m),q if k in ['localization','map'] else (qos_profile_sensor_data if k in ['odom','clock'] else 10)) for k,T,t in [('localization',LocalizationStatus,'/localization/status'),('map',MapStatus,'/mapping/status'),('bridge',Px4BridgeStatus,'/uav_px4_bridge/status'),('detail',String,'/uav_px4_bridge/status/detail'),('odom',Odometry,'/localization/optimized_imu_odom'),('clock',Clock,'/clock')]]
stable_start=None;max_stable=0.;last_sample=0.;passed=False
while time.monotonic()-started<40:
 rclpy.spin_once(n,timeout_sec=.03);now=time.monotonic();fail=[]
 for k in ['localization','map','bridge','detail','odom','clock']:
  if k not in latest:fail.append('missing_'+k)
 l=latest.get('localization');m=latest.get('map');b=latest.get('bridge');o=latest.get('odom')
 if l and not(l.valid and l.state==1):fail.append('localization_'+l.reason)
 if 'localization' in receipt and now-receipt['localization']>nav['max_localization_receipt_age_s']:fail.append('localization_receipt_stale')
 if 'odom' in receipt and now-receipt['odom']>nav['max_odometry_receipt_age_s']:fail.append('optimized_odometry_receipt_stale')
 if l and o and o.header.frame_id!='odom_'+l.epoch:fail.append('epoch_frame_mismatch')
 if m and not(m.input_ready and m.occupied_point_count>0):fail.append('map_'+m.reason)
 if b:
  if not b.ready and b.reason!='px4_preflight_failed':fail.append('bridge_not_ready_'+b.reason)
  if b.control_enabled or b.armed or not b.landed or b.phase!='DISABLED':fail.append('unexpected_control_state')
  if not(b.local_position_valid and b.ev_position_fused and b.ev_yaw_fused):fail.append('px4_external_vision_not_fused')
  if b.gnss_aiding_active:fail.append('gnss_aiding_active')
 if 'detail' in latest:
  try:d=json.loads(latest['detail'].data)
  except ValueError:d={}
  for name in ['vehicle_status','local_position','attitude','estimator_flags','land_detected']:
   s=d.get('px4_telemetry_freshness',{}).get(name,{})
   age=s.get('source_age_sim_s');ra=s.get('receipt_age_wall_s')
   if age is None or ra is None or not math.isfinite(age) or not math.isfinite(ra) or age < -s.get('max_source_future_sim_s',0) or age>s.get('max_source_age_sim_s',0) or ra>s.get('max_receipt_age_wall_s',0):fail.append('px4_stale_'+name)
 if fail:stable_start=None
 else:
  if stable_start is None:stable_start=now
  max_stable=max(max_stable,now-stable_start)
  if max_stable>=5:passed=True
 if now-last_sample>=.1:
  history.append({'wall_s':now-started,'failures':fail,'bridge':asdict(b) if b else None,'localization':asdict(l) if l else None,'map':asdict(m) if m else None,'odom_age_wall_s':now-receipt['odom'] if 'odom' in receipt else None});last_sample=now
 # Continue observing for late localization failure.
passed=bool(stable_start is not None and time.monotonic()-stable_start>=5)
rtf=(clocks[-1]['sim_ns']-clocks[0]['sim_ns'])/1e9/(clocks[-1]['wall_s']-clocks[0]['wall_s']) if len(clocks)>1 else None
gaps=[b['wall_s']-a['wall_s'] for a,b in zip(odoms,odoms[1:])]
r={'vins_metrics':metrics,'scope':'Read-only full-window preflight; no enable service or navigation goal; no truth input.','required_stable_wall_s':5,'max_stable_wall_s':max_stable,'passed':passed,'observed_wall_s':time.monotonic()-started,'rtf':rtf,'max_optimized_odom_receipt_gap_wall_s':max(gaps,default=None),'optimized_odom_gap_over_guard_count':sum(g>nav['max_odometry_receipt_age_s'] for g in gaps),'failure_sample_counts':dict(Counter(f for h in history for f in h['failures'])),'history':history,'optimized_odom_receipts':odoms,'clock_samples':clocks,'last':{k:asdict(v) for k,v in latest.items() if k!='detail'},'last_detail':json.loads(latest['detail'].data) if 'detail' in latest else None}
pending=run/'preflight.json.tmp';pending.write_text(json.dumps(r,indent=2)+'\n');pending.replace(run/'preflight.json');print({k:v for k,v in r.items() if k not in ['history','optimized_odom_receipts','clock_samples','last','last_detail','vins_metrics']});n.destroy_node();rclpy.shutdown()
