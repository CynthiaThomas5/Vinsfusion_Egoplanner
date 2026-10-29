#!/usr/bin/env python3
"""Compute one EGO trajectory, cancel it, and prove the PX4 bridge stayed on hold."""
import argparse
import json
import math
from pathlib import Path
import time

from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
import rclpy
from rosgraph_msgs.msg import Clock
from uav_interfaces.action import NavigateToPose
from uav_interfaces.msg import LocalizationStatus, PositionCommand

from flight_profile import legs
from run_vio_ego_flight import (EgoFlightProbe, call_enable,
                                localization_tracking_current_epoch, spin_until,
                                telemetry_sources_fresh)
from n08_compute_only_record import summarize_navigation_action_result


def endpoint_name(info):
    namespace = str(info.node_namespace or '/').rstrip('/')
    return f'{namespace}/{info.node_name}'.replace('//', '/')


def n08_mode_paths(root, output):
    run_id = Path(output).resolve().parent.name
    return root / 'artifacts/runs' / f'{run_id}-stack' / 'n08-runtime-mode.json'


def current_pose(node):
    pose = node.odometry.pose.pose
    q = pose.orientation
    yaw = math.atan2(2.0 * (q.w*q.z + q.x*q.y),
                     1.0 - 2.0 * (q.y*q.y + q.z*q.z))
    return ([float(pose.position.x), float(pose.position.y), float(pose.position.z)], yaw)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', default='.')
    parser.add_argument('--goal-config', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--precondition-timeout-s', type=float, default=60.0)
    parser.add_argument('--flight-timeout-s', type=float, default=60.0)
    parser.add_argument('--landing-timeout-s', type=float, default=45.0)
    parser.add_argument('--trajectory-timeout-s', type=float, default=20.0)
    parser.add_argument('--hold-after-cancel-s', type=float, default=2.0)
    parser.add_argument('--hold-wall-timeout-s', type=float, default=60.0)
    parser.add_argument('--px4-fresh-stability-s', type=float, default=5.0)
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    output = Path(args.output).resolve()
    run_dir = output.parent
    mode_path = n08_mode_paths(root, output)
    result = {
        'schema': 'n08-compute-only-run/v1',
        'mode': 'compute_only',
        'scope': 'EGO computes and publishes a trajectory while the bridge input is isolated; no intentional horizontal control command reaches PX4',
        'control_owner': 'uav_px4_bridge only',
        'debug_truth_used_for_control': False,
        'result': 'FAIL',
        'action_goal_sent': False,
        'trajectory_ready_seen': False,
        'cancel_accepted': False,
        'bridge_hold_confirmed_after_cancel': False,
        'landed_and_disarmed': False,
    }
    mode = json.loads(mode_path.read_text()) if mode_path.is_file() else {}
    result['launch_mode_record'] = mode
    if mode.get('mode') != 'compute_only':
        raise SystemExit(f'expected compute_only launch mode in {mode_path}')

    profile = json.loads((root / args.goal_config).read_text())
    mission_legs = legs(profile)
    if len(mission_legs) != 1:
        raise SystemExit('N08 compute-only diagnostic accepts exactly one goal')
    live_n05 = run_dir / 'n05-current-area/n05-live-entry-check.json'
    offline_n05 = run_dir / 'n05-current-area/n05-offline-entry-replay.json'
    if not live_n05.is_file() or not offline_n05.is_file():
        raise SystemExit('fresh N05 online and offline current-area gate reports are required')
    live = json.loads(live_n05.read_text())
    offline = json.loads(offline_n05.read_text())
    if not (live.get('accepted') is True
            and live.get('online_offline_result_identical') is True
            and offline.get('matches_online_result') is True):
        raise SystemExit('fresh N05 current-area admission or replay did not pass')
    result['n05_current_area'] = {
        'accepted': True,
        'epoch': live['identity']['epoch'],
        'map_id': live['identity']['map_id'],
        'online_offline_identical': True,
    }
    preflight_path = run_dir / 'preflight.json'
    if not preflight_path.is_file() or not json.loads(preflight_path.read_text()).get('passed'):
        raise SystemExit('fresh read-only bridge/localization preflight did not pass')

    clock_state = {'sim_ns': None, 'last_wall': None, 'regressions': 0}
    rclpy.init()
    node = EgoFlightProbe()

    def on_clock(msg):
        now_ns = int(msg.clock.sec) * 1_000_000_000 + int(msg.clock.nanosec)
        if clock_state['sim_ns'] is not None and now_ns < clock_state['sim_ns']:
            clock_state['regressions'] += 1
        clock_state['sim_ns'] = now_ns
        clock_state['last_wall'] = time.monotonic()

    node.create_subscription(Clock, '/clock', on_clock, node.sensor_qos)
    handle = None
    action_result = None
    try:
        graph_deadline = time.monotonic() + 15.0
        bridge_name = None
        while time.monotonic() < graph_deadline:
            rclpy.spin_once(node, timeout_sec=0.05)
            direct = {endpoint_name(info)
                      for info in node.get_subscriptions_info_by_topic('/position_cmd')}
            isolated = {endpoint_name(info)
                        for info in node.get_subscriptions_info_by_topic(
                            '/n08/compute_only_position_cmd')}
            bridge_name = next((name for name in isolated
                                if name.rsplit('/', 1)[-1] == 'uav_px4_bridge'), None)
            if bridge_name and not any(name.rsplit('/', 1)[-1] == 'uav_px4_bridge'
                                       for name in direct):
                result['compute_only_graph'] = {
                    'bridge_node': bridge_name,
                    'bridge_subscribed_to_position_cmd': False,
                    'bridge_subscribed_to_isolated_input': True,
                    'direct_position_cmd_subscribers': sorted(direct),
                    'isolated_input_subscribers': sorted(isolated),
                }
                break
        if 'compute_only_graph' not in result:
            raise RuntimeError('bridge_position_command_remap_not_observed')

        if not node.action_client.wait_for_server(timeout_sec=8.0):
            raise TimeoutError('navigation_action_server_unavailable')
        ready = spin_until(node, lambda: (
            node.localization is not None
            and node.localization.valid
            and node.localization.state == LocalizationStatus.TRACKING
            and node.odometry is not None
            and node.bridge is not None
            and node.bridge.phase == 'DISABLED'
            and node.bridge.landed and not node.bridge.armed
            and node.bridge.local_position_valid
            and node.bridge.ev_position_fused and node.bridge.ev_yaw_fused
            and not node.bridge.gnss_aiding_active
            and bool(node.map_point_counts)
            and max(node.map_point_counts) >= int(profile['minimum_occupancy_points'])
        ), args.precondition_timeout_s)
        if not ready:
            localization = node.localization
            odometry = node.odometry
            bridge = node.bridge
            vins_history = node.vins_quality_history
            result['precondition_diagnostics'] = {
                'timeout_s': args.precondition_timeout_s,
                'map_point_count_samples': len(node.map_point_counts),
                'map_point_count_max': max(node.map_point_counts, default=0),
                'latest_localization': ({
                    'epoch': localization.epoch, 'state': int(localization.state),
                    'valid': bool(localization.valid), 'reason': localization.reason,
                    'header_stamp_ns': (int(localization.header.stamp.sec) * 1_000_000_000
                                        + int(localization.header.stamp.nanosec)),
                    'source_stamp_ns': (int(localization.source_stamp.sec) * 1_000_000_000
                                         + int(localization.source_stamp.nanosec)),
                    'accepted_optimized': int(localization.accepted_optimized),
                    'accepted_propagated': int(localization.accepted_propagated),
                } if localization is not None else None),
                'latest_odometry': ({
                    'frame_id': odometry.header.frame_id,
                    'stamp_ns': (int(odometry.header.stamp.sec) * 1_000_000_000
                                 + int(odometry.header.stamp.nanosec)),
                } if odometry is not None else None),
                'latest_bridge': ({
                    'phase': bridge.phase, 'reason': bridge.reason,
                    'armed': bool(bridge.armed), 'landed': bool(bridge.landed),
                    'local_position_valid': bool(bridge.local_position_valid),
                    'ev_position_fused': bool(bridge.ev_position_fused),
                    'ev_yaw_fused': bool(bridge.ev_yaw_fused),
                } if bridge is not None else None),
                'latest_bridge_detail': node.latest_bridge_detail,
                'vins_telemetry_topic': node.vins_telemetry_topic,
                'vins_telemetry_samples': len(vins_history),
                'vins_telemetry_first': vins_history[0] if vins_history else None,
                'vins_telemetry_last': vins_history[-1] if vins_history else None,
                'vins_telemetry_max_source_gap_s': max((
                    (vins_history[i]['stamp_ns'] - vins_history[i-1]['stamp_ns']) / 1e9
                    for i in range(1, len(vins_history))), default=None),
            }
            raise TimeoutError('vio_bridge_map_preconditions_not_ready')
        epoch = node.localization.epoch
        if node.odometry.header.frame_id != f'odom_{epoch}':
            raise RuntimeError('vio_epoch_frame_mismatch')

        stability_start = None
        stability_deadline = time.monotonic() + args.precondition_timeout_s
        while rclpy.ok() and time.monotonic() < stability_deadline:
            rclpy.spin_once(node, timeout_sec=0.05)
            now = time.monotonic()
            stable = (telemetry_sources_fresh(node.latest_bridge_detail or {})
                      and localization_tracking_current_epoch(node, epoch))
            if stable:
                if stability_start is None:
                    stability_start = now
                if now - stability_start >= args.px4_fresh_stability_s:
                    break
            else:
                stability_start = None
        if (stability_start is None
                or time.monotonic() - stability_start < args.px4_fresh_stability_s):
            raise TimeoutError('localization_or_px4_freshness_not_stable_before_enable')
        result['pre_enable_stability_s'] = time.monotonic() - stability_start

        enabled = call_enable(node, True)
        result['enable_offboard'] = enabled
        if not enabled['accepted']:
            raise RuntimeError('offboard_enable_rejected:' + enabled['reason'])
        active = spin_until(node, lambda: (
            node.bridge is not None and node.bridge.phase == 'ACTIVE'
            and node.bridge.armed and not node.bridge.landed
            and localization_tracking_current_epoch(node, epoch)
        ), args.flight_timeout_s, abort_predicate=lambda: not localization_tracking_current_epoch(node, epoch))
        if not active:
            raise TimeoutError('bridge_did_not_reach_active_after_takeoff')
        if clock_state['sim_ns'] is None:
            raise TimeoutError('simulation_clock_unavailable_after_takeoff')

        initial_position, initial_yaw = current_pose(node)
        goal_config = mission_legs[0]
        goal = NavigateToPose.Goal()
        goal.target.header.frame_id = f'odom_{epoch}'
        goal.target.header.stamp = node.odometry.header.stamp
        goal.target.pose.position.x = initial_position[0] + float(goal_config['target_offset_enu_m'][0])
        goal.target.pose.position.y = initial_position[1] + float(goal_config['target_offset_enu_m'][1])
        goal.target.pose.position.z = initial_position[2] + float(goal_config['target_offset_enu_m'][2])
        target_yaw = initial_yaw + float(goal_config.get('yaw_offset_rad', 0.0))
        goal.target.pose.orientation.z = math.sin(target_yaw / 2.0)
        goal.target.pose.orientation.w = math.cos(target_yaw / 2.0)
        goal.position_tolerance_m = float(goal_config['position_tolerance_m'])
        goal.yaw_tolerance_rad = float(goal_config['yaw_tolerance_rad'])
        goal.dwell_s = float(goal_config['dwell_s'])
        goal.timeout_s = float(goal_config['timeout_s'])
        sent = node.action_client.send_goal_async(goal)
        if not spin_until(node, sent.done, 5.0):
            raise TimeoutError('navigation_goal_response_timeout')
        handle = sent.result()
        if handle is None or not handle.accepted:
            raise RuntimeError('navigation_goal_rejected')
        result['action_goal_sent'] = True
        result['goal_id'] = bytes(handle.goal_id.uuid).hex()
        result['epoch'] = epoch
        result['goal'] = {
            'frame': goal.target.header.frame_id,
            'target_enu': [goal.target.pose.position.x,
                           goal.target.pose.position.y,
                           goal.target.pose.position.z],
            'yaw_enu': target_yaw,
            'position_tolerance_m': goal.position_tolerance_m,
            'yaw_tolerance_rad': goal.yaw_tolerance_rad,
            'timeout_s': goal.timeout_s,
        }
        action_result = handle.get_result_async()
        ready_deadline = min(args.trajectory_timeout_s, goal.timeout_s)

        def has_ready_trajectory():
            return any(
                item['goal_id'] == result['goal_id']
                and item['epoch'] == epoch
                and item['flag'] == PositionCommand.TRAJECTORY_STATUS_READY
                for item in node.position_commands)

        spin_until(node, lambda: has_ready_trajectory() or action_result.done(), ready_deadline,
                   abort_predicate=lambda: not localization_tracking_current_epoch(node, epoch))
        trajectory_ready = has_ready_trajectory()
        result['trajectory_ready_seen'] = trajectory_ready
        if action_result.done():
            terminal_key = ('action_terminal_result_before_cancel' if trajectory_ready
                            else 'action_terminal_result_before_ready')
            result[terminal_key] = summarize_navigation_action_result(action_result.result())
        if not result['trajectory_ready_seen']:
            terminal = result.get('action_terminal_result_before_ready') or {}
            if terminal:
                raise RuntimeError(
                    'navigation_action_terminal_before_ready:'
                    f"{terminal['outcome']}:{terminal['reason']}")
            raise TimeoutError('ego_ready_trajectory_not_observed')
        if action_result.done():
            raise RuntimeError('action_completed_before_compute_only_cancel')
        result['ready_position_command_samples'] = [item for item in node.position_commands
            if item['goal_id'] == result['goal_id'] and item['epoch'] == epoch
            and item['flag'] == PositionCommand.TRAJECTORY_STATUS_READY]
        publishers = node.get_publishers_info_by_topic('/position_cmd')
        result['position_command_publishers'] = [endpoint_name(info) for info in publishers]
        if len(publishers) != 1:
            raise RuntimeError('position_cmd_must_have_exactly_one_publisher')

        cancel_future = handle.cancel_goal_async()
        if not spin_until(node, cancel_future.done, 4.0):
            raise TimeoutError('compute_only_cancel_response_timeout')
        cancel_response = cancel_future.result()
        result['cancel_goal_count'] = len(cancel_response.goals_canceling)
        result['cancel_accepted'] = bool(cancel_response.goals_canceling)
        if not result['cancel_accepted']:
            raise RuntimeError('compute_only_cancel_rejected')
        if not spin_until(node, action_result.done, 5.0):
            raise TimeoutError('cancelled_action_result_timeout')
        wrapped = action_result.result()
        result['action_status_after_cancel'] = int(wrapped.status)
        result['action_terminal_result_after_cancel'] = summarize_navigation_action_result(wrapped)
        result['action_cancel_confirmed'] = wrapped.status == GoalStatus.STATUS_CANCELED
        if not result['action_cancel_confirmed']:
            raise RuntimeError('action_did_not_report_canceled')

        hold_start_ns = clock_state['sim_ns']
        hold_wall_start = time.monotonic()
        local_start = len(node.local_position_history)
        setpoint_start = len(node.px4_setpoint_observations)
        previous_clock_ns = hold_start_ns
        hold_failure = ''
        while (rclpy.ok()
               and clock_state['sim_ns'] is not None
               and (clock_state['sim_ns'] - hold_start_ns) < args.hold_after_cancel_s * 1e9
               and time.monotonic() - hold_wall_start < args.hold_wall_timeout_s):
            rclpy.spin_once(node, timeout_sec=0.05)
            now = time.monotonic()
            if clock_state['regressions']:
                hold_failure = 'simulation_clock_regressed'
                break
            if clock_state['sim_ns'] < previous_clock_ns:
                hold_failure = 'simulation_clock_regressed'
                break
            if (node.bridge is None or node.bridge.phase != 'ACTIVE'
                    or not node.bridge.armed or node.bridge.landed):
                hold_failure = 'bridge_left_active_hold'
                break
            if not localization_tracking_current_epoch(node, epoch):
                hold_failure = 'localization_not_tracking_during_hold'
                break
            if clock_state['last_wall'] is None or now - clock_state['last_wall'] > 1.0:
                hold_failure = 'simulation_clock_stalled_during_hold'
                break
            previous_clock_ns = clock_state['sim_ns']
        result['hold_after_cancel_sim_s'] = (
            (clock_state['sim_ns'] - hold_start_ns) / 1e9
            if clock_state['sim_ns'] is not None else None)
        result['hold_after_cancel_wall_s'] = time.monotonic() - hold_wall_start
        result['hold_after_cancel_failure'] = hold_failure
        result['local_position_during_hold'] = node.local_position_history[local_start:]
        result['px4_setpoints_during_hold'] = node.px4_setpoint_observations[setpoint_start:]
        result['bridge_hold_confirmed_after_cancel'] = bool(
            not hold_failure
            and result['hold_after_cancel_sim_s'] is not None
            and result['hold_after_cancel_sim_s'] >= args.hold_after_cancel_s)
        if not result['bridge_hold_confirmed_after_cancel']:
            raise RuntimeError(hold_failure or 'insufficient_post_cancel_hold_duration')

        disabled = call_enable(node, False)
        result['disable_offboard'] = disabled
        if not disabled['accepted']:
            raise RuntimeError('offboard_disable_rejected:' + disabled['reason'])
        result['landed_and_disarmed'] = spin_until(node, lambda: (
            node.bridge is not None and node.bridge.phase == 'LANDED'
            and node.bridge.landed and not node.bridge.armed
        ), args.landing_timeout_s)
        if not result['landed_and_disarmed']:
            raise TimeoutError('landed_disarmed_not_observed_after_compute_only')
        result['all_position_command_samples'] = node.position_commands
        result['all_bridge_phases'] = node.bridge_phases
        result['publisher_counts'] = node.publisher_counts()
        result['result'] = 'PASS'
    except Exception as exc:
        result['failure'] = str(exc)
        if (handle is not None and action_result is not None
                and not action_result.done()):
            try:
                failure_cancel = handle.cancel_goal_async()
                if spin_until(node, failure_cancel.done, 4.0):
                    response = failure_cancel.result()
                    result['failure_cancel_accepted'] = bool(response.goals_canceling)
                    if not action_result.done():
                        spin_until(node, action_result.done, 5.0)
                else:
                    result['failure_cancel_error'] = 'cancel_response_timeout'
                if action_result.done():
                    result['failure_action_terminal_result'] = summarize_navigation_action_result(
                        action_result.result())
            except Exception as cancel_exc:
                result['failure_cancel_error'] = str(cancel_exc)
        bridge = node.bridge
        if bridge is not None and bridge.phase not in ('DISABLED', 'LANDED', 'LOCKED'):
            try:
                disabled = call_enable(node, False)
                result['failure_disable_offboard'] = disabled
                result['landed_and_disarmed'] = spin_until(node, lambda: (
                    node.bridge is not None and node.bridge.phase == 'LANDED'
                    and node.bridge.landed and not node.bridge.armed
                ), args.landing_timeout_s)
            except Exception as cleanup_exc:
                result['safe_cleanup_error'] = str(cleanup_exc)
        if node.bridge is not None:
            result['landed_and_disarmed'] = bool(
                node.bridge.landed and not node.bridge.armed
                and node.bridge.phase in ('DISABLED', 'LANDED'))
            result['latest_bridge_status'] = {
                'phase': node.bridge.phase, 'reason': node.bridge.reason,
                'armed': bool(node.bridge.armed), 'landed': bool(node.bridge.landed),
            }
        result['all_position_command_samples'] = node.position_commands
        result['all_bridge_phases'] = node.bridge_phases
        result['publisher_counts'] = node.publisher_counts()
    finally:
        result['clock_regressions'] = clock_state['regressions']
        result['localization_quality_history'] = node.localization_quality_history
        result['vins_quality_history'] = node.vins_quality_history
        result['vins_telemetry_topic'] = node.vins_telemetry_topic
        if node.bridge is not None:
            result.setdefault('latest_bridge_status', {
                'phase': node.bridge.phase, 'reason': node.bridge.reason,
                'armed': bool(node.bridge.armed), 'landed': bool(node.bridge.landed),
            })
        output.parent.mkdir(parents=True, exist_ok=True)
        temp = output.with_suffix(output.suffix + '.tmp')
        temp.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        temp.replace(output)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    print(json.dumps({key: result.get(key) for key in (
        'result', 'failure', 'trajectory_ready_seen', 'cancel_accepted',
        'action_cancel_confirmed', 'bridge_hold_confirmed_after_cancel',
        'landed_and_disarmed')}, ensure_ascii=False, indent=2))
    return 0 if result['result'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
