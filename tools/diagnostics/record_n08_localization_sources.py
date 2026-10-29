#!/usr/bin/env python3
"""Read-only source/receipt timeline for N08 localization freshness failures."""
import argparse
import json
from pathlib import Path
import sys
import time

import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import (DurabilityPolicy, QoSProfile, ReliabilityPolicy,
                       qos_profile_sensor_data)
from rosgraph_msgs.msg import Clock
from std_msgs.msg import String
from uav_interfaces.msg import LocalizationStatus, MapStatus

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from n10_run_identity import read_run_identity
from n08_timeline_helpers import (bridge_timing_fields, clock_sample_due,
                                  health_metric_summary, stream_sample_due)


def stamp_ns(stamp):
    return int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--duration-wall-s', type=float, default=150.0)
    parser.add_argument('--clock-period-wall-s', type=float, default=0.1)
    parser.add_argument('--stream-period-wall-s', type=float, default=0.1)
    parser.add_argument('--output-stem', choices=(
        'n08-localization-source-timeline',
        'n08-prescan-localization-source-timeline'),
        default='n08-localization-source-timeline')
    args = parser.parse_args()
    if (not 1.0 <= args.duration_wall_s <= 1800.0
            or not 0.01 <= args.clock_period_wall_s <= 5.0
            or not 0.05 <= args.stream_period_wall_s <= 5.0):
        parser.error('duration or clock sample period is outside supported bounds')
    run = args.run_dir.resolve()
    destination = run / (args.output_stem + '.json')
    live_path = run / 'n08-localization-source-progress.json'
    node = None
    start = time.monotonic()
    start_monotonic_ns = time.monotonic_ns()
    start_wall_time_ns = time.time_ns()
    events = []
    topics = {}
    state = {'epoch': '', 'clock_ns': None, 'last_write': 0.0,
             'last_clock_record_mono_ns': None,
             'last_recorded_mono_by_stream': {},
             'last_transition_by_stream': {},
             'last_source_stamp_by_stream': {}}

    def add(stream, source_stamp_ns=None, **fields):
        receipt_monotonic_ns = time.monotonic_ns()
        events.append({
            'stream': stream,
            'receipt_wall_time_ns': time.time_ns(),
            'receipt_monotonic_ns': receipt_monotonic_ns,
            'wall_elapsed_s': (receipt_monotonic_ns - start_monotonic_ns) / 1e9,
            'clock_ns_at_receipt': state['clock_ns'],
            'source_stamp_ns': source_stamp_ns,
            **fields,
        })

    def add_sampled(stream, source_stamp_ns=None, transition=None, **fields):
        now_monotonic_ns = time.monotonic_ns()
        last_record_ns = state['last_recorded_mono_by_stream'].get(stream)
        previous_transition = state['last_transition_by_stream'].get(stream)
        transition_changed = (transition is not None
                              and transition != previous_transition)
        previous_source = state['last_source_stamp_by_stream'].get(stream)
        source_regression = (
            isinstance(source_stamp_ns, int) and source_stamp_ns > 0
            and isinstance(previous_source, int) and previous_source > 0
            and source_stamp_ns < previous_source)
        due = stream_sample_due(
            now_monotonic_ns, last_record_ns,
            int(args.stream_period_wall_s * 1e9),
            transition_changed=transition_changed,
            source_regression=source_regression)
        if isinstance(source_stamp_ns, int) and source_stamp_ns > 0:
            state['last_source_stamp_by_stream'][stream] = source_stamp_ns
        if not due:
            return
        state['last_recorded_mono_by_stream'][stream] = now_monotonic_ns
        if transition is not None:
            state['last_transition_by_stream'][stream] = transition
        if source_stamp_ns is not None:
            fields['source_timestamp_regression'] = bool(source_regression)
        add(stream, source_stamp_ns, **fields)

    def on_clock(message):
        previous = state['clock_ns']
        current = stamp_ns(message.clock)
        now_monotonic_ns = time.monotonic_ns()
        due, regression = clock_sample_due(
            previous, current, now_monotonic_ns,
            state['last_clock_record_mono_ns'],
            int(args.clock_period_wall_s * 1e9))
        state['clock_ns'] = current
        if due:
            add('clock', current, regression=regression)
            state['last_clock_record_mono_ns'] = now_monotonic_ns

    def on_status(message):
        state['epoch'] = message.epoch
        add_sampled('localization_status', stamp_ns(message.source_stamp),
            transition=(message.epoch, int(message.state), bool(message.valid),
                        message.reason),
            header_stamp_ns=stamp_ns(message.header.stamp), epoch=message.epoch,
            state=int(message.state), valid=bool(message.valid),
            reason=message.reason,
            accepted_optimized=int(message.accepted_optimized),
            accepted_propagated=int(message.accepted_propagated),
            normalized_cost=float(message.normalized_cost))
        if message.epoch and message.epoch not in topics:
            namespace = f'/vins_raw/s_{message.epoch}'
            telemetry = namespace + '/estimator_telemetry'
            optimized = namespace + '/odometry'
            propagated = namespace + '/imu_propagate'
            topics[message.epoch] = {
                'telemetry': telemetry,
                'raw_optimized': optimized,
                'raw_propagated': propagated,
            }
            node.create_subscription(String, telemetry, on_telemetry,
                                     qos_profile_sensor_data)
            node.create_subscription(Odometry, optimized,
                                     lambda msg, ep=message.epoch: on_odometry(
                                         'raw_optimized', ep, msg),
                                     qos_profile_sensor_data)
            node.create_subscription(Odometry, propagated,
                                     lambda msg, ep=message.epoch: on_odometry(
                                         'raw_propagated', ep, msg),
                                     qos_profile_sensor_data)

    def on_telemetry(message):
        try:
            metrics = json.loads(message.data)
            source = int(metrics.get('stamp_ns', 0))
            record = health_metric_summary(metrics)
            add_sampled('vins_telemetry', source,
                        transition=(record.get('initialized'),
                                    record.get('solver_usable'),
                                    record.get('termination_type'),
                                    record.get('cost_limit_exceeded')),
                        metrics=record)
        except (TypeError, ValueError, AttributeError) as exc:
            add_sampled('vins_telemetry_malformed', None, error=str(exc))

    def on_odometry(stream, epoch, message):
        pose = message.pose.pose.position
        add_sampled(stream, stamp_ns(message.header.stamp),
            epoch=epoch,
            localization_status_epoch_at_receipt=state['epoch'],
            epoch_matches_status=(not epoch or not state['epoch']
                                  or epoch == state['epoch']),
            frame_id=message.header.frame_id, child_frame_id=message.child_frame_id,
            position_xyz_m=[float(pose.x), float(pose.y), float(pose.z)])

    def frame_epoch(message):
        frame_id = message.header.frame_id
        if frame_id.startswith('odom_'):
            return frame_id[len('odom_'):]
        return ''

    def on_adapter_optimized(message):
        epoch = frame_epoch(message)
        on_odometry('adapter_optimized', epoch or state['epoch'], message)

    def on_adapter_propagated(message):
        epoch = frame_epoch(message)
        on_odometry('adapter_propagated', epoch or state['epoch'], message)

    def on_map_status(message):
        add_sampled('map_status', stamp_ns(message.last_depth_source_stamp),
            transition=(message.epoch, message.map_id, bool(message.input_ready),
                        bool(message.reset_acknowledged), message.reason),
            header_stamp_ns=stamp_ns(message.header.stamp), epoch=message.epoch,
            map_id=message.map_id, reset_acknowledged=bool(message.reset_acknowledged),
            input_ready=bool(message.input_ready), reason=message.reason,
            last_occupancy_stamp_ns=stamp_ns(message.last_occupancy_stamp),
            pending_depth_count=int(message.pending_depth_count),
            dropped_depth_count=int(message.dropped_depth_count))

    def on_bridge_detail(message):
        timing = bridge_timing_fields(message.data)
        transition = tuple(timing.get(key) for key in (
            'phase', 'reason', 'px4_time_domain_valid',
            'px4_timestamp_error', 'odometry_time_error'))
        add_sampled('px4_bridge_detail', None, transition=transition, **timing)

    def summarize():
        grouped = {}
        for row in events:
            grouped.setdefault(row['stream'], []).append(row)
        result = {}
        for stream, rows in grouped.items():
            source = [row['source_stamp_ns'] for row in rows
                      if isinstance(row.get('source_stamp_ns'), int)
                      and row['source_stamp_ns'] > 0]
            receipt = [row['wall_elapsed_s'] for row in rows]
            source_gaps = [b - a for a, b in zip(source, source[1:])]
            receipt_gaps = [b - a for a, b in zip(receipt, receipt[1:])]
            max_source_gap = max((gap for gap in source_gaps if gap >= 0), default=None)
            source_clock_ages = [
                (row['clock_ns_at_receipt'] - row['source_stamp_ns']) / 1e9
                for row in rows
                if isinstance(row.get('clock_ns_at_receipt'), int)
                and isinstance(row.get('source_stamp_ns'), int)
                and row['source_stamp_ns'] > 0]
            result[stream] = {
                'count': len(rows),
                'first_wall_elapsed_s': receipt[0] if receipt else None,
                'last_wall_elapsed_s': receipt[-1] if receipt else None,
                'first_receipt_wall_time_ns': (
                    rows[0].get('receipt_wall_time_ns') if rows else None),
                'last_receipt_wall_time_ns': (
                    rows[-1].get('receipt_wall_time_ns') if rows else None),
                'first_source_stamp_ns': source[0] if source else None,
                'last_source_stamp_ns': source[-1] if source else None,
                'max_positive_source_gap_s': (None if max_source_gap is None
                                              else max_source_gap / 1e9),
                'negative_source_gap_count': sum(gap < 0 for gap in source_gaps),
                'max_receipt_gap_wall_s': max(receipt_gaps, default=None),
                'source_clock_age_at_receipt_s': {
                    'minimum': min(source_clock_ages) if source_clock_ages else None,
                    'maximum': max(source_clock_ages) if source_clock_ages else None,
                },
            }
        return result

    try:
        rclpy.init()
        node = Node('n08_localization_source_timeline')
        status_qos = QoSProfile(depth=100,
                                reliability=ReliabilityPolicy.RELIABLE,
                                durability=DurabilityPolicy.TRANSIENT_LOCAL)
        node.create_subscription(Clock, '/clock', on_clock, qos_profile_sensor_data)
        node.create_subscription(LocalizationStatus, '/localization/status',
                                 on_status, status_qos)
        node.create_subscription(
            Odometry, '/localization/optimized_imu_odom',
            on_adapter_optimized, qos_profile_sensor_data)
        node.create_subscription(
            Odometry, '/localization/imu_odom',
            on_adapter_propagated, qos_profile_sensor_data)
        node.create_subscription(MapStatus, '/mapping/status', on_map_status,
                                 status_qos)
        node.create_subscription(String, '/uav_px4_bridge/status/detail',
                                 on_bridge_detail, 10)

        deadline = start + args.duration_wall_s
        stop_reason = 'wall_timeout'
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=0.05)
            now = time.monotonic()
            report_exists = (run / 'flight.json').is_file()
            failed_before_prescan = (
                (run / 'n05-fixture.exitcode').is_file()
                and not (run / 'n05-prescan-ready.json').is_file())
            post_release_path = run / 'n05-post-release/n05-live-entry-check.json'
            post_release_rejected = False
            if post_release_path.is_file():
                try:
                    post_release_rejected = (
                        json.loads(post_release_path.read_text()).get('accepted') is not True)
                except (OSError, ValueError):
                    pass
            stop_requested = (run / (args.output_stem + '.stop')).is_file()
            n05_path = run / 'n05-current-area/n05-live-entry-check.json'
            n05_rejected = False
            if n05_path.is_file():
                try:
                    n05_rejected = json.loads(n05_path.read_text()).get('accepted') is not True
                except (OSError, ValueError):
                    pass
            if report_exists or n05_rejected:
                stop_reason = ('flight_report_written' if report_exists
                               else 'n05_current_area_rejected')
                break
            if failed_before_prescan or post_release_rejected or stop_requested:
                stop_reason = ('support_scan_failed_before_prescan'
                               if failed_before_prescan else
                               'n05_post_release_rejected' if post_release_rejected else
                               'stop_marker')
                break
            if now - state['last_write'] >= 1.0:
                state['last_write'] = now
                live = {'wall_time_ns': time.time_ns(),
                        'wall_elapsed_s': now - start,
                        'event_count': len(events),
                        'latest_event': events[-1] if events else None,
                        'observed_epoch': state['epoch']}
                temp = live_path.with_suffix('.json.tmp')
                temp.write_text(json.dumps(live, ensure_ascii=False) + '\n',
                                encoding='utf-8')
                temp.replace(live_path)

        all_topic_names = {
            '/clock', '/localization/status',
            '/localization/optimized_imu_odom',
            '/localization/imu_odom', '/mapping/status',
            '/uav_px4_bridge/status/detail',
        }
        for group in topics.values():
            all_topic_names.update(group.values())
        endpoint_topics = {}
        for topic in sorted(all_topic_names):
            endpoint_topics[topic] = [
                {'node_name': info.node_name,
                 'node_namespace': info.node_namespace,
                 'endpoint_gid': str(info.endpoint_gid)}
                for info in node.get_publishers_info_by_topic(topic)]
        result = {
            'schema': 'n08-localization-source-timeline/v1',
            'scope': 'Read-only ROS timestamps and receipt timeline; no control, truth or map mutation',
            'run_id': run.name,
            'run_identity': read_run_identity(run, epoch=state['epoch']),
            'duration_wall_s': args.duration_wall_s,
            'clock_sample_period_wall_s': args.clock_period_wall_s,
            'stream_sample_period_wall_s': args.stream_period_wall_s,
            'stream_sampling_policy': (
                'per-stream wall-time decimation; LocalizationStatus, VINS health, '
                'MapStatus, bridge state changes, and source timestamp regressions '
                'are retained immediately'),
            'capture_started_wall_time_ns': start_wall_time_ns,
            'capture_finished_wall_time_ns': time.time_ns(),
            'stop_reason': stop_reason,
            'observed_epoch': state['epoch'],
            'raw_topics_by_epoch': topics,
            'static_topics': sorted(all_topic_names.difference(
                topic for group in topics.values() for topic in group.values())),
            'publisher_nodes_at_exit': endpoint_topics,
            'stream_summary': summarize(),
            'clock_regression_event_count': sum(
                row.get('stream') == 'clock' and row.get('regression') is True
                for row in events),
            'events': events,
        }
    except Exception as exc:
        result = {
            'schema': 'n08-localization-source-timeline/v1',
            'scope': 'Read-only ROS timestamps and receipt timeline; no control, truth or map mutation',
            'run_id': run.name,
            'capture_started_wall_time_ns': start_wall_time_ns,
            'capture_finished_wall_time_ns': time.time_ns(),
            'status': 'failed',
            'failure': str(exc),
            'events': events,
        }
    finally:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp = destination.with_suffix('.json.tmp')
        temp.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n',
                        encoding='utf-8')
        temp.replace(destination)
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    print(json.dumps({'run_id': run.name, 'events': len(result.get('events', [])),
                      'epoch': result.get('observed_epoch'),
                      'failure': result.get('failure')}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
