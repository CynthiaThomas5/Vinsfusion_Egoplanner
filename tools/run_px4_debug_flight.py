#!/usr/bin/env python3
"""Enable the guarded debug_truth bridge, then request landing after takeoff."""

import argparse
from collections import deque
import json
import math
from pathlib import Path
import time

import rclpy
from px4_msgs.msg import (OffboardControlMode, TrajectorySetpoint,
                          VehicleCommand, VehicleLocalPosition,
                          VehicleOdometry, VehicleStatus)
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from uav_interfaces.msg import Px4BridgeStatus
from uav_interfaces.srv import EnableOffboard


class FlightProbe(Node):
    def __init__(self):
        super().__init__('px4_debug_flight_probe')
        sensor_qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)
        reliable_qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        self.bridge = None
        self.ready_streak = 0
        self.status_history = deque(maxlen=400)
        self.counts = {'visual_odometry_input': 0, 'control_mode': 0,
                       'trajectory_setpoint': 0, 'vehicle_command': 0,
                       'px4_status': 0, 'local_position': 0}
        self.latest_vehicle_status = None
        self.latest_local_position = None
        self.takeoff_start_z = None
        self.max_climb_m = 0.0
        self.create_subscription(Px4BridgeStatus, '/uav_px4_bridge/status',
                                 self._on_bridge, reliable_qos)
        self.create_subscription(VehicleOdometry, '/fmu/in/vehicle_visual_odometry',
                                 lambda _: self._count('visual_odometry_input'), sensor_qos)
        self.create_subscription(OffboardControlMode, '/fmu/in/offboard_control_mode',
                                 lambda _: self._count('control_mode'), sensor_qos)
        self.create_subscription(TrajectorySetpoint, '/fmu/in/trajectory_setpoint',
                                 lambda _: self._count('trajectory_setpoint'), sensor_qos)
        self.create_subscription(VehicleCommand, '/fmu/in/vehicle_command',
                                 lambda _: self._count('vehicle_command'), sensor_qos)
        self.create_subscription(VehicleStatus, '/fmu/out/vehicle_status_v1',
                                 self._on_vehicle_status, sensor_qos)
        self.create_subscription(VehicleLocalPosition, '/fmu/out/vehicle_local_position_v1',
                                 self._on_local_position, sensor_qos)
        self.enable_client = self.create_client(
            EnableOffboard, '/uav_px4_bridge/enable_offboard')
        self.ready_since_mono = None
        self.ready_samples = 0
        self.land_request_reason = ''

    def _count(self, key):
        self.counts[key] += 1

    def _on_bridge(self, msg):
        self.bridge = msg
        aligned = (math.isfinite(msg.alignment_drift_m)
                   and 0.0 <= msg.alignment_drift_m <= 0.15
                   and all(math.isfinite(float(v)) for v in msg.frame_offset_ned)
                   and math.isfinite(msg.frame_yaw_offset_ned))
        all_other_gates = (
            msg.phase == 'DISABLED' and msg.landed and not msg.armed
            and msg.local_position_valid and msg.ev_position_fused
            and msg.ev_yaw_fused and not msg.gnss_aiding_active
            and bool(msg.epoch) and aligned
            and msg.reason in ('', 'px4_preflight_failed'))
        if all_other_gates:
            self.ready_streak += 1
            self.ready_samples += 1
            if self.ready_since_mono is None:
                self.ready_since_mono = time.monotonic()
        else:
            self.ready_streak = 0
            self.ready_since_mono = None
        self.status_history.append({
            'receipt_monotonic_s': time.monotonic(),
            'phase': msg.phase, 'reason': msg.reason, 'ready': bool(msg.ready),
            'control_enabled': bool(msg.control_enabled), 'armed': bool(msg.armed),
            'landed': bool(msg.landed),
            'local_position_valid': bool(msg.local_position_valid),
            'ev_position_fused': bool(msg.ev_position_fused),
            'ev_yaw_fused': bool(msg.ev_yaw_fused),
            'gnss_aiding_active': bool(msg.gnss_aiding_active),
            'epoch': msg.epoch,
            'frame_offset_ned': list(map(float, msg.frame_offset_ned)),
            'frame_yaw_offset_ned': float(msg.frame_yaw_offset_ned),
            'alignment_drift_m': float(msg.alignment_drift_m),
            'preflight_candidate': all_other_gates,
        })

    def _on_vehicle_status(self, msg):
        self._count('px4_status')
        self.latest_vehicle_status = {
            'arming_state': int(msg.arming_state),
            'nav_state': int(msg.nav_state),
            'pre_flight_checks_pass': bool(msg.pre_flight_checks_pass),
            'failsafe': bool(msg.failsafe),
        }

    def _on_local_position(self, msg):
        self._count('local_position')
        self.latest_local_position = {
            'position_ned': list(map(float, (msg.x, msg.y, msg.z))),
            'velocity_ned': list(map(float, (msg.vx, msg.vy, msg.vz))),
            'xy_valid': bool(msg.xy_valid), 'z_valid': bool(msg.z_valid),
        }
        if self.takeoff_start_z is None and msg.z_valid:
            self.takeoff_start_z = float(msg.z)
        if self.takeoff_start_z is not None and msg.z_valid:
            self.max_climb_m = max(self.max_climb_m,
                                   self.takeoff_start_z - float(msg.z))

    def publisher_counts(self):
        topics = ('/fmu/in/vehicle_visual_odometry',
                  '/fmu/in/offboard_control_mode',
                  '/fmu/in/trajectory_setpoint',
                  '/fmu/in/vehicle_command')
        return {topic: len(self.get_publishers_info_by_topic(topic)) for topic in topics}


def _spin_until(node, predicate, timeout_s):
    deadline = time.monotonic() + timeout_s
    while rclpy.ok() and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.05)
        if predicate():
            return True
    return False


def _call_enable(node, enable, timeout_s=4.0):
    if not node.enable_client.wait_for_service(timeout_sec=timeout_s):
        raise RuntimeError('enable_offboard_service_unavailable')
    request = EnableOffboard.Request()
    request.enable = enable
    future = node.enable_client.call_async(request)
    if not _spin_until(node, future.done, timeout_s):
        raise TimeoutError('enable_offboard_service_timeout')
    response = future.result()
    if response is None:
        raise RuntimeError('enable_offboard_service_empty_response')
    return {'accepted': bool(response.accepted), 'reason': response.reason}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--preflight-timeout-s', type=float, default=15.0)
    parser.add_argument('--flight-timeout-s', type=float, default=25.0)
    parser.add_argument('--landing-timeout-s', type=float, default=20.0)
    parser.add_argument('--minimum-ready-samples', type=int, default=5)
    args = parser.parse_args()

    result = {'profile': 'debug_truth', 'authorized_control_path': 'enable_offboard service only',
              'result': 'FAIL', 'service_calls': [], 'status_timeline': []}
    rclpy.init()
    node = FlightProbe()
    try:
        preflight_ready = _spin_until(
            node, lambda: node.ready_streak >= args.minimum_ready_samples,
            args.preflight_timeout_s)
        result['non_preflight_gates_ready'] = preflight_ready
        result['preflight_candidate_samples'] = node.ready_streak
        if not preflight_ready:
            raise TimeoutError('non_preflight_bridge_gates_not_ready')

        enable_result = _call_enable(node, True)
        result['service_calls'].append({'enable': True, **enable_result})
        if not enable_result['accepted']:
            raise RuntimeError('enable_rejected:' + enable_result['reason'])

        flight_deadline = time.monotonic() + args.flight_timeout_s
        while rclpy.ok() and time.monotonic() < flight_deadline:
            rclpy.spin_once(node, timeout_sec=0.05)
            bridge = node.bridge
            if bridge is None:
                continue
            if bridge.armed and bridge.phase == 'ACTIVE':
                disable_result = _call_enable(node, False)
                result['service_calls'].append({'enable': False, **disable_result})
                node.land_request_reason = disable_result['reason']
                break
            if bridge.armed and bridge.phase in ('LANDING', 'LANDED', 'LOCKED'):
                break
            if bridge.phase == 'LOCKED':
                break

        result['takeoff_phase_observed'] = any(
            item['phase'] in ('TAKEOFF', 'ACTIVE') and item['armed']
            for item in node.status_history)
        result['takeoff_complete_observed'] = any(
            item['phase'] == 'ACTIVE' and item['armed']
            for item in node.status_history)
        if (node.bridge is not None and node.bridge.armed
                and node.bridge.phase not in ('LANDING', 'LANDED', 'LOCKED')
                and not node.land_request_reason):
            disable_result = _call_enable(node, False)
            result['service_calls'].append({'enable': False, **disable_result})
            node.land_request_reason = disable_result['reason']

        landed = _spin_until(
            node, lambda: (node.bridge is not None and node.bridge.landed
                           and not node.bridge.armed
                           and node.bridge.phase == 'LANDED'),
            args.landing_timeout_s)
        result['landed_and_disarmed'] = landed
        if not landed:
            raise TimeoutError('landed_disarmed_not_observed')
        result['result'] = 'PASS' if result['takeoff_complete_observed'] else 'FAIL'
        if result['result'] != 'PASS':
            result['failure'] = 'takeoff_complete_not_observed'
    except Exception as exc:
        result['failure'] = str(exc)
        if node.bridge is not None and node.bridge.armed and node.bridge.phase not in (
                'LANDING', 'LANDED', 'LOCKED'):
            try:
                disable_result = _call_enable(node, False)
                result['service_calls'].append({'enable': False, **disable_result})
                node.land_request_reason = disable_result['reason']
                result['landed_and_disarmed'] = _spin_until(
                    node, lambda: (node.bridge is not None and node.bridge.landed
                                   and not node.bridge.armed
                                   and node.bridge.phase == 'LANDED'),
                    args.landing_timeout_s)
            except Exception as land_exc:
                result['landing_error'] = str(land_exc)
    finally:
        result['counts'] = node.counts
        result['publisher_counts'] = node.publisher_counts()
        result['latest_vehicle_status'] = node.latest_vehicle_status
        result['latest_local_position'] = node.latest_local_position
        result['max_climb_m'] = node.max_climb_m
        result['status_timeline'] = list(node.status_history)
        Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n',
                                     encoding='utf-8')
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    print(json.dumps(result, indent=2, sort_keys=True))
    if result['result'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
