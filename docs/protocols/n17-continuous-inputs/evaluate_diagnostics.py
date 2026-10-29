"""Read-only, offline diagnostic curves; no added numerical acceptance gates."""
import sys,json,hashlib,bisect
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/debug_truth')]
from evaluate_n10_clearance import parse_obstacles
h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def stats(v):
 a=np.asarray(v,dtype=float);return {'count':len(a),'p50':float(np.median(a)) if len(a) else None,'p95':float(np.percentile(a,95)) if len(a) else None,'max':float(a.max()) if len(a) else None,'min':float(a.min()) if len(a) else None}
def evaluate(run,out):
 run=Path(run);out=Path(out);out.mkdir(parents=True,exist_ok=True)
 flight=json.loads((run/'flight.json').read_text());window=flight['continuous_navigation'];start,end=window['start_source_ns'],window['end_source_ns'];anchor=json.loads((run/'n16-all-goal-arrivals.json').read_text());R=np.asarray(anchor['ground_rotation']);t=np.asarray(anchor['ground_translation'])
 boxes,skipped=parse_obstacles(run/'vio_initialization.sdf');boxes=[b for b in boxes if b['kind']=='vertical_box' and b['size_xyz_m'][2]>=1 and min(b['size_xyz_m'][:2])<1]
 rows=[]
 for row in json.loads((run/'n11-static-map-observation.json').read_text())['snapshots']:
  stamp=row['source_stamp_ns']
  if not start<=stamp<=end:continue
  path=run/row['path'];assert h(path)==row['sha256'];a=np.load(path,allow_pickle=False);indices=np.argwhere(a['occupancy']==100);xyz=(np.asarray(row['origin_m'])+(indices+.5)*row['resolution_m'])@R.T+t;xyz=xyz[(xyz[:,2]>.25)&(xyz[:,2]<2.75)]
  # Associate by nearest vertical-box surface, with no error cutoff. Exclude floor and ceiling by fixed height slab.
  nearest=np.full(len(xyz),np.inf)
  for box in boxes:
   c,s=np.cos(box['yaw_rad']),np.sin(box['yaw_rad']);basis=np.array([[c,-s,0],[s,c,0],[0,0,1]]);q=np.abs((xyz-box['center_xyz_m'])@basis)-np.asarray(box['size_xyz_m'])/2
   d=np.linalg.norm(np.maximum(q,0),axis=1)+np.minimum(q.max(axis=1),0);nearest=np.minimum(nearest,np.abs(d))
  rows.append({'source_ns':stamp,'occupied_surface_distance_m':stats(nearest),'snapshot_source_age_s':(row['snapshot_stamp_ns']-stamp)/1e9,'source_to_fusion_age_s':(row['fusion_stamp_ns']-stamp)/1e9,'snapshot_sha256':row['sha256']})
 samples=json.loads((run/'alignment-observation.json').read_text())['samples'];att=[s for s in samples if s['kind']=='attitude'];walls=[s['wall_s'] for s in att];ages=[];raw_to_adapt=[];raw={s['source_ns']:s['wall_s'] for s in samples if s['kind']=='raw_odom' and 'wall_s' in s}
 for sample in samples:
  if sample['kind']!='odom' or not start<=sample['source_ns']<=end:continue
  i=bisect.bisect_right(walls,sample['wall_s'])-1
  if i>=0:ages.append({'source_ns':sample['source_ns'],'latest_observed_px4_hrt_minus_vio_source_s':(att[i]['timestamp_us']*1000-sample['source_ns'])/1e9,'reference_attitude_receipt_gap_wall_s':sample['wall_s']-att[i]['wall_s']})
  if sample['source_ns'] in raw:raw_to_adapt.append(sample['wall_s']-raw[sample['source_ns']])
 terminal=json.loads((run/'postflight-px4-bridge-readback.json').read_text())['latest']['bridge'];offset=np.asarray(terminal['frame_offset_ned']);yaw_offset=terminal['frame_yaw_offset_ned'];cy,sy=np.cos(yaw_offset),np.sin(yaw_offset);basis=np.array([[cy,-sy,0],[sy,cy,0],[0,0,1]])
 commands=[r for r in flight['position_command_history'] if r['flag']==1 and start<=r['source_stamp_ns']<=end and np.linalg.norm(r['velocity_enu_m_s'])>.05];command_walls=[r['wall_elapsed_s'] for r in commands];matched=[];matched_times=[];unmatched=0
 for output in flight['px4_trajectory_setpoint_observations']:
  stamp=output['timestamp_us']*1000
  if not start<=stamp<=end:continue
  low=bisect.bisect_left(command_walls,output['wall_elapsed_s']-.2);high=bisect.bisect_right(command_walls,output['wall_elapsed_s']+.05);candidates=[]
  for command in commands[low:high]:
   if command['source_stamp_ns']>stamp:continue
   yaw=np.pi/2-command['yaw_enu']+yaw_offset;lever=np.array([.12*np.cos(yaw),.12*np.sin(yaw),-.08]);x,y,z=command['position_enu'];expected=np.array([y,x,-z])@basis.T+offset-lever
   if np.linalg.norm(expected-output['position_ned'])<1e-5:candidates.append(command)
  if candidates:
   selected=max(candidates,key=lambda c:c['source_stamp_ns']);matched.append((stamp-selected['source_stamp_ns'])/1e9);matched_times.append((stamp-start)/1e9)
  else:unmatched+=1
 resource=json.loads((run/'n10-resource-observation.json').read_text());rtf=[r for r in resource['samples'] if isinstance(r.get('sim_ns'),int) and start<=r['sim_ns']<=end and r.get('rtf_sim_over_wall') is not None]
 fig,axes=plt.subplots(5,1,figsize=(11,13),sharex=True)
 for key in ['p50','p95','max']:axes[0].plot([(r['source_ns']-start)/1e9 for r in rows],[r['occupied_surface_distance_m'][key] for r in rows],label=key)
 axes[0].set_ylabel('Map surface distance m');axes[0].legend()
 axes[1].plot([(r['source_ns']-start)/1e9 for r in rows],[r['snapshot_source_age_s'] for r in rows],label='Snapshot source age');axes[1].plot([(r['source_ns']-start)/1e9 for r in rows],[r['source_to_fusion_age_s'] for r in rows],label='Source to fusion');axes[1].legend();axes[1].set_ylabel('Seconds')
 axes[2].plot([(r['source_ns']-start)/1e9 for r in ages],[r['latest_observed_px4_hrt_minus_vio_source_s'] for r in ages]);axes[2].set_ylabel('VIO observed output age s')
 axes[3].plot([(r['sim_ns']-start)/1e9 for r in rtf],[r['rtf_sim_over_wall'] for r in rtf]);axes[3].set_ylabel('RTF sim/wall');axes[4].plot(matched_times,matched);axes[4].set_ylabel('Command to PX4 output s');axes[4].set_xlabel('Mission simulation seconds')
 for ax in axes:ax.grid(alpha=.25)
 fig.suptitle(run.name+' offline diagnostics (no numerical gates)');fig.tight_layout();image=out/'map-timing-rtf.png';fig.savefig(image,dpi=140);plt.close(fig)
 report={'schema':'n16-offline-map-timing-diagnostics/v1','run_id':run.name,'runtime_contract_sha256':json.loads((run/'runtime-contract.json').read_text())['sha256'],'source_sha256':h(Path(__file__)),'start_ns':start,'end_ns':end,'no_control_effect':True,'numeric_acceptance_gates_added':False,'map_method':'occupied voxel centers in fixed world height slab 0.25<z<2.75m; nearest actual vertical-box collision surface; no error cutoff; fixed PRESTREAM rigid alignment; voxel discretization retained; unobserved surfaces not inferred','map_box_names':[b['name'] for b in boxes],'map_snapshots':rows,'vio_observed_output_age_s':stats([r['latest_observed_px4_hrt_minus_vio_source_s'] for r in ages]),'vio_age_reference_receipt_gap_wall_s':stats([r['reference_attitude_receipt_gap_wall_s'] for r in ages]),'raw_to_adapted_same_source_observed_wall_s':stats(raw_to_adapt),'rtf':stats([r['rtf_sim_over_wall'] for r in rtf]),'command_source_to_px4_setpoint_observed_sim_s':stats(matched),'unmatched_setpoint_samples':unmatched,'command_matching_method':'Nonstationary READY commands, fixed alignment readback plus simulator IMU lever arm, actual NED float setpoint match within 1e-5m and observer receipt proximity; newest matching command source <= output HRT. Unmatched reported; no latency credit for stationary ambiguous duplicates.','limitations':['VIO output age uses latest independently received PX4 HRT at odometry receipt; sampled stage observation, not exact causal sensor-to-actuator latency.','Command-to-PX4 output is measured control-stage end-to-end age, not full camera-to-actuator causal latency; no claim of a global worst-case bound.', 'Raw-to-adapted difference compares observer receipt times, not internal callback execution.','Map diagnostic is nearest-surface distance, not full classification/visibility certification.'],'files':{image.name:h(image)}}
 (out/'diagnostics.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['map_snapshots','map_box_names']}))
if __name__=='__main__':evaluate(*sys.argv[1:])
