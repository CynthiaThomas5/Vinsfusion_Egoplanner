"""Pure offline evidence checks for one continuous multi-goal airborne session."""
import math


def assess_continuity(flight, phases, commands, splines, truth_stamps, required_sim_s=600):
    missing=[];failures=[];legs=flight.get('legs') or []
    window=flight.get('continuous_navigation') or {}
    start,end=window.get('start_source_ns'),window.get('end_source_ns')
    report={'schema':'n16-continuity/v1','runtime_control_effect':False}
    if not isinstance(start,int) or not isinstance(end,int) or end<start:
        return {**report,'status':'INSUFFICIENT','missing':['valid_continuous_window'],'failures':[]}
    duration=(end-start)/1e9
    if not isinstance(required_sim_s,(int,float)) or isinstance(required_sim_s,bool) or not math.isfinite(required_sim_s) or required_sim_s<=0:
        missing.append('invalid_required_duration')
    elif duration<required_sim_s:missing.append('navigation_window_shorter_than_required_sim_seconds')
    if len(legs)<2:missing.append('multiple_actual_goals_not_demonstrated')
    if window.get('observed_sim_s')!=duration:missing.append('reported_duration_disagrees_with_source_stamps')
    epoch=flight.get('localization_epoch')
    if not epoch:missing.append('epoch_missing')
    if flight.get('simulation_clock_regressions',0):failures.append('simulation_clock_regression')
    if flight.get('action_success') is False:failures.append('mission_action_failed')
    if not flight.get('landed_and_disarmed'):missing.append('normal_landed_disarmed_evidence_missing')
    if phases:
        stamps=[p['stamp_ns'] for p in phases]
        if any(b<a for a,b in zip(stamps,stamps[1:])):failures.append('phase_source_time_regression')
        before=[p for p in phases if p['stamp_ns']<=start]
        active=([before[-1]] if before else [])+[p for p in phases if start<p['stamp_ns']<=end]
        if not before:missing.append('bridge_state_at_window_start_missing')
        if any(p.get('phase')!='ACTIVE' or p.get('armed') is not True or p.get('landed') is not False for p in active):
            failures.append('window_contains_non_active_or_non_airborne_state')
    else:missing.append('bridge_phase_timeline_missing')
    if not truth_stamps or min(truth_stamps)>start or max(truth_stamps)<end:
        missing.append('independent_truth_does_not_cover_complete_window')
    if truth_stamps and any(b<=a for a,b in zip(truth_stamps,truth_stamps[1:])):
        missing.append('independent_truth_time_not_strictly_monotonic')
    ids=[];goal_rows=[];previous_end=None
    for leg in legs:
        goal=leg.get('goal') or {};gid=leg.get('goal_id');ids.append(gid)
        leg_start=leg.get('goal_start_sim_ns');leg_end=leg.get('goal_completed_source_ns')
        if goal.get('frame')!='odom_'+str(epoch):failures.append('cross_epoch_goal_frame')
        if leg.get('action_success') is not True:failures.append('leg_not_successful')
        if not isinstance(leg_start,int) or not isinstance(leg_end,int) or leg_end<leg_start:
            missing.append('leg_start_end_source_evidence_missing');continue
        if previous_end is not None and leg_start<previous_end:missing.append('overlapping_or_reordered_goals')
        previous_end=leg_end
        rows=[r for r in commands if r.get('goal_id')==gid and r.get('epoch')==epoch and r.get('flag')==1
              and leg_start<=r.get('source_stamp_ns',-1)<=leg_end]
        matched={(m.get('goal_id'),m.get('epoch'),m.get('traj_id')) for m in splines}
        executed={r['trajectory_id'] for r in rows if (gid,epoch,r.get('trajectory_id')) in matched}
        if not rows or not executed:missing.append('leg_without_executed_matching_planner_trajectory')
        speeds=[math.sqrt(sum(float(v)**2 for v in r['velocity_enu_m_s'])) for r in rows if 'velocity_enu_m_s' in r]
        if not any(math.isfinite(v) and v>0 for v in speeds):missing.append('leg_without_observed_motion_command')
        goal_rows.append({'goal_id':gid,'start_ns':leg_start,'end_ns':leg_end,'command_count':len(rows),
                          'executed_trajectory_ids':sorted(executed)})
    if any(not gid for gid in ids) or len(set(ids))!=len(ids):missing.append('goal_identity_missing_or_reused')
    if legs and legs[0].get('goal_start_sim_ns')!=start:missing.append('window_does_not_start_at_first_goal')
    if goal_rows and goal_rows[-1]['end_ns']>end:missing.append('window_ends_before_last_goal')
    report.update(status='FAIL' if failures else 'INSUFFICIENT' if missing else 'PASS',
                  start_ns=start,end_ns=end,duration_sim_s=duration,required_sim_s=required_sim_s,epoch=epoch,legs=goal_rows,
                  missing=sorted(set(missing)),failures=sorted(set(failures)),
                  limitations=['requires independent pose/arrival/contact/resource evidence before N16 overall PASS'])
    return report
