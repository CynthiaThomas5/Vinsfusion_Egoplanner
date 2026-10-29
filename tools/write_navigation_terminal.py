#!/usr/bin/env python3
"""Write independent normal safe-stop evidence after flight; no ROS/control I/O."""
import hashlib,json,sys
from pathlib import Path
from n10_terminal_readback import summarize_terminal_readback


def terminal_record(readback, flight):
    b=readback.get('latest',{}).get('bridge',{});p=readback.get('latest',{}).get('px4_status',{});land=readback.get('latest',{}).get('land_detected',{})
    checks={'bridge_landed_phase':b.get('phase')=='LANDED','bridge_landed':b.get('landed') is True,
            'bridge_disarmed':b.get('armed') is False,'bridge_control_disabled':b.get('control_enabled') is False,
            'px4_disarmed':p.get('arming_state')==1,'px4_land_detected':land.get('landed') is True,
            'zero_control_after_terminal':readback.get('zero_control_after_terminal') is True,
            'goal_identity_present':bool(flight.get('goal_id')) and readback.get('expected_goal_id')==flight.get('goal_id'),
            'epoch_identity_present':bool(flight.get('localization_epoch')) and readback.get('expected_epoch')==flight.get('localization_epoch'),
            'no_old_epoch_goal_or_trajectory':readback.get('no_old_epoch_goal_or_trajectory') is True,
            'stable_terminal_window':readback.get('terminal_state_duration_wall_s',0)>=10,
            'no_terminal_state_violation':readback.get('terminal_state_violation_count')==0}
    native=summarize_terminal_readback(readback)
    return {'classification':'independent normal safe-stop readback; no flight-control effect',
            'safe_to_stop_project_container':all(checks.values()),'checks':checks,
            'native_terminal_evidence_complete':native['native_terminal_evidence_complete'],
            'native_terminal_evidence_summary':native,'expected_goal_id':flight.get('goal_id'),
            'expected_epoch':flight.get('localization_epoch'),'emergency_disarm_used':False}


if __name__=='__main__':
    run=Path(sys.argv[1]);path=run/'postflight-px4-bridge-readback.json'
    result=terminal_record(json.loads(path.read_text()),json.loads((run/'flight.json').read_text()))
    result['readback_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    (run/'safe-to-stop.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result));sys.exit(0 if result['safe_to_stop_project_container'] else 1)
