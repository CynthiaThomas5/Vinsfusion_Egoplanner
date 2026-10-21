"""Read-only offline independent goal/dwell check using one fixed ground SE(3)."""
import json,math,sys
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'tools'))
from evaluate_vins_motion import rotation
run=Path(sys.argv[1]);load=lambda n:json.loads((run/n).read_text())
flight=load('flight.json');truth=load('debug-truth-evaluation.json')['samples'];odom=[x for x in load('alignment-observation.json')['samples'] if x['kind']=='odom'];preflight=load('preflight.json');cfg=json.loads((root/'config/components/navigation/room_crossing_goal.json').read_text())
if not flight.get('goal'):raise ValueError('No navigation goal was dispatched')
refstamp=preflight['clock_samples'][-1]['sim_ns']-1_000_000_000
ref=min(odom,key=lambda p:abs(p['source_ns']-refstamp));tr=min(truth,key=lambda p:abs(p['stamp_ns']-ref['source_ns']));assert abs(tr['stamp_ns']-ref['source_ns'])<=20_000_000
sys.path.insert(0,str(root/'src/own/uav_sim'))
from uav_sim.geometry import px4_sensor_mount
mount=px4_sensor_mount(root/'simulation/models/x500_d435i/model.sdf')
lever=np.array(mount['translation_frd_m'])*np.array([1,-1,-1]);A=rotation(tr['q_xyzw'])@rotation(ref['q_xyzw']).T
origin=np.asarray(tr['xyz'])+rotation(tr['q_xyzw'])@lever-A@ref['xyz']
goal=A@flight['goal']['target_enu']+origin
yawoff=math.atan2(A[1,0],A[0,0]);goalyaw=flight['goal']['yaw_enu']+yawoff
phases=[json.loads(s) for s in (run/'bridge-alignment-timeline.jsonl').read_text().splitlines()]
start=next(x['stamp_ns'] for x in phases if x['phase']=='PRESTREAM');end=next((x['stamp_ns'] for x in phases if x['phase']=='LANDING'),truth[-1]['stamp_ns'])
goal_events=[x for x in load('planner-observation.json')['messages'] if x['type']=='goal'];h=goal_events[0]['message']['target']['header']['stamp'];goalstamp=h['sec']*10**9+h['nanosec']
rows=[]
for p in truth:
 if not goalstamp<=p['stamp_ns']<=end:continue
 R=rotation(p['q_xyzw']);imu=np.asarray(p['xyz'])+R@lever;error=float(np.linalg.norm(imu-goal));yaw=math.atan2(R[1,0],R[0,0]);ye=abs(math.atan2(math.sin(yaw-goalyaw),math.cos(yaw-goalyaw)));rows.append((p['wall_s'],p['stamp_ns'],error,ye,error<=cfg.get('verification_position_tolerance_m',cfg['position_tolerance_m']) and ye<=cfg['yaw_tolerance_rad']))
assert rows
longest=0.;since=None;last=None
for wall,stamp,error,ye,inside in rows:
 if not inside or (last is not None and wall-last>.12):since=None
 if inside:
  if since is None:since=wall
  longest=max(longest,wall-since)
 last=wall
landed_stamp=next((x['stamp_ns'] for x in phases if x['phase']=='LANDED'),truth[-1]['stamp_ns'])
invalid=[x for x in flight['localization_quality_history'] if start<=x['stamp_ns']<=landed_stamp and not x['valid']]
report={'scope':'Offline, single fixed ground SE(3), scale 1; no truth feedback or timestamp repair. Sampled current-room diagnostic, not full P0-P6 acceptance.','reference_source_ns':ref['source_ns'],'reference_truth_gap_sim_s':abs(tr['stamp_ns']-ref['source_ns'])/1e9,'world_imu_goal_xyz':goal.tolist(),'minimum_true_3d_position_error_m':min(x[2] for x in rows),'max_contiguous_true_goal_dwell_wall_s':longest,'required_dwell_wall_s':cfg['dwell_s'],'native_position_tolerance_m':flight['goal']['position_tolerance_m'],'verification_position_tolerance_m':cfg.get('verification_position_tolerance_m',cfg['position_tolerance_m']),'independent_goal_dwell_passed':longest>=cfg['dwell_s'],'native_action_success':flight.get('action_success',False),'landed_and_disarmed':flight.get('landed_and_disarmed',False),'invalid_localization_samples_after_enable':len(invalid),'first_invalid_localization_after_enable':invalid[0] if invalid else None,'ground_rotation':A.tolist(),'ground_translation':origin.tolist()}
lines=(run/'vio.log').read_text().splitlines()
begin=next(i for i,line in enumerate(lines) if 'bridge phase=PRESTREAM' in line)
finish=next((i for i,line in enumerate(lines[begin:],begin) if 'bridge phase=LANDED' in line),len(lines))
failures=[line for line in lines[begin:finish+1] if any(pattern in line for pattern in ['mapping gate closed','odom or depth lost','localization status became stale','EMERGENCY_STOP'])]
report['map_or_navigation_failure_lines_after_enable']=failures
report['control_publisher_counts']=flight['publisher_counts']
report['unique_control_publishers_passed']=bool(flight['publisher_counts']) and all(v==1 for v in flight['publisher_counts'].values())
report['navigation_check_passed']=bool(report['independent_goal_dwell_passed'] and report['native_action_success'] and report['landed_and_disarmed'] and not invalid and not failures and report['unique_control_publishers_passed'])
(run/'arrival-evaluation.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
