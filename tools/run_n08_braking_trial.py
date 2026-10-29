#!/usr/bin/env python3
"""One bounded forward EGO terminal-stop trial; PX4 control remains bridge-owned."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import signal
import time

import numpy as np
import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, qos_profile_sensor_data
from rclpy.signals import SignalHandlerOptions
from rosgraph_msgs.msg import Clock
from uav_interfaces.action import NavigateToPose
from uav_interfaces.msg import MapStatus, PositionCommand
from uav_interfaces.srv import GetOccupancySnapshot
from traj_utils.msg import Bspline
from evaluate_n08_curve_certificate import (resolve_trial_speed_profile,
                                            derivative_polygon, certify_speed_bounds)
from evaluate_n08_curve_certificate import raw_sphere_query
from n05_entry import (load_policy, collision_primitives, check_entry_schedule,
                       fit_ground_plane, check_candidate_landing_schedule)
from n08_trial_gate import (trial_limits, certify_trial_capsule,
                            certify_forward_trial_corridor,
                            certify_trial_reference_tube,
                            certify_trial_turn_approach,
                            trial_takeoff_velocity_settled,
                            candidate_landing_pose_from_ground_planes,
                            TRIAL_FORWARD_REFERENCE_TUBE_M,
                            TRIAL_FORWARD_INITIAL_REVERSE_BOUND_M,
                            TRIAL_FORWARD_YAW_DEVIATION_BOUND_RAD,
                            trial_fixed_heading_deviation_rad,
                            TRIAL_TAKEOFF_TOTAL_SPEED_LIMIT_M_S,
                            TRIAL_TAKEOFF_VERTICAL_SPEED_LIMIT_M_S,
                            TRIAL_TAKEOFF_SETTLE_DURATION_S,
                            remaining_forward_corridor_distance)
from run_n08_compute_only import current_pose
from run_vio_ego_flight import (EgoFlightProbe, call_enable, spin_until,
                               localization_tracking_current_epoch, telemetry_sources_fresh)


class _SingleGoalComplete(Exception):
    pass


class _DestinationHoldPending(Exception):
    pass


def is_caller_cancel_action_result(status, outcome, reason):
    """Match the ROS action terminal status separately from the result reason."""
    return (status == GoalStatus.STATUS_CANCELED
            and outcome == 'canceled'
            and reason == 'caller_cancel')


def bspline_time_window(msg):
    """Return the active source-clock interval used by EGO's trajectory server."""
    order=int(msg.order);point_count=len(msg.pos_pts)
    knots=np.asarray(msg.knots,dtype=float)
    if (order<1 or point_count<order+1
            or knots.shape!=(point_count+order+1,)
            or not np.isfinite(knots).all() or np.any(np.diff(knots)<=0)):
        raise ValueError('invalid_stop_spline_knot_domain')
    start_parameter=float(knots[order])
    end_parameter=float(knots[point_count])
    duration=end_parameter-start_parameter
    stamp=msg.start_time
    start_ns=int(stamp.sec)*1_000_000_000+int(stamp.nanosec)
    if not math.isfinite(duration) or duration<=0 or start_ns<=0:
        raise ValueError('invalid_stop_spline_time_window')
    return {'start_sim_ns':start_ns,'duration_sim_s':duration,
            'end_sim_ns':start_ns+int(round(duration*1_000_000_000))}


def terminal_reference_command(rows, goal_id, epoch, trajectory_id, end_sim_ns):
    """Recognize EGO's terminal hold even though traj_server keeps flag READY."""
    candidates=[row for row in rows if row.get('goal_id')==goal_id
                and row.get('epoch')==epoch
                and int(row.get('trajectory_id',-1))==int(trajectory_id)
                and int(row.get('source_stamp_ns',-1))>=int(end_sim_ns)]
    unique=[]
    fields=('position_enu','velocity_enu_m_s','acceleration_enu_m_s2')
    for row in candidates:
        stamp=int(row['source_stamp_ns'])
        if unique and stamp<int(unique[-1]['source_stamp_ns']):
            raise RuntimeError('cancel_stop_reference_source_time_regressed')
        if unique and stamp==int(unique[-1]['source_stamp_ns']):
            if any(row[key]!=unique[-1][key] for key in fields):
                raise RuntimeError('conflicting_cancel_stop_reference_at_same_source_stamp')
            continue
        unique.append(row)
    if len(unique)<2:
        return None
    last=unique[-1]
    last_stamp=int(last['source_stamp_ns'])
    anchor_index=next((i for i in range(len(unique)-2,-1,-1)
                       if last_stamp-int(unique[i]['source_stamp_ns'])>=50_000_000),None)
    if anchor_index is None:
        return None
    terminal_window=unique[anchor_index:]
    allowed_flags=(PositionCommand.TRAJECTORY_STATUS_READY,
                   PositionCommand.TRAJECTORY_STATUS_COMPLETED)
    terminal_positions=[]
    for row in terminal_window:
        if int(row.get('flag',-1)) not in allowed_flags:
            return None
        position=np.asarray(row['position_enu'],dtype=float)
        velocity=np.asarray(row['velocity_enu_m_s'],dtype=float)
        acceleration=np.asarray(row['acceleration_enu_m_s2'],dtype=float)
        if (position.shape!=(3,) or velocity.shape!=(3,) or acceleration.shape!=(3,)
                or not np.isfinite(np.concatenate((position,velocity,acceleration))).all()):
            raise RuntimeError('invalid_cancel_stop_terminal_reference')
        if np.linalg.norm(velocity)>1e-6 or np.linalg.norm(acceleration)>1e-6:
            return None
        terminal_positions.append(position)
    if any(np.linalg.norm(position-terminal_positions[-1])>1e-4
           for position in terminal_positions[:-1]):
        return None
    return last


def px4_sample_inside_stop_gate(row):
    """Use the N08 measured-stop bounds on fresh PX4 local velocity samples."""
    velocity=np.asarray([row['vx'],row['vy'],row['vz']],dtype=float)
    return (velocity.shape==(3,) and np.isfinite(velocity).all()
            and math.hypot(float(velocity[0]),float(velocity[1]))<=.03
            and abs(float(velocity[2]))<=.05)


def validate_trial_source_fingerprints(root, build_source_hashes, runtime_files):
    """Keep compiled-source checks strict and authenticate runtime Python at run start."""
    root = Path(root).resolve()
    runtime_only_paths=(
        'tools/run_n08_braking_trial.py',
        'tools/n08_trial_gate.py',
    )
    profile_path='config/components/navigation/n08_forward_braking_trial_goal.json'
    if profile_path in build_source_hashes or profile_path in runtime_files:
        runtime_only_paths+=(profile_path,)
    if ('tools/debug_truth/evaluate_n08_braking.py' in build_source_hashes
            or 'tools/debug_truth/evaluate_n08_braking.py' in runtime_files):
        runtime_only_paths+=('tools/debug_truth/evaluate_n08_braking.py',)
    for relative in runtime_only_paths:
        runtime_hash = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        if runtime_files.get(relative) != runtime_hash:
            error = ('run_trial_runner_fingerprint_mismatch'
                     if relative == 'tools/run_n08_braking_trial.py'
                     else 'run_trial_runtime_fingerprint_mismatch')
            raise ValueError(error + ':' + relative)
    for relative, expected_hash in build_source_hashes.items():
        if relative in runtime_only_paths:
            # These Python files are executed from the workspace and are
            # authenticated by this cold-run manifest, not compiled binaries.
            continue
        actual_hash = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError('trial_source_fingerprint_mismatch:' + relative)


def certify_n08_landing_candidate(snapshot, metadata, home_pose, home_plane,
                                  candidate_xy, yaw, hold_height,
                                  policy, primitives):
    """Use this snapshot's raw ground plane to check a future descent only."""
    plane_guess = [float(candidate_xy[0]), float(candidate_xy[1]),
                   float(home_pose['center_xyz_m'][2])]
    plane = fit_ground_plane(snapshot['occupancy'], snapshot['origin_m'],
                             snapshot['resolution_m'], plane_guess, policy)
    result = {'map': metadata, 'plane_fit_guess_xyz_m': plane_guess,
              'candidate_ground_plane': plane}
    if not plane.get('valid'):
        result.update(accepted=False,
                      reason=plane.get('reason', 'candidate_ground_plane_invalid'),
                      ground_confirmed=False)
        return result
    try:
        pose = candidate_landing_pose_from_ground_planes(
            home_pose, home_plane, plane, candidate_xy, yaw)
    except (TypeError, ValueError, OverflowError) as exc:
        result.update(accepted=False, reason=str(exc), ground_confirmed=False)
        return result
    if not math.isfinite(hold_height) or hold_height <= 0:
        result.update(accepted=False, reason='candidate_landing_hold_height_invalid',
                      ground_confirmed=False, landing_pose=pose)
        return result
    certificate = check_candidate_landing_schedule(
        snapshot, pose, hold_height_m=hold_height,
        policy=policy, ground_plane=plane, primitives=primitives)
    result.update(accepted=bool(certificate['accepted']),
                  reason=certificate['reason'], landing_pose=pose,
                  candidate_schedule=certificate,
                  ground_confirmed=False)
    return result


def run_motion_cancel_stop(node, handle, action, goal_id, epoch, limits,
                           trigger_window_m_s, timeout_s, preflight_rtf):
    """Cancel inside a live forward-speed window and observe EGO's replacement stop spline."""
    lower, upper = map(float, trigger_window_m_s)
    if not (0.03 < lower < upper <= 0.1):
        raise ValueError('motion_cancel_trigger_window_outside_n08_range')
    deadline = time.monotonic() + float(timeout_s)
    trigger = None
    old_trajectory_id = None
    while time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.005)
        if node.check_watchdog(epoch):
            raise RuntimeError(node.watchdog_fault)
        if action.done():
            raise RuntimeError('goal_completed_before_motion_cancel_trigger')
        command = node.latest_position_command
        local = node.local_position_history[-1] if node.local_position_history else None
        if (command is None or command.goal_id != goal_id or local is None
                or int(command.trajectory_flag) != PositionCommand.TRAJECTORY_STATUS_READY):
            continue
        reference_velocity = np.asarray(
            [command.velocity.x, command.velocity.y, command.velocity.z], dtype=float)
        reference_acceleration = np.asarray(
            [command.acceleration.x, command.acceleration.y, command.acceleration.z], dtype=float)
        reference_speed = float(np.linalg.norm(reference_velocity))
        actual_horizontal_speed = math.hypot(float(local['vx']), float(local['vy']))
        if reference_speed <= 1e-9:
            continue
        braking_acceleration = float(reference_acceleration @
                                     (reference_velocity / reference_speed))
        if (lower <= actual_horizontal_speed <= upper
                and lower <= reference_speed <= limits['actual_vector_speed_limit_m_s']
                and braking_acceleration >= -0.005):
            current, _ = current_pose(node)
            remaining=remaining_forward_corridor_distance(
                node.trial_start,current,limits['offset_enu_m'])
            trigger = {
                'request_sim_ns': int(node.clock_ns),
                'request_wall_elapsed_s': time.monotonic() - node.started_wall,
                'actual_position_enu_m': list(map(float, current)),
                'px4_horizontal_speed_m_s': actual_horizontal_speed,
                'ego_reference_vector_speed_m_s': reference_speed,
                'ego_longitudinal_acceleration_m_s2': braking_acceleration,
                'remaining_forward_corridor_m': remaining,
                'candidate_cancel_stop_distance_envelope_m':
                    limits['cancel_stop_distance_envelope_m'],
                'local_position_sample_us': int(local['timestamp_sample_us']),
            }
            old_trajectory_id = int(command.trajectory_id)
            break
    if trigger is None:
        raise RuntimeError('motion_cancel_trigger_window_not_observed_before_goal_end')

    cancel_future = handle.cancel_goal_async()
    if not spin_until(node, cancel_future.done, 3.0):
        raise RuntimeError('motion_cancel_acknowledgement_timeout')
    cancel_response = cancel_future.result()
    trigger['cancel_acknowledged'] = bool(cancel_response.goals_canceling)
    if not cancel_response.goals_canceling:
        raise RuntimeError('motion_cancel_request_not_accepted')
    if not spin_until(node, action.done, 5.0):
        raise RuntimeError('canceled_navigation_action_did_not_finish')
    wrapped = action.result()
    nav = wrapped.result
    trigger['action_result'] = {'status': int(wrapped.status), 'success': bool(nav.success),
                                'outcome': nav.outcome, 'reason': nav.reason}
    node.cancel_stop_trace = trigger
    if not is_caller_cancel_action_result(wrapped.status, nav.outcome, nav.reason):
        raise RuntimeError('navigation_action_did_not_report_caller_canceled')

    def replacement_spline_seen():
        return any(row.get('goal_id') == goal_id
                   and row.get('source_clock_ns') is not None
                   and row['source_clock_ns'] >= trigger['request_sim_ns']
                   and row.get('traj_id') != old_trajectory_id
                   for row in node.validated_splines)
    if not spin_until(node, replacement_spline_seen, 5.0,
                      abort_predicate=lambda: node.check_watchdog(epoch)
                      or node.bridge is None or node.bridge.phase != 'ACTIVE'):
        raise RuntimeError(node.watchdog_fault or 'certified_cancel_stop_spline_not_observed')
    stop_spline = next(row for row in reversed(node.validated_splines)
                       if row.get('goal_id') == goal_id
                       and row.get('source_clock_ns') >= trigger['request_sim_ns']
                       and row.get('traj_id') != old_trajectory_id)
    stop_trajectory_id = int(stop_spline['traj_id'])
    trigger['old_trajectory_id'] = old_trajectory_id
    trigger['stop_trajectory_id'] = stop_trajectory_id
    trigger['stop_spline_certified'] = bool(
        stop_spline.get('speed_bounds', {}).get('passed')
        and stop_spline.get('reference_tube', {}).get('passed'))
    trigger['stop_spline_source_sim_ns'] = int(stop_spline['source_clock_ns'])
    stop_message=node.splines.get(goal_id)
    if stop_message is None or int(stop_message.traj_id)!=stop_trajectory_id:
        raise RuntimeError('cancel_stop_spline_message_not_retained')
    time_window=bspline_time_window(stop_message)
    trigger['stop_spline_start_sim_ns']=time_window['start_sim_ns']
    trigger['stop_spline_duration_sim_s']=time_window['duration_sim_s']
    trigger['stop_spline_end_sim_ns']=time_window['end_sim_ns']
    hold_s=max(1.0,float(limits['post_goal_hold_sim_s']))
    rtf=float(preflight_rtf)
    if not math.isfinite(rtf) or rtf<=0:
        raise RuntimeError('cancel_stop_preflight_rtf_invalid')
    wall_timeout_s=max(20.0,(time_window['duration_sim_s']+hold_s+10.0)/rtf*1.5)
    wait_deadline=time.monotonic()+wall_timeout_s
    terminal_command=None;stationary_since_ns=None;last_local_sample_us=None
    stationary_samples=[];last_local_receipt_wall=None
    while time.monotonic()<wait_deadline:
        rclpy.spin_once(node,timeout_sec=.02)
        if node.check_watchdog(epoch):
            raise RuntimeError(node.watchdog_fault)
        if (node.bridge is None or node.bridge.phase!='ACTIVE'
                or not node.bridge.armed or node.bridge.landed):
            raise RuntimeError('bridge_left_active_cancel_stop_hold')
        terminal_command=terminal_reference_command(
            node.position_commands,goal_id,epoch,stop_trajectory_id,
            time_window['end_sim_ns'])
        if terminal_command is None or node.clock_ns<time_window['end_sim_ns']:
            stationary_since_ns=None;stationary_samples.clear()
            continue
        local=node.local_position_history[-1] if node.local_position_history else None
        local_receipt_wall=(None if local is None else
                            node.started_wall+float(local['wall_elapsed_s']))
        if (local is None or local_receipt_wall is None
                or time.monotonic()-local_receipt_wall>.5
                or not telemetry_sources_fresh(node.latest_bridge_detail or {})):
            stationary_since_ns=None;stationary_samples.clear()
            continue
        sample_us=int(local['timestamp_sample_us'])
        if sample_us==last_local_sample_us:
            continue
        if last_local_sample_us is not None and sample_us<last_local_sample_us:
            raise RuntimeError('px4_local_position_sample_time_regressed_during_cancel_hold')
        last_local_sample_us=sample_us
        last_local_receipt_wall=local_receipt_wall
        if px4_sample_inside_stop_gate(local):
            if stationary_since_ns is None:
                stationary_since_ns=int(node.clock_ns)
                stationary_samples=[]
            stationary_samples.append({
                'sim_ns':int(node.clock_ns),'timestamp_sample_us':sample_us,
                'horizontal_speed_m_s':math.hypot(float(local['vx']),float(local['vy'])),
                'absolute_vertical_speed_m_s':abs(float(local['vz']))})
            if node.clock_ns-stationary_since_ns>=hold_s*1_000_000_000:
                break
        else:
            stationary_since_ns=None;stationary_samples.clear()
    if (terminal_command is None or stationary_since_ns is None
            or node.clock_ns-stationary_since_ns<hold_s*1_000_000_000):
        raise RuntimeError(node.watchdog_fault or 'cancel_stop_spline_or_measured_hold_timeout')
    completed=terminal_command
    newer_stop_indices = [i for i, row in enumerate(node.position_commands)
                          if row.get('goal_id') == goal_id
                          and row.get('trajectory_id') == stop_trajectory_id
                          and int(row.get('source_stamp_ns',-1))>=time_window['end_sim_ns']]
    last_newer_index = max(newer_stop_indices, default=-1)
    old_resumed = any(row.get('goal_id') == goal_id
                      and row.get('trajectory_id') == old_trajectory_id
                      for row in node.position_commands[last_newer_index + 1:])
    if old_resumed:
        raise RuntimeError('old_goal_trajectory_resumed_after_cancel_stop_handoff')
    trigger['terminal_reference_command']={
        'source_sim_ns':int(completed['source_stamp_ns']),
        'trajectory_flag':int(completed['flag']),
        'position_enu_m':completed['position_enu'],
        'velocity_enu_m_s':completed['velocity_enu_m_s'],
        'acceleration_enu_m_s2':completed['acceleration_enu_m_s2'],
        'semantics':'EGO traj_server keeps READY after B-spline time domain and holds terminal position with zero derivatives.'}
    trigger['stop_spline_completed_sim_ns'] = int(time_window['end_sim_ns'])
    trigger['actual_stop_onset_sim_ns']=int(stationary_since_ns)
    trigger['actual_stop_dwell_sim_s']=hold_s
    trigger['post_stop_hold_px4_unique_samples']=len(stationary_samples)
    trigger['post_stop_max_horizontal_speed_m_s']=max(
        (row['horizontal_speed_m_s'] for row in stationary_samples),default=None)
    trigger['post_stop_max_absolute_vertical_speed_m_s']=max(
        (row['absolute_vertical_speed_m_s'] for row in stationary_samples),default=None)
    trigger['post_stop_final_px4_sample_us']=(
        None if last_local_sample_us is None else int(last_local_sample_us))
    trigger['post_stop_last_px4_receipt_wall_s']=(
        None if last_local_receipt_wall is None else float(last_local_receipt_wall-node.started_wall))
    trigger['post_stop_hold_end_sim_ns'] = int(node.clock_ns)
    trigger['bridge_active_after_stop_hold'] = True
    trigger['old_trajectory_resumed'] = False
    return trigger


class TrialProbe(EgoFlightProbe):
    def __init__(self):
        super().__init__()
        self.map_status = None
        self.map_status_wall = None
        self.clock_ns = None
        self.clock_wall = None
        self.clock_regressions = 0
        self.goal_id = ''
        self.goal_kind = 'forward'
        self.goal_anchor = None
        self.goal_yaw = None
        self.goal_start_yaw = None
        self.trial_start = None
        self.trial_tube_forward_distance = None
        self.limits = None
        self.watchdog_fault = ''
        self.watchdog_events = []
        self.yaw_tracking_history = []
        self.maximum_yaw_tracking_error_rad = 0.0
        self.spline_rejections = []
        self.splines = {}
        self.validated_splines = []
        self.cancel_stop_trace = None
        status_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                                durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(MapStatus, '/mapping/status', self.on_map_status, status_qos)
        self.create_subscription(Clock, '/clock', self.on_clock, qos_profile_sensor_data)
        self.snapshot_client = self.create_client(GetOccupancySnapshot, '/mapping/get_occupancy_snapshot')
        self.create_subscription(Bspline, '/drone_0_planning/bspline', self.on_spline, 10)

    def on_spline(self, msg):
        self.splines[msg.goal_id] = msg
        if msg.goal_id == self.goal_id:
            self.check_spline(msg)

    def check_spline(self, msg):
        if self.trial_start is None or self.limits is None:
            return
        points=np.asarray([[p.x,p.y,p.z] for p in msg.pos_pts],dtype=float)
        knots=np.asarray(msg.knots,dtype=float)
        if (int(msg.order)!=3 or points.ndim!=2 or points.shape[1]!=3 or len(points)<6
                or knots.size!=len(points)+4 or not np.isfinite(points).all()
                or not np.isfinite(knots).all() or np.any(np.diff(knots)<=0)):
            self.trip('invalid_live_trial_spline')
            return
        yaw_points=np.asarray(msg.yaw_pts,dtype=float)
        if self.goal_kind == 'turn_in_place':
            if self.goal_anchor is None or self.goal_yaw is None:
                self.trip('missing_yaw_turn_certificate_context')
                return
            if np.max(np.linalg.norm(points-self.goal_anchor,axis=1)) > .05:
                self.trip('yaw_only_reference_translated_outside_hold_tolerance')
                return
            if yaw_points.shape != (len(points),) or not np.isfinite(yaw_points).all():
                self.trip('invalid_live_yaw_turn_spline')
                return
            if not math.isfinite(float(msg.yaw_dt)) or float(msg.yaw_dt)<=0:
                self.trip('invalid_live_yaw_turn_interval')
                return
            yaw_unwrapped=np.unwrap(yaw_points)
            yaw_delta=float(yaw_unwrapped[-1]-yaw_unwrapped[0])
            start_yaw_error=math.atan2(math.sin(float(yaw_points[0])-self.goal_start_yaw),
                                        math.cos(float(yaw_points[0])-self.goal_start_yaw))
            yaw_error=math.atan2(math.sin(float(yaw_points[-1])-self.goal_yaw),
                                 math.cos(float(yaw_points[-1])-self.goal_yaw))
            yaw_rate_bound=float(np.max(np.abs(3.0*np.diff(yaw_points)/float(msg.yaw_dt))))
            monotonic=(np.all(np.diff(yaw_unwrapped)>=-1e-6) if yaw_delta>=0
                       else np.all(np.diff(yaw_unwrapped)<=1e-6))
            if (abs(start_yaw_error)>.1 or abs(yaw_error) > .1 or yaw_rate_bound>.5 or not monotonic
                    or abs(abs(yaw_delta)-math.pi)>.1):
                self.trip('live_yaw_turn_spline_misses_requested_heading')
                return
        elif self.goal_kind in ('forward','forward_positioning','forward_return'):
            if self.goal_yaw is None or yaw_points.shape != (len(points),) or not np.isfinite(yaw_points).all():
                self.trip('invalid_forward_heading_reference')
                return
        try:
            tube=certify_trial_reference_tube(
                knots,points,int(msg.order),self.trial_start,
                (self.trial_tube_forward_distance
                 if self.trial_tube_forward_distance is not None
                 else self.limits['offset_enu_m'][0]),
                tolerance_m=TRIAL_FORWARD_REFERENCE_TUBE_M,
                minimum_forward_delta_m=(-TRIAL_FORWARD_INITIAL_REVERSE_BOUND_M
                                         if self.goal_kind == 'forward'
                                         else None))
        except (ValueError,IndexError,TypeError,OverflowError):
            self.trip('invalid_live_trial_reference_tube')
            return
        if not tube['passed']:
            rejection={'goal_id':msg.goal_id,'traj_id':int(msg.traj_id),
                       'goal_kind':self.goal_kind,'reference_tube':tube}
            if not any(row.get('goal_id')==msg.goal_id for row in self.spline_rejections):
                self.spline_rejections.append(rejection)
            self.trip('reference_curve_left_certified_trial_tube')
            return
        try:
            derivative,_=derivative_polygon(knots,points,int(msg.order))
            bounds=certify_speed_bounds(derivative,
                (self.limits['configured_axis_velocity_limit_m_s']-.0001)/1.05,
                self.limits['actual_vector_speed_limit_m_s'])
        except (ValueError,IndexError,TypeError):
            self.trip('invalid_live_trial_derivative')
            return
        if self.goal_kind in ('forward','forward_positioning','forward_return'):
            body_forward=np.asarray([math.cos(self.goal_yaw),math.sin(self.goal_yaw)])
            longitudinal=derivative[:,:2]@body_forward
            yaw_error=np.arctan2(np.sin(yaw_points-self.goal_yaw),
                                 np.cos(yaw_points-self.goal_yaw))
            if (np.min(longitudinal)<-.005
                    or np.max(np.abs(yaw_error))>TRIAL_FORWARD_YAW_DEVIATION_BOUND_RAD):
                self.trip('live_translation_is_not_forward_in_body_frame')
                return
        if not bounds['passed']:
            self.trip('live_trial_spline_speed_certificate_failed')
            return
        self.validated_splines.append({'goal_id':msg.goal_id,'traj_id':int(msg.traj_id),
                                      'speed_bounds':bounds,'reference_tube':tube,
                                      'source_clock_ns':self.clock_ns,
                                      'goal_kind':self.goal_kind,
                                      'yaw_rate_control_bound_rad_s':(
                                          yaw_rate_bound if self.goal_kind=='turn_in_place' else None)})

    def on_map_status(self, msg):
        self.map_status, self.map_status_wall = msg, time.monotonic()

    def on_clock(self, msg):
        now = int(msg.clock.sec)*1000000000+int(msg.clock.nanosec)
        if self.clock_ns is not None and now < self.clock_ns:
            self.clock_regressions += 1
        self.clock_ns, self.clock_wall = now, time.monotonic()

    def trip(self, reason):
        if not self.watchdog_fault:
            self.watchdog_fault = reason
            self.watchdog_events.append({'reason':reason,'clock_ns':self.clock_ns,
                                          'wall_elapsed_s':time.monotonic()-self.started_wall})

    def _on_position_command(self, msg):
        super()._on_position_command(msg)
        if not self.goal_id or msg.goal_id != self.goal_id or self.limits is None:
            return
        if msg.trajectory_flag in (PositionCommand.TRAJECTORY_STATUS_READY,
                                   PositionCommand.TRAJECTORY_STATUS_COMPLETED):
            speed = math.sqrt(msg.velocity.x**2+msg.velocity.y**2+msg.velocity.z**2)
            if not math.isfinite(speed) or speed > self.limits['actual_vector_speed_limit_m_s']+1e-6:
                self.trip('reference_vector_speed_exceeded_trial_limit')

    def check_watchdog(self, epoch):
        if not localization_tracking_current_epoch(self, epoch):
            self.trip('localization_not_tracking')
        if self.clock_regressions:
            self.trip('clock_regression')
        if self.clock_wall is None or time.monotonic()-self.clock_wall > .5:
            self.trip('clock_stalled')
        if self.goal_id and self.odometry is not None and self.trial_start is not None:
            pos,actual_yaw=current_pose(self)
            delta=np.asarray(pos)-self.trial_start
            max_forward=(self.trial_tube_forward_distance
                         if self.trial_tube_forward_distance is not None
                         else self.limits['offset_enu_m'][0])
            if delta[0] < -.15 or delta[0] > max_forward+.15 or np.linalg.norm(delta[1:]) > .15:
                self.trip('actual_motion_left_trial_tracking_tube')
            command=self.latest_position_command
            if command is not None and command.goal_id==self.goal_id:
                reference=np.asarray([command.position.x,command.position.y,command.position.z])
                if np.linalg.norm(np.asarray(pos)-reference) > self.limits['maximum_tracking_error_m']:
                    self.trip('actual_tracking_error_exceeded_trial_limit')
            if (self.goal_kind in ('forward','forward_positioning','forward_return')
                    and self.goal_yaw is not None):
                yaw_error=trial_fixed_heading_deviation_rad(
                    self.goal_yaw,actual_yaw)
                self.maximum_yaw_tracking_error_rad=max(
                    self.maximum_yaw_tracking_error_rad,abs(yaw_error))
                self.yaw_tracking_history.append({
                    'goal_id':self.goal_id,
                    'source_stamp_ns':(
                        int(self.odometry.header.stamp.sec)*1_000_000_000
                        +int(self.odometry.header.stamp.nanosec)),
                    'reference_yaw_rad':self.goal_yaw,
                    'estimated_body_yaw_rad':actual_yaw,
                    'absolute_error_rad':abs(yaw_error),
                    'limit_rad':TRIAL_FORWARD_YAW_DEVIATION_BOUND_RAD,
                })
                if abs(yaw_error)>TRIAL_FORWARD_YAW_DEVIATION_BOUND_RAD:
                    self.trip('actual_yaw_left_certified_trial_envelope')
            if self.local_position_history:
                latest=self.local_position_history[-1]
                if math.hypot(latest['vx'],latest['vy']) > .15:
                    self.trip('actual_horizontal_speed_exceeded_abort_limit')
        return bool(self.watchdog_fault)


def capture_snapshot(node, run, label, epoch, map_id):
    if not node.snapshot_client.wait_for_service(timeout_sec=3):
        raise RuntimeError('trial_raw_snapshot_service_unavailable')
    # wait_for_service() blocks this single-threaded node executor. MapStatus
    # callbacks may queue during discovery, so the cached receipt time above
    # cannot be treated as current until spin_until() processes a fresh one.
    refresh_started_wall=time.monotonic()
    if not spin_until(node,lambda:(node.map_status is not None
            and node.map_status_wall is not None
            and node.map_status_wall>=refresh_started_wall),1.):
        raise RuntimeError('trial_map_status_refresh_timeout_after_snapshot_service_wait')

    def status_problem(during_request=False):
        status=node.map_status
        suffix='_during_snapshot_request' if during_request else '_after_snapshot_service_wait'
        if status is None:
            return 'trial_map_status_missing'+suffix
        if status.epoch!=epoch or status.map_id!=map_id:
            return ('trial_map_identity_changed'+suffix+':expected='
                    +epoch+'/'+map_id+',observed='+str(status.epoch)+'/'+str(status.map_id))
        if not status.reset_acknowledged:
            return 'trial_map_reset_not_acknowledged'+suffix
        if not status.input_ready:
            return 'trial_map_inputs_not_ready'+suffix+':'+str(status.reason)
        if (node.map_status_wall is None
                or time.monotonic()-node.map_status_wall>.5):
            return 'trial_map_status_stale'+suffix
        return ''

    problem=status_problem()
    if problem:
        raise RuntimeError(problem)
    attempts=[];deadline=time.monotonic()+2.
    while True:
        problem=status_problem(during_request=True)
        if problem:
            raise RuntimeError(problem)
        request=GetOccupancySnapshot.Request();request.expected_epoch=epoch;request.expected_map_id=map_id
        future=node.snapshot_client.call_async(request)
        if not spin_until(node,future.done,min(1.,max(.001,deadline-time.monotonic()))):
            raise RuntimeError('trial_raw_snapshot_timeout')
        response=future.result()
        observation={'attempt':len(attempts)+1,'clock_ns':node.clock_ns,
            'accepted':bool(response is not None and response.accepted),
            'reason':None if response is None else response.reason,
            'epoch':None if response is None else response.epoch,
            'map_id':None if response is None else response.map_id,
            'frame_id':None if response is None else response.header.frame_id}
        attempts.append(observation)
        (run/(label+'-requests.json')).write_text(json.dumps(attempts,indent=2)+'\n')
        if response is None:raise RuntimeError('trial_raw_snapshot_no_response')
        if response.accepted:
            if (response.reason!='ok' or response.epoch!=epoch or response.map_id!=map_id
                    or response.header.frame_id!='odom_'+epoch):
                raise RuntimeError('trial_raw_snapshot_wrong_identity_or_frame:'+str(observation))
            break
        if response.reason not in {'no_fresh_fused_depth','occupancy_update_stale','depth_source_stale'}:
            raise RuntimeError('trial_raw_snapshot_rejected:'+response.reason)
        if time.monotonic()>=deadline:
            raise RuntimeError('trial_raw_snapshot_transient_deadline:'+response.reason)
        # Same finite retry policy as the existing compute-only recorder:
        # wait for a completed fresh fusion, never accept the rejected grid.
        wait_until=min(deadline,time.monotonic()+.01)
        while time.monotonic()<wait_until:
            rclpy.spin_once(node,timeout_sec=min(.005,wait_until-time.monotonic()))
    stamp=lambda s:int(s.sec)*1000000000+int(s.nanosec)
    ages=[(node.clock_ns-stamp(response.last_depth_source_stamp))/1e9,
          (node.clock_ns-stamp(response.last_fusion_stamp))/1e9]
    if any(age<0 or age>.4 for age in ages):
        raise RuntimeError('trial_snapshot_source_or_fusion_stale')
    shape=(int(response.size_x),int(response.size_y),int(response.size_z))
    occupancy=np.asarray(response.occupancy_data,dtype=np.int8).reshape(shape)
    origin=[response.origin.x,response.origin.y,response.origin.z]
    raw={'occupancy':occupancy,'origin_m':origin,'resolution_m':float(response.resolution)}
    archive=run/(label+'.npz');np.savez_compressed(archive,occupancy=occupancy)
    metadata={'epoch':epoch,'map_id':map_id,'frame_id':response.header.frame_id,
              'source_age_s':ages[0],'fusion_age_s':ages[1],
              'last_depth_source_stamp_ns':stamp(response.last_depth_source_stamp),
              'last_fusion_stamp_ns':stamp(response.last_fusion_stamp),
              'origin_m':origin,'resolution_m':response.resolution,'shape':list(shape),
              'archive':archive.name,'capture_clock_ns':node.clock_ns}
    (run/(label+'.json')).write_text(json.dumps(metadata,indent=2)+'\n')
    return raw,metadata


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root',default='.')
    parser.add_argument('--goal-config',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--completion-mode',choices=('single_goal','round_trip'),
                        default='single_goal')
    parser.add_argument('--trial-kind',choices=('terminal_stop','motion_cancel'),
                        default='terminal_stop')
    parser.add_argument('--cancel-speed-window',nargs=2,type=float,
                        default=(0.04,0.06),metavar=('MIN_M_S','MAX_M_S'))
    args=parser.parse_args()
    if args.trial_kind=='motion_cancel' and args.completion_mode!='single_goal':
        raise SystemExit('motion_cancel_requires_single_goal_completion')
    root=Path(args.project_root).resolve();output=Path(args.output).resolve();run=output.parent
    if output.exists():
        raise SystemExit('refusing_to_overwrite_flight_record')
    profile=json.loads((root/args.goal_config).read_text())
    launch=json.loads((run.parent/(run.name+'-stack')/'launch-manifest.json').read_text())
    mode=json.loads((run.parent/(run.name+'-stack')/'n08-runtime-mode.json').read_text())
    speed=resolve_trial_speed_profile(launch,root)
    dynamics=json.loads((root/'progress/evidence/n08-speed-final-feasibility-20261024-251.json').read_text())
    yaw_build_path=root/'progress/evidence/n08-cancel-stop-build-20261026-289.json'
    yaw_build=json.loads(yaw_build_path.read_text())
    runtime=json.loads((run/'runtime-contract.json').read_text())['files']
    for relative, expected_hash in dynamics['runtime_files_sha256'].items():
        if relative.startswith('install/'):
            # 0045 intentionally changes the EGO executable; its exact new
            # source/build identity is checked against the #261 build record.
            continue
        if hashlib.sha256((root/relative).read_bytes()).hexdigest()!=expected_hash:
            raise SystemExit('trial_dynamics_build_fingerprint_mismatch:'+relative)
    if yaw_build.get('result')!='PASS':
        raise SystemExit('yaw_first_return_build_record_not_passed')
    try:
        validate_trial_source_fingerprints(
            root, yaw_build['source_files_sha256'], runtime)
    except ValueError as exc:
        raise SystemExit(str(exc))
    for relative, expected_hash in yaw_build['runtime_files_sha256'].items():
        if hashlib.sha256((root/relative).read_bytes()).hexdigest()!=expected_hash:
            raise SystemExit('yaw_first_return_built_binary_fingerprint_mismatch:'+relative)
        if relative.startswith('install/') and runtime.get(relative)!=expected_hash:
            raise SystemExit('run_yaw_first_return_binary_fingerprint_mismatch:'+relative)
    planner=json.loads((root/speed['path']).read_text());limits=trial_limits(profile,planner)
    if speed['vector_speed_cap_m_s'] != limits['actual_vector_speed_limit_m_s']:
        raise SystemExit('trial_profile_and_launch_speed_caps_differ')
    if mode.get('mode')!='execute' or mode.get('bridge_trajectory_input_topic')!='/position_cmd':
        raise SystemExit('braking_trial_requires_native_execute_mode')
    if (args.completion_mode=='round_trip'
            and mode.get('completion_mode') not in (None,'round_trip')):
        raise SystemExit('round_trip_completion_mode_mismatch')
    n05=json.loads((run/'n05-current-area/n05-live-entry-check.json').read_text())
    replay=json.loads((run/'n05-current-area/n05-offline-entry-replay.json').read_text())
    if not (n05.get('accepted') and replay.get('matches_online_result')):
        raise SystemExit('fresh_n05_admission_required')
    expected=n05['identity'];epoch=expected['epoch'];map_id=expected['map_id']
    cancelled=False
    def cancel(_signum,_frame):
        nonlocal cancelled
        cancelled=True
    signal.signal(signal.SIGINT,cancel);signal.signal(signal.SIGTERM,cancel)
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    node=TrialProbe();node.limits=limits
    result={'schema':'n08-braking-trial-run/v3','mode':'execute',
            'trial_kind':args.trial_kind,
            'cancel_trigger_speed_window_m_s':list(args.cancel_speed_window),
            'completion_mode':args.completion_mode,
            'scope':('One ordinary forward EGO goal, terminal stop/hold, and separately checked landing at the destination; no return goal is implied or sent.' if args.completion_mode=='single_goal' and args.trial_kind=='terminal_stop' else 'One forward goal canceled in a measured forward-speed window; EGO replaces its active spline with a separately certified stop/hold spline, then the stopped destination is separately checked for landing.' if args.trial_kind=='motion_cancel' else 'One forward EGO planned terminal stop followed by separately issued stationary yaw reorientation and forward-only EGO return; not moving-cancel braking qualification.'),
            'result':'FAIL','goal_config':args.goal_config,'profile':'vio_closed_loop',
            'control_owner':'uav_px4_bridge only','debug_truth_used_for_control':False,
            'action_goal_sent':False,'return_action_sent':False,'landed_and_disarmed':False,
            'wall_monotonic_origin_s':node.started_wall,'trial_limits':limits,
            'localization_epoch':epoch,'service_calls':[],'n05_identity':expected,
            'source_sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in [root/args.goal_config,root/speed['path'],yaw_build_path,
                          root/'dependencies/sources.json',
                          root/'dependencies/patches/ego/0045-stationary-yaw-only-return.patch',
                          root/'dependencies/patches/ego/0046-cancel-stop-hold.patch',
                          root/'src/vendor/ego_planner/planner/plan_manage/src/ego_replan_fsm.cpp',
                          root/'src/own/uav_interfaces/msg/TrajectoryCancel.msg',
                          root/'src/own/uav_navigation/uav_navigation/node.py',
                          Path(__file__).resolve(),
                          root/'tools/n08_trial_gate.py',root/'tools/mission_runtime.sh',
                          root/'tools/n05_entry.py',
                          root/'tools/debug_truth/evaluate_n08_braking.py']}}
    handle=None;action=None
    try:
        ready=spin_until(node,lambda:node.bridge is not None and node.bridge.phase=='DISABLED'
                         and node.bridge.landed and not node.bridge.armed and node.odometry is not None
                         and node.clock_ns is not None and node.map_status is not None
                         and localization_tracking_current_epoch(node,epoch)
                         and telemetry_sources_fresh(node.latest_bridge_detail or {}),45)
        if not ready:raise RuntimeError('trial_preconditions_not_ready')
        if not node.action_client.wait_for_server(timeout_sec=5):raise RuntimeError('action_server_unavailable')
        ground=n05['state']['body_pose_imu_m']
        now,ground_yaw=current_pose(node)
        if np.linalg.norm(np.asarray(now)-ground['center_xyz_m'])>.1:
            raise RuntimeError('ground_pose_changed_since_current_n05_admission')
        raw,meta=capture_snapshot(node,run,'n08-trial-ground-map',epoch,map_id)
        body=float(planner['obstacles_inflation_m'])
        predicted=np.asarray(now)+[0,0,1]
        policy=load_policy(root)
        primitives=collision_primitives(root)
        capsule=certify_forward_trial_corridor(
            raw,predicted,limits['offset_enu_m'],body,
            limits['tracking_margin_m'],limits['maximum_tracking_error_m'],
            limits['forward_stopping_extension_m'],yaw_rad=ground_yaw,
            policy=policy,primitives=primitives)
        cancel_corridor={'passed':True,'required':args.trial_kind=='motion_cancel',
                         'reason':'not_required_for_terminal_stop'}
        if args.trial_kind=='motion_cancel':
            cancel_offset=np.asarray([limits['cancel_stop_distance_envelope_m'],0.0,0.0])
            cancel_corridor=certify_forward_trial_corridor(
                raw,predicted,cancel_offset,body,limits['tracking_margin_m'],
                limits['maximum_tracking_error_m'],0.0,yaw_rad=ground_yaw,
                policy=policy,primitives=primitives)
        home_pad=check_entry_schedule(raw,ground,ground_confirmed=True,
                                      disarmed=True,control_disabled=True,
                                      policy=policy,primitives=primitives)
        result['pre_enable_corridor']={'map':meta,'capsule':capsule,
                                      'cancel_stop_envelope':cancel_corridor,
                                      'home_pad_entry':home_pad,
                                      'landing_plan':(
                                          'land at the separately checked destination after the one-way goal; no return goal is sent'
                                          if args.completion_mode=='single_goal' else
                                          'after the first goal stops, issue a separate 180-degree turn and a second forward EGO return goal')}
        (run/'n08-trial-pre-enable-admission.json').write_text(json.dumps(result['pre_enable_corridor'],indent=2)+'\n')
        if (not capsule['passed']
                or (args.trial_kind=='motion_cancel' and not cancel_corridor['passed'])
                or not home_pad['accepted']):
            raise RuntimeError('trial_corridor_or_home_pad_unknown_or_occupied')
        # The independent raw snapshot above is the N08 map evidence. The
        # inherited PointCloud2 observer is not used by this trial and can
        # delay health-status callbacks while PX4 is taking off.
        map_observer_topic='/grid_map/occupancy'
        map_observers=[sub for sub in list(node.subscriptions)
                       if sub.topic_name==map_observer_topic]
        for sub in map_observers:
            node.destroy_subscription(sub)
        result['pre_enable_observer_shutdown']={
            'topic':map_observer_topic,
            'removed_subscription_count':len(map_observers),
            'remaining_subscription_count':sum(
                sub.topic_name==map_observer_topic for sub in node.subscriptions),
        }
        publishers=node.publisher_counts()
        if any(count!=1 for count in publishers.values()):
            raise RuntimeError('trial_requires_unique_native_publishers')
        result['publisher_counts_before_enable']=publishers
        stable_since=None;deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            rclpy.spin_once(node,timeout_sec=.03)
            if cancelled:raise RuntimeError('operator_cancelled_trial')
            if localization_tracking_current_epoch(node,epoch) and telemetry_sources_fresh(node.latest_bridge_detail or {}):
                if stable_since is None:stable_since=time.monotonic()
                if time.monotonic()-stable_since>=5:break
            else:stable_since=None
        if stable_since is None or time.monotonic()-stable_since<5:
            raise RuntimeError('trial_pre_enable_freshness_not_stable')
        enabled=call_enable(node,True);result['service_calls'].append({'enable':True,**enabled})
        if not enabled['accepted']:raise RuntimeError('offboard_enable_rejected:'+enabled['reason'])
        if not spin_until(node,lambda:node.bridge is not None and node.bridge.phase=='ACTIVE'
                          and node.bridge.armed and not node.bridge.landed,90,
                          abort_predicate=lambda:cancelled or not localization_tracking_current_epoch(node,epoch)):
            raise RuntimeError('trial_takeoff_did_not_reach_active')
        settled_since=None;settle_deadline=time.monotonic()+20
        settle_started=time.monotonic();settle_samples=[];last_settle_sample_us=None
        while time.monotonic()<settle_deadline:
            rclpy.spin_once(node,timeout_sec=.03)
            if cancelled or not localization_tracking_current_epoch(node,epoch):
                raise RuntimeError('trial_cancelled_or_localization_lost_before_motion')
            row=node.local_position_history[-1] if node.local_position_history else None
            if row is not None and row['timestamp_sample_us']!=last_settle_sample_us:
                settle_samples.append(row)
                last_settle_sample_us=row['timestamp_sample_us']
            settled=trial_takeoff_velocity_settled(row)
            if settled:
                if settled_since is None:settled_since=time.monotonic()
                if time.monotonic()-settled_since>=TRIAL_TAKEOFF_SETTLE_DURATION_S:break
            else:settled_since=None
        settle_elapsed=time.monotonic()-settle_started
        settle_duration=(0.0 if settled_since is None else time.monotonic()-settled_since)
        latest_settle_sample=settle_samples[-1] if settle_samples else None
        result['takeoff_settle']={
            'passed':settle_duration>=TRIAL_TAKEOFF_SETTLE_DURATION_S,
            'total_speed_limit_m_s':TRIAL_TAKEOFF_TOTAL_SPEED_LIMIT_M_S,
            'vertical_speed_limit_m_s':TRIAL_TAKEOFF_VERTICAL_SPEED_LIMIT_M_S,
            'required_stable_wall_s':TRIAL_TAKEOFF_SETTLE_DURATION_S,
            'observed_wait_wall_s':settle_elapsed,
            'stable_wall_s':settle_duration,
            'unique_px4_samples':len(settle_samples),
            'maximum_total_speed_m_s':max((math.sqrt(
                sample['vx']**2+sample['vy']**2+sample['vz']**2)
                for sample in settle_samples),default=None),
            'maximum_absolute_vertical_speed_m_s':max((abs(sample['vz'])
                for sample in settle_samples),default=None),
            'stable_since_wall_elapsed_s':(None if settled_since is None else
                settled_since-node.started_wall),
            'latest_px4_local_ned_velocity_m_s':(None if latest_settle_sample is None else
                [latest_settle_sample['vx'],latest_settle_sample['vy'],
                 latest_settle_sample['vz']]),
            'latest_timestamp_sample_us':(None if latest_settle_sample is None else
                latest_settle_sample['timestamp_sample_us']),
        }
        if settle_duration<TRIAL_TAKEOFF_SETTLE_DURATION_S:
            raise RuntimeError('trial_takeoff_hold_did_not_settle')
        initial,yaw=current_pose(node);node.trial_start=np.asarray(initial)
        node.trial_tube_forward_distance=float(limits['offset_enu_m'][0])
        result['airborne_origin_enu']=initial
        raw,meta=capture_snapshot(node,run,'n08-trial-airborne-map',epoch,map_id)
        capsule=certify_forward_trial_corridor(
            raw,initial,limits['offset_enu_m'],body,
            limits['tracking_margin_m'],limits['maximum_tracking_error_m'],
            limits['forward_stopping_extension_m'],yaw_rad=yaw,
            policy=policy,primitives=primitives)
        cancel_corridor={'passed':True,'required':args.trial_kind=='motion_cancel',
                         'reason':'not_required_for_terminal_stop'}
        if args.trial_kind=='motion_cancel':
            cancel_offset=np.asarray([limits['cancel_stop_distance_envelope_m'],0.0,0.0])
            cancel_corridor=certify_forward_trial_corridor(
                raw,initial,cancel_offset,body,limits['tracking_margin_m'],
                limits['maximum_tracking_error_m'],0.0,yaw_rad=yaw,
                policy=policy,primitives=primitives)
        result['airborne_corridor']={'map':meta,'capsule':capsule,
                                     'cancel_stop_envelope':cancel_corridor}
        if (not capsule['passed']
                or (args.trial_kind=='motion_cancel' and not cancel_corridor['passed'])):
            raise RuntimeError('actual_airborne_trial_corridor_not_clear:'+capsule['reason'])
        destination=np.asarray(initial)+limits['offset_enu_m']
        if args.completion_mode=='single_goal':
            candidate=certify_n08_landing_candidate(
                raw,meta,ground,home_pad['ground_plane'],destination[:2],yaw,1.0,
                load_policy(root),collision_primitives(root))
            result['destination_landing_pre_goal']=candidate
            (run/'n08-trial-destination-landing-pre-goal.json').write_text(
                json.dumps(candidate,indent=2)+'\n')
            if not candidate.get('accepted'):
                raise RuntimeError('destination_landing_pre_goal_refused:'+str(candidate.get('reason')))
        if not spin_until(node,lambda:localization_tracking_current_epoch(node,epoch),2):
            raise RuntimeError('localization_not_fresh_after_corridor_check')
        goal=NavigateToPose.Goal();goal.target.header.frame_id='odom_'+epoch;goal.target.header.stamp=node.odometry.header.stamp
        goal.target.pose.position.x,goal.target.pose.position.y,goal.target.pose.position.z=map(float,destination)
        goal.target.pose.orientation.z=math.sin(yaw/2);goal.target.pose.orientation.w=math.cos(yaw/2)
        node.goal_kind='forward';node.goal_anchor=np.asarray(initial,dtype=float)
        node.goal_yaw=yaw;node.goal_start_yaw=yaw
        goal.position_tolerance_m=float(profile['position_tolerance_m']);goal.yaw_tolerance_rad=float(profile['yaw_tolerance_rad'])
        goal.dwell_s=float(profile['dwell_s']);goal.timeout_s=float(profile['timeout_s'])
        result['goal']={'frame':'odom_'+epoch,'target_enu':destination.tolist(),'yaw_enu':yaw,
                        'position_tolerance_m':goal.position_tolerance_m,'yaw_tolerance_rad':goal.yaw_tolerance_rad,
                        'source_ns':int(goal.target.header.stamp.sec)*1000000000+int(goal.target.header.stamp.nanosec)}
        sent=node.action_client.send_goal_async(goal)
        if not spin_until(node,sent.done,4):raise RuntimeError('goal_response_timeout')
        handle=sent.result()
        if handle is None or not handle.accepted:raise RuntimeError('trial_goal_rejected')
        node.goal_id=bytes(handle.goal_id.uuid).hex();result['goal_id']=node.goal_id
        if node.goal_id in node.splines:node.check_spline(node.splines[node.goal_id])
        result['action_goal_sent']=True;result['goal_start_sim_ns']=node.clock_ns
        result['goal_sent_wall_elapsed_s']=time.monotonic()-node.started_wall
        action=handle.get_result_async()
        if args.trial_kind=='motion_cancel':
            preflight=json.loads((run/'preflight.json').read_text())
            result['cancel_stop']=run_motion_cancel_stop(
                node,handle,action,node.goal_id,epoch,limits,
                args.cancel_speed_window,goal.timeout_s+10,
                float(preflight['rtf']))
            result['action_result']=result['cancel_stop']['action_result']
            result['action_success']=False
            result['action_canceled']=True
            result['goal_completed_source_ns']=result['cancel_stop']['stop_spline_completed_sim_ns']
            result['post_goal_hold_end_sim_ns']=result['cancel_stop']['post_stop_hold_end_sim_ns']
        else:
            if not spin_until(node,action.done,goal.timeout_s+10,
                              abort_predicate=lambda:cancelled or node.check_watchdog(epoch)):
                raise RuntimeError(node.watchdog_fault or 'operator_cancelled_or_trial_action_timeout')
            wrapped=action.result();nav=wrapped.result
            result['action_result']={'status':int(wrapped.status),'success':bool(nav.success),
                                      'outcome':nav.outcome,'reason':nav.reason}
            result['action_success']=bool(nav.success and nav.outcome=='succeeded')
            if not result['action_success']:raise RuntimeError('trial_action_failed:'+nav.reason)
            result['goal_completed_source_ns']=node.clock_ns
            hold_start=node.clock_ns;wall_end=time.monotonic()+20
            while node.clock_ns-hold_start<limits['post_goal_hold_sim_s']*1e9 and time.monotonic()<wall_end:
                rclpy.spin_once(node,timeout_sec=.03)
                if cancelled or node.check_watchdog(epoch):raise RuntimeError(node.watchdog_fault or 'operator_cancelled')
                if node.bridge.phase!='ACTIVE':raise RuntimeError('bridge_left_active_during_post_goal_hold')
            if node.clock_ns-hold_start<limits['post_goal_hold_sim_s']*1e9:raise RuntimeError('post_goal_hold_timeout')
            result['post_goal_hold_end_sim_ns']=node.clock_ns
        if args.trial_kind=='terminal_stop' and not any(
                row['goal_id']==node.goal_id for row in node.validated_splines):
            raise RuntimeError('live_trial_spline_certificate_not_observed')
        if args.completion_mode=='single_goal':
            current,current_yaw=current_pose(node)
            landing_map,landing_meta=capture_snapshot(
                node,run,'n08-trial-destination-landing-map',epoch,map_id)
            candidate=certify_n08_landing_candidate(
                landing_map,landing_meta,ground,home_pad['ground_plane'],
                np.asarray(current)[:2],current_yaw,
                float(current[2])-float(ground['center_xyz_m'][2]),
                load_policy(root),collision_primitives(root))
            result['destination_landing_final']=candidate
            (run/'n08-trial-destination-landing-final.json').write_text(
                json.dumps(candidate,indent=2)+'\n')
            if not candidate.get('accepted'):
                raise _DestinationHoldPending(
                    'destination_landing_final_refused:'+str(candidate.get('reason')))
            result['destination_landing_command']={
                'issued_after_single_goal_completion':args.trial_kind=='terminal_stop',
                'issued_after_certified_cancel_stop':args.trial_kind=='motion_cancel',
                'method':'uav_px4_bridge normal landing request at the checked destination',
                'landing_pose_enu_m':candidate['landing_pose']['center_xyz_m'],
            }
            disabled=call_enable(node,False)
            result['service_calls'].append({'enable':False,**disabled})
            if not disabled['accepted']:
                raise RuntimeError('destination_landing_request_rejected:'+disabled['reason'])
            result['landed_and_disarmed']=spin_until(
                node,lambda:node.bridge is not None and node.bridge.phase=='LANDED'
                and node.bridge.landed and not node.bridge.armed,45)
            if not result['landed_and_disarmed']:
                raise RuntimeError('destination_landed_disarmed_not_observed')
            result['return_action_sent']=False
            result['result']='PASS'
            raise _SingleGoalComplete()
        # Reorient the front camera before returning. If the first turn volume
        # is unknown behind the current heading, one separately admitted EGO
        # forward positioning goal may move the stationary-turn point into a
        # known-free volume. No reverse translation is allowed.
        turn_position,turn_start_yaw=current_pose(node)
        turn_anchor=np.asarray(turn_position,dtype=float)
        pre_turn_map,pre_turn_meta=capture_snapshot(node,run,'n08-trial-pre-turn-map',
                                                    epoch,map_id)
        turn_position_tolerance=.05
        turn_radius=body+limits['tracking_margin_m']+turn_position_tolerance
        turn_sweep=raw_sphere_query(pre_turn_map,turn_anchor,turn_radius)
        initial_turn_precheck={
            'map':pre_turn_meta,'center_xyz_m':turn_anchor.tolist(),
            'radius_m':turn_radius,'query':turn_sweep,
            'strategy':'stationary 180-degree yaw before any return translation'}
        result['yaw_reorientation_initial_precheck']=initial_turn_precheck
        result['yaw_reorientation_precheck']=initial_turn_precheck
        applied_turn_approach=0.0
        if turn_sweep.get('accepted') and turn_sweep.get('reason')=='unknown':
            approach_distance=limits['turn_approach_distance_m']
            if approach_distance<=0:
                raise RuntimeError('yaw_reorientation_hold_volume_not_known_free:unknown')
            approach=certify_trial_turn_approach(
                pre_turn_map,turn_anchor,turn_start_yaw,approach_distance,body,
                limits['tracking_margin_m'],turn_radius)
            result['turn_approach_admission']={'map':pre_turn_meta,**approach}
            if not approach['passed']:
                raise RuntimeError('turn_approach_capsule_or_candidate_hold_not_known_free')
            approach_start=turn_anchor.copy()
            approach_target=np.asarray(approach['candidate_turn_center_xyz_m'],dtype=float)
            approach_goal=NavigateToPose.Goal()
            approach_goal.target.header.frame_id='odom_'+epoch
            approach_goal.target.header.stamp=node.odometry.header.stamp
            approach_goal.target.pose.position.x,approach_goal.target.pose.position.y,approach_goal.target.pose.position.z=map(float,approach_target)
            approach_goal.target.pose.orientation.z=math.sin(turn_start_yaw/2)
            approach_goal.target.pose.orientation.w=math.cos(turn_start_yaw/2)
            approach_goal.position_tolerance_m=.02
            approach_goal.yaw_tolerance_rad=.1
            approach_goal.dwell_s=1.
            approach_goal.timeout_s=30.
            node.goal_kind='forward_positioning'
            node.goal_anchor=approach_start
            node.goal_yaw=turn_start_yaw
            node.goal_start_yaw=turn_start_yaw
            node.trial_tube_forward_distance=(
                float(limits['offset_enu_m'][0])+approach_distance)
            sent=node.action_client.send_goal_async(approach_goal)
            if not spin_until(node,sent.done,4):
                raise RuntimeError('turn_approach_goal_response_timeout')
            handle=sent.result()
            if handle is None or not handle.accepted:
                raise RuntimeError('turn_approach_goal_rejected')
            approach_goal_id=bytes(handle.goal_id.uuid).hex()
            node.goal_id=approach_goal_id
            if approach_goal_id in node.splines:
                node.check_spline(node.splines[approach_goal_id])
            result['turn_approach_goal']={
                'goal_id':approach_goal_id,'start_xyz_m':approach_start.tolist(),
                'target_xyz_m':approach_target.tolist(),'yaw_enu':turn_start_yaw,
                'distance_m':approach_distance,
                'position_tolerance_m':approach_goal.position_tolerance_m,
                'timeout_s':approach_goal.timeout_s,
                'reference_tube_forward_distance_m':node.trial_tube_forward_distance}
            approach_action=handle.get_result_async()
            action=approach_action
            if not spin_until(node,approach_action.done,approach_goal.timeout_s+10,
                              abort_predicate=lambda:cancelled or node.check_watchdog(epoch)):
                raise RuntimeError(node.watchdog_fault or 'turn_approach_goal_timeout')
            approach_nav=approach_action.result().result
            result['turn_approach_action_result']={
                'success':bool(approach_nav.success),'outcome':approach_nav.outcome,
                'reason':approach_nav.reason}
            if not (approach_nav.success and approach_nav.outcome=='succeeded'):
                raise RuntimeError('turn_approach_goal_failed:'+approach_nav.reason)
            if not any(row['goal_id']==approach_goal_id
                       for row in node.validated_splines):
                raise RuntimeError('live_turn_approach_spline_certificate_not_observed')
            approached_position,approached_yaw=current_pose(node)
            approach_delta=np.asarray(approached_position)-approach_start
            heading=np.asarray([math.cos(turn_start_yaw),math.sin(turn_start_yaw)])
            forward_progress=float(np.dot(approach_delta[:2],heading))
            lateral_progress=float(np.dot(approach_delta[:2],
                                          [-heading[1],heading[0]]))
            approach_position_error=float(np.linalg.norm(
                np.asarray(approached_position)-approach_target))
            approach_yaw_error=abs(math.atan2(math.sin(approached_yaw-turn_start_yaw),
                                               math.cos(approached_yaw-turn_start_yaw)))
            result['turn_approach_observed']={
                'position_xyz_m':approached_position,'position_error_m':approach_position_error,
                'forward_progress_m':forward_progress,'lateral_progress_m':lateral_progress,
                'yaw_enu':approached_yaw,'yaw_error_rad':approach_yaw_error}
            if (approach_position_error>approach_goal.position_tolerance_m+.005
                    or forward_progress<approach_distance-approach_goal.position_tolerance_m-.005
                    or abs(lateral_progress)>.05 or approach_yaw_error>.1):
                raise RuntimeError('turn_approach_endpoint_outside_tolerance')
            applied_turn_approach=approach_distance
            turn_position,turn_start_yaw=current_pose(node)
            turn_anchor=np.asarray(turn_position,dtype=float)
            pre_turn_map,pre_turn_meta=capture_snapshot(
                node,run,'n08-trial-pre-turn-map-after-positioning',epoch,map_id)
            turn_sweep=raw_sphere_query(pre_turn_map,turn_anchor,turn_radius)
            result['yaw_reorientation_precheck']={
                'map':pre_turn_meta,'center_xyz_m':turn_anchor.tolist(),
                'radius_m':turn_radius,'query':turn_sweep,
                'strategy':'stationary 180-degree yaw after a certified forward EGO positioning goal'}
        if not turn_sweep.get('accepted') or turn_sweep.get('reason')!='free':
            raise RuntimeError('yaw_reorientation_hold_volume_not_known_free:'+str(turn_sweep.get('reason')))
        turn_target_yaw=math.atan2(math.sin(turn_start_yaw+math.pi),
                                   math.cos(turn_start_yaw+math.pi))
        turn=NavigateToPose.Goal();turn.target.header.frame_id='odom_'+epoch
        turn.target.header.stamp=node.odometry.header.stamp
        turn.target.pose.position.x,turn.target.pose.position.y,turn.target.pose.position.z=map(float,turn_anchor)
        turn.target.pose.orientation.z=math.sin(turn_target_yaw/2)
        turn.target.pose.orientation.w=math.cos(turn_target_yaw/2)
        turn.position_tolerance_m=turn_position_tolerance;turn.yaw_tolerance_rad=.1
        turn.dwell_s=2.;turn.timeout_s=60.
        node.goal_kind='turn_in_place';node.goal_anchor=turn_anchor
        node.goal_yaw=turn_target_yaw;node.goal_start_yaw=turn_start_yaw
        handle=None;action=None
        sent=node.action_client.send_goal_async(turn)
        if not spin_until(node,sent.done,4):raise RuntimeError('yaw_turn_goal_response_timeout')
        handle=sent.result()
        if handle is None or not handle.accepted:raise RuntimeError('yaw_turn_goal_rejected')
        turn_goal_id=bytes(handle.goal_id.uuid).hex();node.goal_id=turn_goal_id
        if turn_goal_id in node.splines:node.check_spline(node.splines[turn_goal_id])
        result['yaw_turn_goal']={'goal_id':turn_goal_id,'position_enu':turn_anchor.tolist(),
                                 'start_yaw_enu':turn_start_yaw,
                                 'target_yaw_enu':turn_target_yaw,
                                 'position_tolerance_m':turn.position_tolerance_m,
                                 'yaw_tolerance_rad':turn.yaw_tolerance_rad,
                                 'start_sim_ns':node.clock_ns}
        turn_action=handle.get_result_async()
        action=turn_action
        if not spin_until(node,turn_action.done,turn.timeout_s+10,
                          abort_predicate=lambda:cancelled or node.check_watchdog(epoch)):
            raise RuntimeError(node.watchdog_fault or 'yaw_turn_timeout_or_cancelled')
        turn_nav=turn_action.result().result
        result['yaw_turn_result']={'success':bool(turn_nav.success),
                                   'outcome':turn_nav.outcome,'reason':turn_nav.reason}
        if not (turn_nav.success and turn_nav.outcome=='succeeded'):
            raise RuntimeError('yaw_reorientation_failed:'+turn_nav.reason)
        if not any(row['goal_id']==turn_goal_id for row in node.validated_splines):
            raise RuntimeError('live_yaw_turn_spline_certificate_not_observed')
        turned_position,turned_yaw=current_pose(node)
        turn_position_error=float(np.linalg.norm(np.asarray(turned_position)-turn_anchor))
        turn_yaw_error=abs(math.atan2(math.sin(turned_yaw-turn_target_yaw),
                                      math.cos(turned_yaw-turn_target_yaw)))
        result['yaw_turn_observed']={'position_enu':turned_position,
                                     'yaw_enu':turned_yaw,
                                     'position_change_m':turn_position_error,
                                     'absolute_yaw_error_rad':turn_yaw_error,
                                     'end_sim_ns':node.clock_ns}
        if turn_position_error>.05 or turn_yaw_error>.1:
            raise RuntimeError('yaw_turn_final_pose_outside_tolerance')
        # Require a newer fused view after the camera has turned before asking
        # EGO to plan the return through the previously unknown rear corridor.
        stamp=lambda value:int(value.sec)*1000000000+int(value.nanosec)
        fresh_view=spin_until(node,lambda:(node.map_status is not None
            and node.map_status.epoch==epoch and node.map_status.map_id==map_id
            and stamp(node.map_status.last_depth_source_stamp)>pre_turn_meta['last_depth_source_stamp_ns']
            and stamp(node.map_status.last_occupancy_stamp)>pre_turn_meta['last_fusion_stamp_ns']
            and node.clock_ns-stamp(node.map_status.last_occupancy_stamp)<=400000000),4.)
        if not fresh_view:raise RuntimeError('no_fresh_map_update_after_yaw_reorientation')
        raw,meta=capture_snapshot(node,run,'n08-trial-forward-return-map',epoch,map_id)
        home_position=np.asarray(initial,dtype=float)
        return_offset=home_position-np.asarray(turned_position,dtype=float)
        max_return_distance=(float(np.linalg.norm(limits['offset_enu_m']))
                             +applied_turn_approach+.15)
        if (not np.isfinite(return_offset).all() or np.linalg.norm(return_offset)<.2
                or np.linalg.norm(return_offset)>max_return_distance
                or np.dot(return_offset[:2],
                          [math.cos(turned_yaw),math.sin(turned_yaw)])<=0):
            raise RuntimeError('return_direction_is_not_forward_in_reoriented_body_frame')
        return_corridor=certify_trial_capsule(raw,turned_position,
            return_offset.tolist(),body,limits['tracking_margin_m'],0.)
        result['forward_return_corridor']={'map':meta,'capsule':return_corridor,
            'max_return_distance_m':max_return_distance,
            'body_forward_dot_m':float(np.dot(return_offset[:2],
                                              [math.cos(turned_yaw),math.sin(turned_yaw)]))}
        if not return_corridor['passed']:
            raise RuntimeError('forward_return_corridor_not_known_free')
        # EGO now receives a home goal while the camera faces the route. This
        # makes the return a forward trajectory in body coordinates.
        home=NavigateToPose.Goal()
        home.target.header.frame_id='odom_'+epoch
        home.target.header.stamp=node.odometry.header.stamp
        home.target.pose.position.x,home.target.pose.position.y,home.target.pose.position.z=map(float,initial)
        home.target.pose.orientation.z=math.sin(turned_yaw/2);home.target.pose.orientation.w=math.cos(turned_yaw/2)
        home.position_tolerance_m=.05;home.yaw_tolerance_rad=goal.yaw_tolerance_rad
        home.dwell_s=2.;home.timeout_s=40.
        node.goal_kind='forward_return';node.goal_anchor=np.asarray(turned_position,dtype=float)
        node.goal_yaw=turned_yaw;node.goal_start_yaw=turned_yaw
        node.trial_tube_forward_distance=(
            float(limits['offset_enu_m'][0])+applied_turn_approach)
        handle=None;action=None
        sent=node.action_client.send_goal_async(home)
        if not spin_until(node,sent.done,4):raise RuntimeError('return_goal_response_timeout')
        handle=sent.result()
        if handle is None or not handle.accepted:raise RuntimeError('return_goal_rejected')
        result['return_action_sent']=True
        node.goal_id=bytes(handle.goal_id.uuid).hex()
        if node.goal_id in node.splines:node.check_spline(node.splines[node.goal_id])
        result['return_goal_id']=node.goal_id
        result['return_goal_start_sim_ns']=node.clock_ns
        action=handle.get_result_async()
        if not spin_until(node,action.done,50,
                          abort_predicate=lambda:cancelled or node.check_watchdog(epoch)):
            raise RuntimeError(node.watchdog_fault or 'return_goal_timeout')
        home_result=action.result().result
        result['return_action_result']={'success':bool(home_result.success),
                                        'outcome':home_result.outcome,'reason':home_result.reason}
        if not (home_result.success and home_result.outcome=='succeeded'):
            raise RuntimeError('return_to_n05_home_pad_failed:'+home_result.reason)
        if not any(row['goal_id']==node.goal_id for row in node.validated_splines):
            raise RuntimeError('live_forward_return_spline_certificate_not_observed')
        result['return_completed_sim_ns']=node.clock_ns
        result['return_pose_enu']=current_pose(node)[0]
        disabled=call_enable(node,False);result['service_calls'].append({'enable':False,**disabled})
        if not disabled['accepted']:raise RuntimeError('disable_offboard_rejected')
        result['landed_and_disarmed']=spin_until(node,lambda:node.bridge is not None and node.bridge.phase=='LANDED'
                                                and node.bridge.landed and not node.bridge.armed,45)
        if not result['landed_and_disarmed']:raise RuntimeError('trial_landed_disarmed_not_observed')
        result['result']='PASS'
    except _SingleGoalComplete:
        pass
    except _DestinationHoldPending as exc:
        result['failure']=str(exc)
        result['landed_and_disarmed']=False
        last_goal_command=next((row for row in reversed(node.position_commands)
                                if row.get('goal_id')==node.goal_id),None)
        result['destination_hold_preserved']=bool(
            node.bridge is not None and node.bridge.phase=='ACTIVE'
            and node.bridge.control_enabled and node.bridge.armed
                and not node.bridge.landed
                and (result.get('action_success') is True or result.get('cancel_stop') is not None)
            and last_goal_command is not None
            and last_goal_command.get('flag')==PositionCommand.TRAJECTORY_STATUS_COMPLETED
            and localization_tracking_current_epoch(node,epoch))
        result['cleanup_policy']='keep the completed-position hold; do not request descent without a current candidate landing certificate'
    except Exception as exc:
        result['failure']=str(exc)
        if handle is not None and action is not None and not action.done():
            try:
                request=handle.cancel_goal_async();spin_until(node,request.done,2)
            except Exception as error:result['cancel_error']=str(error)
        if node.bridge is not None and node.bridge.phase not in ('DISABLED','LANDED','LOCKED'):
            try:
                disabled=call_enable(node,False);result['service_calls'].append({'enable':False,**disabled})
                spin_until(node,lambda:node.bridge is not None and node.bridge.landed and not node.bridge.armed,45)
            except Exception as error:result['cleanup_error']=str(error)
        if node.bridge is not None:result['landed_and_disarmed']=bool(node.bridge.landed and not node.bridge.armed)
    finally:
        result.update(counts=dict(node.counts),localization_quality_history=node.localization_quality_history,
                      vins_quality_history=node.vins_quality_history,local_position_history=node.local_position_history,
                      position_command_history=node.position_commands,px4_trajectory_setpoint_observations=node.px4_setpoint_observations,
                      bridge_phases=node.bridge_phases,bridge_detail_history=node.bridge_detail_history,
                      latest_bridge_detail=node.latest_bridge_detail,vehicle_status_history=node.vehicle_status_history,
                      watchdog_events=node.watchdog_events,clock_regressions=node.clock_regressions,
                      yaw_tracking_history=node.yaw_tracking_history,
                      maximum_yaw_tracking_error_rad=node.maximum_yaw_tracking_error_rad,
                      live_spline_certificates=node.validated_splines,
                      live_spline_rejections=node.spline_rejections,
                      publisher_counts=node.publisher_counts(),stream_diagnostics=node.streams)
        if node.cancel_stop_trace is not None:
            result['cancel_stop_trace'] = node.cancel_stop_trace
        if node.bridge is not None:result['latest_bridge_status']={'phase':node.bridge.phase,'reason':node.bridge.reason,
                                                                'armed':bool(node.bridge.armed),'landed':bool(node.bridge.landed)}
        output.write_text(json.dumps(result,indent=2)+'\n');node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
    print(json.dumps({k:result.get(k) for k in ['result','failure','action_success','landed_and_disarmed']},ensure_ascii=False))
    return 0 if result['result']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
