#!/usr/bin/env python3
"""Hold the VIO bridge's current PX4 pose without sending a navigation goal."""

import argparse
import json
import math
from pathlib import Path
import time

import rclpy
from rosgraph_msgs.msg import Clock
from run_vio_ego_flight import (EgoFlightProbe, call_enable,
                                localization_tracking_current_epoch, spin_until,
                                telemetry_sources_fresh)
from uav_interfaces.msg import LocalizationStatus


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-root', default='.')
    parser.add_argument('--goal-config', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--hover-seconds', type=float, default=20.0)
    parser.add_argument('--precondition-timeout-s', type=float, default=60.0)
    parser.add_argument('--flight-timeout-s', type=float, default=60.0)
    parser.add_argument('--landing-timeout-s', type=float, default=35.0)
    parser.add_argument('--px4-fresh-stability-s', type=float, default=2.0)
    parser.add_argument('--hover-wall-timeout-s', type=float, default=300.0)
    args = parser.parse_args()
    if not math.isfinite(args.hover_seconds) or args.hover_seconds <= 0:
        raise SystemExit('--hover-seconds must be a finite positive value')
    if not math.isfinite(args.hover_wall_timeout_s) or args.hover_wall_timeout_s <= 0:
        raise SystemExit('--hover-wall-timeout-s must be a finite positive value')

    root = Path(args.project_root).resolve()
    goal_config = json.loads((root / args.goal_config).read_text())
    result = {
        'profile': 'vio_closed_loop',
        'run_mode': 'no_navigation_goal_bridge_hold',
        'control_owner': 'uav_px4_bridge only',
        'result': 'FAIL',
        'service_calls': [],
        'action_goal_sent': False,
        'action_success': False,
        'hover_target_source': 'PX4 local pose held by bridge while no EGO trajectory is active',
    }

    rclpy.init()
    node = EgoFlightProbe()
    node.clock_history = []
    node.clock_ns = None
    node.clock_regressions = 0

    def on_clock(msg):
        sim_ns = int(msg.clock.sec) * 1_000_000_000 + int(msg.clock.nanosec)
        if node.clock_ns is not None and sim_ns < node.clock_ns:
            node.clock_regressions += 1
        node.clock_ns = sim_ns
        node.clock_history.append({
            'wall_elapsed_s': time.monotonic() - node.started_wall,
            'sim_time_ns': sim_ns,
        })

    node.create_subscription(Clock, '/clock', on_clock, node.sensor_qos)
    hover_history_start = None
    try:
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
            and max(node.map_point_counts) >= int(goal_config['minimum_occupancy_points'])
        ), args.precondition_timeout_s)
        result['preconditions_ready'] = ready
        result['localization_epoch'] = node.localization.epoch if node.localization else ''
        result['map_max_point_count_before_enable'] = max(node.map_point_counts, default=0)
        if not ready:
            raise TimeoutError('vio_bridge_map_preconditions_not_ready')
        if node.odometry.header.frame_id != f'odom_{node.localization.epoch}':
            raise RuntimeError('vio_epoch_frame_mismatch')

        stability_start = None
        stable_deadline = time.monotonic() + args.precondition_timeout_s
        while rclpy.ok() and time.monotonic() < stable_deadline:
            rclpy.spin_once(node, timeout_sec=0.05)
            now = time.monotonic()
            if (telemetry_sources_fresh(node.latest_bridge_detail or {})
                    and localization_tracking_current_epoch(node, result['localization_epoch'])):
                if stability_start is None:
                    stability_start = now
                if now - stability_start >= args.px4_fresh_stability_s:
                    break
            else:
                stability_start = None
        stable = (
            stability_start is not None
            and time.monotonic() - stability_start >= args.px4_fresh_stability_s
            and localization_tracking_current_epoch(node, result['localization_epoch'])
            and telemetry_sources_fresh(node.latest_bridge_detail or {})
        )
        result['px4_telemetry_stability_required_s'] = args.px4_fresh_stability_s
        result['px4_telemetry_stability_passed'] = stable
        result['localization_tracking_stability_passed'] = stable
        result['px4_telemetry_detail_at_enable'] = node.latest_bridge_detail
        if not stable:
            raise TimeoutError('localization_or_px4_freshness_not_stable_before_enable')

        enabled = call_enable(node, True)
        result['service_calls'].append({'enable': True, **enabled})
        if not enabled['accepted']:
            raise RuntimeError('offboard_enable_rejected:' + enabled['reason'])
        active = spin_until(node, lambda: (
            node.bridge is not None and node.bridge.phase == 'ACTIVE'
            and node.bridge.armed and not node.bridge.landed
            and localization_tracking_current_epoch(node, result['localization_epoch'])
        ), args.flight_timeout_s, abort_predicate=lambda: not localization_tracking_current_epoch(
            node, result['localization_epoch']))
        result['takeoff_active_observed'] = active
        if not active:
            raise RuntimeError('localization_lost_or_bridge_failed_during_takeoff')

        clock_ready = spin_until(node, lambda: node.clock_ns is not None,
                                 min(args.precondition_timeout_s, 10.0))
        if not clock_ready:
            raise TimeoutError('simulation_clock_unavailable_before_hover')
        hover_history_start = len(node.local_position_history)
        hold_start = time.monotonic()
        hold_start_sim_ns = node.clock_ns
        last_clock_wall = hold_start
        clock_stalled = False
        while (rclpy.ok()
               and node.clock_ns is not None
               and (node.clock_ns - hold_start_sim_ns) < args.hover_seconds * 1e9
               and time.monotonic() - hold_start < args.hover_wall_timeout_s):
            rclpy.spin_once(node, timeout_sec=0.05)
            now = time.monotonic()
            if (node.clock_history
                    and node.clock_history[-1]['wall_elapsed_s'] > last_clock_wall - node.started_wall):
                last_clock_wall = node.started_wall + node.clock_history[-1]['wall_elapsed_s']
            elif now - last_clock_wall > 5.0:
                clock_stalled = True
                break
            bridge = node.bridge
            if bridge is None or bridge.phase != 'ACTIVE' or not bridge.armed:
                break
            if not localization_tracking_current_epoch(node, result['localization_epoch']):
                break
            if node.clock_regressions:
                break
        hover_end = time.monotonic()
        hold_end_sim_ns = node.clock_ns
        result['hover_start_wall_elapsed_s'] = hold_start - node.started_wall
        result['hover_end_wall_elapsed_s'] = hover_end - node.started_wall
        result['hover_duration_wall_s'] = hover_end - hold_start
        result['hover_start_sim_time_ns'] = hold_start_sim_ns
        result['hover_end_sim_time_ns'] = hold_end_sim_ns
        result['hover_duration_sim_s'] = (
            (hold_end_sim_ns - hold_start_sim_ns) / 1e9
            if hold_end_sim_ns is not None else None)
        result['hover_requested_sim_s'] = args.hover_seconds
        result['hover_wall_timeout_s'] = args.hover_wall_timeout_s
        result['hover_clock_stalled'] = clock_stalled
        result['clock_regressions'] = node.clock_regressions
        result['hover_local_position_sample_start'] = hover_history_start
        result['hover_local_position_sample_end'] = len(node.local_position_history)
        result['hover_local_position_history'] = node.local_position_history[hover_history_start:]
        result['hover_position_command_count'] = len(node.position_commands)
        result['hover_bridge_status_at_end'] = (
            {'phase': node.bridge.phase, 'reason': node.bridge.reason,
             'armed': bool(node.bridge.armed), 'landed': bool(node.bridge.landed)}
            if node.bridge is not None else None)
        result['hover_completed_without_quality_abort'] = (
            result['hover_duration_sim_s'] is not None
            and result['hover_duration_sim_s'] >= args.hover_seconds
            and not clock_stalled and node.clock_regressions == 0
            and node.bridge is not None
            and node.bridge.phase == 'ACTIVE' and node.bridge.armed
            and localization_tracking_current_epoch(node, result['localization_epoch']))

        if (node.bridge is not None and node.bridge.armed
                and node.bridge.phase in ('TAKEOFF', 'ACTIVE')):
            disabled = call_enable(node, False)
            result['service_calls'].append({'enable': False, **disabled})
            if not disabled['accepted']:
                raise RuntimeError('bridge_hover_disable_rejected:' + disabled['reason'])

        landed = spin_until(node, lambda: (
            node.bridge is not None and node.bridge.phase == 'LANDED'
            and node.bridge.landed and not node.bridge.armed
        ), args.landing_timeout_s)
        result['landed_and_disarmed'] = landed
        if not landed:
            raise TimeoutError('landed_disarmed_not_observed_after_hover')
        if result['hover_completed_without_quality_abort']:
            result['result'] = 'PASS'
        else:
            result['result'] = 'SAFETY_ABORT'
            result['failure'] = (node.bridge.reason if node.bridge is not None
                                 else 'hover_did_not_complete')
    except Exception as exc:
        result['failure'] = str(exc)
        if (node.bridge is not None and node.bridge.armed
                and node.bridge.phase == 'ACTIVE'):
            try:
                disabled = call_enable(node, False)
                result['service_calls'].append({'enable': False, **disabled})
            except Exception as land_exc:
                result['landing_error'] = str(land_exc)
        if node.bridge is not None and node.bridge.phase in ('TAKEOFF', 'ACTIVE', 'LANDING'):
            result['landed_and_disarmed'] = spin_until(node, lambda: (
                node.bridge is not None and node.bridge.phase == 'LANDED'
                and node.bridge.landed and not node.bridge.armed
            ), args.landing_timeout_s)
    finally:
        result['wall_monotonic_origin_s'] = node.started_wall
        result['counts'] = dict(node.counts)
        result['stream_diagnostics'] = node.streams
        result['localization_quality_history'] = node.localization_quality_history
        result['vins_quality_history'] = node.vins_quality_history
        result['vins_telemetry_topic'] = node.vins_telemetry_topic
        result['local_position_history'] = node.local_position_history
        result['map_point_count_max'] = max(node.map_point_counts, default=0)
        result['position_command_history'] = node.position_commands
        result['px4_trajectory_setpoint_observations'] = node.px4_setpoint_observations
        result['bridge_phases'] = node.bridge_phases
        result['bridge_detail_history'] = node.bridge_detail_history
        result['timesync_history'] = node.timesync_history
        result['simulation_clock_history'] = node.clock_history
        result['simulation_clock_regressions'] = node.clock_regressions
        result['latest_bridge_status'] = ({
            'phase': node.bridge.phase, 'reason': node.bridge.reason,
            'armed': bool(node.bridge.armed), 'landed': bool(node.bridge.landed),
            'ready': bool(node.bridge.ready),
        } if node.bridge is not None else None)
        result['latest_vehicle_status'] = node.vehicle_status
        result['vehicle_status_history'] = node.vehicle_status_history
        result['latest_localization_status'] = ({
            'epoch': node.localization.epoch, 'state': int(node.localization.state),
            'valid': bool(node.localization.valid), 'reason': node.localization.reason,
            'accepted_optimized': int(node.localization.accepted_optimized),
            'accepted_propagated': int(node.localization.accepted_propagated),
        } if node.localization is not None else None)
        result['publisher_counts'] = node.publisher_counts()
        result['action_goal_sent'] = False
        result['action_success'] = False
        Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n',
                                     encoding='utf-8')
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    print(json.dumps({k: result.get(k) for k in (
        'result','failure','preconditions_ready','takeoff_active_observed',
        'hover_duration_sim_s','hover_duration_wall_s','hover_completed_without_quality_abort',
        'landed_and_disarmed','action_goal_sent','latest_bridge_status')},
        indent=2, sort_keys=True))
    if result['result'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
