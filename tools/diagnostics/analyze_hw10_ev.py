#!/usr/bin/env python3
"""Correlate actual DDS snapshots with selected-instance ULog EV aiding."""
import json,sys,argparse
from pathlib import Path
import numpy as np
from pyulog import ULog
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path);parser.add_argument('root',type=Path);parser.add_argument('--epoch');parser.add_argument('--ulog',type=Path)
parser.add_argument('--max-system-ns',type=int);parser.add_argument('--min-system-ns',type=int)
a=parser.parse_args();root=a.root;rows=[json.loads(l) for l in (root/'ev.jsonl').read_text().splitlines()]
rows=[r for r in rows if (a.max_system_ns is None or r['system_ns']<=a.max_system_ns)
      and (a.min_system_ns is None or r['system_ns']>=a.min_system_ns)]
epoch=a.epoch
if epoch is None:
 epochs={json.loads(r['latest'].get('/px4_bridge/hardware_ev/detail',{}).get('message',{}).get('data','{}')).get('epoch') for r in rows}
 epochs.discard(None)
 if len(epochs)!=1:raise ValueError('Specify --epoch for a recording with multiple/no epochs')
 epoch=epochs.pop()
good=[];phase=[];last_count=None
for r in rows:
 d=json.loads(r['latest'].get('/px4_bridge/hardware_ev/detail',{}).get('message',{}).get('data','{}'))
 if d.get('epoch')!=epoch:continue
 phase.append(d);count=d.get('published',0);advanced=count>0 and (last_count is None or count>last_count);last_count=count
 sync=r['latest'].get('/fmu/out/timesync_status',{}).get('message',{})
 if d.get('reason')=='ev_only' and sync and advanced:
  good.append((r['system_ns']//1000+int(sync['estimated_offset']),d))
assert good
logs=[a.ulog] if a.ulog else sorted(root.glob('*.ulg'))
if len(logs)!=1:raise ValueError('Specify --ulog when recording has multiple/no ULogs')
start,end=good[0][0],good[-1][0];u=ULog(str(logs[0]))
selector=next(d.data for d in u.data_list if d.name=='estimator_selector_status')
idx=np.searchsorted(selector['timestamp'],[start,end],side='right')-1;selected=[int(selector['primary_instance'][i]) for i in idx]
result={'epoch':epoch,'fc_interval_us':[start,end],'dds_ev_interval_s':(end-start)/1e6,'published_max':max(d['published'] for d in phase),'max_reported_source_age_s':max(d['last_publish_ages']['source_age_s'] for _,d in good if d['last_publish_ages']), 'selected_instances_at_endpoints':selected,'ulog_duration_s':(u.last_timestamp-u.start_timestamp)/1e6,'dropouts_ms':[d.duration for d in u.dropouts],'aiding':{}}
for name in ('estimator_aid_src_ev_pos','estimator_aid_src_ev_hgt','estimator_aid_src_ev_yaw','estimator_status_flags'):
 summaries=[]
 for topic in [d for d in u.data_list if d.name==name]:
  d=topic.data;t=d['timestamp'];primary=selector['primary_instance'][np.maximum(0,np.searchsorted(selector['timestamp'],t,side='right')-1)]
  mask=(t>=start)&(t<=end)&(primary==topic.multi_id)
  if not mask.any():continue
  summary={'instance':topic.multi_id,'samples':int(mask.sum())}
  for k in ('fused','innovation_rejected','cs_ev_pos','cs_ev_hgt','cs_ev_yaw','cs_ev_yaw_fault','cs_yaw_align','cs_tilt_align','reject_hor_pos','reject_ver_pos','reject_yaw'):
   if k in d:summary[k+'_true']=int(np.count_nonzero(d[k][mask]))
  for k in d:
   if k.startswith('innovation') and (k=='innovation' or k.startswith('innovation[')):
    summary[k+'_max_abs']=float(np.abs(d[k][mask]).max())
  summaries.append(summary)
 result['aiding'][name]=summaries
local=next(d.data for d in u.data_list if d.name=='vehicle_local_position' and d.multi_id==selected[-1])
mask=(local['timestamp']>=start)&(local['timestamp']<=end)
result['local_position']={k:sorted(float(v) for v in set(local[k][mask])) for k in
 ('xy_valid','z_valid','heading_good_for_control','xy_reset_counter','z_reset_counter','heading_reset_counter') if k in local}
status=next(d.data for d in u.data_list if d.name=='vehicle_status');result['ulog_arming_states']=sorted(int(x) for x in set(status['arming_state']))
(a.output or root/'ulog-analysis.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
