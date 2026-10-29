#!/usr/bin/env python3
"""Evaluate one genuine N14 archive against its released scene/runtime/GUI identity."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.debug_truth.evaluate_n10_acceptance import evaluate


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def launch_protocol_bound(run, launch, policy, release):
    if launch.get('protocol_sha256') == sha(release):
        return True
    historical = policy.get('authorized_reassessments', {}).get(Path(run).name, {})
    return (historical.get('basis') == 'evidence_processing_fix_no_runtime_or_numeric_change'
            and historical.get('launch_record_sha256') == sha(Path(run)/'n14-launch-record.json')
            and historical.get('original_protocol_sha256') == launch.get('protocol_sha256'))


def assess(run, metrics, config, release):
    run=Path(run)
    missing=[]
    failures=[]
    policy=json.loads(Path(release).read_text())
    result={'schema':'n14-formal-run/v1','run_id':run.name,'runtime_control_effect':False,
            'formal_count_eligible':False,'release_sha256':sha(release)}
    try:
        contract=json.loads((run/'runtime-contract.json').read_text())
        launch=json.loads((run/'n14-launch-record.json').read_text())
        gui=json.loads((run/'gui-windows.json').read_text())
        if policy.get('status')!='ready_for_formal':missing.append('protocol_not_released')
        if policy.get('acceptance_config_sha256')!=sha(config):failures.append('config_release_mismatch')
        if contract.get('sha256')!=policy.get('frozen_runtime_contract_sha256'):failures.append('runtime_release_mismatch')
        if (launch.get('scenario')!='narrow_corridor'
                or not launch_protocol_bound(run, launch, policy, release)
                or launch.get('runtime_contract_sha256')!=contract.get('sha256')
                or launch.get('world_mutation_commands')!=[]):failures.append('launch_release_mismatch')
        if (gui.get('run_id')!=run.name or gui.get('gazebo_window_present') is not True
                or gui.get('rviz_window_present') is not True
                or gui.get('window_listing_sha256')!=sha(run/'gui-windows.txt')):
            missing.append('visible_gui_not_verified')
        core=evaluate(config,metrics,run,run.name)
        result['acceptance']=core
        if core['overall_status']=='FAIL':failures.append('core_acceptance_failed')
        elif core['overall_status']!='PASS':missing.append('core_acceptance_incomplete')
    except (OSError,ValueError,KeyError,TypeError) as exc:
        missing.append(str(exc))
    result.update(overall_status='FAIL' if failures else 'INSUFFICIENT' if missing else 'PASS',
                  failures=failures,insufficient=missing)
    result['formal_count_eligible']=result['overall_status']=='PASS'
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('run',type=Path);p.add_argument('--metrics',type=Path,required=True)
    p.add_argument('--config',type=Path,required=True);p.add_argument('--release',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=assess(a.run,a.metrics,a.config,a.release)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(result['overall_status'])
