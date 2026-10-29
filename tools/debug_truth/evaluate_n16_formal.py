#!/usr/bin/env python3
"""Bind N16 measured evidence and figures to the released actual run identity."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.n10_run_identity import read_run_identity


def load(path):return json.loads(Path(path).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def assess(run,config,release):
    run=Path(run).resolve();missing=[];fail=[]
    out={'schema':'n16-formal-evaluation/v1','run_id':run.name,'runtime_control_effect':False,'formal_count_eligible':False}
    try:
        cfg=load(config);policy=load(release);evidence=load(run/'n16-evidence.json');flight=load(run/'flight.json')
        out['evidence']=evidence
        if evidence['overall_status']=='FAIL':fail.append('measured_evidence_failure')
        elif evidence['overall_status']!='PASS':missing.append('measured_evidence_incomplete')
        if cfg.get('status')!='frozen' or policy.get('status')!='ready_for_formal':missing.append('release_not_frozen')
        if policy.get('acceptance_config_sha256')!=sha(config):missing.append('acceptance_config_identity')
        hashes=policy.get('evaluator_sha256') or {}
        required=['tools/debug_truth/evaluate_n16_run.py','tools/debug_truth/evaluate_n16_formal.py',
                  'tools/debug_truth/plot_n16_run.py','tools/debug_truth/prepare_n16_evaluation.py',
                  'tools/n16_continuity.py','tools/n16_resource_evidence.py','tools/diagnostics/record_n16_processes.py']
        if not all(hashes.get(p)==sha(ROOT/p) for p in required):missing.append('released_evaluator_source_identity')
        runtime=load(run/'runtime-contract.json');current=load(run/'n09-runtime-contract-current.json')
        if not runtime.get('sha256')==current.get('sha256')==policy.get('frozen_runtime_contract_sha256'):missing.append('runtime_release_identity')
        launch=load(run/'n16-launch-record.json')
        if (launch.get('scenario')!='continuous_normal_navigation' or launch.get('protocol_sha256')!=sha(release)
                or launch.get('runtime_contract_sha256')!=runtime.get('sha256') or launch.get('pre_goal_record') is not True):missing.append('launch_release_identity')
        goal=ROOT/flight['goal_config']
        if sha(goal)!=policy.get('goal_profile_sha256'):missing.append('goal_profile_release_identity')
        if load(goal).get('continuous_navigation_min_sim_s')!=cfg['metrics']['continuous_navigation']['thresholds']['minimum_sim_s']:missing.append('goal_duration_config_disagreement')
        world=load(run/'world.json')
        if world.get('output_sha256')!=sha(run/'vio_initialization.sdf') or world.get('project_geometry_sha256')!=policy.get('scene_source_sha256'):missing.append('active_world_source_identity')
        identity=read_run_identity(run);out['run_identity']=identity
        if identity.get('complete') is not True:missing.append('incomplete_run_identity')
        for name in ['debug-truth-evaluation.json','alignment-observation.json','planner-observation.json',
                     'bridge-observation.json','n09-contact-observation.json','n10-resource-observation.json','n11-static-map-observation.json']:
            observed=load(run/name).get('run_identity') or {}
            if observed.get('complete') is not True or any(observed.get(k)!=identity.get(k) for k in ['run_id','runtime_contract_sha256','goal_id','epoch','map_id']):missing.append('observer_identity:'+name)
        processes=load(run/'n16-process-observation.json')
        if processes.get('run_id')!=run.name or processes.get('source_sha256')!=hashes.get('tools/diagnostics/record_n16_processes.py'):missing.append('process_observer_identity')
        gui=load(run/'gui-windows.json')
        if gui.get('run_id')!=run.name or not gui.get('gazebo_window_present') or not gui.get('rviz_window_present') or gui.get('window_listing_sha256')!=sha(run/'gui-windows.txt'):missing.append('visible_gui_evidence')
        mode=load(run.parent/(run.name+'-stack')/'n08-runtime-mode.json')
        if mode.get('control_owner')!='uav_px4_bridge only' or mode.get('ground_truth_online_allowed') is not False:missing.append('control_or_truth_contract')
        for topic in ['/fmu/in/offboard_control_mode','/fmu/in/trajectory_setpoint','/fmu/in/vehicle_command']:
            if flight.get('publisher_counts',{}).get(topic)!=1:missing.append('unique_control_publisher:'+topic)
        plots=load(run/'n16-plot-manifest.json')
        if plots.get('scope')!='continuous mission' or len(plots.get('files',{}))<2:missing.append('continuous_curve_evidence')
        for name,digest in plots.get('files',{}).items():
            path=(run/name).resolve()
            if not path.is_relative_to(run) or sha(path)!=digest:missing.append('plot_identity:'+name)
        out['input_sha256']={name:sha(run/name) for name in ['flight.json','runtime-contract.json','n16-evidence.json','n16-plot-manifest.json','n16-launch-record.json','n16-process-observation.json']}
        out['acceptance_config_sha256']=sha(config);out['release_sha256']=sha(release)
    except (OSError,ValueError,KeyError,TypeError) as exc:missing.append(repr(exc))
    out.update(overall_status='FAIL' if fail else 'INSUFFICIENT' if missing else 'PASS',failures=sorted(set(fail)),insufficient=sorted(set(missing)))
    out['formal_count_eligible']=out['overall_status']=='PASS';return out

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--config',type=Path,default=ROOT/'config/acceptance_n16.json');p.add_argument('--release',type=Path,default=ROOT/'docs/protocols/n16-continuous-load.json');p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=assess(a.run,a.config,a.release);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n');print(r['overall_status'])
