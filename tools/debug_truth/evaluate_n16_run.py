#!/usr/bin/env python3
"""N16 independent continuity, all-goal arrivals, motion, contact and resource evidence."""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tools'))
from tools.n16_continuity import assess_continuity
from tools.n16_resource_evidence import assess_resources
from tools.n16_process_lifecycle import assess_lifecycle
from tools.n09_contact_evaluation import evaluate_contacts
from tools.n13_navigation_policy import contact_and_terminal
from tools.debug_truth.evaluate_arrival import evaluate_run as arrival_evaluation
from tools.truth_reference import imu_truth_samples


def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def jsonl(p):return [json.loads(s) for s in Path(p).read_text().splitlines() if s.strip()]


def evaluate_evidence(run,config):
    run=Path(run).resolve();missing=[];failures=[]
    out={'schema':'n16-full-load-evidence/v1','run_id':run.name,'runtime_control_effect':False}
    try:
        acceptance_config=load(config)
        required_sim_s=acceptance_config.get('metrics',{}).get('continuous_navigation',{}).get('thresholds',{}).get('minimum_sim_s',600)
        flight=load(run/'flight.json');truth,reference=imu_truth_samples(run,load(run/'debug-truth-evaluation.json'))
        phases=jsonl(run/'bridge-alignment-timeline.jsonl');commands=flight['position_command_history']
        planner=load(run/'planner-observation.json');splines=[m['message'] for m in planner['messages'] if m['type']=='bspline']
        continuity=assess_continuity(flight,phases,commands,splines,[p['stamp_ns'] for p in truth],required_sim_s=required_sim_s);out['continuity']=continuity
        if continuity['status']=='FAIL':failures.append('continuity_failed')
        elif continuity['status']!='PASS':missing.append('continuity_incomplete')
        arrival,_=arrival_evaluation(run,output_name='n16-all-goal-arrivals.json',acceptance_config_path=config)
        out['arrivals']=arrival
        if arrival['classification']=='FAIL':failures.append('independent_arrival_failed')
        elif arrival['classification']!='PASS':missing.append('independent_arrival_incomplete')
        if len(arrival['legs'])!=len(flight.get('legs') or []):missing.append('arrival_leg_count_differs')
        first_stamp=flight['legs'][0]['goal']['source_ns']
        contact=evaluate_contacts(load(run/'n09-contact-observation.json'),load(run/'n09-contact-model-manifest.json'),phases,first_stamp)
        terminal=contact_and_terminal(run);out.update(full_mission_contact=contact,terminal=terminal)
        if contact.get('prohibited_contact_event_count',0)>0 or terminal['status']=='FAIL':failures.append('contact_or_terminal_failure')
        elif not contact.get('passed') or terminal['status']!='PASS':missing.append('contact_or_terminal_incomplete')
        safe=load(run/'safe-to-stop.json')
        if not safe.get('safe_to_stop_project_container') or not all(safe.get('checks',{}).values()):missing.append('independent_safe_terminal_missing')
        if 'start_ns' in continuity:
            start,end=continuity['start_ns'],continuity['end_ns'];epoch=flight['localization_epoch']
            resources=assess_resources(run,start,end,epoch);out['resource_evidence']=resources
            if resources['status']!='OBSERVED':missing.append('resource_coverage_or_trend_needs_review')
            selected=[p for p in truth if start<=p['stamp_ns']<=end];points=np.asarray([p['xyz'] for p in selected])
            if len(points)<2:missing.append('actual_motion_truth_missing')
            else:
                distance=float(np.linalg.norm(np.diff(points,axis=0),axis=1).sum())
                out['actual_motion']={'sampled_distance_m':distance,'sample_count':len(points),'reference_contract':reference}
                if distance<=0:missing.append('no_actual_motion')
            for leg in flight['legs']:
                times=[r['trajectory_id'] for r in commands if r.get('goal_id')==leg['goal_id'] and r.get('epoch')==epoch and r.get('flag')==1]
                if len(set(times))<2:missing.append('leg_executed_replanning_not_demonstrated')
            observation=load(run/'n11-static-map-observation.json');valid_snapshots=[]
            for snap in observation['snapshots']:
                if not start<=snap['snapshot_stamp_ns']<=end:continue
                path=(run/snap['path']).resolve()
                if not path.is_relative_to(run) or sha(path)!=snap['sha256']:missing.append('map_snapshot_hash_or_path');continue
                if snap['epoch']!=epoch:failures.append('cross_epoch_map_snapshot');continue
                if not 0<snap['source_stamp_ns']<=snap['fusion_stamp_ns']<=snap['snapshot_stamp_ns']:missing.append('snapshot_source_order');continue
                valid_snapshots.append(snap)
            for leg in flight['legs']:
                if not any(s['goal_id']==leg['goal_id'] and leg['goal_start_sim_ns']<=s['snapshot_stamp_ns']<=leg['goal_completed_source_ns'] for s in valid_snapshots):missing.append('leg_without_observed_map_update')
            out['map_updates']={'supported_snapshot_count':len(valid_snapshots),'fusion_stamp_count':len({s['fusion_stamp_ns'] for s in valid_snapshots})}
            process=load(run/'n16-process-observation.json');rows=jsonl(run/process['rows_file'])
            if sha(run/process['rows_file'])!=process['rows_sha256'] or len(rows)!=process['sample_count']:missing.append('process_record_hash_or_count')
            supplement={};supplement_rows=[]
            supplement_path=run/'n16-process-clock-supplement.json'
            if supplement_path.is_file():
                supplement=load(supplement_path);supplement_rows=jsonl(run/supplement['rows_file'])
                if sha(run/supplement['rows_file'])!=supplement['rows_sha256'] or len(supplement_rows)!=supplement['sample_count']:
                    missing.append('supplement_hash_or_count')
            lifecycle=assess_lifecycle(process,rows,supplement,supplement_rows,start,end,run.name)
            out['process_liveness']=lifecycle
            if lifecycle['status']!='PASS':missing.append('core_process_lifetime_evidence_incomplete')
    except (OSError,ValueError,KeyError,TypeError,IndexError) as exc:missing.append(repr(exc))
    out.update(overall_status='FAIL' if failures else 'INSUFFICIENT' if missing else 'PASS',
               failures=sorted(set(failures)),insufficient=sorted(set(missing)),
               note='Runtime/config/GUI/observer identity release binding and plots are required by final formal audit.')
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--config',type=Path,default=ROOT/'config/acceptance_n16.json');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=evaluate_evidence(a.run,a.config);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n');print(r['overall_status'])
