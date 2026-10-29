#!/usr/bin/env python3
"""Offline N08 reference/independent-motion terminal braking measurement."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np


def _strict_times(rows, key):
    values=np.asarray([int(row[key]) for row in rows],dtype=np.int64)
    if len(values)<10 or np.any(np.diff(values)<=0):
        raise ValueError('source stamps must be strictly increasing; no sorting or repair')
    return values


def _reference_state_equal(left, right):
    keys=('position_enu','velocity_enu_m_s','acceleration_enu_m_s2')
    if any(left[key]!=right[key] for key in keys):
        return False
    return left.get('yaw_enu')==right.get('yaw_enu')


def _trajectory_handoff_metrics(previous, current):
    previous_position=np.asarray(previous['position_enu'],dtype=float)
    current_position=np.asarray(current['position_enu'],dtype=float)
    previous_velocity=np.asarray(previous['velocity_enu_m_s'],dtype=float)
    current_velocity=np.asarray(current['velocity_enu_m_s'],dtype=float)
    previous_acceleration=np.asarray(previous['acceleration_enu_m_s2'],dtype=float)
    current_acceleration=np.asarray(current['acceleration_enu_m_s2'],dtype=float)
    previous_yaw=previous.get('yaw_enu');current_yaw=current.get('yaw_enu')
    yaw_delta=None
    if previous_yaw is not None and current_yaw is not None:
        yaw_delta=math.atan2(math.sin(float(current_yaw)-float(previous_yaw)),
                             math.cos(float(current_yaw)-float(previous_yaw)))
    return {
        'source_stamp_ns':int(current['source_stamp_ns']),
        'source_time_gap_s':(int(current['source_stamp_ns'])
                             -int(previous['source_stamp_ns']))/1e9,
        'from_trajectory_id':previous.get('trajectory_id'),
        'to_trajectory_id':current.get('trajectory_id'),
        'position_delta_m':float(np.linalg.norm(current_position-previous_position)),
        'velocity_delta_m_s':float(np.linalg.norm(current_velocity-previous_velocity)),
        'acceleration_delta_m_s2':float(np.linalg.norm(current_acceleration-previous_acceleration)),
        'yaw_delta_rad':yaw_delta,
    }


def _reference_samples(rows, certified_spline_starts=None):
    """Keep source order, collapsing exact repeats and certified same-time handoffs.

    EGO can publish the outgoing command and the newly certified spline command
    at one /clock stamp. That is a real transition with two states, not a repeat.
    It is accepted only when the incoming trajectory has a live spline
    certificate starting at that exact source stamp; both states remain
    represented in the returned handoff deltas. Other conflicting states and
    time regressions still fail.
    """
    result=[];repeats=0;handoffs=[]
    certified_spline_starts={int(key):int(value) for key,value in
                             (certified_spline_starts or {}).items()}
    for row in rows:
        if not result:
            result.append(row)
            continue
        previous=result[-1]
        source_stamp=int(row['source_stamp_ns'])
        previous_stamp=int(previous['source_stamp_ns'])
        if source_stamp<previous_stamp:
            raise ValueError('source stamps must be strictly increasing; no sorting or repair')
        previous_trajectory=previous.get('trajectory_id')
        current_trajectory=row.get('trajectory_id')
        same_trajectory=(previous_trajectory==current_trajectory)
        if source_stamp==previous_stamp:
            if same_trajectory and _reference_state_equal(previous,row):
                repeats+=1
                continue
            certified_handoff=(
                not same_trajectory
                and current_trajectory is not None
                and certified_spline_starts.get(int(current_trajectory))==source_stamp
                and previous.get('goal_id')==row.get('goal_id')
                and previous.get('epoch')==row.get('epoch'))
            if not certified_handoff:
                raise ValueError('conflicting reference states at an identical source stamp')
            handoffs.append(_trajectory_handoff_metrics(previous,row))
            result[-1]=row
            continue
        if (previous_trajectory is not None and current_trajectory is not None
                and not same_trajectory):
            handoffs.append(_trajectory_handoff_metrics(previous,row))
        result.append(row)
    return result,repeats,handoffs


def _first_sustained(times, mask, minimum_time, duration):
    for i in np.flatnonzero((times>=minimum_time)&mask):
        end=int(np.searchsorted(times,times[i]+duration,side='left'))
        if end<len(times) and np.all(mask[i:end+1]):
            return int(i)
    return None


def measure(reference, truth, start_ns, end_ns, alignment=None,
            stop_speed=.03, stop_dwell=1., step=.02,
            actual_vector_speed_limit=.12, certified_spline_starts=None):
    if end_ns<=start_ns:raise ValueError('invalid measurement interval')
    if not math.isfinite(float(actual_vector_speed_limit)) or actual_vector_speed_limit <= 0:
        raise ValueError('invalid actual vector speed limit')
    reference=[row for row in reference if start_ns<=int(row['source_stamp_ns'])<=end_ns]
    truth=[row for row in truth if start_ns-200000000<=int(row['stamp_ns'])<=end_ns+200000000]
    reference,reference_repeats,reference_handoffs=_reference_samples(
        reference,certified_spline_starts)
    rt_ns=_strict_times(reference,'source_stamp_ns');tt_ns=_strict_times(truth,'stamp_ns')
    if tt_ns[0]>start_ns or tt_ns[-1]<end_ns:
        raise ValueError('truth does not cover the complete braking/hold interval')
    if np.diff(tt_ns).max()>100000000:
        raise ValueError('truth source gap exceeds0.1s; interpolation is not supported')
    rt=(rt_ns-start_ns)/1e9;tt=(tt_ns-start_ns)/1e9
    position=np.asarray([row['xyz'] for row in truth],dtype=float)
    ref_position=np.asarray([row['position_enu'] for row in reference],dtype=float)
    ref_velocity=np.asarray([row['velocity_enu_m_s'] for row in reference],dtype=float)
    ref_acceleration=np.asarray([row['acceleration_enu_m_s2'] for row in reference],dtype=float)
    if any(not np.isfinite(a).all() for a in [position,ref_position,ref_velocity,ref_acceleration]):
        raise ValueError('non-finite motion samples')
    ref_speed=np.linalg.norm(ref_velocity,axis=1)
    peak_index=int(np.argmax(ref_speed));peak=float(ref_speed[peak_index])
    direction=ref_position[-1]-ref_position[0]
    length=float(np.linalg.norm(direction))
    if length<.2:raise ValueError('reference displacement is too small for braking calibration')
    direction/=length
    candidates=np.flatnonzero((np.arange(len(rt))>=peak_index)&(ref_acceleration@direction<-.005))
    if not len(candidates):raise ValueError('no planned deceleration segment observed')
    brake_time=float(rt[candidates[0]])
    ref_zero=_first_sustained(rt,ref_speed<=.005,brake_time,.2)

    uniform=np.arange(0,(end_ns-start_ns)/1e9+step/2,step)
    uniform=uniform[uniform<=(end_ns-start_ns)/1e9]
    p=np.asarray([np.interp(uniform,tt,position[:,j]) for j in range(3)]).T
    velocity=np.gradient(p,step,axis=0)
    # A 0.22s symmetric moving average; trim edges so padding cannot create a stop.
    width=11;half=width//2
    v=np.asarray([np.convolve(velocity[:,j],np.ones(width)/width,mode='valid') for j in range(3)]).T
    t=uniform[half:-half];p_filtered=p[half:-half]
    horizontal=np.linalg.norm(v[:,:2],axis=1)
    acceleration=np.gradient(horizontal,step)
    stopped=(horizontal<=stop_speed)&(np.abs(v[:,2])<=.05)
    stop_index=_first_sustained(t,stopped,brake_time,stop_dwell)
    response_index=_first_sustained(t,acceleration<=-.005,brake_time,.15)
    brake_index=int(np.searchsorted(t,brake_time))
    stop_time=None if stop_index is None else float(t[stop_index])
    metrics={'reference_identical_source_repeats':reference_repeats,
             'reference_unique_source_samples':len(reference),
             'reference_trajectory_handoffs':reference_handoffs,
             'actual_vector_speed_limit_m_s':float(actual_vector_speed_limit),
             'reference_peak_vector_speed_m_s':peak,
             'reference_braking_start_elapsed_sim_s':brake_time,
             'reference_zero_speed_elapsed_sim_s':None if ref_zero is None else float(rt[ref_zero]),
             'actual_peak_horizontal_speed_m_s':float(horizontal.max()),
             'actual_peak_vector_speed_m_s':float(np.linalg.norm(v,axis=1).max()),
             'actual_stop_elapsed_sim_s':stop_time,
             'actual_stop_observed':stop_index is not None,
             'stop_speed_threshold_m_s':stop_speed,'stop_dwell_sim_s':stop_dwell,
             'response_delay_to_sustained_deceleration_s':None if response_index is None else max(0.,float(t[response_index]-brake_time)),
             'actual_net_horizontal_displacement_m':float(np.linalg.norm(p[-1,:2]-p[0,:2])),
             'truth_max_source_gap_sim_s':float(np.diff(tt_ns).max()/1e9),
             'truth_derivative_smoothing_window_sim_s':width*step,
             'reference_max_source_gap_sim_s':float(np.diff(rt_ns).max()/1e9)}
    if stop_index is not None:
        segment=p_filtered[brake_index:stop_index+1,:2]
        metrics['actual_distance_from_reference_braking_start_m']=float(np.linalg.norm(np.diff(segment,axis=0),axis=1).sum())
        metrics['time_from_reference_braking_start_to_actual_stop_s']=float(t[stop_index]-brake_time)
        if ref_zero is not None:
            zero_index=min(len(t)-1,int(np.searchsorted(t,rt[ref_zero])))
            segment=p_filtered[zero_index:max(zero_index,stop_index)+1,:2]
            metrics['actual_residual_distance_after_reference_zero_m']=float(np.linalg.norm(np.diff(segment,axis=0),axis=1).sum())
        dwell_end=int(np.searchsorted(t,t[stop_index]+stop_dwell,side='right'))
        metrics['actual_stop_dwell_position_excursion_m']=float(np.linalg.norm(p_filtered[stop_index:dwell_end,:2]-p_filtered[stop_index,:2],axis=1).max())
        band=(t>=brake_time)&(t<=stop_time)&(horizontal>=max(stop_speed,.3*horizontal.max()))&(horizontal<=.9*horizontal.max())&(acceleration<-.005)
        deceleration=-acceleration[band]
        metrics['deceleration_speed_band_m_s']=[max(stop_speed,.3*float(horizontal.max())),.9*float(horizontal.max())]
        metrics['deceleration_samples']=int(len(deceleration))
        metrics['observed_deceleration_p10_m_s2']=None if len(deceleration)<3 else float(np.percentile(deceleration,10))
        metrics['observed_deceleration_mean_m_s2']=None if len(deceleration)<3 else float(deceleration.mean())
    if alignment is not None:
        rotation=np.asarray(alignment['rotation'],dtype=float);translation=np.asarray(alignment['translation_m'],dtype=float)
        actual=np.asarray([np.interp(rt,tt,position[:,j]) for j in range(3)]).T
        estimate=ref_position@rotation.T+translation
        metrics['independent_reference_tracking_error_max_m']=float(np.linalg.norm(estimate-actual,axis=1).max())
    checks={'nonzero_reference_speed':peak>=.04,
            'reference_speed_within_trial_limit':peak<=.12+1e-6,
            'actual_speed_within_abort_limit':metrics['actual_peak_horizontal_speed_m_s']<=.15+1e-6,
            'actual_vector_speed_within_trial_limit':metrics['actual_peak_vector_speed_m_s']<=actual_vector_speed_limit+1e-6,
            'meaningful_actual_displacement':metrics['actual_net_horizontal_displacement_m']>=.25,
            'actual_stop_and_dwell_observed':stop_index is not None,
            'reference_terminal_zero_observed':ref_zero is not None,
            'reference_source_gaps_bounded':metrics['reference_max_source_gap_sim_s']<=.1,
            'deceleration_measurement_supported':metrics.get('deceleration_samples',0)>=3,
            'sustained_deceleration_response_observed':response_index is not None}
    if alignment is not None:checks['independent_tracking_inside_certified_margin']=metrics['independent_reference_tracking_error_max_m']<=.25
    curve=[{'elapsed_sim_s':float(t[i]),'actual_horizontal_speed_m_s':float(horizontal[i]),
            'reference_vector_speed_m_s':float(np.interp(t[i],rt,ref_speed)),
            'actual_signed_speed_derivative_m_s2':float(acceleration[i]),
            'actual_world_xyz_m':p_filtered[i].tolist()} for i in range(len(t))]
    return {'metrics':metrics,'checks':checks,'passed':all(checks.values())},curve


def audit_forward_return(flight, truth):
    """Independently check the stationary turn and body-forward return in truth."""
    turn_goal=flight.get('yaw_turn_goal') or {}
    turn_observed=flight.get('yaw_turn_observed') or {}
    turn_map=flight.get('yaw_reorientation_precheck') or {}
    return_start=flight.get('return_goal_start_sim_ns')
    return_end=flight.get('return_completed_sim_ns')
    turn_start=turn_goal.get('start_sim_ns')
    turn_end=turn_observed.get('end_sim_ns')
    anchor=np.asarray(turn_map.get('center_xyz_m',[]),dtype=float)
    target_yaw=turn_goal.get('target_yaw_enu')
    report={'checks':{},'metrics':{}}
    required=(return_start,return_end,turn_start,turn_end,target_yaw)
    if any(value is None for value in required) or anchor.shape!=(3,) or not np.isfinite(anchor).all():
        report['checks']={'yaw_turn_observed':False,'turn_position_held':False,
                          'turn_before_return':False,'return_motion_forward':False}
        return report
    turn_start=int(turn_start);turn_end=int(turn_end)
    return_start=int(return_start);return_end=int(return_end)
    rows=[row for row in truth if turn_start<=int(row['stamp_ns'])<=turn_end]
    checks={'yaw_turn_observed':bool(flight.get('yaw_turn_result',{}).get('success')
                                     and turn_observed.get('absolute_yaw_error_rad',math.inf)<=.1),
            'turn_before_return':bool(turn_end<=return_start
                                      and turn_start>=int(flight.get('post_goal_hold_end_sim_ns',turn_start)))}
    if len(rows)<3:
        checks.update(turn_position_held=False,return_motion_forward=False)
        report['checks']=checks
        report['metrics']['truth_turn_samples']=len(rows)
        return report
    turn_position=np.asarray([row['xyz'] for row in rows],dtype=float)
    turn_max_excursion=float(np.linalg.norm(turn_position-anchor,axis=1).max())
    q=np.asarray([row['q_xyzw'] for row in rows],dtype=float)
    turn_yaw=np.arctan2(2.0*(q[:,3]*q[:,2]+q[:,0]*q[:,1]),
                        1.0-2.0*(q[:,1]**2+q[:,2]**2))
    turn_final_yaw=float(turn_yaw[-1])
    turn_final_error=abs(math.atan2(math.sin(turn_final_yaw-float(target_yaw)),
                                    math.cos(turn_final_yaw-float(target_yaw))))
    checks['turn_position_held']=turn_max_excursion<=.10
    checks['yaw_turn_observed']=checks['yaw_turn_observed'] and turn_final_error<=.1
    report['metrics'].update(truth_turn_samples=len(rows),
                             turn_max_position_excursion_m=turn_max_excursion,
                             turn_final_yaw_enu=turn_final_yaw,
                             turn_final_yaw_error_rad=turn_final_error)

    return_rows=[row for row in truth if return_start<=int(row['stamp_ns'])<=return_end]
    if len(return_rows)<10:
        checks['return_motion_forward']=False
        report['metrics']['truth_return_samples']=len(return_rows)
        report['checks']=checks
        return report
    stamps=np.asarray([int(row['stamp_ns']) for row in return_rows],dtype=np.int64)
    if np.any(np.diff(stamps)<=0):
        checks['return_motion_forward']=False
        report['metrics']['truth_return_source_order_valid']=False
        report['checks']=checks
        return report
    position=np.asarray([row['xyz'] for row in return_rows],dtype=float)
    q=np.asarray([row['q_xyzw'] for row in return_rows],dtype=float)
    yaw=np.unwrap(np.arctan2(2.0*(q[:,3]*q[:,2]+q[:,0]*q[:,1]),
                             1.0-2.0*(q[:,1]**2+q[:,2]**2)))
    dt=np.diff(stamps)/1e9
    velocity=np.diff(position[:,:2],axis=0)/dt[:,None]
    yaw_mid=.5*(yaw[:-1]+yaw[1:])
    forward_speed=velocity[:,0]*np.cos(yaw_mid)+velocity[:,1]*np.sin(yaw_mid)
    horizontal_speed=np.linalg.norm(velocity,axis=1)
    moving=horizontal_speed>=.03
    backwards=moving&(forward_speed<-.005)
    forward=moving&(forward_speed>=.03)
    checks['return_motion_forward']=bool(forward.sum()>=5 and not backwards.any())
    report['metrics'].update(truth_return_samples=len(return_rows),
        truth_return_motion_intervals=int(moving.sum()),
        truth_return_forward_intervals=int(forward.sum()),
        truth_return_backward_intervals=int(backwards.sum()),
        truth_return_min_forward_speed_m_s=(float(forward_speed[moving].min()) if moving.any() else None),
        truth_return_source_order_valid=True)
    report['checks']=checks
    return report


def measure_cancel_stop(curve, flight, trigger_window_m_s, braking_metrics,
                        candidate_stop_envelope_m):
    """Measure independent truth travel and response from a source-clocked cancel."""
    cancel = flight.get('cancel_stop') or {}
    try:
        start_ns = int(flight['goal_start_sim_ns'])
        request_ns = int(cancel['request_sim_ns'])
        trigger_elapsed = (request_ns - start_ns) / 1e9
        times = np.asarray([row['elapsed_sim_s'] for row in curve], dtype=float)
        speed = np.asarray([row['actual_horizontal_speed_m_s'] for row in curve], dtype=float)
        acceleration = np.asarray([row['actual_signed_speed_derivative_m_s2'] for row in curve], dtype=float)
        positions = np.asarray([row['actual_world_xyz_m'] for row in curve], dtype=float)
    except (KeyError, TypeError, ValueError, OverflowError):
        raise ValueError('cancel_stop_event_or_truth_curve_missing')
    if (not len(times) or not np.isfinite(times).all() or not np.isfinite(speed).all()
            or not np.isfinite(acceleration).all() or not np.isfinite(positions).all()
            or trigger_elapsed < times[0] or trigger_elapsed > times[-1]):
        raise ValueError('cancel_stop_event_outside_truth_curve')
    start = int(np.searchsorted(times, trigger_elapsed, side='left'))
    stop_time = braking_metrics.get('actual_stop_elapsed_sim_s')
    if stop_time is None:
        raise ValueError('cancel_stop_actual_stop_not_observed')
    stop = int(np.searchsorted(times, float(stop_time), side='right')) - 1
    if stop <= start:
        raise ValueError('cancel_stop_interval_has_no_motion_samples')
    distance = float(np.linalg.norm(np.diff(positions[start:stop+1, :2], axis=0), axis=1).sum())
    response = None
    sample_step = float(np.median(np.diff(times))) if len(times) > 1 else math.nan
    needed = max(2, int(math.ceil(.15 / sample_step))) if sample_step > 0 else len(times)+1
    for i in np.flatnonzero((times >= trigger_elapsed) & (acceleration <= -.005)):
        if i + needed <= len(times) and np.all(acceleration[i:i+needed] <= -.005):
            response = max(0.0, float(times[i] - trigger_elapsed))
            break
    lower, upper = map(float, trigger_window_m_s)
    metrics = {
        'cancel_request_elapsed_sim_s': trigger_elapsed,
        'cancel_to_stop_distance_m': distance,
        'cancel_to_stop_elapsed_sim_s': max(0.0, float(times[stop] - trigger_elapsed)),
        'cancel_to_sustained_deceleration_response_s': response,
        'trigger_px4_horizontal_speed_m_s': float(cancel['px4_horizontal_speed_m_s']),
        'trigger_ego_reference_speed_m_s': float(cancel['ego_reference_vector_speed_m_s']),
        'trigger_ego_longitudinal_acceleration_m_s2': float(cancel['ego_longitudinal_acceleration_m_s2']),
        'candidate_stop_distance_envelope_m': float(candidate_stop_envelope_m),
    }
    remaining=cancel.get('remaining_forward_corridor_m')
    if remaining is None:
        # Historical trial records predate the online reserve field. Reconstruct
        # it from the recorded goal and independent trigger position when possible.
        try:
            target=np.asarray(flight['goal']['target_enu'],dtype=float)
            origin=np.asarray(flight['airborne_origin_enu'],dtype=float)
            position=np.asarray(cancel['actual_position_enu_m'],dtype=float)
            direction=(target-origin)/np.linalg.norm(target-origin)
            remaining=float(np.dot(target-position,direction))
        except (KeyError,TypeError,ValueError,ZeroDivisionError):
            remaining=None
    metrics['remaining_forward_corridor_m_at_cancel']=remaining
    checks = {
        'caller_cancel_acknowledged': cancel.get('cancel_acknowledged') is True,
        'navigation_action_canceled': (cancel.get('action_result') or {}).get('status') == 5
            and (cancel.get('action_result') or {}).get('outcome') == 'canceled'
            and (cancel.get('action_result') or {}).get('reason') == 'caller_cancel'
            and (cancel.get('action_result') or {}).get('success') is False,
        'cancel_trigger_speed_window_observed': lower <= metrics['trigger_px4_horizontal_speed_m_s'] <= upper
            and lower <= metrics['trigger_ego_reference_speed_m_s'] <= .12,
        'cancel_trigger_preceded_planned_deceleration': metrics['trigger_ego_longitudinal_acceleration_m_s2'] >= -.005,
        'certified_replacement_stop_spline_observed': cancel.get('stop_spline_certified') is True
            and cancel.get('stop_trajectory_id') != cancel.get('old_trajectory_id'),
        'old_trajectory_not_resumed': cancel.get('old_trajectory_resumed') is False,
        'actual_stop_and_hold_after_cancel': braking_metrics.get('actual_stop_observed') is True,
        'cancel_to_sustained_deceleration_observed': response is not None,
        'cancel_stop_inside_candidate_envelope': distance <= metrics['candidate_stop_distance_envelope_m'],
        'bridge_active_through_cancel_stop_hold': cancel.get('bridge_active_after_stop_hold') is True,
    }
    return {'metrics': metrics, 'checks': checks}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('run',type=Path);parser.add_argument('--plot',action='store_true');parser.add_argument('--completion-mode',choices=('single_goal','round_trip'));args=parser.parse_args()
    run=args.run.resolve();flight=json.loads((run/'flight.json').read_text());truth=json.loads((run/'debug-truth-evaluation.json').read_text())['samples']
    completion_mode=args.completion_mode or flight.get('completion_mode','round_trip')
    if completion_mode not in ('single_goal','round_trip'):
        raise SystemExit('unknown N08 completion mode in run record')
    trial_kind=flight.get('trial_kind','terminal_stop')
    if trial_kind not in ('terminal_stop','motion_cancel'):
        raise SystemExit('unknown N08 trial kind in run record')
    report={'schema':'n08-independent-terminal-braking/v2','run_id':run.name,
            'completion_mode':completion_mode,
            'trial_kind':trial_kind,
            'scope':('one ordinary forward EGO goal, terminal stop/hold, separately checked destination landing; no return goal is required' if completion_mode=='single_goal' and trial_kind=='terminal_stop' else 'one forward goal canceled during measured motion; evaluate the replacement EGO stop/hold spline and separately checked destination landing' if trial_kind=='motion_cancel' else 'one planned EGO terminal stop, stationary EGO yaw turn and forward-only EGO return to the N05 home pad'),
            'passed':False,'native_trial_failure':flight.get('failure')}
    try:
        reference=[r for r in flight['position_command_history'] if r['goal_id']==flight['goal_id']]
        localization=json.loads((run/'odometry-evaluation.json').read_text())
        limits=flight.get('trial_limits') or {}
        actual_vector_speed_limit=float(limits.get('actual_vector_speed_limit_m_s',.12))
        certified_spline_starts={
            int(row['traj_id']):int(row['source_clock_ns'])
            for row in flight.get('live_spline_certificates',[])
            if row.get('goal_id')==flight.get('goal_id')
            and row.get('traj_id') is not None and row.get('source_clock_ns') is not None}
        result,curve=measure(reference,truth,int(flight['goal_start_sim_ns']),int(flight['post_goal_hold_end_sim_ns']),localization['alignment'],actual_vector_speed_limit=actual_vector_speed_limit,certified_spline_starts=certified_spline_starts)
        report.update(result)
        if trial_kind=='motion_cancel':
            cancel_result=measure_cancel_stop(
                curve,flight,flight.get('cancel_trigger_speed_window_m_s',(.04,.06)),
                report['metrics'],
                float(limits.get('cancel_stop_distance_envelope_m',.50)))
            report['cancel_stop']=cancel_result
            cancel=flight.get('cancel_stop') or {}
            report['checks']['cancel_stop_trajectory_handoff_observed']=any(
                row.get('from_trajectory_id')==cancel.get('old_trajectory_id')
                and row.get('to_trajectory_id')==cancel.get('stop_trajectory_id')
                for row in report['metrics']['reference_trajectory_handoffs'])
        report['checks'].update(native_trial_completed=flight.get('result')=='PASS',
            n05_and_airborne_capsules_passed=bool(flight.get('pre_enable_corridor',{}).get('capsule',{}).get('passed') and flight.get('airborne_corridor',{}).get('capsule',{}).get('passed')),
            cancel_stop_corridor_admitted=(trial_kind!='motion_cancel' or (
                bool(flight.get('pre_enable_corridor',{}).get('cancel_stop_envelope',{}).get('passed'))
                and bool(flight.get('airborne_corridor',{}).get('cancel_stop_envelope',{}).get('passed')))),
            landed_and_disarmed=bool(flight.get('landed_and_disarmed')),
            clock_did_not_regress=flight.get('clock_regressions')==0,
            no_watchdog_violation=not flight.get('watchdog_events'),
            live_spline_certificates_present=bool(flight.get('live_spline_certificates')),
            sole_expected_publishers=bool(flight.get('publisher_counts')) and all(n==1 for n in flight['publisher_counts'].values()),
            no_truth_control=flight.get('debug_truth_used_for_control') is False,
            localization_continuous=localization.get('invalid_localization_status_samples')==0)
        if completion_mode=='single_goal':
            report['checks'].update(
                destination_pre_goal_landing_candidate_passed=bool(flight.get('destination_landing_pre_goal',{}).get('accepted')),
                destination_final_landing_candidate_passed=bool(flight.get('destination_landing_final',{}).get('accepted')),
                no_return_action_or_goal=flight.get('return_action_sent') is False and not flight.get('return_goal_id'))
            if trial_kind=='terminal_stop':
                report['checks']['ordinary_goal_action_succeeded']=flight.get('action_success') is True
            else:
                report['checks'].update(cancel_result['checks'])
        else:
            turn_audit=audit_forward_return(flight,truth)
            report['yaw_first_forward_return']=turn_audit
            report['checks'].update(turn_audit['checks'])
            certs=flight.get('live_spline_certificates',[])
            report['checks'].update(
                live_stationary_yaw_spline_certified=any(
                    row.get('goal_kind')=='turn_in_place' and
                    row.get('goal_id')==(flight.get('yaw_turn_goal') or {}).get('goal_id')
                    for row in certs),
                live_forward_return_spline_certified=any(
                    row.get('goal_kind')=='forward_return' and
                    row.get('goal_id')==flight.get('return_goal_id')
                    for row in certs),
                returned_to_n05_home_pad=bool(flight.get('return_action_result',{}).get('success')))
        report['passed']=all(report['checks'].values())
        report['limitations']=['Finite simulation sample; observed deceleration quantiles are not guaranteed lower bounds.',
            'Symmetric0.22s smoothing limits response-delay precision; raw position records remain available.',
            'One fixed pre-enable SE(3) alignment, scale1; no truth or full map fed to control.',
            'Exact equal-stamp reference repeats are counted once; a changed state at equal time is accepted only as a live-certified trajectory start, and its position/velocity/acceleration/yaw deltas are retained. No sorting or stamp rewriting.',
            'Moving-cancel distance applies only to the measured forward low-speed calibration window; it is not a general cancellation guarantee. Three-run ordinary-goal qualification remains a separate exit.']
        (run/'n08-braking-curve.json').write_text(json.dumps(curve,indent=2)+'\n')
        if args.plot:
            import matplotlib;matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            fig,axis=plt.subplots(figsize=(8,4));axis.plot([r['elapsed_sim_s'] for r in curve],[r['reference_vector_speed_m_s'] for r in curve],label='EGO reference');axis.plot([r['elapsed_sim_s'] for r in curve],[r['actual_horizontal_speed_m_s'] for r in curve],label='Independent actual');axis.axvline(report['metrics']['reference_braking_start_elapsed_sim_s'],color='gray',linestyle='--',label='Reference deceleration');axis.set(xlabel='Simulation time after goal (s)',ylabel='Speed (m/s)');axis.legend();axis.grid(alpha=.3);fig.tight_layout();fig.savefig(run/'n08-braking-speed.png',dpi=160);plt.close(fig)
    except (ValueError,KeyError,OSError,TypeError) as exc:
        report['failure']=str(exc)
    report['evaluator_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report['runtime_evaluator_sha256']=flight.get('source_sha256',{}).get('tools/debug_truth/evaluate_n08_braking.py')
    report['measurement_definitions']={
        'stop':'speed<=0.03m/s horizontal and<=0.05m/s vertical for1s; not exact zero motion',
        'braking_distance':'independent horizontal path length from reference acceleration along goal direction<-0.005m/s^2 after reference peak to the threshold stop',
        'response_delay':'time until actual horizontal deceleration>=0.005m/s^2 persists0.15s; includes control dynamics and0.22s symmetric filtering, not a pure transport latency',
        'cancel_to_stop_distance':'independent truth path length from the first sample at or after the source-clocked caller-cancel request to the measured actual stop',
        'identical_reference_repeats':'count exact same-trajectory source-time states once; timestamp regressions and conflicting states fail except a changed state on a live-certified incoming trajectory at its exact start stamp, which is retained as a handoff with full position/velocity/acceleration/yaw deltas'}
    report['input_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [run/'flight.json',run/'debug-truth-evaluation.json',run/'odometry-evaluation.json'] if p.exists()}
    (run/'n08-braking-evaluation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(report,indent=2,allow_nan=False))
    return 0 if report['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
