#!/usr/bin/env python3
"""Current delivery normal-scene regression, using existing functional predicates."""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from tools.n13_navigation_policy import contact_and_terminal
from tools.debug_truth.evaluate_n13_route import evaluate as staggered_route,evaluate_obstacle
from tools.debug_truth.evaluate_n14_route import evaluate as corridor_route
from tools.n16_resource_evidence import assess_resources


def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def core_sha(files):return hashlib.sha256(json.dumps({k:v for k,v in files.items() if k!='simulation/worlds/ego.sdf'},sort_keys=True).encode()).hexdigest()


def assess(run,config,release,metrics=None):
    run=Path(run);missing=[];fail=[];checks={};report={'schema':'n17-delivery-scene-regression/v1','run_id':run.name,'runtime_control_effect':False,'formal_count_eligible':False}
    try:
        cfg=load(config);policy=load(release);launch=load(run/'n17-launch-record.json');scene=launch['scene'];case=policy['cases'][scene];flight=load(run/'flight.json');arrival=load(run/'arrival-evaluation.json');contract=load(run/'runtime-contract.json');current=load(run/'n09-runtime-contract-current.json');obs=load(run/'n11-static-map-observation.json');identity=obs['run_identity'];gui=load(run/'gui-windows.json');safe=load(run/'safe-to-stop.json')
        checks.update(release_frozen=policy['status']=='ready_for_regression' and cfg['status']=='frozen',config_identity=policy['acceptance_config_sha256']==sha(config),core_runtime_identity=core_sha(contract['files'])==policy['core_runtime_sha256'],unchanged_active_runtime=contract['sha256']==current['sha256'],scene_source_identity=contract['files']['simulation/worlds/ego.sdf']==case['scene_source_sha256'],launch_identity=launch['protocol_sha256']==sha(release) and launch['runtime_contract_sha256']==contract['sha256'] and launch['pre_goal_record'] is True and launch['world_mutation_commands']==[],goal_identity=sha(ROOT/flight['goal_config'])==policy['goal_profile_sha256'],spawn_identity=load(run/'spawn-pose.json')['source_sha256']==policy['spawn_profile_sha256'],visible_gui=gui['run_id']==run.name and gui['gazebo_window_present'] and gui['rviz_window_present'] and gui['window_listing_sha256']==sha(run/'gui-windows.txt'),unique_control=all(flight.get('publisher_counts',{}).get(t)==1 for t in ['/fmu/in/offboard_control_mode','/fmu/in/trajectory_setpoint','/fmu/in/vehicle_command']),independent_arrival=arrival['independent_goal_dwell_passed'] is True,normal_terminal=safe['safe_to_stop_project_container'] and safe['emergency_disarm_used'] is False)
        for p,digest in policy['evaluator_sha256'].items():
            if sha(ROOT/p)!=digest:missing.append('evaluator_source:'+p)
        core=contact_and_terminal(run);report['contact_and_terminal']=core
        if core['status']=='FAIL':fail+=core.get('failures',['contact_or_terminal_failure'])
        elif core['status']!='PASS':missing+=core.get('missing_evidence',['contact_or_terminal_incomplete'])
        if not arrival['independent_goal_dwell_passed']:fail.append('independent_arrival_failed')
        if flight.get('action_success') is not True:fail.append('native_action_failed')
        expected={'run_id':run.name,'runtime_contract_sha256':contract['sha256'],'goal_id':flight['goal_id'],'epoch':flight['localization_epoch'],'map_id':launch['map_id']}
        checks['map_observer_identity']=identity.get('complete') is True and all(identity.get(k)==v for k,v in expected.items())
        rows=obs['snapshots'];updates=set()
        for row in rows:
            if any(row.get(k)!=expected[k] for k in ['goal_id','epoch','map_id']):raise ValueError('snapshot identity mismatch')
            path=(run/row['path']).resolve()
            if not path.is_relative_to(run.resolve()) or sha(path)!=row['sha256']:raise ValueError('snapshot path/hash mismatch')
            if not 0<row['source_stamp_ns']<=row['fusion_stamp_ns']<=row['snapshot_stamp_ns']:raise ValueError('snapshot time ordering')
            with np.load(path,allow_pickle=False) as arrays:
                if list(arrays['occupancy'].shape)!=row['shape'] or arrays['inflated'].shape!=arrays['occupancy'].shape:raise ValueError('snapshot dimensions')
            updates.add(row['fusion_stamp_ns'])
        checks['multiple_map_updates']=len(updates)>=2
        planner=load(run/'planner-observation.json');spline_ids={r['message']['traj_id'] for r in planner['messages'] if r['type']=='bspline' and r['message'].get('goal_id')==flight['goal_id'] and r['message'].get('epoch')==flight['localization_epoch']}
        commands=[r for r in flight['position_command_history'] if r.get('goal_id')==flight['goal_id'] and r.get('epoch')==flight['localization_epoch'] and r.get('flag')==1];executed=sorted({r['trajectory_id'] for r in commands}&spline_ids);checks['executed_replanning']=len(executed)>=2
        checks['actual_moving_commands']=any(np.linalg.norm(r['velocity_enu_m_s'])>0 for r in commands)
        for name in ['debug-truth-evaluation.json','alignment-observation.json','planner-observation.json','bridge-observation.json','n09-contact-observation.json','n10-resource-observation.json']:
            recorded=load(run/name).get('run_identity',{});checks['identity:'+name]=recorded.get('complete') is True and all(recorded.get(k)==v for k,v in expected.items())
        if scene=='staggered':route=staggered_route(run,config)
        elif scene=='single':route=evaluate_obstacle(run,config,1,obstacle_prefix='n12_single_cylinder/')
        elif scene=='corridor':route=corridor_route(run,config)
        else:
            import xml.etree.ElementTree as ET
            models=[m.get('name') for m in ET.parse(run/'vio_initialization.sdf').getroot().find('world').findall('model') if m.findtext('static') in ['true','1']]
            route={'status':'PASS' if set(models)=={'ground_plane','blank'} else 'FAIL','static_models':models}
        report['scene_route']=route
        if route.get('status')=='FAIL':fail.append('scene_route_failed')
        elif route.get('status')!='PASS':missing.append('scene_route_incomplete')
        process=load(run/'n16-process-observation.json');processpath=run/process['rows_file'];checks['process_record_hash']=sha(processpath)==process['rows_sha256'];prows=[json.loads(s) for s in processpath.read_text().splitlines() if s.strip()]
        # Same-source coverage throughout the full PRESTREAM-to-LANDED session.
        phases=[json.loads(s) for s in (run/'bridge-alignment-timeline.jsonl').read_text().splitlines() if s.strip()];start=next(x['stamp_ns'] for x in phases if x['phase']=='PRESTREAM');end=next(x['stamp_ns'] for x in phases if x['phase']=='LANDED')
        # Explicit direct bracketing is evaluated here, with stable kernel birth IDs.
        covered=[r for r in prows if isinstance(r.get('sim_ns'),int) and start<=r['sim_ns']<=end]
        checks['process_source_coverage']=any(isinstance(r.get('sim_ns'),int) and r['sim_ns']<=start for r in prows) and any(isinstance(r.get('sim_ns'),int) and r['sim_ns']>=end for r in prows)
        checks['core_process_liveness']=bool(covered) and all(len({tuple(r['roles'].get(role,[])) for r in covered})==1 and bool(covered[0]['roles'].get(role)) for role in process['expected_roles'])
        resource=load(run/'n10-resource-observation.json');checks['resource_record_complete']=resource.get('safe_session_terminal_observed') is True and len(resource.get('samples',[]))>=2
        checks['resource_queue_capture_bound']=resource.get('run_id')==run.name
        resources=assess_resources(run,start,end,flight['localization_epoch']);report['resource_evidence']=resources
        checks['no_observed_unbounded_work_backlog']=resources['status']=='OBSERVED' and not resources['missing'] and not resources['queue_trends_requiring_review']
        report.update(scene=scene,run_identity=expected,arrival=arrival['longest_joint_tolerance_window'],executed_matching_trajectory_ids=executed,distinct_map_update_count=len(updates),diagnostic_metrics=load(metrics) if metrics else None,input_sha256={name:sha(run/name) for name in ['flight.json','arrival-evaluation.json','n17-launch-record.json','runtime-contract.json','n11-static-map-observation.json','safe-to-stop.json','n16-process-observation.json']},release_sha256=sha(release),acceptance_config_sha256=sha(config))
    except (OSError,ValueError,KeyError,TypeError,StopIteration) as exc:missing.append(repr(exc))
    missing += [key for key,value in checks.items() if not value]
    report.update(checks=checks,failures=sorted(set(fail)),insufficient=sorted(set(missing)),overall_status='FAIL' if fail else 'INSUFFICIENT' if missing else 'PASS')
    report['formal_count_eligible']=report['overall_status']=='PASS';return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--config',type=Path,required=True);p.add_argument('--release',type=Path,required=True);p.add_argument('--metrics',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=assess(a.run,a.config,a.release,a.metrics);a.output.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n');print(r['overall_status'])
