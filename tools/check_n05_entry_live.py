#!/usr/bin/env python3
"""Run the N05 phased entry check on the active raw plan_env map; read-only."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np
import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import (DurabilityPolicy, QoSProfile, ReliabilityPolicy,
                       qos_profile_sensor_data)
from rosgraph_msgs.msg import Clock
from uav_interfaces.msg import LocalizationStatus, MapStatus, Px4BridgeStatus
from uav_interfaces.srv import GetOccupancySnapshot

from n05_entry import ROOT, check_entry_schedule, collision_primitives, load_policy


def _ns(stamp):
    return int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rpy(q):
    roll = math.atan2(2 * (q.w * q.x + q.y * q.z),
                      1 - 2 * (q.x * q.x + q.y * q.y))
    sin_pitch = 2 * (q.w * q.y - q.z * q.x)
    pitch = math.copysign(math.pi / 2, sin_pitch) if abs(sin_pitch) >= 1 else math.asin(sin_pitch)
    yaw = math.atan2(2 * (q.w * q.z + q.x * q.y),
                     1 - 2 * (q.y * q.y + q.z * q.z))
    return roll, pitch, yaw


class LiveCheck(Node):
    def __init__(self):
        super().__init__('n05_entry_preflight_readonly')
        qos_status = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                                durability=DurabilityPolicy.TRANSIENT_LOCAL)
        qos_bridge = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                                durability=DurabilityPolicy.VOLATILE)
        self.values = {}
        self.receipts = {}
        self.create_subscription(LocalizationStatus, '/localization/status',
                                 lambda m: self._receive('localization', m), qos_status)
        self.create_subscription(MapStatus, '/mapping/status',
                                 lambda m: self._receive('map', m), qos_status)
        self.create_subscription(Px4BridgeStatus, '/uav_px4_bridge/status',
                                 lambda m: self._receive('bridge', m), qos_bridge)
        self.create_subscription(Odometry, '/localization/optimized_imu_odom',
                                 lambda m: self._receive('odom', m), qos_profile_sensor_data)
        self.create_subscription(Clock, '/clock', lambda m: self._receive('clock', m),
                                 qos_profile_sensor_data)
        self.snapshot_client = self.create_client(
            GetOccupancySnapshot, '/mapping/get_occupancy_snapshot')

    def _receive(self, name, msg):
        self.values[name] = msg
        self.receipts[name] = time.monotonic()

    def spin_for(self, duration_s):
        deadline = time.monotonic() + duration_s
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.02)

    def wait_complete(self, timeout_s):
        required = {'localization', 'map', 'bridge', 'odom', 'clock'}
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.05)
            if required <= self.values.keys():
                return
        missing = sorted(required - self.values.keys())
        received = sorted(self.values.keys())
        raise TimeoutError('timed out waiting for current localization/map/bridge/odom/clock state; '
                           f'missing={missing}; received={received}')

    def call_snapshot(self, epoch, map_id, timeout_s):
        if not self.snapshot_client.wait_for_service(timeout_sec=timeout_s):
            raise TimeoutError('plan_env raw occupancy snapshot service unavailable')
        request = GetOccupancySnapshot.Request()
        request.expected_epoch = epoch
        request.expected_map_id = map_id
        future = self.snapshot_client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=timeout_s)
        if not future.done() or future.result() is None:
            raise TimeoutError('plan_env raw occupancy snapshot request failed or timed out')
        return future.result()


def run(args):
    policy = load_policy(ROOT)
    model = ROOT / 'simulation/models/d435i/model.sdf'
    input_config = ROOT / 'config/components/mapping/ego_input.json'
    policy_hash = _sha256(ROOT / 'config/components/navigation/vehicle_envelope.json')
    rclpy.init()
    node = LiveCheck()
    try:
        node.wait_complete(args.wait_s)
        readiness_deadline = time.monotonic() + args.wait_s
        last_readiness_reason = 'map_or_localization_not_ready'
        while time.monotonic() < readiness_deadline:
            node.spin_for(0.1)
            loc = node.values['localization']
            status_before = node.values['map']
            bridge = node.values['bridge']
            odom = node.values['odom']
            clock = node.values['clock']
            epoch = loc.epoch
            if bridge.armed or bridge.control_enabled or bridge.phase != 'DISABLED':
                raise RuntimeError('N05 read-only admission requires PX4 DISARMED and control DISABLED')
            if not epoch or not loc.valid or loc.state != LocalizationStatus.TRACKING:
                last_readiness_reason = 'localization_not_tracking'
                continue
            if status_before.epoch != epoch or not status_before.map_id.startswith(epoch + '-'):
                last_readiness_reason = 'map_status_identity_mismatch'
                continue
            if not (status_before.reset_acknowledged and status_before.input_ready
                    and status_before.occupancy_cloud_received):
                last_readiness_reason = 'map_status_not_ready:' + status_before.reason
                continue
            if (status_before.calibration_sha256 != _sha256(model)
                    or status_before.input_config_sha256 != _sha256(input_config)):
                raise RuntimeError('active map calibration or input-config hash mismatch')
            if odom.header.frame_id != f'odom_{epoch}' or odom.child_frame_id != f'd435i_imu_{epoch}':
                last_readiness_reason = 'optimized_odometry_frame_mismatch'
                continue
            map_receipt_age = time.monotonic() - node.receipts['map']
            loc_receipt_age = time.monotonic() - node.receipts['localization']
            odom_receipt_age = time.monotonic() - node.receipts['odom']
            if max(map_receipt_age, loc_receipt_age, odom_receipt_age) > 0.5:
                last_readiness_reason = 'localization_or_map_status_receipt_stale'
                continue
            break
        else:
            raise TimeoutError(f'N05 online prerequisites did not become ready: {last_readiness_reason}')

        transient_rejections = {'no_fresh_fused_depth', 'depth_source_stale', 'occupancy_update_stale'}
        snapshot_deadline = time.monotonic() + args.wait_s
        while True:
            status_before = node.values['map']
            response = node.call_snapshot(epoch, status_before.map_id,
                                          max(0.5, min(2.0, snapshot_deadline-time.monotonic())))
            if response.accepted and response.reason == 'ok':
                break
            if response.reason not in transient_rejections or time.monotonic() >= snapshot_deadline:
                raise RuntimeError('raw map snapshot refused: ' + (response.reason or 'unknown'))
            node.spin_for(0.2)
        node.spin_for(0.05)
        status_after = node.values.get('map')
        bridge = node.values.get('bridge')
        loc = node.values.get('localization')
        odom_after = node.values.get('odom')
        if (status_after is None or status_after.epoch != epoch
                or not status_after.reset_acknowledged or not status_after.input_ready
                or status_after.map_id != status_before.map_id
                or response.epoch != epoch or response.map_id != status_before.map_id
                or response.header.frame_id != f'odom_{epoch}'):
            raise RuntimeError('map identity changed during N05 snapshot capture')
        if (bridge is None or bridge.armed or bridge.control_enabled or bridge.phase != 'DISABLED'
                or loc is None or not loc.valid or loc.epoch != epoch):
            raise RuntimeError('localization/control state changed during N05 snapshot capture')
        receipt_ages = {name: time.monotonic()-node.receipts[name]
                        for name in ('map', 'localization', 'bridge', 'odom')}
        if max(receipt_ages.values()) > 0.5:
            raise RuntimeError('map, localization, bridge, or odometry state became stale during snapshot capture')
        map_receipt_age = receipt_ages['map']
        loc_receipt_age = receipt_ages['localization']
        odom_receipt_age = receipt_ages['odom']
        p_before = np.asarray([odom.pose.pose.position.x, odom.pose.pose.position.y,
                               odom.pose.pose.position.z], dtype=float)
        p_after = np.asarray([odom_after.pose.pose.position.x, odom_after.pose.pose.position.y,
                              odom_after.pose.pose.position.z], dtype=float)
        pose_change = float(np.linalg.norm(p_after-p_before))
        if (odom_after.header.frame_id != f'odom_{epoch}'
                or odom_after.child_frame_id != f'd435i_imu_{epoch}'
                or not math.isfinite(pose_change)
                or pose_change > policy['spatial_budget']['terms_m']['sweep_sample_half_step']):
            raise RuntimeError('body pose changed during N05 map snapshot capture')

        shape = (int(response.size_x), int(response.size_y), int(response.size_z))
        occupancy = np.asarray(response.occupancy_data, dtype=np.int8)
        inflated = np.asarray(response.inflated_data, dtype=np.uint8)
        if int(np.prod(shape)) != occupancy.size or occupancy.size != inflated.size:
            raise RuntimeError('snapshot array size disagrees with map dimensions')
        occupancy = occupancy.reshape(shape, order='C')
        inflated = inflated.reshape(shape, order='C')
        if not np.all(np.isin(occupancy, (-1, 0, 100))) or not np.all(np.isin(inflated, (0, 1))):
            raise RuntimeError('snapshot contains invalid raw occupancy or inflation codes')
        if response.data_order != 'x_major_y_mid_z_fastest':
            raise RuntimeError('unsupported plan_env occupancy data order')
        snapshot_ns = _ns(response.header.stamp)
        source_ns = _ns(response.last_depth_source_stamp)
        fusion_ns = _ns(response.last_fusion_stamp)
        source_age_s = (snapshot_ns - source_ns) / 1e9
        fusion_age_s = (snapshot_ns - fusion_ns) / 1e9
        sim_now_ns = _ns(node.values['clock'].clock)
        snapshot_age_s = (sim_now_ns - snapshot_ns) / 1e9
        limit = policy['map_policy']['freshness_limit_sim_s']
        if any(t <= 0 for t in (snapshot_ns, source_ns, fusion_ns)):
            raise RuntimeError('map snapshot has a zero source/fusion/snapshot timestamp')
        if any(not math.isfinite(age) or age < 0 or age > limit
               for age in (source_age_s, fusion_age_s, snapshot_age_s)):
            raise RuntimeError('map source, fusion, or snapshot age exceeds the N05 freshness limit')

        p = odom_after.pose.pose.position
        q = odom_after.pose.pose.orientation
        quaternion_norm = math.sqrt(q.x*q.x + q.y*q.y + q.z*q.z + q.w*q.w)
        if (not math.isfinite(quaternion_norm) or abs(quaternion_norm - 1.0) > 1e-3
                or not all(math.isfinite(value) for value in (p.x, p.y, p.z))):
            raise RuntimeError('optimized IMU odometry pose is non-finite or quaternion-invalid')
        roll, pitch, yaw = _rpy(q)
        pose = {'center_xyz_m': [p.x, p.y, p.z], 'yaw_rad': yaw,
                'roll_rad': roll, 'pitch_rad': pitch}
        snapshot = {
            'occupancy': occupancy,
            'origin_m': [response.origin.x, response.origin.y, response.origin.z],
            'map_size_m': [response.map_size.x, response.map_size.y, response.map_size.z],
            'resolution_m': float(response.resolution),
            'dimensions_xyz': list(shape),
            'frame_id': response.header.frame_id,
            'epoch': response.epoch, 'map_id': response.map_id,
            'snapshot_stamp_ns': snapshot_ns,
            'source_stamp_ns': source_ns, 'fusion_stamp_ns': fusion_ns,
        }
        ground_confirmed = bool(bridge.landed and not bridge.armed and not bridge.control_enabled)
        result = check_entry_schedule(
            snapshot, pose, args.hold_height_m, args.sample_step_m,
            ground_confirmed=ground_confirmed, disarmed=not bridge.armed,
            control_disabled=not bridge.control_enabled, policy=policy,
            primitives=collision_primitives(ROOT))

        args.output_dir.mkdir(parents=True, exist_ok=True)
        archive = args.output_dir / 'n05-live-raw-map.npz'
        np.savez_compressed(archive, occupancy=occupancy, inflated=inflated)
        with np.load(archive, allow_pickle=False) as saved:
            offline_snapshot = dict(snapshot, occupancy=saved['occupancy'])
            offline = check_entry_schedule(
                offline_snapshot, pose, args.hold_height_m, args.sample_step_m,
                ground_confirmed=ground_confirmed, disarmed=not bridge.armed,
                control_disabled=not bridge.control_enabled, policy=policy,
                primitives=collision_primitives(ROOT))
        identical = result == offline
        report = {
            'schema': 'n05-live-entry-check/v1',
            'scope': 'DISARMED, read-only raw-map check; no enable, arm, navigation goal, truth input, or control publisher',
            'accepted': bool(result['accepted']), 'reason': result['reason'],
            'qualification': 'observation/entry diagnostic only; never flight approval',
            'identity': {'epoch': epoch, 'map_id': status_before.map_id,
                         'frame_id': response.header.frame_id,
                         'calibration_sha256': status_before.calibration_sha256,
                         'input_config_sha256': status_before.input_config_sha256,
                         'envelope_policy_sha256': policy_hash},
            'state': {'bridge_phase': bridge.phase, 'armed': bridge.armed,
                      'control_enabled': bridge.control_enabled, 'landed': bridge.landed,
                      'localization_valid': loc.valid, 'localization_state': loc.state,
                      'body_pose_imu_m': pose},
            'freshness': {'snapshot_age_sim_s': snapshot_age_s,
                          'depth_source_age_sim_s': source_age_s,
                          'fusion_age_sim_s': fusion_age_s,
                          'map_status_receipt_age_wall_s': map_receipt_age,
                          'localization_receipt_age_wall_s': loc_receipt_age,
                          'odometry_receipt_age_wall_s': odom_receipt_age,
                          'limit_sim_s': limit},
            'snapshot': {'origin_m': snapshot['origin_m'],
                         'map_size_m': snapshot['map_size_m'],
                         'resolution_m': snapshot['resolution_m'],
                         'dimensions_xyz': list(shape),
                         'voxel_counts': {'unknown': int(np.count_nonzero(occupancy == -1)),
                                          'free': int(np.count_nonzero(occupancy == 0)),
                                          'occupied': int(np.count_nonzero(occupancy == 100)),
                                          'inflated': int(np.count_nonzero(inflated == 1))},
                         'archive': archive.name, 'archive_sha256': _sha256(archive)},
            'online_admission': result,
            'offline_snapshot_replay': offline,
            'online_offline_result_identical': identical,
            'self_filter': policy['map_policy']['self_filter'],
            'truth_subscribed': False,
            'control_or_goal_published': False,
        }
        (args.output_dir / 'n05-live-entry-check.json').write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + '\n')
        return report
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--hold-height-m', type=float, default=1.0)
    parser.add_argument('--sample-step-m', type=float, default=0.05)
    parser.add_argument('--wait-s', type=float, default=30.0)
    args = parser.parse_args()
    try:
        result = run(args)
    except Exception as exc:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        failure = {
            'schema': 'n05-live-entry-check-error/v1',
            'accepted': False,
            'reason': 'online_snapshot_or_prerequisite_check_failed',
            'error': str(exc),
            'qualification': 'fail-closed read-only diagnostic; no entry authorization',
            'truth_subscribed': False,
            'control_or_goal_published': False,
        }
        (args.output_dir/'n05-live-entry-check-error.json').write_text(
            json.dumps(failure, indent=2, ensure_ascii=False)+'\n')
        raise
    print(json.dumps({k: result[k] for k in (
        'accepted', 'reason', 'identity', 'state', 'online_offline_result_identical')},
        indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
