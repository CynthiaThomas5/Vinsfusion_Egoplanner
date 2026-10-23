#!/usr/bin/env python3
"""Read-only trace of the live adapter -> plan_env depth fusion path.

The optional fault mode republishes depth unchanged and withholds a bounded
window of input samples. It never publishes navigation goals or PX4 controls.
"""
import argparse
import json
import math
from pathlib import Path
import signal
import threading
import time

import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.executors import MultiThreadedExecutor
from rclpy.qos import (QoSProfile, DurabilityPolicy, ReliabilityPolicy,
                       qos_profile_sensor_data)
from rclpy.signals import SignalHandlerOptions
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from px4_msgs.msg import VehicleStatus
from rosgraph_msgs.msg import Clock as RosClock
from sensor_msgs.msg import Image, PointCloud2
from std_msgs.msg import String
from uav_interfaces.msg import (DepthHealth, LocalizationStatus, MapStatus,
                                NavigationCommand)
from uav_interfaces.srv import QueryOccupancySphere


def stamp_ns(stamp):
    return stamp.sec * 1_000_000_000 + stamp.nanosec


def quantile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


def interval_summary(values_ns):
    intervals = [b - a for a, b in zip(values_ns, values_ns[1:]) if b > a]
    return {
        'count': len(intervals),
        'p50_s': round(quantile(intervals, 0.50) / 1e9, 6) if intervals else None,
        'p95_s': round(quantile(intervals, 0.95) / 1e9, 6) if intervals else None,
        'max_s': round(max(intervals) / 1e9, 6) if intervals else None,
    }


def duration_summary(samples, key, end_wall_elapsed_s=None):
    if not samples:
        return {'sample_count': 0, 'max_true_s': None, 'max_false_s': None}
    true_durations = []
    false_durations = []
    run_state = bool(samples[0][key])
    run_start = samples[0]['wall_elapsed_s']
    for sample in samples[1:]:
        state = bool(sample[key])
        if state == run_state:
            continue
        duration = max(0.0, sample['wall_elapsed_s'] - run_start)
        (true_durations if run_state else false_durations).append(duration)
        run_state = state
        run_start = sample['wall_elapsed_s']
    end = (samples[-1]['wall_elapsed_s'] if end_wall_elapsed_s is None
           else max(samples[-1]['wall_elapsed_s'], end_wall_elapsed_s))
    duration = max(0.0, end - run_start)
    (true_durations if run_state else false_durations).append(duration)
    return {
        'sample_count': len(samples),
        'max_true_s': round(max(true_durations), 6) if true_durations else 0.0,
        'max_false_s': round(max(false_durations), 6) if false_durations else 0.0,
    }


def build_summary(report):
    received = [e for e in report['ego_fusion_trace'] if e.get('phase') == 'ego_received']
    fused = [e for e in report['ego_fusion_trace'] if e.get('phase') == 'fused']
    queries = report['map_query_samples']
    statuses = report['map_status_samples']
    output_stamps = sorted({s['source_stamp_ns'] for s in report['adapter_depth_output_samples']})
    pose_stamps = sorted({s['source_stamp_ns'] for s in report['adapter_pose_output_samples']})
    raw_stamps = [s['source_stamp_ns'] for s in report['depth_input_samples']]
    fusion_ros_stamps = [e['fusion_ros_stamp_ns'] for e in fused]
    fusion_source_stamps = [e['pose_source_stamp_ns'] for e in fused]
    receive_stamps = [e['pose_source_stamp_ns'] for e in received]
    ego_synced_stamp_mismatch_count = sum(
        1 for e in received if e.get('image_source_stamp_ns') != e.get('pose_source_stamp_ns'))
    source_age_at_callback = [
        (e['callback_ros_stamp_ns'] - e['pose_source_stamp_ns']) / 1e9
        for e in received if e.get('callback_ros_stamp_ns', 0) >= e['pose_source_stamp_ns'] > 0
    ]
    source_age_at_fusion = [
        (e['fusion_ros_stamp_ns'] - e['pose_source_stamp_ns']) / 1e9
        for e in fused if e.get('fusion_ros_stamp_ns', 0) >= e['pose_source_stamp_ns'] > 0
    ]
    callback_to_fusion_s = [
        (e['fusion_monotonic_ns'] - e['callback_monotonic_ns']) / 1e9
        for e in fused if e.get('fusion_monotonic_ns', 0) >= e.get('callback_monotonic_ns', 0) > 0
    ]
    received_by_source = {e['image_source_stamp_ns']: e for e in received}
    status_by_source = {}
    for status in statuses:
        source = status['last_depth_source_stamp_ns']
        publish_ns = status['last_depth_forward_monotonic_ns']
        if source > 0 and publish_ns > 0:
            status_by_source[source] = publish_ns
    publish_to_callback_s = [
        (received_by_source[source]['callback_monotonic_ns'] - publish_ns) / 1e9
        for source, publish_ns in status_by_source.items()
        if source in received_by_source
    ]
    ready_queries = [q for q in queries if q['accepted']]
    query_age_s = [q['source_age_at_query_s'] for q in ready_queries
                   if q.get('source_age_at_query_s') is not None]
    query_ready_sim_stamps = [q['response_stamp_ns'] for q in ready_queries
                              if q.get('response_stamp_ns', 0) > 0]
    ready_statuses = [s for s in statuses if s['input_ready']]
    epochs = sorted({e.get('epoch', '') for e in received + fused if e.get('epoch')})
    map_ids = sorted({s['map_id'] for s in statuses if s.get('map_id')})
    fusion_ids = {}
    for event in fused:
        identity = (event.get('epoch', ''), event.get('map_id', ''))
        fusion_ids.setdefault(identity, []).append(event)
    fusion_counter_gaps = []
    for identity, events in fusion_ids.items():
        counts = [event.get('fused_count', 0) for event in events if event.get('fused_count', 0) > 0]
        gaps = [following - current - 1 for current, following in zip(counts, counts[1:])
                if following > current + 1]
        if gaps:
            fusion_counter_gaps.append({
                'epoch': identity[0], 'map_id': identity[1], 'missing_trace_events': sum(gaps)})
    receive_ids = {}
    for event in received:
        identity = (event.get('epoch', ''), event.get('map_id', ''))
        receive_ids.setdefault(identity, []).append(event)
    receive_counter_gaps = []
    for identity, events in receive_ids.items():
        counts = [event.get('callback_count', 0) for event in events
                  if event.get('callback_count', 0) > 0]
        gaps = [following - current - 1 for current, following in zip(counts, counts[1:])
                if following > current + 1]
        if gaps:
            receive_counter_gaps.append({
                'epoch': identity[0], 'map_id': identity[1], 'missing_trace_events': sum(gaps)})
    ready_duration = duration_summary(statuses, 'input_ready', report.get('wall_seconds'))
    query_max_gap = (
        max(b - a for a, b in zip(query_ready_sim_stamps, query_ready_sim_stamps[1:])) / 1e9
        if len(query_ready_sim_stamps) > 1 else None
    )
    # A sphere query uses a stricter service guard than the planner's curve
    # admission: it may reject while a new depth pair is pending even though
    # the last completed fusion remains fresh. Fusion intervals/ages are the
    # authoritative continuous readiness evidence; keep service rejects visible.
    query_gate = len(ready_queries) >= 2 and bool(query_age_s) and max(query_age_s) <= 0.4
    first_ready_index = next((i for i, sample in enumerate(statuses) if sample['input_ready']), None)
    status_after_ready = statuses[first_ready_index:] if first_ready_index is not None else []
    status_ready_after_bootstrap = bool(status_after_ready) and all(
        sample['input_ready'] for sample in status_after_ready)
    ready_duration_after_bootstrap = duration_summary(
        status_after_ready, 'input_ready', report.get('wall_seconds'))
    fusion_ros_interval = interval_summary(fusion_ros_stamps)
    fusion_source_interval = interval_summary(fusion_source_stamps)
    fusion_gate = (bool(fused) and bool(source_age_at_fusion)
                   and max(source_age_at_callback, default=math.inf) <= 0.4
                   and max(source_age_at_fusion) <= 0.4
                   and fusion_ros_interval['max_s'] is not None
                   and fusion_ros_interval['max_s'] <= 0.4
                   and fusion_source_interval['max_s'] is not None
                   and fusion_source_interval['max_s'] <= 0.4
                   and not ego_synced_stamp_mismatch_count
                   and not fusion_counter_gaps and not receive_counter_gaps)
    queue_gate = max((s['pending_depth_high_water_count'] for s in statuses), default=0) <= 8
    return {
        'raw_depth_count': len(report['depth_input_samples']),
        'adapter_depth_output_count': len(report['adapter_depth_output_samples']),
        'adapter_pose_output_count': len(report['adapter_pose_output_samples']),
        'adapter_depth_pose_exact_stamp_pairs': len(set(output_stamps) & set(pose_stamps)),
        'ego_synced_pair_callback_count': len(received),
        'ego_synced_stamp_mismatch_count': ego_synced_stamp_mismatch_count,
        'plan_env_fusion_complete_count': len(fused),
        'map_query_count': len(queries),
        'map_query_accepted_count': len(ready_queries),
        'map_status_sample_count': len(statuses),
        'map_status_ready_sample_count': len(ready_statuses),
        'map_status_input_ready_duration_s': ready_duration,
        'map_status_input_ready_after_bootstrap_duration_s': ready_duration_after_bootstrap,
        'epochs_seen': epochs,
        'map_ids_seen': map_ids,
        'raw_depth_source_interval': interval_summary(raw_stamps),
        'ego_received_source_interval': interval_summary(receive_stamps),
        'fusion_complete_ros_interval': interval_summary(fusion_ros_stamps),
        'fusion_complete_source_interval': interval_summary(fusion_source_stamps),
        'fusion_trace_counter_gaps': fusion_counter_gaps,
        'ego_receive_trace_counter_gaps': receive_counter_gaps,
        'callback_source_age_s': {
            'p95': round(quantile(source_age_at_callback, 0.95), 6) if source_age_at_callback else None,
            'max': round(max(source_age_at_callback), 6) if source_age_at_callback else None,
        },
        'fusion_source_age_s': {
            'p95': round(quantile(source_age_at_fusion, 0.95), 6) if source_age_at_fusion else None,
            'max': round(max(source_age_at_fusion), 6) if source_age_at_fusion else None,
        },
        'adapter_publish_to_ego_callback_wall_s': {
            'count': len(publish_to_callback_s),
            'p95': round(quantile(publish_to_callback_s, 0.95), 6) if publish_to_callback_s else None,
            'max': round(max(publish_to_callback_s), 6) if publish_to_callback_s else None,
        },
        'ego_callback_to_fusion_wall_s': {
            'count': len(callback_to_fusion_s),
            'p95': round(quantile(callback_to_fusion_s, 0.95), 6) if callback_to_fusion_s else None,
            'max': round(max(callback_to_fusion_s), 6) if callback_to_fusion_s else None,
        },
        'successful_query_source_age_s': {
            'p95': round(quantile(query_age_s, 0.95), 6) if query_age_s else None,
            'max': round(max(query_age_s), 6) if query_age_s else None,
        },
        'successful_query_max_sim_gap_s': round(query_max_gap, 6) if query_max_gap is not None else None,
        'current_identity_query_accepted_count': len(ready_queries),
        'map_query_acceptance_ratio': (
            round(len(ready_queries) / len(queries), 6) if queries else 0.0),
        'map_query_rejections_by_reason': {
            reason: sum(1 for q in queries if not q['accepted'] and q.get('reason') == reason)
            for reason in sorted({q.get('reason', '') for q in queries if not q['accepted']})
        },
        'stale_identity_query_count': sum(1 for q in queries if q.get('query_kind') == 'stale_identity'),
        'stale_identity_query_rejected_count': sum(
            1 for q in queries if q.get('query_kind') == 'stale_identity' and not q['accepted']),
        'reset_trace_event_count': sum(
            1 for e in report['ego_fusion_trace'] if e.get('phase') == 'reset'),
        'identity_change_count': max(0, len(map_ids) - 1),
        'pending_depth_high_water_count': max(
            (s['pending_depth_high_water_count'] for s in statuses), default=0),
        'pending_depth_count_max': max((s['pending_depth_count'] for s in statuses), default=0),
        'dropped_depth_count_max': max((s['dropped_depth_count'] for s in statuses), default=0),
        'vehicle_arming_states': sorted(set(report['vehicle_arming_states'])),
        'navigation_command_count': len(report['navigation_commands']),
        'cgroup_memory_peak_bytes': max(
            (s['memory_current_bytes'] for s in report['cgroup_resource_samples']
             if s['memory_current_bytes'] is not None), default=0),
        'cgroup_cpu_usage_usec_delta': (
            report['cgroup_resource_samples'][-1]['cpu_usage_usec']
            - report['cgroup_resource_samples'][0]['cpu_usage_usec']
            if len(report['cgroup_resource_samples']) > 1 else 0
        ),
        'diagnostic_freshness_gate': {
            'limit_s': 0.4,
            'query_age_pass': query_gate,
            'fusion_age_and_interval_pass': fusion_gate,
            'adapter_ready_after_bootstrap_pass': status_ready_after_bootstrap,
            'adapter_pending_queue_pass': queue_gate,
            'pass': query_gate and fusion_gate and status_ready_after_bootstrap and queue_gate,
        },
    }


class DepthFusionContinuityProbe:
    def __init__(self, output, seconds, query_period_s, fault_input_topic,
                 fault_drop_after_forwarded, fault_drop_duration_s):
        self.node = rclpy.create_node('depth_fusion_continuity_probe')
        self.output = Path(output)
        self.seconds = seconds
        self.query_period_s = query_period_s
        self.fault_input_topic = fault_input_topic
        self.fault_drop_after_forwarded = fault_drop_after_forwarded
        self.fault_drop_duration_s = fault_drop_duration_s
        self.started_monotonic_ns = time.monotonic_ns()
        self.started_wall = time.time()
        self.last_clock_stamp_ns = 0
        self.latest_map = None
        self.latest_identity = None
        self.retired_identity_queue = []
        self.retired_identity_requested = set()
        self.latest_odom = None
        self.query_inflight = False
        self.active_query_future = None
        self.stopping = False
        self.fault_forwarded_count = 0
        self.fault_drop_until_ns = 0
        self.fault_drop_started_ns = 0
        self.fault_drop_completed = False
        self.output.parent.mkdir(parents=True, exist_ok=True)
        if self.output.exists():
            raise FileExistsError(self.output)

        self.depth_input_samples = []
        self.adapter_depth_output_samples = []
        self.adapter_pose_output_samples = []
        self.depth_health_history = []
        self.localization_history = []
        self.map_status_samples = []
        self.map_samples = []
        self.ego_fusion_trace = []
        self.map_query_samples = []
        self.vehicle_arming_states = []
        self.navigation_commands = []
        self.cgroup_resource_samples = []
        self.fault_events = []
        self.observer_errors = []
        self.last_depth_health = None
        self.last_localization = None

        status_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                                durability=DurabilityPolicy.TRANSIENT_LOCAL)
        output_qos = QoSProfile(depth=100, reliability=ReliabilityPolicy.RELIABLE)
        self.node.create_subscription(
            Image, fault_input_topic or '/sensors/d435i/depth', self.on_depth_input,
            qos_profile_sensor_data)
        self.node.create_subscription(
            Image, '/drone_0_depth_image', self.on_adapter_depth, output_qos)
        self.node.create_subscription(
            PoseStamped, '/drone_0_camera_pose', self.on_adapter_pose, output_qos)
        self.node.create_subscription(
            DepthHealth, '/mapping/depth_health', self.on_depth_health, status_qos)
        self.node.create_subscription(
            LocalizationStatus, '/localization/status', self.on_localization, status_qos)
        self.node.create_subscription(
            MapStatus, '/mapping/status', self.on_map_status, status_qos)
        self.node.create_subscription(
            PointCloud2, '/grid_map/occupancy', self.on_map, qos_profile_sensor_data)
        self.node.create_subscription(
            String, '/mapping/depth_fusion_trace', self.on_fusion_trace,
            QoSProfile(depth=100, reliability=ReliabilityPolicy.BEST_EFFORT))
        self.node.create_subscription(
            RosClock, '/clock', self.on_clock,
            QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT))
        self.node.create_subscription(
            Odometry, '/localization/optimized_imu_odom', self.on_odom,
            qos_profile_sensor_data)
        self.node.create_subscription(
            VehicleStatus, '/fmu/out/vehicle_status_v1', self.on_vehicle_status,
            qos_profile_sensor_data)
        self.node.create_subscription(
            NavigationCommand, '/navigation/ego_goal', self.navigation_commands.append, 10)
        self.map_query = self.node.create_client(
            QueryOccupancySphere, '/mapping/query_occupancy_sphere')
        self.depth_relay_pub = (self.node.create_publisher(
            Image, '/sensors/d435i/depth', qos_profile_sensor_data)
            if fault_input_topic else None)
        self.query_timer = self.node.create_timer(
            query_period_s, self.on_query_timer,
            clock=Clock(clock_type=ClockType.STEADY_TIME))
        self.resource_timer = self.node.create_timer(
            1.0, self.on_resource_timer,
            clock=Clock(clock_type=ClockType.STEADY_TIME))

    def elapsed(self):
        return (time.monotonic_ns() - self.started_monotonic_ns) / 1e9

    def on_depth_input(self, msg):
        now_ns = time.monotonic_ns()
        self.depth_input_samples.append({
            'source_stamp_ns': stamp_ns(msg.header.stamp),
            'monotonic_ns': now_ns,
            'wall_elapsed_s': round((now_ns - self.started_monotonic_ns) / 1e9, 6),
            'clock_stamp_ns_at_receipt': self.last_clock_stamp_ns,
        })
        if self.depth_relay_pub is None:
            return
        if (self.fault_drop_started_ns == 0
                and self.fault_forwarded_count >= self.fault_drop_after_forwarded):
            self.fault_drop_started_ns = now_ns
            self.fault_drop_until_ns = now_ns + int(self.fault_drop_duration_s * 1e9)
            self.fault_events.append({
                'event': 'depth_drop_started',
                'monotonic_ns': now_ns,
                'source_stamp_ns': stamp_ns(msg.header.stamp),
                'forwarded_before_drop': self.fault_forwarded_count,
            })
        if self.fault_drop_started_ns and now_ns < self.fault_drop_until_ns:
            return
        if self.fault_drop_started_ns and not self.fault_drop_completed:
            self.fault_drop_completed = True
            self.fault_events.append({
                'event': 'depth_drop_ended',
                'monotonic_ns': now_ns,
                'source_stamp_ns': stamp_ns(msg.header.stamp),
            })
        self.depth_relay_pub.publish(msg)
        self.fault_forwarded_count += 1

    def on_adapter_depth(self, msg):
        now_ns = time.monotonic_ns()
        self.adapter_depth_output_samples.append({
            'source_stamp_ns': stamp_ns(msg.header.stamp),
            'monotonic_ns': now_ns,
            'wall_elapsed_s': round((now_ns - self.started_monotonic_ns) / 1e9, 6),
            'clock_stamp_ns_at_receipt': self.last_clock_stamp_ns,
        })

    def on_adapter_pose(self, msg):
        now_ns = time.monotonic_ns()
        self.adapter_pose_output_samples.append({
            'source_stamp_ns': stamp_ns(msg.header.stamp),
            'frame_id': msg.header.frame_id,
            'monotonic_ns': now_ns,
            'wall_elapsed_s': round((now_ns - self.started_monotonic_ns) / 1e9, 6),
            'clock_stamp_ns_at_receipt': self.last_clock_stamp_ns,
        })

    def on_depth_health(self, msg):
        state = (int(msg.state), bool(msg.valid), msg.reason)
        if state != self.last_depth_health:
            self.depth_health_history.append({
                'wall_elapsed_s': round(self.elapsed(), 6),
                'monotonic_ns': time.monotonic_ns(),
                'state': state[0], 'valid': state[1], 'reason': state[2],
                'source_stamp_ns': stamp_ns(msg.source_stamp),
                'received_count': int(msg.received_count),
            })
            self.last_depth_health = state

    def on_localization(self, msg):
        state = (msg.epoch, int(msg.state), bool(msg.valid), msg.reason)
        if state != self.last_localization:
            self.localization_history.append({
                'wall_elapsed_s': round(self.elapsed(), 6),
                'monotonic_ns': time.monotonic_ns(),
                'epoch': msg.epoch, 'state': int(msg.state), 'valid': bool(msg.valid),
                'reason': msg.reason, 'frame_id': msg.header.frame_id,
            })
            self.last_localization = state

    def on_map_status(self, msg):
        now_ns = time.monotonic_ns()
        sample = {
            'header_stamp_ns': stamp_ns(msg.header.stamp),
            'header_frame_id': msg.header.frame_id,
            'monotonic_ns': now_ns,
            'wall_elapsed_s': round((now_ns - self.started_monotonic_ns) / 1e9, 6),
            'epoch': msg.epoch,
            'map_id': msg.map_id,
            'reset_acknowledged': bool(msg.reset_acknowledged),
            'input_ready': bool(msg.input_ready),
            'reason': msg.reason,
            'last_depth_source_stamp_ns': stamp_ns(msg.last_depth_source_stamp),
            'last_occupancy_stamp_ns': stamp_ns(msg.last_occupancy_stamp),
            'occupancy_cloud_received': bool(msg.occupancy_cloud_received),
            'occupied_point_count': int(msg.occupied_point_count),
            'forwarded_depth_count': int(msg.forwarded_depth_count),
            'depth_callback_count': int(msg.depth_callback_count),
            'pending_depth_count': int(msg.pending_depth_count),
            'pending_depth_high_water_count': int(msg.pending_depth_high_water_count),
            'dropped_depth_count': int(msg.dropped_depth_count),
            'last_depth_forward_monotonic_ns': int(msg.last_depth_forward_monotonic_ns),
            'calibration_sha256': msg.calibration_sha256,
            'input_config_sha256': msg.input_config_sha256,
            'keyframe_count': int(msg.keyframe_count),
            'keyframe_dropped_count': int(msg.keyframe_dropped_count),
        }
        self.map_status_samples.append(sample)
        identity = (msg.epoch, msg.map_id)
        if self.latest_identity and identity != self.latest_identity:
            retired = self.latest_identity
            if retired[0] and retired[1] and retired not in self.retired_identity_requested:
                self.retired_identity_queue.append(retired)
                self.retired_identity_requested.add(retired)
        if identity[0] and identity[1]:
            self.latest_identity = identity
        self.latest_map = msg

    def on_map(self, msg):
        now_ns = time.monotonic_ns()
        self.map_samples.append({
            'source_stamp_ns': stamp_ns(msg.header.stamp),
            'frame_id': msg.header.frame_id,
            'monotonic_ns': now_ns,
            'wall_elapsed_s': round((now_ns - self.started_monotonic_ns) / 1e9, 6),
            'occupied_point_count': int(msg.width) * int(msg.height),
        })

    def on_fusion_trace(self, msg):
        now_ns = time.monotonic_ns()
        try:
            event = json.loads(msg.data)
            event['observer_monotonic_ns'] = now_ns
            event['observer_wall_elapsed_s'] = round(
                (now_ns - self.started_monotonic_ns) / 1e9, 6)
            self.ego_fusion_trace.append(event)
        except (json.JSONDecodeError, TypeError) as exc:
            self.observer_errors.append({'kind': 'fusion_trace_parse', 'error': str(exc)})

    def on_clock(self, msg):
        self.last_clock_stamp_ns = stamp_ns(msg.clock)

    def on_odom(self, msg):
        self.latest_odom = msg

    def on_vehicle_status(self, msg):
        self.vehicle_arming_states.append(int(msg.arming_state))

    def on_query_timer(self):
        if self.stopping or self.query_inflight or self.latest_map is None or self.latest_odom is None:
            return
        if not self.map_query.service_is_ready() or not self.latest_map.epoch or not self.latest_map.map_id:
            return
        request = QueryOccupancySphere.Request()
        query_kind = 'current'
        expected_identity = (self.latest_map.epoch, self.latest_map.map_id)
        if self.latest_map.reset_acknowledged and self.retired_identity_queue:
            expected_identity = self.retired_identity_queue.pop(0)
            query_kind = 'stale_identity'
        request.expected_epoch, request.expected_map_id = expected_identity
        request.frame_id = self.latest_map.header.frame_id
        request.center = self.latest_odom.pose.pose.position
        request.radius_m = 0.05
        start_ns = time.monotonic_ns()
        future = self.map_query.call_async(request)
        self.active_query_future = future
        self.query_inflight = True
        future.add_done_callback(lambda f, begin=start_ns, expected=expected_identity,
                                 kind=query_kind:
                                 self.on_query_done(f, begin, expected, kind))

    def on_query_done(self, future, start_ns, expected, query_kind):
        done_ns = time.monotonic_ns()
        self.query_inflight = False
        self.active_query_future = None
        try:
            response = future.result()
            response_stamp_ns = stamp_ns(response.header.stamp)
            source_stamp_ns = stamp_ns(response.last_depth_source_stamp)
            self.map_query_samples.append({
                'monotonic_ns': done_ns,
                'wall_elapsed_s': round((done_ns - self.started_monotonic_ns) / 1e9, 6),
                'round_trip_s': round((done_ns - start_ns) / 1e9, 6),
                'expected_epoch': expected[0],
                'expected_map_id': expected[1],
                'query_kind': query_kind,
                'accepted': bool(response.accepted),
                'free': bool(response.free),
                'reason': response.reason,
                'response_epoch': response.epoch,
                'response_map_id': response.map_id,
                'response_frame_id': response.header.frame_id,
                'response_stamp_ns': response_stamp_ns,
                'depth_source_stamp_ns': source_stamp_ns,
                'fusion_stamp_ns': stamp_ns(response.last_fusion_stamp),
                'source_age_at_query_s': (
                    round((response_stamp_ns - source_stamp_ns) / 1e9, 6)
                    if response_stamp_ns >= source_stamp_ns > 0 else None),
                'unknown_count': int(response.unknown_count),
                'free_count': int(response.free_count),
                'occupied_count': int(response.occupied_count),
            })
        except Exception as exc:  # noqa: BLE001
            self.observer_errors.append({'kind': 'map_query', 'error': repr(exc)})

    def _cgroup_sample(self):
        root = Path('/sys/fs/cgroup')
        cpu_usage_usec = None
        try:
            for line in (root / 'cpu.stat').read_text().splitlines():
                key, value = line.split()
                if key == 'usage_usec':
                    cpu_usage_usec = int(value)
                    break
        except (OSError, ValueError):
            pass
        try:
            memory_current = int((root / 'memory.current').read_text().strip())
        except (OSError, ValueError):
            memory_current = None
        return {
            'monotonic_ns': time.monotonic_ns(),
            'wall_elapsed_s': round(self.elapsed(), 6),
            'cpu_usage_usec': cpu_usage_usec,
            'memory_current_bytes': memory_current,
        }

    def on_resource_timer(self):
        self.cgroup_resource_samples.append(self._cgroup_sample())

    def report(self):
        self.cgroup_resource_samples.append(self._cgroup_sample())
        report = {
            'schema': 'n03-depth-fusion-continuity-probe-v1',
            'scope': ('Full idle PX4 SITL/VINS/adapter/plan_env/EGO/navigation load; '
                      'read-only trace and map-query probe, no goal or setpoint action'),
            'runtime': {
                'ros_distribution': 'Jazzy',
                'sim_clock_last_ns': self.last_clock_stamp_ns,
                'configured_freshness_limit_s': 0.4,
                'configured_adapter_pending_depth_size': 8,
                'fault_input_topic': self.fault_input_topic,
                'fault_drop_after_forwarded': self.fault_drop_after_forwarded,
                'fault_drop_duration_s': self.fault_drop_duration_s,
            'freshness_gate_s': 0.4,
            },
            'started_wall_epoch_s': self.started_wall,
            'wall_seconds': round(self.elapsed(), 6),
            'depth_input_samples': self.depth_input_samples,
            'adapter_depth_output_samples': self.adapter_depth_output_samples,
            'adapter_pose_output_samples': self.adapter_pose_output_samples,
            'depth_health_history': self.depth_health_history,
            'localization_history': self.localization_history,
            'map_status_samples': self.map_status_samples,
            'map_samples': self.map_samples,
            'ego_fusion_trace': self.ego_fusion_trace,
            'map_query_samples': self.map_query_samples,
            'vehicle_arming_states': self.vehicle_arming_states,
            'navigation_commands': [
                {'goal_id': msg.goal_id, 'epoch': msg.epoch, 'map_id': msg.map_id}
                for msg in self.navigation_commands
            ],
            'cgroup_resource_samples': self.cgroup_resource_samples,
            'fault_events': self.fault_events,
            'observer_errors': self.observer_errors,
        }
        report['summary'] = build_summary(report)
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=120.0)
    parser.add_argument('--query-period-s', type=float, default=0.25)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fault-input-topic', default='')
    parser.add_argument('--fault-drop-after-forwarded', type=int, default=0)
    parser.add_argument('--fault-drop-duration-s', type=float, default=0.0)
    args = parser.parse_args()
    if args.seconds <= 0 or args.query_period_s <= 0:
        raise ValueError('--seconds and --query-period-s must be positive')
    if args.fault_drop_after_forwarded < 0 or args.fault_drop_duration_s < 0:
        raise ValueError('fault thresholds and durations cannot be negative')
    if args.fault_input_topic:
        if args.fault_drop_after_forwarded <= 0 or args.fault_drop_duration_s <= 0:
            raise ValueError('fault mode requires a positive forward threshold and drop duration')
    elif args.fault_drop_after_forwarded or args.fault_drop_duration_s:
        raise ValueError('fault options require --fault-input-topic')

    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    probe = DepthFusionContinuityProbe(
        args.output, args.seconds, args.query_period_s, args.fault_input_topic,
        args.fault_drop_after_forwarded, args.fault_drop_duration_s)
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(probe.node)
    spin_thread = threading.Thread(target=executor.spin, name='depth_fusion_probe_executor')
    spin_thread.start()
    interrupted = False
    signal.signal(signal.SIGINT, signal.default_int_handler)
    try:
        deadline = time.monotonic() + args.seconds
        while time.monotonic() < deadline:
            time.sleep(min(0.2, max(0.0, deadline - time.monotonic())))
    except KeyboardInterrupt:
        interrupted = True
    finally:
        probe.stopping = True
        drain_deadline = time.monotonic() + 5.0
        while probe.query_inflight and time.monotonic() < drain_deadline:
            time.sleep(0.05)
        if probe.query_inflight:
            probe.observer_errors.append({
                'kind': 'map_query_pending_at_shutdown', 'wait_limit_s': 5.0})
        executor.shutdown(timeout_sec=5.0)
        spin_thread.join(timeout=5.0)
        report = probe.report()
        report['interrupted'] = interrupted
        report['executor_stopped_before_node_destroy'] = not spin_thread.is_alive()
        probe.node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['summary'], indent=2))
    if not report['executor_stopped_before_node_destroy']:
        raise SystemExit('Probe executor did not stop cleanly')
    if not report['vehicle_arming_states']:
        raise SystemExit('No PX4 arming state was observed; disarmed status is unverified')
    if any(state != VehicleStatus.ARMING_STATE_DISARMED
           for state in report['vehicle_arming_states']):
        raise SystemExit('Probe observed PX4 not DISARMED; no control action was issued')


if __name__ == '__main__':
    main()
