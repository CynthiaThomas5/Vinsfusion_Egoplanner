#!/usr/bin/env python3
"""Offline everyday navigation result; not scene qualification or formal credit."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
from n09_contact_evaluation import evaluate_contacts
from write_navigation_terminal import terminal_record


def evaluate(run):
    run=Path(run);names=['flight.json','arrival-evaluation.json','n09-contact-observation.json','n09-contact-model-manifest.json','bridge-alignment-timeline.jsonl','safe-to-stop.json','runtime-contract.json','n09-runtime-contract-current.json','postflight-px4-bridge-readback.json'];checks={};errors=[];hashes={}
    try:
        data={n:json.loads((run/n).read_text()) for n in names if not n.endswith('.jsonl')};phases=[json.loads(s) for s in (run/'bridge-alignment-timeline.jsonl').read_text().splitlines() if s.strip()];f=data['flight.json'];arrival=data['arrival-evaluation.json'];safe=data['safe-to-stop.json']
        contact=evaluate_contacts(data['n09-contact-observation.json'],data['n09-contact-model-manifest.json'],phases,int(f['goal']['source_ns']))
        normal=terminal_record(data['postflight-px4-bridge-readback.json'],f)
        checks={'native_mission':f.get('result')=='PASS' and f.get('action_success') is True,'independent_arrival':arrival.get('independent_goal_dwell_passed') is True,'contact':contact.get('passed') is True,'normal_landed_disarmed':normal['safe_to_stop_project_container'] is True and f.get('landed_and_disarmed') is True and safe.get('safe_to_stop_project_container') is True and all(safe.get('checks',{}).values()) and safe.get('emergency_disarm_used') is False,'terminal_identity':safe.get('expected_goal_id')==f.get('goal_id') and safe.get('expected_epoch')==f.get('localization_epoch'),'runtime_identity':data['runtime-contract.json'].get('sha256')==data['n09-runtime-contract-current.json'].get('sha256'),'unique_control_publishers':all(f.get('publisher_counts',{}).get(t)==1 for t in ['/fmu/in/offboard_control_mode','/fmu/in/trajectory_setpoint','/fmu/in/vehicle_command'])}
        hashes={n:hashlib.sha256((run/n).read_bytes()).hexdigest() for n in names}
    except (OSError,ValueError,KeyError,TypeError) as exc:errors.append(str(exc))
    return {'schema':'normal-navigation-qualification/v1','run_id':run.name,'passed':bool(checks) and all(checks.values()) and not errors,'checks':checks,'missing_or_invalid':errors,'input_sha256':hashes,'runtime_effect':False,'formal_count_eligible':False,'scope':'everyday single-goal navigation result only; formal scene and duration evidence evaluated separately'}


if __name__=='__main__':
    run=Path(sys.argv[1]);report=evaluate(run);(run/'qualification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));sys.exit(0 if report['passed'] else 1)
