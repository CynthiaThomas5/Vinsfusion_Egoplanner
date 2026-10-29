#!/usr/bin/env python3
"""Capture a live EGO spline/map, or a failure map when no spline is emitted.

This observer only subscribes and calls read-only map services. It never sends
navigation, PX4 control, simulator-truth, or map-mutation messages.
"""
import argparse
import json
from pathlib import Path
import sys
import time

import numpy as np
import rclpy
from rclpy.node import Node
from rosidl_runtime_py.convert import message_to_ordereddict
from traj_utils.msg import Bspline
from uav_interfaces.msg import NavigationCommand
from uav_interfaces.srv import GetMapStatus, GetOccupancySnapshot


def stamp_ns(stamp):
    return int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)


def as_json(message):
    return message_to_ordereddict(message)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run')
    parser.add_argument(
        '--resume-failed-capture', action='store_true',
        help='retry a prior no_fresh_fused_depth snapshot for its recorded goal/spline')
    args = parser.parse_args()
    run = Path(args.run).resolve()
    record_path = run / 'n08-live-curve-map.json'
    archive_path = run / 'n08-live-curve-map.npz'
    node = None
    outcome = {
        'schema': 'n08-live-curve-map-capture/v1',
        'scope': 'Read-only same-run goal/spline and exact-identity raw occupancy snapshot; goal-only on failure before spline',
        'run_id': run.name,
        'status': 'failed',
        'failure': 'not_started',
        'navigation_goals_seen': 0,
        'splines_seen': 0,
        'control_or_truth_published': False,
    }
    write_record = not args.resume_failed_capture
    try:
        previous = None
        runner_failure = None
        if args.resume_failed_capture:
            if not record_path.is_file():
                raise FileNotFoundError('previous_curve_capture_missing')
            previous = json.loads(record_path.read_text())
            flight_path = run / 'flight.json'
            flight = json.loads(flight_path.read_text()) if flight_path.is_file() else {}
            previous_goal = previous.get('goal') or {}
            previous_spline = previous.get('bspline') or {}
            if (previous.get('run_id') not in (None, run.name)
                    or previous.get('status') != 'failed'
                    or previous.get('failure')
                    != 'raw_snapshot_rejected:no_fresh_fused_depth'
                    or not previous_goal or not previous_spline
                    or previous_goal.get('goal_id') != flight.get('goal_id')
                    or previous_goal.get('epoch') != flight.get('epoch')
                    or previous_spline.get('goal_id') != flight.get('goal_id')
                    or previous_spline.get('epoch') != flight.get('epoch')):
                raise RuntimeError('previous_capture_not_resumable')
            write_record = True
        rclpy.init()
        node = Node('n08_live_curve_map_capture')
        goals = {}
        splines = {}
        node.create_subscription(
            NavigationCommand, '/navigation/ego_goal',
            lambda msg: goals.__setitem__((msg.goal_id, msg.epoch), msg), 10)
        node.create_subscription(
            Bspline, '/drone_0_planning/bspline',
            lambda msg: splines.__setitem__((msg.goal_id, msg.epoch), msg), 10)
        status_client = node.create_client(GetMapStatus, '/mapping/get_map_status')
        snapshot_client = node.create_client(
            GetOccupancySnapshot, '/mapping/get_occupancy_snapshot')

        def spin_future(client, request, service_name, timeout_s=6.0):
            if not client.wait_for_service(timeout_sec=timeout_s):
                raise TimeoutError('service_unavailable:' + service_name)
            future = client.call_async(request)
            deadline = time.monotonic() + timeout_s
            while rclpy.ok() and not future.done() and time.monotonic() < deadline:
                rclpy.spin_once(node, timeout_sec=0.05)
            if not future.done():
                raise TimeoutError('service_timeout:' + service_name)
            response = future.result()
            if response is None:
                raise RuntimeError('empty_service_response:' + service_name)
            return response

        if previous is not None:
            if archive_path.exists():
                raise FileExistsError('refusing_to_overwrite_existing_raw_map_archive')
            goal_record = previous['goal']
            spline_record = previous['bspline']
            outcome['navigation_goals_seen'] = previous.get('navigation_goals_seen', 0)
            outcome['splines_seen'] = previous.get('splines_seen', 0)
            outcome['resumed_from_previous_capture'] = {
                'failure': previous['failure'],
                'capture_wall_monotonic_s': previous.get('capture_wall_monotonic_s'),
                'goal_id': goal_record.get('goal_id'),
                'epoch': spline_record.get('epoch'),
                'map_id': goal_record.get('map_id'),
                'recovery': previous.get('recovery'),
            }
        else:
            deadline = time.monotonic() + 75.0
            selected = None
            runner_failure = None
            flight_path = run / 'flight.json'
            while rclpy.ok() and time.monotonic() < deadline:
                rclpy.spin_once(node, timeout_sec=0.05)
                for key in list(splines):
                    spline = splines[key]
                    goal = goals.get(key)
                    if goal is not None and spline.goal_id and spline.epoch:
                        selected = (goal, spline)
                        break
                if selected is not None:
                    break
                if flight_path.is_file():
                    try:
                        flight = json.loads(flight_path.read_text())
                    except (OSError, json.JSONDecodeError):
                        flight = None
                    if flight is not None and flight.get('result') != 'PASS':
                        key = (flight.get('goal_id'), flight.get('epoch'))
                        goal = goals.get(key)
                        if goal is not None and goal.goal_id and goal.epoch:
                            selected = (goal, None)
                            runner_failure = {
                                'result': flight.get('result'),
                                'failure': flight.get('failure'),
                                'goal_id': flight.get('goal_id'),
                                'epoch': flight.get('epoch'),
                            }
                            break

            outcome['navigation_goals_seen'] = len(goals)
            outcome['splines_seen'] = len(splines)
            if selected is None:
                raise TimeoutError('matching_goal_epoch_bspline_not_observed')
            goal, spline = selected
            goal_record = as_json(goal)
            spline_record = as_json(spline) if spline is not None else None
            if runner_failure is not None:
                outcome['capture_mode'] = 'goal_only_after_runner_failure'
                outcome['runner_failure_before_spline'] = runner_failure
            else:
                outcome['capture_mode'] = 'goal_and_live_spline'

        outcome['goal'] = goal_record
        outcome['bspline'] = spline_record
        outcome['capture_wall_monotonic_s'] = time.monotonic()
        epoch = goal_record['epoch']
        goal_id = goal_record['goal_id']
        map_id = goal_record['map_id']
        target_frame = goal_record['target']['header']['frame_id']
        if (spline_record is not None
                and (spline_record.get('goal_id') != goal_id
                     or spline_record.get('epoch') != epoch)):
            raise RuntimeError('recorded_goal_spline_identity_mismatch')

        status_request = GetMapStatus.Request()
        status_request.expected_epoch = epoch
        status_response = spin_future(status_client, status_request,
                                      '/mapping/get_map_status')
        outcome['map_status_service_accepted'] = bool(status_response.accepted)
        outcome['map_status_reason'] = str(status_response.reason)
        outcome['map_status'] = as_json(status_response.status)
        if not status_response.accepted:
            raise RuntimeError('map_status_rejected:' + str(status_response.reason))
        status = status_response.status
        if status.epoch != epoch or status.map_id != map_id:
            raise RuntimeError('live_map_identity_does_not_match_goal_and_spline')
        if not status.reset_acknowledged or not status.input_ready:
            raise RuntimeError('live_map_input_not_ready')

        transient_snapshot_reasons = {
            'no_fresh_fused_depth', 'occupancy_update_stale', 'depth_source_stale'}
        snapshot_deadline = time.monotonic() + 2.0
        snapshot_attempts = []
        while True:
            snapshot_request = GetOccupancySnapshot.Request()
            snapshot_request.expected_epoch = epoch
            snapshot_request.expected_map_id = map_id
            snapshot = spin_future(snapshot_client, snapshot_request,
                                   '/mapping/get_occupancy_snapshot', timeout_s=1.0)
            snapshot_attempts.append({
                'attempt': len(snapshot_attempts) + 1,
                'accepted': bool(snapshot.accepted),
                'reason': str(snapshot.reason),
                'response_stamp_ns': stamp_ns(snapshot.header.stamp),
            })
            outcome['snapshot_attempts'] = snapshot_attempts
            if snapshot.accepted:
                break
            if snapshot.reason not in transient_snapshot_reasons:
                raise RuntimeError('raw_snapshot_rejected:' + str(snapshot.reason))
            if time.monotonic() >= snapshot_deadline:
                raise TimeoutError('raw_snapshot_retries_exhausted:'
                                   + str(snapshot.reason))
            status_response = spin_future(status_client, status_request,
                                          '/mapping/get_map_status', timeout_s=1.0)
            outcome['map_status_service_accepted'] = bool(status_response.accepted)
            outcome['map_status_reason'] = str(status_response.reason)
            outcome['map_status'] = as_json(status_response.status)
            status = status_response.status
            if (not status_response.accepted or status.epoch != epoch
                    or status.map_id != map_id or not status.reset_acknowledged
                    or not status.input_ready):
                raise RuntimeError('map_identity_or_input_changed_during_snapshot_retry')
            time.sleep(0.005)
        outcome['snapshot_attempts'] = snapshot_attempts
        outcome['snapshot_service_accepted'] = bool(snapshot.accepted)
        outcome['snapshot_reason'] = str(snapshot.reason)
        if not snapshot.accepted:
            raise RuntimeError('raw_snapshot_rejected:' + str(snapshot.reason))
        if (snapshot.epoch != epoch or snapshot.map_id != map_id
                or snapshot.header.frame_id != target_frame):
            raise RuntimeError('raw_snapshot_identity_or_frame_mismatch')

        shape = (int(snapshot.size_x), int(snapshot.size_y), int(snapshot.size_z))
        occupancy = np.asarray(snapshot.occupancy_data, dtype=np.int8)
        inflated = np.asarray(snapshot.inflated_data, dtype=np.uint8)
        expected_size = int(np.prod(shape, dtype=np.int64))
        if occupancy.size != expected_size or inflated.size != expected_size:
            raise RuntimeError('raw_snapshot_array_size_mismatch')
        occupancy = occupancy.reshape(shape)
        inflated = inflated.reshape(shape)
        np.savez_compressed(archive_path, occupancy=occupancy,
                            inflated=inflated)
        outcome['snapshot'] = {
            'archive': archive_path.name,
            'epoch': snapshot.epoch,
            'map_id': snapshot.map_id,
            'frame_id': snapshot.header.frame_id,
            'response_stamp_ns': stamp_ns(snapshot.header.stamp),
            'last_depth_source_stamp_ns': stamp_ns(snapshot.last_depth_source_stamp),
            'last_fusion_stamp_ns': stamp_ns(snapshot.last_fusion_stamp),
            'origin_m': [float(snapshot.origin.x), float(snapshot.origin.y),
                         float(snapshot.origin.z)],
            'map_size_m': [float(snapshot.map_size.x), float(snapshot.map_size.y),
                           float(snapshot.map_size.z)],
            'resolution_m': float(snapshot.resolution),
            'shape_xyz': list(shape),
            'data_order': str(snapshot.data_order),
            'unknown_voxel_count': int(snapshot.unknown_voxel_count),
            'free_voxel_count': int(snapshot.free_voxel_count),
            'occupied_voxel_count': int(snapshot.occupied_voxel_count),
            'inflated_voxel_count': int(snapshot.inflated_voxel_count),
        }
        outcome['status'] = 'captured'
        outcome['failure'] = None
    except Exception as exc:
        outcome['failure'] = str(exc)
    finally:
        if write_record:
            record_path.parent.mkdir(parents=True, exist_ok=True)
            temp = record_path.with_suffix('.json.tmp')
            temp.write_text(json.dumps(outcome, indent=2, ensure_ascii=False) + '\n',
                            encoding='utf-8')
            temp.replace(record_path)
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    print(json.dumps({'status': outcome['status'], 'failure': outcome['failure']},
                     ensure_ascii=False))
    # Missing observer evidence is a certificate failure, not a mission-runner
    # failure. The independent evaluator records that distinction explicitly.
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
