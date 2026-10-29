"""Offline long-run measurements; no CPU peaks or legacy queue budgets gate control."""
import hashlib
import json
import math
from pathlib import Path
import numpy as np


def series_summary(points):
    clean=[(float(t),float(v)) for t,v in points if v is not None and math.isfinite(float(v))]
    if len(clean)<4:return {'status':'INSUFFICIENT','sample_count':len(clean)}
    times=np.asarray([p[0] for p in clean]);values=np.asarray([p[1] for p in clean])
    if np.any(np.diff(times)<=0):return {'status':'INSUFFICIENT','reason':'nonmonotonic_series'}
    quarters=[values[(times>=a)&(times< b if i<3 else times<=b)] for i,(a,b) in enumerate(zip(np.linspace(times[0],times[-1],5)[:-1],np.linspace(times[0],times[-1],5)[1:]))]
    if any(len(q)==0 for q in quarters):return {'status':'INSUFFICIENT','reason':'empty_time_quarter'}
    medians=[float(np.median(q)) for q in quarters]
    growth=all(b>a for a,b in zip(medians,medians[1:])) and float(quarters[-1].min())>float(quarters[0].max())
    centered=times-times[0]
    slope=float(np.polyfit(centered,values,1)[0])
    return {'status':'OBSERVED','sample_count':len(clean),'minimum':float(values.min()),
            'p50':float(np.median(values)),'p95':float(np.percentile(values,95)),
            'maximum':float(values.max()),'linear_slope_per_sim_s':slope,'time_quarter_medians':medians,
            'persistent_separated_envelope_growth':bool(growth),
            'interpretation':'finite-window observation; cannot establish a mathematical infinite-time bound'}


def assess_resources(run,start_ns,end_ns,epoch):
    run=Path(run);missing=[]
    try:
        report=json.loads((run/'n10-resource-observation.json').read_text())
        source=run/'n10-vins-queue-telemetry.jsonl'
        qrows=[json.loads(line) for line in source.read_text().splitlines() if line.strip()]
    except (OSError,ValueError) as exc:return {'status':'INSUFFICIENT','missing':[str(exc)],'runtime_control_effect':False}
    artifact=report.get('vins_queue_telemetry_artifact') or {}
    if artifact.get('sha256')!=hashlib.sha256(source.read_bytes()).hexdigest() or artifact.get('row_count')!=len(qrows):missing.append('native_queue_artifact_binding_mismatch')
    samples=[r for r in report.get('samples',[]) if isinstance(r.get('sim_ns'),int)]
    native=[r for r in qrows if r.get('epoch')==epoch and isinstance(r.get('source_stamp_ns'),int)]
    for name,rows,field in [('resource',samples,'sim_ns'),('native_queue',native,'source_stamp_ns')]:
        stamps=[r[field] for r in rows]
        if not stamps or min(stamps)>start_ns or max(stamps)<end_ns:missing.append(name+'_full_window_not_covered')
    selected=[r for r in samples if start_ns<=r['sim_ns']<=end_ns]
    native=[r for r in native if start_ns<=r['source_stamp_ns']<=end_ns]
    queues={'native_waiting_features':[],'native_lag_sim_s':[],'native_pending_span_sim_s':[],'mapping_pending_depth':[]}
    resource={'cgroup_memory_bytes':[],'cpu_used_cores':[],'rtf_sim_over_wall':[]}
    for row in selected:
        t=(row['sim_ns']-start_ns)/1e9;cgroup=row.get('cgroup') or {}
        try:
            memory=float(cgroup['memory_current'])
            if not math.isfinite(memory):raise ValueError('nonfinite memory')
            resource['cgroup_memory_bytes'].append((t,memory))
        except (KeyError,TypeError,ValueError):missing.append('memory_current_field_missing_or_invalid')
        if row.get('rtf_sim_over_wall') is not None:resource['rtf_sim_over_wall'].append((t,row['rtf_sim_over_wall']))
        mapping=row.get('map_queue_counters') or {}
        if mapping.get('epoch')==epoch and isinstance(mapping.get('pending_depth_count'),int):queues['mapping_pending_depth'].append((t,mapping['pending_depth_count']))
    for a,b in zip(selected,selected[1:]):
        wall=b['wall_elapsed_s']-a['wall_elapsed_s']
        before=(a.get('cgroup',{}).get('cpu_stat') or {}).get('usage_usec')
        after=(b.get('cgroup',{}).get('cpu_stat') or {}).get('usage_usec')
        if wall>0 and before is not None and after is not None and after>=before:
            resource['cpu_used_cores'].append(((b['sim_ns']-start_ns)/1e9,(after-before)/1e6/wall))
        else:missing.append('cpu_counter_or_wall_interval_invalid')
    sequences=[]
    for row in native:
        work=(row.get('queue_metrics') or {}).get('work') or {};t=(row['source_stamp_ns']-start_ns)/1e9
        if work.get('schema')!='vins-native-pending-work/v1':missing.append('native_work_schema');continue
        try:
            lag=(work['latest_imu_before_ns']-work['interval_endpoint_ns'])/1e9
            span=work['pending_feature_span_ns']/1e9
            waiting=work['waiting_features'];sequences.append(work['sequence'])
            if min(lag,span,waiting)<0:raise ValueError('negative work')
            queues['native_waiting_features'].append((t,waiting));queues['native_lag_sim_s'].append((t,lag));queues['native_pending_span_sim_s'].append((t,span))
        except (KeyError,TypeError,ValueError):missing.append('native_work_fields')
    if any(b!=a+1 for a,b in zip(sequences,sequences[1:])):missing.append('native_work_sequence_gap')
    qs={k:series_summary(v) for k,v in queues.items()};rs={k:series_summary(v) for k,v in resource.items()}
    for name,s in {**qs,**rs}.items():
        if s['status']=='INSUFFICIENT':missing.append(name+'_coverage_or_fields')
    review=[k for k,v in qs.items() if v.get('persistent_separated_envelope_growth')]
    return {'schema':'n16-resource-evidence/v1','status':'INSUFFICIENT' if missing or review else 'OBSERVED',
            'missing':sorted(set(missing)),'queue_trends_requiring_review':review,'queues':qs,'resources':rs,
            'resource_sample_count':len(selected),'native_sample_count':len(native),
            'runtime_control_effect':False,'legacy_numeric_limits_applied':False,
            'note':'Persistent separated growth is insufficient evidence of bounded operation; inspect data, do not infer infinity or add a flight gate.'}
