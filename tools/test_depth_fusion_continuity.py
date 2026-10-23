#!/usr/bin/env python3
"""Pure metric tests for N03's read-only depth-fusion probe."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe_depth_fusion_continuity import build_summary, duration_summary, interval_summary


class DepthFusionContinuityTests(unittest.TestCase):
    def test_pipeline_stages_and_age_metrics_are_distinct(self):
        source = 1_000_000_000
        receive_mono = 2_000_000_000
        fusion_mono = 2_020_000_000
        report = {
            'depth_input_samples': [{'source_stamp_ns': source}],
            'adapter_depth_output_samples': [{'source_stamp_ns': source}],
            'adapter_pose_output_samples': [{'source_stamp_ns': source}],
            'ego_fusion_trace': [
                {'phase': 'ego_received', 'epoch': 'a' * 32, 'map_id': 'a' * 32 + '-m',
                 'callback_count': 1,
                 'image_source_stamp_ns': source, 'pose_source_stamp_ns': source,
                 'callback_ros_stamp_ns': source + 10_000_000,
                 'callback_monotonic_ns': receive_mono},
                {'phase': 'fused', 'epoch': 'a' * 32, 'map_id': 'a' * 32 + '-m',
                 'callback_count': 1, 'fused_count': 1,
                 'image_source_stamp_ns': source, 'pose_source_stamp_ns': source,
                 'callback_ros_stamp_ns': source + 10_000_000,
                 'callback_monotonic_ns': receive_mono,
                 'fusion_ros_stamp_ns': source + 30_000_000,
                 'fusion_monotonic_ns': fusion_mono},
                {'phase': 'ego_received', 'epoch': 'a' * 32, 'map_id': 'a' * 32 + '-m',
                 'callback_count': 2,
                 'image_source_stamp_ns': source + 100_000_000,
                 'pose_source_stamp_ns': source + 100_000_000,
                 'callback_ros_stamp_ns': source + 110_000_000,
                 'callback_monotonic_ns': receive_mono + 100_000_000},
                {'phase': 'fused', 'epoch': 'a' * 32, 'map_id': 'a' * 32 + '-m',
                 'callback_count': 2, 'fused_count': 2,
                 'image_source_stamp_ns': source + 100_000_000,
                 'pose_source_stamp_ns': source + 100_000_000,
                 'callback_ros_stamp_ns': source + 110_000_000,
                 'callback_monotonic_ns': receive_mono + 100_000_000,
                 'fusion_ros_stamp_ns': source + 130_000_000,
                 'fusion_monotonic_ns': fusion_mono + 100_000_000},
            ],
            'map_query_samples': [
                {'accepted': True, 'source_age_at_query_s': 0.04,
                 'response_stamp_ns': source + 40_000_000, 'query_kind': 'current'},
                {'accepted': True, 'source_age_at_query_s': 0.04,
                 'response_stamp_ns': source + 540_000_000, 'query_kind': 'current'},
                {'accepted': False, 'source_age_at_query_s': None,
                 'response_stamp_ns': 0, 'query_kind': 'current',
                 'reason': 'no_fresh_fused_depth'}],
            'map_status_samples': [
                {'last_depth_source_stamp_ns': source,
                 'last_depth_forward_monotonic_ns': receive_mono - 5_000_000,
                 'wall_elapsed_s': 0.0,
                 'input_ready': True, 'pending_depth_count': 0,
                 'pending_depth_high_water_count': 2, 'dropped_depth_count': 0,
                 'epoch': 'a' * 32, 'map_id': 'a' * 32 + '-m'},
                {'last_depth_source_stamp_ns': source + 100_000_000,
                 'last_depth_forward_monotonic_ns': receive_mono + 95_000_000,
                 'wall_elapsed_s': 0.1,
                 'input_ready': True, 'pending_depth_count': 0,
                 'pending_depth_high_water_count': 2, 'dropped_depth_count': 0,
                 'epoch': 'a' * 32, 'map_id': 'a' * 32 + '-m'}],
            'vehicle_arming_states': [1],
            'navigation_commands': [],
            'cgroup_resource_samples': [],
        }
        summary = build_summary(report)
        self.assertEqual(summary['adapter_depth_pose_exact_stamp_pairs'], 1)
        self.assertEqual(summary['ego_synced_pair_callback_count'], 2)
        self.assertEqual(summary['plan_env_fusion_complete_count'], 2)
        self.assertEqual(summary['map_query_accepted_count'], 2)
        self.assertEqual(summary['map_query_rejections_by_reason']['no_fresh_fused_depth'], 1)
        self.assertEqual(summary['adapter_publish_to_ego_callback_wall_s']['max'], 0.005)
        self.assertEqual(summary['ego_callback_to_fusion_wall_s']['max'], 0.02)
        self.assertEqual(summary['fusion_source_age_s']['max'], 0.03)
        self.assertEqual(summary['successful_query_source_age_s']['max'], 0.04)
        self.assertEqual(summary['navigation_command_count'], 0)
        self.assertTrue(summary['diagnostic_freshness_gate']['pass'])

    def test_interval_summary_uses_monotonic_source_order(self):
        summary = interval_summary([0, 40_000_000, 100_000_000])
        self.assertEqual(summary['count'], 2)
        self.assertEqual(summary['max_s'], 0.06)

    def test_duration_summary_groups_contiguous_state_samples(self):
        samples = [
            {'wall_elapsed_s': 0.0, 'ready': False},
            {'wall_elapsed_s': 0.2, 'ready': False},
            {'wall_elapsed_s': 0.4, 'ready': True},
            {'wall_elapsed_s': 1.0, 'ready': True},
            {'wall_elapsed_s': 1.2, 'ready': False},
        ]
        summary = duration_summary(samples, 'ready', end_wall_elapsed_s=1.5)
        self.assertEqual(summary['max_false_s'], 0.4)
        self.assertEqual(summary['max_true_s'], 0.8)

    def test_stale_identity_queries_are_reported_separately(self):
        report = {
            'depth_input_samples': [], 'adapter_depth_output_samples': [],
            'adapter_pose_output_samples': [], 'ego_fusion_trace': [],
            'map_query_samples': [
                {'accepted': True, 'source_age_at_query_s': 0.05,
                 'response_stamp_ns': 100_000_000, 'query_kind': 'current'},
                {'accepted': False, 'source_age_at_query_s': None,
                 'response_stamp_ns': 0, 'query_kind': 'stale_identity'},
            ],
            'map_status_samples': [
                {'input_ready': True, 'wall_elapsed_s': 0.0,
                 'pending_depth_high_water_count': 1, 'pending_depth_count': 0,
                 'dropped_depth_count': 0, 'last_depth_source_stamp_ns': 0,
                 'last_depth_forward_monotonic_ns': 0, 'map_id': 'new-map'}],
            'vehicle_arming_states': [1], 'navigation_commands': [],
            'cgroup_resource_samples': [],
        }
        summary = build_summary(report)
        self.assertEqual(summary['stale_identity_query_count'], 1)
        self.assertEqual(summary['stale_identity_query_rejected_count'], 1)


if __name__ == '__main__':
    unittest.main()
