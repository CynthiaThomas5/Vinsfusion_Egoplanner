#!/usr/bin/env python3
"""Read PX4 bridge, estimator, and control-topic state without publishing."""

import argparse
import json
import math
import time

import rclpy
from observer_window import install_observer_stop_handlers, restore_observer_stop_handlers
from px4_msgs.msg import (EstimatorStatusFlags, OffboardControlMode,
                          TimesyncStatus, TrajectorySetpoint, VehicleCommand,
                          VehicleCommandAck,
                          VehicleAttitude, VehicleLandDetected,
                          VehicleLocalPosition, VehicleOdometry, VehicleStatus)
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rosgraph_msgs.msg import Clock as ClockMessage
from std_msgs.msg import String
from uav_interfaces.msg import (NavigationCommand, PositionCommand,
                                Px4BridgeStatus, TrajectoryCancel)


class Probe(Node):
    def __init__(self, direct_sim_time=False, expected_goal_id='', expected_epoch=''):
        super().__init__('px4_bridge_live_probe')
        self.direct_sim_time = bool(direct_sim_time)
        self.expected_goal_id = str(expected_goal_id or '')
        self.expected_epoch = str(expected_epoch or '')
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        reliable = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        self.counts = {'bridge_status': 0, 'visual_odometry_input': 0,
                       'px4_status': 0, 'local_position': 0,
                       'timesync_status': 0,
                       'estimator_flags': 0, 'attitude': 0,
                       'land_detected': 0,
                       'control_mode': 0, 'trajectory_setpoint': 0,
                       'vehicle_command': 0}
        self.latest = {}
        self.started_mono = time.monotonic()
        self.latest_clock_ns = 0
        self.latest_clock_elapsed_wall_s = None
        self.latest_timesync_offset_us = None
        self.clock_samples = []
        self.timesync_samples = []
        self.px4_timestamp_samples = []
        self.bridge_status_samples = []
        self.bridge_detail_samples = []
        self.px4_status_samples = []
        self.land_detected_samples = []
        self.command_ack_samples = []
        self.control_topic_events = []
        self.planner_state_samples = []
        self.terminal_readback_samples = []
        self.terminal_state_first_wall_s = None
        self.terminal_state_violation_count = 0
        self._terminal_state_active = False
        self.receipt_last = {}
        self.receipt_gaps = {}
        self.bridge_reason_counts = {}
        self.bridge_state_counts = {
            'ready': 0, 'local_position_valid': 0,
            'ev_position_fused': 0, 'ev_yaw_fused': 0,
            'gnss_aiding_active': 0,
        }
        self.create_subscription(Px4BridgeStatus, '/uav_px4_bridge/status',
                                 self._bridge_status, reliable)
        self.create_subscription(String, '/uav_px4_bridge/status/detail',
                                 self._bridge_detail, reliable)
        self.create_subscription(ClockMessage, '/clock', self._on_clock_message, qos)
        self.create_subscription(VehicleOdometry, '/fmu/in/vehicle_visual_odometry',
                                 self._visual_odom, qos)
        self.create_subscription(VehicleStatus, '/fmu/out/vehicle_status_v1',
                                 self._vehicle_status, qos)
        self.create_subscription(VehicleLocalPosition, '/fmu/out/vehicle_local_position_v1',
                                 self._local_position, qos)
        self.create_subscription(TimesyncStatus, '/fmu/out/timesync_status',
                                 self._timesync_status, qos)
        self.create_subscription(EstimatorStatusFlags, '/fmu/out/estimator_status_flags',
                                 self._estimator, qos)
        self.create_subscription(VehicleAttitude, '/fmu/out/vehicle_attitude',
                                 self._attitude, qos)
        self.create_subscription(VehicleLandDetected, '/fmu/out/vehicle_land_detected',
                                 self._land_detected, qos)
        self.create_subscription(OffboardControlMode, '/fmu/in/offboard_control_mode',
                                 lambda _: self._control_event('control_mode'), qos)
        self.create_subscription(TrajectorySetpoint, '/fmu/in/trajectory_setpoint',
                                 lambda _: self._control_event('trajectory_setpoint'), qos)
        self.create_subscription(VehicleCommand, '/fmu/in/vehicle_command',
                                 lambda _: self._control_event('vehicle_command'), qos)
        self.create_subscription(VehicleCommandAck, '/fmu/out/vehicle_command_ack',
                                 self._command_ack, qos)
        self.create_subscription(NavigationCommand, '/navigation/ego_goal',
                                 self._navigation_goal, reliable)
        self.create_subscription(PositionCommand, '/position_cmd',
                                 self._position_command, qos)
        self.create_subscription(TrajectoryCancel, '/navigation/trajectory_cancel',
                                 self._trajectory_cancel, reliable)

    def _elapsed_wall_s(self):
        return time.monotonic() - self.started_mono

    def _count(self, key):
        self.counts[key] += 1

    def _control_event(self, key):
        self._count(key)
        self.control_topic_events.append({
            'elapsed_wall_s': self._elapsed_wall_s(), 'topic': key,
        })

    def _maybe_terminal_readback(self):
        bridge = self.latest.get('bridge') or {}
        px4 = self.latest.get('px4_status') or {}
        land = self.latest.get('land_detected') or {}
        available = bool(bridge and px4 and land)
        safe = (available and bridge.get('phase') == 'LANDED'
                and bridge.get('landed') is True
                and bridge.get('armed') is False
                and bridge.get('control_enabled') is False
                and px4.get('arming_state') == 1
                and land.get('landed') is True)
        elapsed = self._elapsed_wall_s()
        if safe and not self._terminal_state_active:
            self._terminal_state_active = True
            self.terminal_state_first_wall_s = elapsed
            self.terminal_readback_samples.append({
                'elapsed_wall_s': elapsed,
                'state': 'native_terminal_observed',
            })
        elif not safe and self._terminal_state_active:
            self._terminal_state_active = False
            self.terminal_state_violation_count += 1
            self.terminal_readback_samples.append({
                'elapsed_wall_s': elapsed,
                'state': 'terminal_state_left',
            })

    def _navigation_goal(self, msg):
        self.planner_state_samples.append({
            'kind': 'navigation_goal',
            'elapsed_wall_s': self._elapsed_wall_s(),
            'goal_id': str(msg.goal_id), 'epoch': str(msg.epoch),
            'map_id': str(msg.map_id),
            'source_stamp_ns': (int(msg.target.header.stamp.sec) * 1_000_000_000
                                + int(msg.target.header.stamp.nanosec)),
        })

    def _position_command(self, msg):
        self.planner_state_samples.append({
            'kind': 'position_command',
            'elapsed_wall_s': self._elapsed_wall_s(),
            'goal_id': str(msg.goal_id), 'epoch': str(msg.epoch),
            'trajectory_id': int(msg.trajectory_id),
            'trajectory_flag': int(msg.trajectory_flag),
            'source_stamp_ns': (int(msg.header.stamp.sec) * 1_000_000_000
                                + int(msg.header.stamp.nanosec)),
        })

    def _trajectory_cancel(self, msg):
        self.planner_state_samples.append({
            'kind': 'trajectory_cancel',
            'elapsed_wall_s': self._elapsed_wall_s(),
            'goal_id': str(msg.goal_id), 'epoch': str(msg.epoch),
            'mode': int(msg.mode), 'reason': str(msg.reason),
        })

    def _command_ack(self, msg):
        self.command_ack_samples.append({
            'elapsed_wall_s': self._elapsed_wall_s(),
            'timestamp_us': int(msg.timestamp),
            'ros_clock_ns_at_receipt': self.latest_clock_ns,
            'command': int(msg.command), 'result': int(msg.result),
            'result_param1': float(msg.result_param1),
            'result_param2': float(msg.result_param2),
            'target_system': int(msg.target_system),
            'target_component': int(msg.target_component),
        })

    def _record_receipt(self, key):
        now = time.monotonic()
        previous = self.receipt_last.get(key)
        if previous is not None:
            self.receipt_gaps.setdefault(key, []).append(now - previous)
        self.receipt_last[key] = now

    def _record_px4_timestamp(self, key, msg):
        offset_us = (0 if self.direct_sim_time
                     else self.latest_timesync_offset_us)
        recovered_timestamp_us = (
            int(msg.timestamp) + offset_us if offset_us is not None else None)
        self.px4_timestamp_samples.append({
            'topic': key,
            'elapsed_wall_s': time.monotonic() - self.started_mono,
            'timestamp_us': int(msg.timestamp),
            'timestamp_domain': ('gazebo_sim_time' if self.direct_sim_time
                                 else 'agent_clock'),
            'estimated_offset_us': offset_us,
            'recovered_px4_timestamp_us': recovered_timestamp_us,
            'latest_ros_clock_ns': self.latest_clock_ns,
            'timestamp_minus_ros_clock_us': (
                recovered_timestamp_us - self.latest_clock_ns // 1000
                if recovered_timestamp_us is not None and self.latest_clock_ns > 0
                else None),
            'latest_clock_elapsed_wall_s': self.latest_clock_elapsed_wall_s,
        })

    def receipt_gap_summary(self):
        result = {}
        for key, gaps in self.receipt_gaps.items():
            ordered = sorted(gaps)
            p95_index = max(0, math.ceil(0.95 * len(ordered)) - 1)
            result[key] = {
                'samples': len(ordered) + 1,
                'p50_s': ordered[len(ordered) // 2],
                'p95_s': ordered[p95_index],
                'max_s': ordered[-1],
            }
        return result

    def _bridge_status(self, msg):
        self._count('bridge_status')
        self.bridge_reason_counts[msg.reason] = self.bridge_reason_counts.get(msg.reason, 0) + 1
        self.bridge_status_samples.append({
            'elapsed_wall_s': time.monotonic() - self.started_mono,
            'reason': msg.reason,
            'ready': bool(msg.ready),
            'phase': msg.phase,
        })
        for field in self.bridge_state_counts:
            if getattr(msg, field):
                self.bridge_state_counts[field] += 1
        self.latest['bridge'] = {
            'phase': msg.phase, 'reason': msg.reason, 'ready': msg.ready,
            'control_enabled': msg.control_enabled, 'armed': msg.armed,
            'landed': msg.landed,
            'local_position_valid': msg.local_position_valid,
            'ev_position_fused': msg.ev_position_fused,
            'ev_yaw_fused': msg.ev_yaw_fused,
            'gnss_aiding_active': msg.gnss_aiding_active,
            'epoch': msg.epoch,
            'frame_offset_ned': list(map(float, msg.frame_offset_ned)),
            'frame_yaw_offset_ned': msg.frame_yaw_offset_ned,
            'alignment_drift_m': msg.alignment_drift_m,
        }
        self._maybe_terminal_readback()

    def _bridge_detail(self, msg):
        try:
            detail = json.loads(msg.data)
        except (TypeError, ValueError):
            detail = {'parse_error': True}
        self.latest['bridge_detail'] = detail
        self.bridge_detail_samples.append({
            'elapsed_wall_s': time.monotonic() - self.started_mono,
            'detail': detail,
        })

    def _on_clock_message(self, msg):
        now = time.monotonic()
        ros_ns = int(msg.clock.sec) * 1_000_000_000 + int(msg.clock.nanosec)
        previous = self.clock_samples[-1] if self.clock_samples else None
        elapsed = now - self.started_mono
        sample = {
            'elapsed_wall_s': elapsed,
            'ros_clock_ns': ros_ns,
        }
        if previous is not None:
            wall_delta = elapsed - previous['elapsed_wall_s']
            sim_delta = (ros_ns - previous['ros_clock_ns']) / 1e9
            sample.update({
                'delta_wall_s': wall_delta,
                'delta_sim_s': sim_delta,
                'sim_rate': sim_delta / wall_delta if wall_delta > 0 else None,
            })
        self.clock_samples.append(sample)
        self.latest_clock_ns = ros_ns
        self.latest_clock_elapsed_wall_s = elapsed

    def _visual_odom(self, msg):
        self._count('visual_odometry_input')
        self.latest['visual_odometry'] = {
            'timestamp': msg.timestamp, 'sample_timestamp': msg.timestamp_sample,
            'pose_frame': msg.pose_frame, 'velocity_frame': msg.velocity_frame,
            'quality': msg.quality,
            'position': list(map(float, msg.position)),
        }

    def _vehicle_status(self, msg):
        self._count('px4_status')
        self._record_receipt('px4_status')
        self._record_px4_timestamp('vehicle_status', msg)
        self.latest['px4_status'] = {
            'arming_state': msg.arming_state, 'nav_state': msg.nav_state,
            'pre_flight_checks_pass': msg.pre_flight_checks_pass,
            'failsafe': msg.failsafe,
        }
        self.px4_status_samples.append({
            'elapsed_wall_s': self._elapsed_wall_s(),
            **self.latest['px4_status'],
        })
        self._maybe_terminal_readback()

    def _local_position(self, msg):
        self._count('local_position')
        self._record_receipt('local_position')
        self._record_px4_timestamp('local_position', msg)
        self.latest['local_position'] = {
            'xy_valid': msg.xy_valid, 'z_valid': msg.z_valid,
            'heading_good_for_control': msg.heading_good_for_control,
            'position_ned': list(map(float, (msg.x, msg.y, msg.z))),
            'velocity_ned': list(map(float, (msg.vx, msg.vy, msg.vz))),
            'heading': float(msg.heading),
        }

    def _timesync_status(self, msg):
        self._count('timesync_status')
        self._record_receipt('timesync_status')
        self.latest_timesync_offset_us = int(msg.estimated_offset)
        self.timesync_samples.append({
            'elapsed_wall_s': time.monotonic() - self.started_mono,
            'timestamp_px4_us': int(msg.timestamp),
            'source_protocol': int(msg.source_protocol),
            'observed_offset_us': int(msg.observed_offset),
            'estimated_offset_us': int(msg.estimated_offset),
            'round_trip_time_us': int(msg.round_trip_time),
            'px4_clock_recovered_us': int(msg.timestamp) + int(msg.estimated_offset),
            'ros_clock_ns': self.latest_clock_ns,
        })
        self.latest['timesync_status'] = {
            'timestamp': int(msg.timestamp),
            'source_protocol': int(msg.source_protocol),
            'observed_offset': int(msg.observed_offset),
            'estimated_offset': int(msg.estimated_offset),
            'round_trip_time': int(msg.round_trip_time),
        }

    def _estimator(self, msg):
        self._count('estimator_flags')
        self._record_receipt('estimator_flags')
        self._record_px4_timestamp('estimator_flags', msg)
        self.latest['estimator'] = {
            'cs_ev_pos': msg.cs_ev_pos, 'cs_ev_hgt': msg.cs_ev_hgt,
            'cs_ev_yaw': msg.cs_ev_yaw, 'cs_ev_vel': msg.cs_ev_vel,
            'cs_gnss_pos': msg.cs_gnss_pos, 'cs_gnss_vel': msg.cs_gnss_vel,
            'cs_gps_hgt': msg.cs_gps_hgt, 'cs_gnss_yaw': msg.cs_gnss_yaw,
            'cs_aux_gpos': msg.cs_aux_gpos,
        }

    def _attitude(self, msg):
        self._count('attitude')
        self._record_receipt('attitude')
        self._record_px4_timestamp('attitude', msg)

    def _land_detected(self, msg):
        self._count('land_detected')
        self._record_receipt('land_detected')
        self._record_px4_timestamp('land_detected', msg)
        self.latest['land_detected'] = {'landed': bool(msg.landed)}
        self.land_detected_samples.append({
            'elapsed_wall_s': self._elapsed_wall_s(),
            'landed': bool(msg.landed),
        })
        self._maybe_terminal_readback()

    def publisher_counts(self):
        return {topic: len(self.get_publishers_info_by_topic(topic)) for topic in (
            '/fmu/in/offboard_control_mode', '/fmu/in/trajectory_setpoint',
            '/fmu/in/vehicle_command', '/fmu/in/vehicle_visual_odometry')}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=float, default=20.0)
    parser.add_argument('--output', required=True)
    parser.add_argument('--stop-after-terminal-wall-s', type=float, default=None,
                        help='End read-only observation after this stable native terminal window')
    parser.add_argument('--direct-sim-time', action='store_true')
    parser.add_argument('--expected-goal-id', default='')
    parser.add_argument('--expected-epoch', default='')
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or args.seconds <= 0:
        parser.error('--seconds must be finite and positive')
    if args.stop_after_terminal_wall_s is not None and (
            not math.isfinite(args.stop_after_terminal_wall_s)
            or args.stop_after_terminal_wall_s <= 0):
        parser.error('--stop-after-terminal-wall-s must be finite and positive')
    rclpy.init()
    stop_request, previous_handlers = install_observer_stop_handlers()
    node = Probe(direct_sim_time=args.direct_sim_time,
                 expected_goal_id=args.expected_goal_id,
                 expected_epoch=args.expected_epoch)
    deadline = time.monotonic() + args.seconds
    try:
        stop_reason = 'observation_timeout'
        while rclpy.ok() and time.monotonic() < deadline:
            if stop_request.requested:
                stop_reason = 'signal_requested'
                break
            if (args.stop_after_terminal_wall_s is not None
                    and node._terminal_state_active
                    and node.terminal_state_first_wall_s is not None
                    and node._elapsed_wall_s() - node.terminal_state_first_wall_s
                    >= args.stop_after_terminal_wall_s):
                stop_reason = 'stable_native_terminal'
                break
            rclpy.spin_once(node, timeout_sec=0.05)
        terminal_start = node.terminal_state_first_wall_s
        controls_after_terminal = (
            [event for event in node.control_topic_events
             if terminal_start is not None
             and event['elapsed_wall_s'] >= terminal_start]
            if terminal_start is not None else None)
        old_active_planner_events = None
        if terminal_start is not None and node.expected_goal_id and node.expected_epoch:
            old_active_planner_events = [
                event for event in node.planner_state_samples
                if event['elapsed_wall_s'] >= terminal_start
                and event.get('goal_id') == node.expected_goal_id
                and event.get('epoch') == node.expected_epoch
                and (event['kind'] == 'navigation_goal'
                     or (event['kind'] == 'position_command'
                         and event.get('trajectory_flag') == PositionCommand.TRAJECTORY_STATUS_READY))]
        result = {
            'duration_wall_s': args.seconds,
            'observed_wall_s': node._elapsed_wall_s(),
            'observation_stop_reason': stop_reason,
            'observer_stop_signal': stop_request.signal_name,
            'px4_timestamp_domain': ('gazebo_sim_time' if args.direct_sim_time
                                     else 'agent_clock_with_estimated_offset'),
            'counts': node.counts,
            'bridge_reason_counts': node.bridge_reason_counts,
            'bridge_state_counts': node.bridge_state_counts,
            'telemetry_interarrival_s': node.receipt_gap_summary(),
            'ros_clock_samples': node.clock_samples,
            'timesync_receipt_samples': node.timesync_samples,
            'px4_timestamp_samples': node.px4_timestamp_samples,
            'bridge_status_samples': node.bridge_status_samples,
            'bridge_detail_samples': node.bridge_detail_samples,
            'px4_status_samples': node.px4_status_samples,
            'land_detected_samples': node.land_detected_samples,
            'vehicle_command_ack_samples': node.command_ack_samples,
            'control_topic_events': node.control_topic_events,
            'planner_state_samples': node.planner_state_samples,
            'expected_goal_id': node.expected_goal_id or None,
            'expected_epoch': node.expected_epoch or None,
            'terminal_state_first_wall_s': terminal_start,
            'terminal_state_duration_wall_s': (
                max(0.0, time.monotonic() - node.started_mono - terminal_start)
                if terminal_start is not None and node._terminal_state_active else 0.0),
            'terminal_state_violation_count': node.terminal_state_violation_count,
            'terminal_readback_samples': node.terminal_readback_samples,
            'zero_control_after_terminal': (
                bool(terminal_start is not None and not controls_after_terminal)),
            'control_samples_after_terminal': controls_after_terminal,
            'no_old_epoch_goal_or_trajectory': (
                bool(old_active_planner_events == [])
                if old_active_planner_events is not None else None),
            'old_epoch_goal_or_trajectory_after_terminal': old_active_planner_events,
            'publisher_counts': node.publisher_counts(),
            'latest': node.latest,
            'control_samples_zero': all(node.counts[key] == 0 for key in (
                'control_mode', 'trajectory_setpoint', 'vehicle_command')),
            'vehicle_remained_disarmed': (
                node.latest.get('px4_status', {}).get('arming_state') == 1),
        }
        with open(args.output, 'w', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write('\n')
        print(json.dumps(result, indent=2, sort_keys=True))
    finally:
        node.destroy_node()
        restore_observer_stop_handlers(previous_handlers)
        rclpy.shutdown()


if __name__ == '__main__':
    main()
