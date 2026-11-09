#!/usr/bin/env python3
"""Workstation-only live view from existing log and read-only serial relay.

The two local frames are deliberately displayed 3m apart; they are not aligned.
No vehicle command, EV or control publisher is created.
"""
import json
import argparse
import re
import math
from pathlib import Path
import queue
import subprocess
import threading
import sys
import time
import signal
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped,TransformStamped
from nav_msgs.msg import Path as ROSPath,Odometry
from tf2_ros import TransformBroadcaster
from visualization_msgs.msg import Marker, MarkerArray
from vins_visual_transport import TYPES,decode_visual
from pymavlink.dialects.v20 import common
from relay_hw08_serial import HEADER
from decode_hw08_serial import read_exact

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src/own/uav_px4_bridge'))
from uav_px4_bridge.rigid_body import imu_to_body_flu, mount_rotation_translation

def display_mount():
 mount=json.loads((ROOT/'config/hardware/rig.json').read_text())['airframe_mount']
 matrix=mount.get('T_airframe_imu') or mount['bench_observation']['approximate_transform']['T_fc_imu_candidate']
 mount_rotation_translation(matrix)
 return matrix

def vins_body_pose(observation,matrix):
 # Display uses the same full reference-point change as EV; never yaw-only.
 p,q,_,_=imu_to_body_flu(observation['position_m'],observation['orientation_xyzw'],(0,0,0),(0,0,0),matrix)
 return p,q

REMOTE='/home/jetson/D435i-VINS-EGO-ROS2-hardware'
SSH=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','jetson@192.168.31.186']

def product(a,b):
 x,y,z,w=a;X,Y,Z,W=b
 return (w*X+x*W+y*Z-z*Y,w*Y-x*Z+y*W+z*X,w*Z+x*Y-y*X+z*W,w*W-x*X-y*Y-z*Z)

def px4_quaternion(q):
 return product(product((math.sqrt(.5),math.sqrt(.5),0.,0.),(q[1],q[2],q[3],q[0])),(1.,0.,0.,0.))

def native_vins_pose(line):
 match=re.search(r'time: ([^,]+), t: (\S+) (\S+) (\S+) q: (\S+) (\S+) (\S+) (\S+)',line)
 if not match:return None
 try:stamp,x,y,z,w,qx,qy,qz=map(float,match.groups())
 except ValueError:return None
 if not all(math.isfinite(v) for v in (stamp,x,y,z,w,qx,qy,qz)) or stamp<=0 or w*w+qx*qx+qy*qy+qz*qz<1e-12:return None
 return {'stamp_ns':int(stamp*1e9),'position_m':[x,y,z],'orientation_xyzw':[qx,qy,qz,w]}

def body_odometry_and_tf(pose,child):
 odom=Odometry();odom.header=pose.header;odom.child_frame_id=child;odom.pose.pose=pose.pose
 # RViz requires finite pose covariance even when hidden. These zero placeholders
 # are display-only, not uncertainty estimates; covariance rendering stays disabled.
 odom.pose.covariance=[0.]*36;odom.twist.covariance=[float('nan')]*36
 for vector in (odom.twist.twist.linear,odom.twist.twist.angular):vector.x=vector.y=vector.z=float('nan')
 tf=TransformStamped();tf.header=pose.header;tf.child_frame_id=child
 tf.transform.translation.x=pose.pose.position.x;tf.transform.translation.y=pose.pose.position.y;tf.transform.translation.z=pose.pose.position.z;tf.transform.rotation=pose.pose.orientation
 return odom,tf

def write_live_status(status_path,sample_stream,snapshot):
 status_path.write_text(json.dumps(snapshot,indent=2))
 if sample_stream:sample_stream.write(json.dumps(snapshot,separators=(',',':'))+'\n')

def resource_snapshot():
 snapshot={}
 try:snapshot['host_loadavg']=[float(x) for x in Path('/proc/loadavg').read_text().split()[:3]]
 except (OSError,ValueError):pass
 try:
  for line in Path('/proc/meminfo').read_text().splitlines():
   if line.startswith('MemAvailable:'):
    snapshot['host_mem_available_bytes']=int(line.split()[1])*1024;break
 except (OSError,ValueError,IndexError):pass
 try:
  for line in Path('/proc/self/status').read_text().splitlines():
   if line.startswith('VmRSS:'):
    snapshot['viewer_process_rss_bytes']=int(line.split()[1])*1024;break
 except (OSError,ValueError,IndexError):pass
 cgroup=Path('/sys/fs/cgroup')
 try:
  stats={key:int(value) for key,value in (line.split() for line in (cgroup/'cpu.stat').read_text().splitlines())}
  snapshot['container_cpu_stat']=stats
 except (OSError,ValueError):pass
 try:snapshot['container_memory_current_bytes']=int((cgroup/'memory.current').read_text())
 except (OSError,ValueError):pass
 try:
  maximum=(cgroup/'memory.max').read_text().strip()
  snapshot['container_memory_max_bytes']=None if maximum=='max' else int(maximum)
 except (OSError,ValueError):pass
 try:
  events={key:int(value) for key,value in (line.split() for line in (cgroup/'memory.events').read_text().splitlines())}
  snapshot['container_memory_events']=events
 except (OSError,ValueError):pass
 try:
  route=next(line.split()[0] for line in Path('/proc/net/route').read_text().splitlines()[1:] if line.split()[1]=='00000000')
  stats={}
  for name in ('rx_bytes','tx_bytes','rx_dropped','tx_dropped','rx_errors','tx_errors'):
   try:stats[name]=int((Path('/sys/class/net')/route/'statistics'/name).read_text())
   except (OSError,ValueError):pass
  if stats:snapshot['default_route_interface']={'name':route,**stats}
 except (OSError,StopIteration):pass
 for device in sorted(Path('/sys/class/drm').glob('renderD*/device/gpu_busy_percent')):
  try:snapshot.setdefault('gpu_busy_percent',{})[device.parents[1].name]=float(device.read_text())
  except (OSError,ValueError):pass
 return snapshot

def main():
 signal.signal(signal.SIGTERM,signal.default_int_handler)
 parser=argparse.ArgumentParser();parser.add_argument('--visuals',action='store_true');parser.add_argument('--live',action='store_true',help='Tail only new health and native optimized-pose log lines');parser.add_argument('--vins-only',action='store_true');parser.add_argument('--px4-dds-log');parser.add_argument('--run-path',default=REMOTE+'/artifacts/runs/hw09-live-view-20261104')
 parser.add_argument('--nano-host',default='jetson@192.168.31.186')
 parser.add_argument('--remote-root',default=REMOTE)
 parser.add_argument('--status-file',type=Path,default=Path('artifacts/runs/hw09-live-view-20261104/live-status.json'))
 parser.add_argument('--status-samples-file',type=Path)
 parser.add_argument('--visual-events-file',type=Path)
 args=parser.parse_args()
 global SSH
 SSH=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8',args.nano_host]
 remote_root=args.remote_root
 args.status_file.parent.mkdir(parents=True,exist_ok=True)
 sample_stream=None
 if args.status_samples_file:
  args.status_samples_file.parent.mkdir(parents=True,exist_ok=True)
  sample_stream=args.status_samples_file.open('x',buffering=1)
 visual_event_stream=None;visual_event_lock=threading.Lock()
 if args.visual_events_file:
  args.visual_events_file.parent.mkdir(parents=True,exist_ok=True)
  visual_event_stream=args.visual_events_file.open('x',buffering=1)
 rclpy.init();node=Node('hardware_live_readonly_view');events=queue.Queue();children=[]
 matrix=display_mount()
 viz_counts={};viz_sizes={};viz_errors=[];viz_timing={};visual_latest={};visual_lock=threading.Lock();last_draw=0.;clock_offset=0.;clock_uncertainty=None
 viz_pubs={k:node.create_publisher(typ,'/hardware_view/'+k,1) for k,typ in TYPES.items()} if args.visuals else {}
 run=args.run_path
 def logs():
  command=('tail -q -n 0 -s 0.1 -F '+run+'/localization.log '+run+'/vins.log') if args.live else 'tail -n +1 -F '+run+'/localization.log'
  p=subprocess.Popen(SSH+[command],stdout=subprocess.PIPE,text=True);children.append(p)
  for line in p.stdout:
   if 'localization_age_observation ' in line:
    try:events.put(('vins',json.loads(line.split('localization_age_observation ',1)[1])))
    except ValueError:pass
   elif args.live:
    ob=native_vins_pose(line)
    if ob:events.put(('vins_pose',ob))
 def visuals(channel):
  command='cd '+remote_root+'; source tools/hardware-env.bash; export FASTRTPS_DEFAULT_PROFILES_FILE="$PWD/config/hardware/vins_fastdds_udp_rxbuf4m.xml"; exec setsid python3 tools/diagnostics/relay_vins_visuals.py --run '+run+' --channel '+channel
  p=subprocess.Popen(SSH+['bash -c '+__import__('shlex').quote(command)],stdout=subprocess.PIPE,text=True);children.append(p)
  last_receive_mono=None
  for line in p.stdout:
   try:row=json.loads(line)
   except ValueError:continue
   if row.get('kind') in TYPES:
    row['pc_received_wall_s']=time.time();row['pc_received_monotonic_s']=time.monotonic()
    if last_receive_mono is not None:row['pc_receive_interval_s']=row['pc_received_monotonic_s']-last_receive_mono
    last_receive_mono=row['pc_received_monotonic_s']
    if visual_event_stream:
     event={k:row[k] for k in ('kind','epoch','source_stamp_s','sent_wall_s','pc_received_wall_s','pc_received_monotonic_s','pc_receive_interval_s') if k in row}
     with visual_event_lock:visual_event_stream.write(json.dumps(event,separators=(',',':'))+'\n')
    with visual_lock:visual_latest[row['kind']]=row
 def serial():
  p=subprocess.Popen(SSH+['cd '+remote_root+'; PYTHONPATH=$PWD/artifacts/runs/hw07-usb-20261103-01/python python3 tools/diagnostics/relay_hw08_serial.py --device /dev/ttyACM0 --seconds 1800 --discovery-heartbeat'],stdout=subprocess.PIPE);children.append(p)
  decoder=common.MAVLink(None);decoder.robust_parsing=True
  while True:
   h=read_exact(p.stdout,HEADER.size)
   if h is None:return
   kind,system,mono,n=HEADER.unpack(h)
   data=read_exact(p.stdout,n) if n else b''
   if kind==1:
    for msg in decoder.parse_buffer(data) or []:
     if msg.get_srcSystem()==1:events.put(('px4',msg.to_dict()))
 def dds():
  p=subprocess.Popen(SSH+['tail -n 1 -F '+args.px4_dds_log],stdout=subprocess.PIPE,text=True);children.append(p)
  for line in p.stdout:
   try:row=json.loads(line)
   except ValueError:continue
   for topic,v in row.get('latest',{}).items():
    if row['monotonic_s']-v['receipt_mono']>2:continue
    m=v['message']
    if topic=='/fmu/out/vehicle_attitude':events.put(('px4',dict(mavpackettype='ATTITUDE_QUATERNION',q1=m['q'][0],q2=m['q'][1],q3=m['q'][2],q4=m['q'][3])))
    if topic=='/fmu/out/vehicle_local_position_v1':events.put(('px4',dict(mavpackettype='DISPLAY_LOCAL_VALIDITY',x=m['x'],y=m['y'],z=m['z'],xy_valid=m['xy_valid'],z_valid=m['z_valid'])))
    if topic=='/fmu/out/estimator_status_flags':events.put(('px4',dict(mavpackettype='DISPLAY_EV_AIDING',pos=m.get('cs_ev_pos'),hgt=m.get('cs_ev_hgt'),yaw=m.get('cs_ev_yaw'))))
 threading.Thread(target=logs,daemon=True).start();
 if args.visuals:
  estimates=[]
  clock_code='import sys,time; print("ready",flush=True); [(print(time.time(),flush=True)) for line in sys.stdin]'
  clock_process=subprocess.Popen(SSH+['python3 -u -c '+__import__('shlex').quote(clock_code)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
  try:
   if clock_process.stdout.readline().strip()!='ready':raise RuntimeError('Clock probe unavailable')
   for _ in range(5):
    before=time.time();clock_process.stdin.write('ping\n');clock_process.stdin.flush()
    remote=float(clock_process.stdout.readline());after=time.time()
    estimates.append((after-before,(before+after)/2-remote))
  finally:
   clock_process.stdin.close();clock_process.wait(timeout=5)
  rtt,clock_offset=min(estimates);clock_uncertainty=rtt/2
  for channel in ('geometry','image'):threading.Thread(target=visuals,args=(channel,),daemon=True).start()
 if args.px4_dds_log:threading.Thread(target=dds,daemon=True).start()
 elif not args.vins_only:threading.Thread(target=serial,daemon=True).start()
 odom_pub=node.create_publisher(Odometry,'/hardware_view/vins_odom',1);tf_pub=TransformBroadcaster(node)
 path_pub=node.create_publisher(ROSPath,'/hardware_view/vins_path',1)
 pose_pub=node.create_publisher(PoseStamped,'/hardware_view/vins_pose',1)
 pxpose_pub=node.create_publisher(PoseStamped,'/hardware_view/px4_pose',1)
 pxpath_pub=node.create_publisher(ROSPath,'/hardware_view/px4_path',1)
 markers=node.create_publisher(MarkerArray,'/hardware_view/status',1)
 path=ROSPath();path.header.frame_id='hardware_display';pxpath=ROSPath();pxpath.header.frame_id='hardware_display'
 state={'epoch':None,'vins':None,'vins_t':0.,'px4_t':0.,'q':None,'local':None,'flags':None,'heartbeat':None,'ev_aiding':None};last_stamp=None
 def pose(p,q):
  m=PoseStamped();m.header.frame_id='hardware_display';m.header.stamp=node.get_clock().now().to_msg()
  m.pose.position.x,m.pose.position.y,m.pose.position.z=map(float,p)
  m.pose.orientation.x,m.pose.orientation.y,m.pose.orientation.z,m.pose.orientation.w=map(float,q)
  return m
 def tick():
  nonlocal last_stamp,path,pxpath,last_draw
  with visual_lock:batch=dict(visual_latest);visual_latest.clear()
  for row in batch.values():events.put(('visual',row))
  while not events.empty():
   kind,d=events.get()
   if kind=='visual':
    try:
     epoch=state['epoch'] or d['epoch']
     k=d['kind']
     processed_wall=time.time();source_age=processed_wall-(d['source_stamp_s']+clock_offset)
     viz_timing[k]={'source_stamp_s':d['source_stamp_s'],'relay_sent_wall_s':d['sent_wall_s'],
                    'pc_received_wall_s':d['pc_received_wall_s'],'pc_receive_interval_s':d.get('pc_receive_interval_s'),
                    'pc_processed_wall_s':processed_wall,'transport_age_s':d['pc_received_wall_s']-(d['sent_wall_s']+clock_offset),
                    'pc_queue_age_s':processed_wall-d['pc_received_wall_s'],'source_age_s':source_age,
                    'remote_processing_age_s':d['sent_wall_s']-d['source_stamp_s']}
     if source_age < -.05 or source_age > (0.75 if k=='body' else 2.):continue
     msg=decode_visual(d,epoch,node.get_clock().now().to_msg())
     viz_counts[k]=viz_counts.get(k,0)+1
     if k=='image':viz_sizes[k]=[msg.width,msg.height]
     elif k=='camera':viz_sizes[k]=len(msg.markers)
     elif k!='body':viz_sizes[k]=len(msg.points)
     health=state['vins']
     if k=='body':
      if health and health['status']['valid'] and time.monotonic()-state['vins_t']<3:
       p=msg.pose.pose;ob={'position_m':[p.position.x,p.position.y,p.position.z],
          'orientation_xyzw':[p.orientation.x,p.orientation.y,p.orientation.z,p.orientation.w]}
       values=ob['position_m']+ob['orientation_xyzw']
       if not all(math.isfinite(x) for x in values):raise ValueError('Nonfinite body pose')
       m=pose(*vins_body_pose(ob,matrix));pose_pub.publish(m)
       o,tf=body_odometry_and_tf(m,'hardware_view/vins_body');odom_pub.publish(o);tf_pub.sendTransform(tf)
     elif k=='image' or (health and health['status']['valid'] and time.monotonic()-state['vins_t']<3):viz_pubs[k].publish(msg)
    except Exception as exc:
     viz_errors.append(str(exc));viz_errors[:]=viz_errors[-5:]
   elif kind=='vins_pose':
    health=state['vins']
    if health and health['status']['valid'] and time.monotonic()-state['vins_t']<3 and (last_stamp is None or d['stamp_ns']>last_stamp+1000):
     last_stamp=d['stamp_ns'];m=pose(*vins_body_pose(d,matrix));path.poses.append(m);path.poses=path.poses[-1800:];
     if not args.visuals:
      pose_pub.publish(m);o,tf=body_odometry_and_tf(m,'hardware_view/vins_body');odom_pub.publish(o);tf_pub.sendTransform(tf)
   elif kind=='vins':
    if state['epoch']!=d['epoch']:
     state['epoch']=d['epoch'];path.poses=[];last_stamp=None
    state['vins']=d;state['vins_t']=time.monotonic()
    ob=d.get('pose_observation')
    if ob and d['status']['valid'] and (last_stamp is None or ob['stamp_ns']>last_stamp+1000):
     last_stamp=ob['stamp_ns'];m=pose(*vins_body_pose(ob,matrix));path.poses.append(m);path.poses=path.poses[-1800:];
     if not args.visuals:
      pose_pub.publish(m);o,tf=body_odometry_and_tf(m,'hardware_view/vins_body');odom_pub.publish(o);tf_pub.sendTransform(tf)
   else:
    state['px4_t']=time.monotonic();typ=d.get('mavpackettype')
    if typ=='ATTITUDE_QUATERNION':state['q']=[d[k] for k in ('q1','q2','q3','q4')]
    if typ=='LOCAL_POSITION_NED':state['local']=d
    if typ=='ESTIMATOR_STATUS':state['flags']=d['flags']
    if typ=='DISPLAY_LOCAL_VALIDITY':
     state['local']=d;state['flags']=(8 if d['xy_valid'] else 0)+(32 if d['z_valid'] else 0)
    if typ=='DISPLAY_EV_AIDING':state['ev_aiding']=d
    if typ=='HEARTBEAT':state['heartbeat']=d
  if time.monotonic()-last_draw<.2:return
  last_draw=time.monotonic()
  path.header.stamp=node.get_clock().now().to_msg();path_pub.publish(path)
  v=state['vins'];now=time.monotonic()
  valid=v and v['status']['valid'] and now-state['vins_t']<3
  vs=('LIVE VINS BODY: ' if args.live else 'LOG VIEW VINS BODY: ')+('TRACKING' if valid else 'INVALID / STALE')+' | FLU X forward / Y left / Z up'
  if args.visuals:vs='LIVE VINS '+('TRACKING' if valid else 'INVALID')+'\nBODY FLU | propagated pose\noptimized trajectory | stereo preview'
  if v:vs+='\n'+v['status']['reason']+'\nepoch '+str(state['epoch'])[:8]
  received=now-state['px4_t']<3
  ps='PX4: '+('receiving' if received else 'NO TELEMETRY')+'\nEV fusion NOT VERIFIED | no EV sent\nSeparate local frame; display offset +3m'
  if state['ev_aiding']:ps+='\nReported EV aiding: '+str(state['ev_aiding'])+' | ULog pending'
  flags=state['flags'];posvalid=received and flags is not None and flags&24 and flags&32
  if received and state['q']:
   p=(3.,0.,0.)
   if posvalid and state['local']:
    d=state['local'];p=(d['y']+3,d['x'],-d['z'])
   m=pose(p,px4_quaternion(state['q']));pxpose_pub.publish(m)
   if posvalid:pxpath.poses.append(m);pxpath.poses=pxpath.poses[-1800:]
   else:ps+='\nLocal position invalid/unverified: attitude only at display origin'
  pxpath.header.stamp=node.get_clock().now().to_msg();pxpath_pub.publish(pxpath)
  array=MarkerArray()
  labels=[(vs,0.,bool(valid))] if args.vins_only and not args.px4_dds_log else [(vs,0.,bool(valid)),(ps,3.,bool(posvalid))]
  for i,(txt,x,ok) in enumerate(labels):
   m=Marker();m.header.frame_id='hardware_display';m.header.stamp=node.get_clock().now().to_msg();m.id=i;m.type=Marker.TEXT_VIEW_FACING;m.action=Marker.ADD;m.pose.position.x=x;m.pose.position.z=1.;m.pose.orientation.w=1.;m.scale.z=.12;m.color.a=1.;m.color.r=.2 if ok else 1.;m.color.g=1. if ok else .5;m.color.b=.8 if ok else .2;m.text=txt;array.markers.append(m)
  markers.publish(array)
  wall_now=time.time();v=state['vins'];ob=v.get('pose_observation') if v else None
  vins_status=None if not v else {'state':v['status']['state'],'valid':bool(v['status']['valid']),
      'reason':v['status']['reason'],'pose_stamp_ns':ob.get('stamp_ns') if ob else None,
      'pose_source_age_s':wall_now-(ob['stamp_ns']/1e9+clock_offset) if ob else None,
      'accepted_optimized':v['status'].get('accepted_optimized'),
      'accepted_propagated':v['status'].get('accepted_propagated'),
      'streams':{name:{key:stream.get(key) for key in ('count','last_source_stamp_ns','last_receipt_wall_s','max_receipt_interval_s','max_source_interval_s','max_source_age_s')}
                 for name,stream in v.get('streams',{}).items()}}
  write_live_status(args.status_file,sample_stream,{'clock_offset_s':clock_offset,'clock_uncertainty_s':clock_uncertainty,'vins_status':vins_status,'visual_timing':viz_timing,'visual_counts':viz_counts,'visual_sizes':viz_sizes,'visual_decode_errors':viz_errors,'resources':resource_snapshot(),'mode':'live' if args.live else 'log_view','run_path':run,'epoch':state['epoch'],'vins_valid':bool(valid),'vins_points':len(path.poses),'px4_receiving':received,'px4_flags':flags,'px4_position_verified':bool(posvalid),'px4_ev_fusion_verified':False,'wall_s':wall_now,'monotonic_s':time.monotonic()})
 node.create_timer(.05,tick)
 try:rclpy.spin(node)
 except KeyboardInterrupt:pass
 finally:
  for p in children:p.terminate()
  for p in children:
   try:p.wait(timeout=3)
   except subprocess.TimeoutExpired:p.kill();p.wait()
  if sample_stream:sample_stream.close()
  if visual_event_stream:visual_event_stream.close()
  node.destroy_node()
  if rclpy.ok():rclpy.shutdown()

if __name__=='__main__':main()
