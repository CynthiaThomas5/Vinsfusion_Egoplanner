#!/usr/bin/env python3
"""Observe process/cgroup load, RTF, and exposed queue counters during N10 SITL.

This recorder is read-only. Its samples are offline evidence and never affect
task admission, cancellation, landing, or controller state.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.qos import qos_profile_sensor_data
from rosgraph_msgs.msg import Clock
from std_msgs.msg import String
from uav_interfaces.msg import LocalizationStatus, MapStatus
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from n10_vins_queue_metrics import summarize_queue_samples
from observer_window import (safe_session_terminal_observed, install_observer_stop_handlers,
                             restore_observer_stop_handlers)
from n10_run_identity import read_run_identity


ROOT = Path(__file__).resolve().parents[2]


def configured_queue_capacities():
    mapping_path = ROOT / 'config/components/mapping/ego_input.json'
    adapter_path = ROOT / 'src/own/uav_mapping/uav_mapping/adapter.py'
    capture_path = ROOT / 'config/n10_capture.json'
    vins_source = ROOT / 'src/vendor/vins_fusion/vins/src/estimator/estimator.cpp'
    vins_header = ROOT / 'src/vendor/vins_fusion/vins/src/estimator/estimator.h'
    vins_patch = ROOT / 'dependencies/patches/vins/0020-readonly-estimator-queue-high-water.patch'
    sources_path = ROOT / 'dependencies/sources.json'
    try:
        mapping = json.loads(mapping_path.read_text())
        adapter_text = adapter_path.read_text()
        capture = json.loads(capture_path.read_text())
        import re
        match = re.search(
            r'while len\(self\.pending_keyframe_depth\) > (\d+)', adapter_text)
        keyframe_limit = int(match.group(1)) if match else None
        return {
            'mapping_pending_depth_limit': mapping.get('pending_depth_size'),
            'mapping_pending_keyframe_depth_limit': keyframe_limit,
            'sensor_capture_rosbag_max_cache_bytes': (
                capture.get('payload', {}).get('rosbag_max_cache_bytes')),
            'sensor_capture_ros_subscription_depth': (
                capture.get('receipt_observer', {}).get(
                    'sensor_subscription_depth')),
            'sensor_capture_ros_subscription_queue_memory_budget_bytes': (
                capture.get('capacity_planning', {}).get(
                    'receipt_queue_memory_budget_bytes')),
            'resource_observer_ros_subscription_depth': 10,
            'sensor_observer_qos_profile': 'qos_profile_sensor_data',
            'vins_estimator_queue_capacity': 'unbounded_by_source; no cap or drop added',
            'vins_estimator_queue_observation': (
                '/vins_raw/<epoch>/estimator_telemetry.queue_metrics'),
            'vins_estimator_queue_observation_requires_patch_0020_build': True,
            'unexposed_or_unresolved': [],
            'source_sha256': {
                str(mapping_path.relative_to(ROOT)): hashlib.sha256(
                    mapping_path.read_bytes()).hexdigest(),
                str(adapter_path.relative_to(ROOT)): hashlib.sha256(
                    adapter_path.read_bytes()).hexdigest(),
                str(capture_path.relative_to(ROOT)): hashlib.sha256(
                    capture_path.read_bytes()).hexdigest(),
                str(vins_source.relative_to(ROOT)): hashlib.sha256(
                    vins_source.read_bytes()).hexdigest(),
                str(vins_header.relative_to(ROOT)): hashlib.sha256(
                    vins_header.read_bytes()).hexdigest(),
                str(vins_patch.relative_to(ROOT)): hashlib.sha256(
                    vins_patch.read_bytes()).hexdigest(),
                **{str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in [ROOT / 'dependencies/patches/vins/0021-readonly-native-work-queue.patch'] if p.is_file()},
                str(sources_path.relative_to(ROOT)): hashlib.sha256(
                    sources_path.read_bytes()).hexdigest(),
            },
        }
    except (OSError, ValueError, TypeError):
        return {'unresolved': True, 'unexposed_or_unresolved': ['all_queue_capacities']}


def read_text(path):
    try:
        return Path(path).read_text().strip()
    except (OSError, PermissionError):
        return None


def cgroup_snapshot(root=Path('/sys/fs/cgroup')):
    values = {}
    cpu_stat = read_text(root / 'cpu.stat')
    if cpu_stat:
        values['cpu_stat'] = {
            key: int(value) for key, value in
            (line.split() for line in cpu_stat.splitlines() if len(line.split()) == 2)
        }
    for name in ('cpu.max', 'memory.current', 'memory.peak', 'memory.max',
                 'pids.current', 'pids.max'):
        raw = read_text(root / name)
        if raw is not None:
            values[name.replace('.', '_')] = raw
    for name in ('memory.events', 'memory.stat'):
        raw = read_text(root / name)
        if raw:
            values[name.replace('.', '_')] = {
                key: int(value) for key, value in
                (line.split() for line in raw.splitlines() if len(line.split()) == 2)
            }
    return values


def process_snapshot(clock_ticks_per_second):
    processes = []
    proc_root = Path('/proc')
    for path in proc_root.iterdir():
        if not path.name.isdigit():
            continue
        try:
            stat = (path / 'stat').read_text()
            comm = stat[stat.index('(') + 1:stat.rindex(')')]
            fields = stat[stat.rindex(')') + 1:].split()
            status_lines = (path / 'status').read_text().splitlines()
            status = dict(line.split(':', 1) for line in status_lines if ':' in line)
            command = (path / 'cmdline').read_bytes().replace(b'\0', b' ').decode(
                errors='replace').strip()[:300]
            rss_kib = int(status.get('VmRSS', '0 kB').split()[0])
            hwm_kib = int(status.get('VmHWM', '0 kB').split()[0])
            processes.append({
                'pid': int(path.name),
                'comm': comm,
                'command': command,
                'cpu_ticks': int(fields[11]) + int(fields[12]),
                'rss_kib': rss_kib,
                'hwm_kib': hwm_kib,
                'threads': int(status.get('Threads', '0')),
                'cpu_clock_ticks_per_s': clock_ticks_per_second,
            })
        except (OSError, ValueError, IndexError):
            continue
    return processes


def stamp_ns(stamp):
    return int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)


def record(run, period_s, max_wall_s):
    rclpy.init()
    stop_request, previous_handlers = install_observer_stop_handlers()
    node = rclpy.create_node('n10_readonly_resource_observer')
    state = {
        'clock_ns': None, 'map': None, 'localization': None,
        'vins_queue_samples': [], 'vins_queue_telemetry_errors': [],
    }
    queue_subscriptions = {}
    clock = node.create_subscription(
        Clock, '/clock',
        lambda message: state.update(clock_ns=stamp_ns(message.clock)),
        qos_profile_sensor_data)
    mapping = node.create_subscription(MapStatus, '/mapping/status',
                                       lambda message: state.update(map=message), 10)
    def on_vins_queue_telemetry(message, epoch, topic):
        receipt_ns = time.monotonic_ns()
        try:
            payload = json.loads(message.data)
            state['vins_queue_samples'].append({
                'epoch': epoch,
                'topic': topic,
                'source_stamp_ns': payload.get('stamp_ns'),
                'receipt_monotonic_ns': receipt_ns,
                'sim_ns_at_receipt': state['clock_ns'],
                'queue_metrics': payload.get('queue_metrics'),
            })
        except (TypeError, ValueError) as exc:
            state['vins_queue_telemetry_errors'].append(
                f'{topic}:{type(exc).__name__}:{exc}')

    def on_localization(message):
        state['localization'] = message
        epoch = str(message.epoch)
        if not epoch:
            return
        topic = f'/vins_raw/s_{epoch}/estimator_telemetry'
        if topic in queue_subscriptions:
            return
        queue_subscriptions[topic] = node.create_subscription(
            String, topic,
            lambda payload, current_epoch=epoch, current_topic=topic:
                on_vins_queue_telemetry(payload, current_epoch, current_topic),
            50)

    localization = node.create_subscription(
        LocalizationStatus, '/localization/status', on_localization, 10)
    wall_start = time.monotonic()
    clock_ticks = os.sysconf('SC_CLK_TCK')
    samples = []
    previous_processes = {}
    previous_wall = wall_start
    previous_sim = None
    after_safe_terminal = None
    flight_record = run / 'flight.json'
    stop_reason = 'max_wall_s'
    try:
        while not stop_request.requested and time.monotonic() - wall_start < max_wall_s:
            rclpy.spin_once(node, timeout_sec=min(0.1, period_s))
            now = time.monotonic()
            safe_terminal = safe_session_terminal_observed(run)
            if safe_terminal:
                after_safe_terminal = after_safe_terminal or now
                if now - after_safe_terminal >= 3.0:
                    stop_reason = 'safe_session_terminal_plus_3s'
                    break
            if now - previous_wall < period_s:
                continue
            processes = process_snapshot(clock_ticks)
            process_by_pid = {item['pid']: item for item in processes}
            dt_wall = now - previous_wall
            for item in processes:
                old = previous_processes.get(item['pid'])
                if old is not None and dt_wall > 0.0:
                    item['cpu_percent_one_core'] = max(
                        0.0, (item['cpu_ticks'] - old) * 100.0 / clock_ticks / dt_wall)
            current_sim = state['clock_ns']
            map_status = state['map']
            localization_status = state['localization']
            sample = {
                'wall_elapsed_s': now - wall_start,
                'wall_interval_s': dt_wall,
                'sim_ns': current_sim,
                'sim_interval_s': ((current_sim - previous_sim) / 1e9
                                   if current_sim is not None and previous_sim is not None else None),
                'rtf_sim_over_wall': ((current_sim - previous_sim) / 1e9 / dt_wall
                                      if current_sim is not None and previous_sim is not None
                                      and dt_wall > 0.0 else None),
                'cpu_count_visible': os.cpu_count(),
                'cgroup': cgroup_snapshot(),
                'process_count': len(processes),
                'top_processes_by_rss': sorted(processes, key=lambda p: p['rss_kib'], reverse=True)[:20],
                'top_processes_by_cpu': sorted(
                    (p for p in processes if 'cpu_percent_one_core' in p),
                    key=lambda p: p.get('cpu_percent_one_core', 0.0), reverse=True)[:20],
                'map_queue_counters': ({
                    'epoch': map_status.epoch,
                    'map_id': map_status.map_id,
                    'pending_depth_count': int(map_status.pending_depth_count),
                    'pending_depth_high_water_count': int(map_status.pending_depth_high_water_count),
                    'dropped_depth_count': int(map_status.dropped_depth_count),
                    'forwarded_depth_count': int(map_status.forwarded_depth_count),
                    'keyframe_count': int(map_status.keyframe_count),
                    'keyframe_dropped_count': int(map_status.keyframe_dropped_count),
                    'keyframe_max_rgbd_stamp_delta_s': float(map_status.keyframe_max_rgbd_stamp_delta_s),
                } if map_status is not None else None),
                'localization_counters': ({
                    'epoch': localization_status.epoch,
                    'state': int(localization_status.state),
                    'valid': bool(localization_status.valid),
                    'accepted_optimized': int(localization_status.accepted_optimized),
                    'accepted_propagated': int(localization_status.accepted_propagated),
                    'normalized_cost': float(localization_status.normalized_cost),
                } if localization_status is not None else None),
                'observer_qos': {
                    'clock_subscription_depth': qos_profile_sensor_data.depth,
                    'clock_subscription_reliability': str(
                        qos_profile_sensor_data.reliability),
                    'map_status_subscription_depth': 10,
                    'localization_subscription_depth': 10,
                },
            }
            samples.append(sample)
            previous_processes = {pid: item['cpu_ticks'] for pid, item in process_by_pid.items()}
            previous_wall = now
            previous_sim = current_sim
        if stop_request.requested:
            stop_reason = ('observer_interrupted_after_safe_terminal'
                           if safe_session_terminal_observed(run)
                           else 'observer_interrupted_before_safe_terminal')
    except ExternalShutdownException:
        stop_reason = ('observer_interrupted_after_safe_terminal'
                       if safe_session_terminal_observed(run)
                       else 'observer_interrupted_before_safe_terminal')
    finally:
        node.destroy_subscription(clock)
        node.destroy_subscription(mapping)
        node.destroy_subscription(localization)
        for subscription in queue_subscriptions.values():
            node.destroy_subscription(subscription)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    restore_observer_stop_handlers(previous_handlers)
    return {
        'schema': 'n10-resource-observation/v1',
        'classification': 'offline diagnostic samples; no flight decision or runtime thresholds',
        'read_only': True,
        'truth_subscribed': False,
        'control_published': False,
        'run_id': run.name,
        'run_identity': read_run_identity(run,
            epoch=(state['map'].epoch if state['map'] is not None else None),
            map_id=(state['map'].map_id if state['map'] is not None else None)),
        'configured_queue_capacities': configured_queue_capacities(),
        'wall_duration_s': time.monotonic() - wall_start,
        'stop_reason': stop_reason,
        'safe_session_terminal_observed': safe_session_terminal_observed(run),
        'terminal_flight_record_observed': flight_record.is_file(),
        'observation_stop_reason': stop_reason,
        'sample_period_s': period_s,
        'cgroup_root': '/sys/fs/cgroup',
        'cpu_ticks_per_second': clock_ticks,
        'samples': samples,
        'vins_queue_telemetry_samples': state['vins_queue_samples'],
        'vins_queue_telemetry_errors': state['vins_queue_telemetry_errors'],
        'vins_queue_telemetry_topics': sorted(queue_subscriptions),
        'limitations': [
            'Process and cgroup counters are sampled; peaks between samples can be missed.',
            'Estimator queue telemetry is emitted per processed image; a stalled estimator may not emit a final post-stall sample.',
            'VINS queue high-water counters are process-lifetime observations; no queue cap, drop, admission, or control behavior is added.',
            'DDS middleware history occupancy is not reported by the VINS estimator telemetry.',
            'RTF is derived from successive /clock and wall samples, not Gazebo real-time factor internals.',
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--period-s', type=float, default=1.0)
    parser.add_argument('--max-wall-s', type=float, default=3600.0)
    args = parser.parse_args()
    if not args.run.is_dir():
        parser.error('run directory must exist')
    if args.period_s <= 0.0 or args.max_wall_s <= 0.0:
        parser.error('period and maximum duration must be positive')
    result = record(args.run.resolve(), args.period_s, args.max_wall_s)
    queue_rows = result.pop('vins_queue_telemetry_samples')
    queue_errors = result.pop('vins_queue_telemetry_errors')
    queue_path = args.run / 'n10-vins-queue-telemetry.jsonl'
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    with queue_path.open('x') as stream:
        for row in queue_rows:
            stream.write(json.dumps(row, separators=(',', ':'), allow_nan=False) + '\n')
    queue_summary = summarize_queue_samples(queue_rows)
    if queue_errors:
        queue_summary['status'] = 'INSUFFICIENT'
        queue_summary['errors'].extend(queue_errors)
    result['vins_estimator_queue_observation'] = queue_summary
    result['vins_queue_telemetry_artifact'] = {
        'path': queue_path.name,
        'row_count': len(queue_rows),
        'sha256': hashlib.sha256(queue_path.read_bytes()).hexdigest(),
        'observer_errors': queue_errors,
        'topics': result.pop('vins_queue_telemetry_topics'),
    }
    output = args.run / 'n10-resource-observation.json'
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'samples': len(result['samples']), 'stop_reason': result['stop_reason']}))


if __name__ == '__main__':
    main()
