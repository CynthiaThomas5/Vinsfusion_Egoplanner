import json
import tempfile
import unittest
from pathlib import Path

from tools.debug_truth.evaluate_n10_acceptance import (
    archived_input_hashes, evaluate, evaluate_run, identity_evidence, sha256, continuous_clearance_evidence,
    observer_identity_binding_result, tracking_clearance_budget_result, summarize_required_metrics,
    cgroup_cpu_quota_capacity, cgroup_numeric_limit, gate, compare,
    resource_and_queue_behavior_result, dynamic_replanning_result,
)


ROOT = Path(__file__).resolve().parents[1]


def _stat(value):
    return {'p95': value, 'max': value}


def _metrics():
    pose = {
        'supported': True,
        'sample_count': 10,
        'position_error_m': _stat(0.2),
        'absolute_yaw_error_deg': _stat(5.0),
    }
    velocity = {'supported': True, 'velocity_error_norm_m_s': _stat(0.02)}
    segments = {
        'goal_motion_and_arrival_dwell': {
            'absolute_position_yaw_error': pose,
            'raw_velocity_error': velocity,
            'ego_tracking_error': {'position_error_m': _stat(0.5)},
            'relative_pose_error': {
                '10s': {'supported': True, 'supported_pairs': 10,
                        'translation_error_m': _stat(0.02),
                        'rotation_error_deg': _stat(0.2)},
            },
        },
        'requested_active_hold': {
            'absolute_position_yaw_error': pose,
            'raw_velocity_error': velocity,
            'relative_pose_error': {
                '10s': {'supported': True, 'supported_pairs': 10,
                        'translation_error_m': _stat(0.02),
                        'rotation_error_deg': _stat(0.2)},
            },
        },
        'hold_end_to_landed': {'absolute_position_yaw_error': pose},
        'prestream_to_landed': {
            'absolute_position_yaw_error': pose,
            'relative_pose_error': {
                'supported': True,
                'supported_pairs': 10,
                'translation_error_m': _stat(0.02),
                'rotation_error_deg': _stat(0.2),
            },
            'map_and_source_timing': {
                'source_age_sim_s': {'max': 0.1},
                'occupancy_update_age_sim_s': {'max': 0.1},
            },
        },
    }
    return {
        'run_id': 'run-1',
        'runtime_contract_sha256': 'contract-hash',
        'input_sha256': {},
        'arrival': {
            'independent_goal_dwell_status': 'PASS',
            'longest_joint_tolerance_window': {'duration_sim_s': 3.2},
            'max_truth_sample_gap_sim_s': 0.02,
        },
        'segments': segments,
    }


def _resource_capacity_fixture(run_dir, cpu_max='150000 100000'):
    run_dir.mkdir(parents=True, exist_ok=True)
    run_id, epoch, map_id, goal_id = run_dir.name, 'epoch-1', 'epoch-1-map-1', 'goal-1'
    runtime_hash = 'runtime-contract-test-hash'
    (run_dir / 'runtime-contract.json').write_text(json.dumps({'sha256': runtime_hash}))
    (run_dir / 'flight.json').write_text(json.dumps({
        'goal_id': goal_id, 'localization_epoch': epoch,
    }))
    queue_sources = (
        'config/components/mapping/ego_input.json',
        'src/own/uav_mapping/uav_mapping/adapter.py',
        'config/n10_capture.json',
        'src/vendor/vins_fusion/vins/src/estimator/estimator.cpp',
        'src/vendor/vins_fusion/vins/src/estimator/estimator.h',
        'dependencies/patches/vins/0020-readonly-estimator-queue-high-water.patch',
        'dependencies/sources.json',
    )
    source_hashes = {name: sha256(ROOT / name) for name in queue_sources}
    queue_rows = []
    for index, (stamp, depth) in enumerate(((1_000_000_000, 3), (2_000_000_000, 2))):
        queue_rows.append({
            'epoch': epoch,
            'source_stamp_ns': stamp,
            'receipt_monotonic_ns': 10_000 + index * 1_000,
            'queue_metrics': {
                'scope': 'estimator_process_lifetime',
                'acc_current_before_feature_dequeue': depth,
                'gyr_current_before_feature_dequeue': depth,
                'feature_current_before_feature_dequeue': 1,
                'acc_high_water': 4,
                'gyr_high_water': 4,
                'feature_high_water': 1,
            },
        })
    queue_path = run_dir / 'n10-vins-queue-telemetry.jsonl'
    queue_path.write_text(''.join(json.dumps(row) + '\n' for row in queue_rows))
    samples = []
    for index, (wall, usage, peak) in enumerate(((0.0, 1_000_000, 131_072),
                                                   (1.0, 1_500_000, 262_144))):
        samples.append({
            'wall_elapsed_s': wall,
            'cpu_count_visible': 2,
            'rtf_sim_over_wall': 0.8,
            'cgroup': {
                'cpu_max': cpu_max,
                'memory_max': '1048576',
                'cpu_stat': {'usage_usec': usage, 'throttled_usec': 0},
                'memory_peak': peak,
                'pids_current': 3,
                'memory_events': {'oom': 0, 'oom_kill': 0, 'oom_group_kill': 0},
            },
            'map_queue_counters': {
                'epoch': epoch, 'map_id': map_id,
                'pending_depth_count': 1,
                'pending_depth_high_water_count': 2,
                'dropped_depth_count': 0,
                'keyframe_dropped_count': 0,
            },
        })
    resource = {
        'run_id': run_id,
        'run_identity': {
            'run_id': run_id, 'runtime_contract_sha256': runtime_hash,
            'goal_id': goal_id, 'epoch': epoch, 'map_id': map_id,
            'complete': True,
        },
        'sample_period_s': 1,
        'wall_duration_s': 1,
        'safe_session_terminal_observed': True,
        'terminal_flight_record_observed': True,
        'samples': samples,
        'configured_queue_capacities': {
            'mapping_pending_depth_limit': 2,
            'vins_estimator_queue_capacity': 'unbounded_by_source; no cap or drop added',
            'source_sha256': source_hashes,
        },
        'vins_estimator_queue_observation': {
            'status': 'OBSERVED', 'sample_count': 2, 'valid_sample_count': 2,
            'queue_capacity_or_runtime_limit_inferred': False, 'errors': [],
        },
        'vins_queue_telemetry_artifact': {
            'path': queue_path.name, 'row_count': 2, 'sha256': sha256(queue_path),
        },
    }
    resource_path = run_dir / 'n10-resource-observation.json'
    resource_path.write_text(json.dumps(resource))
    platform_report = {
        '_file_sha256': 'platform-report-test-hash',
        'run_binding': {
            'run_id': run_id,
            'runtime_contract_sha256': runtime_hash,
            'resource_observation_sha256': sha256(resource_path),
        },
        'platform': {
            'logical_cpu_count': 2,
            'effective_cpu_capacity_cores': 2,
            'effective_memory_capacity_bytes': 2 * 1024 * 1024,
        },
    }
    return resource_path, platform_report, {'runtime_contract_sha256': runtime_hash}


def _dynamic_replan_fixture(run_dir, first_safe_command_ns=90_000_000_000):
    run_dir.mkdir(parents=True, exist_ok=True)
    run_id, epoch, map_id, goal_id = run_dir.name, 'epoch-1', 'epoch-1-map-1', 'goal-1'
    contract_hash = 'runtime-contract-test-hash'
    (run_dir / 'runtime-contract.json').write_text(json.dumps({'sha256': contract_hash}))
    flight = {
        'goal_id': goal_id, 'localization_epoch': epoch,
        'goal_completed_source_ns': 110_000_000_000,
        'position_command_history': [
            {'goal_id': goal_id, 'epoch': epoch, 'flag': 1,
             'source_stamp_ns': 79_000_000_000, 'trajectory_id': 4},
            {'goal_id': goal_id, 'epoch': epoch, 'flag': 1,
             'source_stamp_ns': first_safe_command_ns, 'trajectory_id': 5},
            {'goal_id': goal_id, 'epoch': epoch, 'flag': 1,
             'source_stamp_ns': first_safe_command_ns + 1_000_000_000,
             'trajectory_id': 5},
        ],
    }
    (run_dir / 'flight.json').write_text(json.dumps(flight))
    sdf_path = run_dir / 'injected-box.sdf'
    sdf_path.write_text('<sdf version="1.9"/>\n')
    observation = {
        'run_id': run_id, 'goal_id': goal_id, 'epoch': epoch,
        'map_id_at_goal': map_id,
        'obstacle': {'sdf_file': sdf_path.name, 'sdf_sha256': sha256(sdf_path)},
    }
    (run_dir / 'n10-live-obstacle-observation.json').write_text(json.dumps(observation))
    for name in ('planner-observation.json', 'n10-map-snapshot/metadata.json',
                 'n10-clearance-evaluation.json', 'arrival-evaluation-simtime-v2.json'):
        path = run_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{}')
    snapshot = {
        'snapshot_matches_live_observer_epoch_map_frame': True,
        'snapshot_source_coverage': {'covered': True},
        'snapshot_roi': {
            'near_surface_raw_occupied_point_count': 1,
            'near_surface_raw_occupied_inflated_count': 1,
        },
    }
    (run_dir / 'n10-box-map-snapshot-analysis.json').write_text(json.dumps(snapshot))
    geometry = {
        'first_trajectory_with_required_body_clearance_after_cloud': {
            'traj_id': 5, 'receipt_sim_ns': 85_000_000_000,
            'minimum_centerline_body_margin_m': 0.2,
        },
        'post_margin_qualified_spline_geometry': {
            'minimum_centerline_body_margin_m': 0.2,
            'below_required_body_clearance_count': 0,
        },
        'replanning_deadline': {
            'reference_trajectory_id': 4,
            'latest_strictly_pre_cloud_ready_command': {
                'trajectory_id': 4, 'source_stamp_ns': 79_000_000_000,
            },
            'reference_trajectory_matches_latest_pre_cloud_ready_command': True,
            'predicted_clearance_boundary_stamp_ns': 100_000_000_000,
            'available_time_to_clearance_boundary_sim_s': 20.0,
            'replacement_delay_after_first_positive_cloud_sim_s': 5.0,
            'deadline_slack_after_replacement_sim_s': 15.0,
        },
    }
    report = {
        'schema': 'n10-obstacle-replan-geometry/v3', 'run_id': run_id,
        'identity': {
            'runtime_contract_sha256': contract_hash,
            'goal_id': goal_id, 'epoch': epoch, 'map_id': map_id,
        },
        'injection': {
            'gazebo_create_acknowledged': True,
            'obstacle': observation['obstacle'],
        },
        'raw_occupancy_cloud_observations': {
            'first_sample_with_points': {
                'stamp_ns': 80_000_000_000, 'obstacle_roi_point_count': 1,
            },
        },
        'identity_bound_raw_inflated_snapshot': {
            'snapshot_identity_matches_live_observer': True,
            'snapshot_source_stamp_ns': 82_000_000_000,
        },
        'planner_centerline_geometry': geometry,
    }
    input_paths = {
        'observation': run_dir / 'n10-live-obstacle-observation.json',
        'planner': run_dir / 'planner-observation.json',
        'flight': run_dir / 'flight.json',
        'runtime': run_dir / 'runtime-contract.json',
        'snapshot_metadata': run_dir / 'n10-map-snapshot/metadata.json',
        'snapshot_analysis': run_dir / 'n10-box-map-snapshot-analysis.json',
        'body_clearance': run_dir / 'n10-clearance-evaluation.json',
        'alignment': run_dir / 'arrival-evaluation-simtime-v2.json',
        'vehicle_envelope': ROOT / 'config/components/navigation/vehicle_envelope.json',
        'injected_obstacle_sdf': sdf_path,
    }
    report['inputs_sha256'] = {name: sha256(path) for name, path in input_paths.items()}
    report['tool_sha256'] = sha256(ROOT / 'tools/debug_truth/evaluate_n10_replan_geometry.py')
    tracking_rows = [
        {'source_stamp_ns': row['source_stamp_ns'], 'trajectory_id': 5,
         'actual_body_clearance_to_nearest_obstacle_m': 0.12}
        for row in flight['position_command_history'][1:]
    ]
    return report, {'per_sample': tracking_rows}, {
        'status': 'PASS',
    }, {
        'status': 'PASS',
        'continuous_interval_evidence': {
            'status': 'PASS',
            'minimum_no_contact_interval_clearance_m': 0.12,
        },
        'comparisons': [{'metric': 'minimum_full_body_clearance_m', 'value': 0.12}],
        'observed_prohibited_contact_event_count': 0,
    }


def _interval_report(run_dir, lower_bound=0.19, solver_state_min=0.2,
                     complete_partition=True, all_states=True):
    inputs = {}
    for name in ('flight.json','debug-truth-evaluation.json','bridge-alignment-timeline.jsonl',
                 'n09-contact-observation.json','vehicle-contact-evaluation.json','runtime-contract.json',
                 'n10-tool-freeze-used.json','n09-contact-model-manifest.json',
                 'n10-px4-model-source.json'):
        path = run_dir / name
        if not path.exists(): path.write_text('{}')
        inputs[name] = sha256(path)
    ledger = run_dir / 'debug-truth-kinematics.jsonl'
    ledger.write_text('fixture-ledger')
    report = {'schema':'n10-model-bounded-interval-clearance/v3','run_id':run_dir.name,
        'interval_bound_verified':True,'status':'AIRBORNE_MODEL_BOUND_POSITIVE_CONTACT_PHASE_SEPARATE',
        'evaluator_sha256':sha256(ROOT/'tools/debug_truth/evaluate_n10_interval_clearance_bound.py'),
        'input_sha256':inputs,'velocity_endpoint_evidence':{'status':'PASS',
            'instantaneous_endpoint_state_observed':True,'record_sha256':sha256(ledger)},
        'flight_interval': {'solver_state_count': 10, 'every_solver_step_present': True,
                            'step_s': 0.004, 'maximum_observed_step_gap_s': 0.004},
        'collision_component_sphere_geometry': {
            'schema': 'n10-sdf-collision-component-spheres/v1',
            'component_count': 10, 'complete_for_parsed_vehicle_models': True},
        'solver_state_clearance': {
            'status': 'COMPLETE',
            'geometry_schema': 'n10-sdf-collision-component-spheres/v1',
            'solver_state_count': 10, 'clearance_sample_count': 10,
            'all_solver_states_have_clearance': all_states,
            'minimum_component_clearance_m': solver_state_min},
        'interval_partition_coverage': {
            'expected_adjacent_interval_count': 9,
            'reported_interval_count': 9 if complete_partition else 8,
            'bounded_no_contact_interval_count': 8,
            'unavailable_no_contact_interval_count': 0,
            'contact_interval_count': 1,
            'complete_partition': complete_partition},
        'contact_intervals': {'total_interval_count': 1,
                              'prohibited_contact_interval_count': 0},
        'airborne_intervals':{'count': 8,
                              'min_clearance_lower_bound_m':lower_bound}}
    (run_dir/'n10-interval-clearance-bound.json').write_text(json.dumps(report))


def _clearance_reports(run_dir, every_step=True, clearance_m=0.2, contact_count=0):
    (run_dir / 'n10-clearance-evaluation.json').write_text(json.dumps({
        'physics_step_sample_coverage': {
            'all_received_pose_gaps_within_one_physics_step': True,
            'every_consecutive_physics_state_captured': every_step,
            'minimum_clearance_at_all_received_states_m': clearance_m,
        },
        'interval': {'truth_max_source_gap_sim_s': 0.004},
    }))
    (run_dir / 'vehicle-contact-evaluation.json').write_text(json.dumps({
        'passed': True,
        'sensor_topics_ready': True,
        'prohibited_contact_event_count': contact_count,
    }))

    _interval_report(run_dir, solver_state_min=clearance_m, all_states=every_step)

def _clearance_report_with_v2_field_names(run_dir, clearance_m=0.2):
    (run_dir / 'n10-clearance-evaluation.json').write_text(json.dumps({
        'physics_step_sample_coverage': {
            'all_received_pose_gaps_within_one_physics_step': True,
            'every_consecutive_physics_state_captured': True,
            'minimum_clearance_at_received_states_m': clearance_m,
        },
        'interval': {'truth_max_source_gap_sim_s': 0.004},
    }))
    (run_dir / 'vehicle-contact-evaluation.json').write_text(json.dumps({
        'passed': True,
        'sensor_topics_ready': True,
        'prohibited_contact_event_count': 0,
    }))

    _interval_report(run_dir, solver_state_min=clearance_m)

class N10AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((ROOT / 'config/acceptance.json').read_text())

    def test_frozen_metrics_and_capture_contract_are_offline_only(self):
        self.assertEqual(self.config['status'], 'frozen')
        self.assertTrue(self.config['runtime_effect']['offline_evaluator_only'])
        self.assertFalse(self.config['runtime_effect']['adds_admission_cancel_or_landing_gate'])
        self.assertFalse(self.config['runtime_effect']['thresholds_may_change_control_flow'])
        capture = self.config['calibration_observation_contract']
        self.assertTrue(capture['read_only'])
        self.assertFalse(capture['may_publish_vehicle_control'])
        self.assertTrue(capture['must_not_add_runtime_refusal_cancel_pause_or_landing'])
        self.assertIn('stereo_left_image', capture['sensor_streams']['required_streams'])
        self.assertEqual(capture['sensor_streams']['capture_config'],
                         'config/n10_capture.json')
        self.assertIn('INSUFFICIENT', capture['missing_or_invalid_evidence'])

    def test_direct_arrival_failure_survives_missing_numeric_data(self):
        metrics = _metrics()
        metrics['arrival']['independent_goal_dwell_status'] = 'FAIL'
        metrics['arrival']['longest_joint_tolerance_window'] = {}
        result = evaluate_run(self.config, metrics, Path('/tmp/n10-no-run'))
        arrival = next(row for row in result['metrics']
                       if row['id'] == 'arrival_position_yaw_dwell')
        self.assertEqual(arrival['status'], 'FAIL')
        self.assertEqual(result['overall_status'], 'FAIL')

    def test_pose_thresholds_cover_each_required_segment(self):
        metrics = _metrics()
        metrics['segments']['hold_end_to_landed']['absolute_position_yaw_error'][
            'position_error_m'] = _stat(0.7)
        result = evaluate_run(self.config, metrics, Path('/tmp/n10-no-run'))
        pose = next(row for row in result['metrics']
                    if row['id'] == 'raw_vio_absolute_error')
        self.assertEqual(pose['status'], 'FAIL')
        failed = [row['metric'] for row in pose['comparisons']
                  if row['value'] > row['threshold']]
        self.assertIn('landing_position_p95_m', failed)

    def test_unresolved_candidate_failure_does_not_freeze_draft_config(self):
        metrics = _metrics()
        metrics['segments']['goal_motion_and_arrival_dwell'][
            'absolute_position_yaw_error']['position_error_m'] = _stat(0.7)
        draft_config = {**self.config, 'status': 'draft'}
        result = evaluate_run(draft_config, metrics, Path('/tmp/n10-no-run'))
        pose = next(row for row in result['metrics']
                    if row['id'] == 'raw_vio_absolute_error')
        self.assertEqual(pose['status'], 'FAIL')
        self.assertEqual(result['overall_status'], 'INSUFFICIENT')

    def test_tracking_candidate_breach_remains_diagnostic_under_scene_geometry_threshold(self):
        metrics = _metrics()
        metrics['segments']['goal_motion_and_arrival_dwell'][
            'ego_tracking_error']['position_error_m'] = _stat(0.8)
        result = evaluate_run(self.config, metrics, Path('/tmp/n10-no-run'))
        tracking = next(row for row in result['metrics']
                        if row['id'] == 'ego_tracking_error')
        self.assertEqual(tracking['status'], 'INSUFFICIENT')
        self.assertEqual(
            tracking['acceptance_thresholds'],
            self.config['metrics']['ego_tracking_error']['acceptance_thresholds'])
        self.assertEqual(tracking['diagnostic_candidate_breaches'], ['tracking_p95_m'])
        self.assertTrue(tracking['scalar_candidate_values_are_diagnostic_only'])

    def test_rpe_motion_and_hold_are_checked_separately_from_full_task(self):
        metrics = _metrics()
        metrics['segments']['goal_motion_and_arrival_dwell']['relative_pose_error']['10s'][
            'translation_error_m'] = _stat(0.096)
        metrics['segments']['prestream_to_landed']['relative_pose_error']['supported'] = True
        metrics['segments']['prestream_to_landed']['relative_pose_error']['supported_pairs'] = 1000
        metrics['segments']['prestream_to_landed']['relative_pose_error']['10s'] = {
            'supported': True, 'supported_pairs': 1000,
            'translation_error_m': _stat(0.042), 'rotation_error_deg': _stat(0.3),
        }
        result = evaluate_run(self.config, metrics, Path('/tmp/n10-rpe-segment-fixture'))
        rpe = next(row for row in result['metrics'] if row['id'] == 'raw_vio_rpe_10s')
        self.assertEqual(rpe['status'], 'FAIL')
        self.assertEqual(rpe['segment_coverage']['goal_motion']['status'], 'OBSERVED')
        self.assertEqual(rpe['segment_coverage']['active_hold']['status'], 'OBSERVED')
        self.assertTrue(rpe['full_task_rpe_is_diagnostic_only'])
        self.assertEqual(
            next(c for c in rpe['comparisons']
                 if c['metric'] == 'goal_motion_translation_p95_m')['value'], 0.096)

    def _tracking_budget_report(self, run_dir):
        run_dir.mkdir()
        (run_dir / 'runtime-contract.json').write_text(json.dumps({'sha256': 'contract-hash'}))
        (run_dir / 'flight.json').write_text(json.dumps({
            'goal_id': 'goal-1', 'localization_epoch': 'epoch-1',
        }))
        (run_dir / 'debug-truth-evaluation.json').write_text('{}')
        (run_dir / 'n10-dynamic-clearance-world.sdf').write_text('<sdf/>')
        (run_dir / 'n10-live-obstacle-observation.json').write_text(json.dumps({
            'run_id': run_dir.name, 'goal_id': 'goal-1', 'epoch': 'epoch-1',
            'map_id_at_goal': 'epoch-1-map-1',
        }))
        for relative in (
                'n09-contact-model-manifest.json',
                'n09-contact-models/x500_base/model.sdf',
                'n09-contact-models/x500_d435i/model.sdf',
                'n09-contact-models/d435i/model.sdf'):
            path = run_dir / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{}')
        input_paths = {
            'flight': run_dir / 'flight.json',
            'truth': run_dir / 'debug-truth-evaluation.json',
            'runtime_contract': run_dir / 'runtime-contract.json',
            'envelope': ROOT / 'config/components/navigation/vehicle_envelope.json',
            'world': run_dir / 'n10-dynamic-clearance-world.sdf',
            'observation': run_dir / 'n10-live-obstacle-observation.json',
            'contact_model_manifest': run_dir / 'n09-contact-model-manifest.json',
            'base_collision_model': run_dir / 'n09-contact-models/x500_base/model.sdf',
            'vehicle_collision_model': run_dir / 'n09-contact-models/x500_d435i/model.sdf',
            'camera_collision_model': run_dir / 'n09-contact-models/d435i/model.sdf',
        }
        return {
            'schema': 'n10-tracking-clearance-relation/v3',
            'run_id': run_dir.name,
            'identity': {
                'run_directory_matches_selected_run': True,
                'runtime_contract_identity_sha256': 'contract-hash',
                'goal_id': 'goal-1', 'epoch': 'epoch-1',
                'map_id': 'epoch-1-map-1', 'goal_map_identity_matches': True,
            },
            'input_sha256': {name: sha256(path) for name, path in input_paths.items()},
            'tracking_clearance_evaluator_sha256': 'offline-tool-hash',
            'interval': {
                'matching_ready_commands': 4,
                'paired_truth_commands': 4,
                'rejected_commands': [],
                'maximum_truth_bracket_gap_sim_s': 0.004,
            },
            'collision_component_sphere_geometry': {
                'schema': 'n10-sdf-collision-component-spheres/v1',
                'component_count': 10,
                'model_source_checks': {
                    'x500_base/model.sdf': True,
                    'x500_d435i/model.sdf': True,
                    'd435i/model.sdf': True,
                },
            },
            'minimum_actual_body_clearance': {
                'actual_body_clearance_to_nearest_obstacle_m': 0.12,
                'nearest_actual_component': 'rotor_0',
                'nearest_actual_obstacle': 'test_box',
            },
            'tracking_error_m': {'p95': 0.3, 'max': 0.34},
            'translation_only_clearance_budget': {
                'pointwise_lower_bound_m': {'count': 4, 'p50': 0.1, 'p95': 0.2,
                                            'p99': 0.2, 'max': 0.3},
                'negative_sample_count': 1,
                'negative_sample_fraction': 0.25,
                'classification': 'offline diagnostic; no runtime gate',
            },
        }

    def test_tracking_geometry_passes_while_scalar_lower_bound_stays_diagnostic(self):
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp) / 'run-1'
            report = self._tracking_budget_report(run_dir)
            metric = tracking_clearance_budget_result(
                self.config, {'runtime_contract_sha256': 'contract-hash'},
                run_dir, report)
            self.assertEqual(metric['status'], 'PASS')
            self.assertTrue(metric['tracking_report_identity_matches'])
            self.assertTrue(metric['tracking_report_inputs_match'])
            self.assertEqual(metric['negative_bound_sample_fraction'], 0.25)
            self.assertFalse(metric['runtime_gate_added'])
            self.assertTrue(metric['translation_only_lower_bound_is_diagnostic'])
            self.assertEqual(metric['comparisons'][0]['value'], 0.12)

    def test_tracking_geometry_margin_or_truth_bracket_breach_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp) / 'run-1'
            report = self._tracking_budget_report(run_dir)
            report['minimum_actual_body_clearance'][
                'actual_body_clearance_to_nearest_obstacle_m'] = 0.05
            metric = tracking_clearance_budget_result(
                self.config, {'runtime_contract_sha256': 'contract-hash'},
                run_dir, report)
            self.assertEqual(metric['status'], 'FAIL')
            report['minimum_actual_body_clearance'][
                'actual_body_clearance_to_nearest_obstacle_m'] = 0.12
            report['interval']['maximum_truth_bracket_gap_sim_s'] = 0.005
            metric = tracking_clearance_budget_result(
                self.config, {'runtime_contract_sha256': 'contract-hash'},
                run_dir, report)
            self.assertEqual(metric['status'], 'FAIL')

    def test_tracking_clearance_budget_missing_or_old_schema_is_insufficient(self):
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp) / 'run-1'
            run_dir.mkdir()
            missing = tracking_clearance_budget_result(
                self.config, {'runtime_contract_sha256': 'contract-hash'}, run_dir, None)
            self.assertEqual(missing['status'], 'INSUFFICIENT')
            report = {'schema': 'n10-tracking-clearance-relation/v1'}
            old_schema = tracking_clearance_budget_result(
                self.config, {'runtime_contract_sha256': 'contract-hash'}, run_dir, report)
            self.assertEqual(old_schema['status'], 'INSUFFICIENT')
            self.assertIn('unsupported', old_schema['reason'])

    def test_tracking_clearance_budget_wrong_identity_or_input_stays_insufficient(self):
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp) / 'run-1'
            report = self._tracking_budget_report(run_dir)
            report['identity']['map_id'] = 'other-epoch-map'
            metric = tracking_clearance_budget_result(
                self.config, {'runtime_contract_sha256': 'contract-hash'},
                run_dir, report)
            self.assertEqual(metric['status'], 'INSUFFICIENT')
            self.assertFalse(metric['tracking_report_identity_matches'])
            report['identity']['map_id'] = 'epoch-1-map-1'
            report['input_sha256']['flight'] = 'wrong-hash'
            metric = tracking_clearance_budget_result(
                self.config, {'runtime_contract_sha256': 'contract-hash'},
                run_dir, report)
            self.assertEqual(metric['status'], 'INSUFFICIENT')
            self.assertFalse(metric['tracking_report_inputs_match'])

    def test_identity_mismatch_does_not_hide_independently_observed_contact_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_dir = root / 'run-1'
            run_dir.mkdir()
            (run_dir / 'runtime-contract.json').write_text(json.dumps({'sha256': 'actual-contract'}))
            (run_dir / 'flight.json').write_text(json.dumps({
                'goal_id': 'goal-1', 'localization_epoch': 'epoch-1',
            }))
            (run_dir / 'n10-live-obstacle-observation.json').write_text(json.dumps({
                'run_id': 'run-1', 'goal_id': 'goal-1', 'epoch': 'epoch-1',
                'map_id_at_goal': 'epoch-1-map-1',
            }))
            (run_dir / 'n10-contact-evaluation-partial.json').write_text(json.dumps({
                'result': {'sensor_topics_ready': True,
                           'prohibited_contact_event_count': 1},
            }))
            calibration_path = root / 'calibration.json'
            calibration_path.write_text(json.dumps({
                'schema': 'n10-cross-run-calibration-pair/v1',
                'runs': [{'run_id': 'run-1',
                          'runtime_contract_sha256': 'wrong-contract',
                          'input_sha256': {}}],
            }))
            result = evaluate(ROOT / 'config/acceptance.json', calibration_path,
                              run_dir, 'run-1')
            self.assertFalse(result['runtime_identity_matches'])
            self.assertEqual(result['overall_status'], 'FAIL')
            clearance = next(row for row in result['metrics']
                             if row['id'] == 'full_body_clearance_and_contact')
            self.assertTrue(clearance['direct_safety_failure'])
            runtime_identity = next(row for row in result['metrics']
                                    if row['id'] == 'runtime_identity')
            self.assertEqual(runtime_identity['status'], 'INSUFFICIENT')

    def test_nan_or_missing_measurement_is_insufficient(self):
        metrics = _metrics()
        metrics['arrival']['longest_joint_tolerance_window']['duration_sim_s'] = float('nan')
        result = evaluate_run(self.config, metrics, Path('/tmp/n10-no-run'))
        arrival = next(row for row in result['metrics']
                       if row['id'] == 'arrival_position_yaw_dwell')
        self.assertEqual(arrival['status'], 'INSUFFICIENT')
        self.assertEqual(arrival['missing'], ['joint_dwell_sim_s'])

    def test_discrete_clearance_cannot_pass_without_bound_or_with_changed_ledger(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            _clearance_reports(run)
            (run/'n10-interval-clearance-bound.json').unlink()
            result = evaluate_run(self.config, _metrics(), run)
            metric = next(r for r in result['metrics'] if r['id']=='full_body_clearance_and_contact')
            self.assertEqual(metric['status'], 'INSUFFICIENT')
            _interval_report(run)
            self.assertEqual(continuous_clearance_evidence(run, .1)['status'], 'PASS')
            (run/'debug-truth-kinematics.jsonl').write_text('changed')
            self.assertEqual(continuous_clearance_evidence(run, .1)['status'], 'INSUFFICIENT')
            _interval_report(run, lower_bound=.05)
            self.assertEqual(continuous_clearance_evidence(run, .1)['status'], 'FAIL')
            _clearance_reports(run, contact_count=1)
            (run/'n10-interval-clearance-bound.json').unlink()
            result = evaluate_run(self.config, _metrics(), run)
            metric = next(r for r in result['metrics'] if r['id']=='full_body_clearance_and_contact')
            self.assertEqual(metric['status'], 'FAIL')

    def test_component_clearance_requires_complete_interval_partition(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            _clearance_reports(run)
            _interval_report(run, complete_partition=False)
            self.assertEqual(continuous_clearance_evidence(run, .1)['status'],
                             'INSUFFICIENT')

    def test_clearance_requires_every_physics_state_and_complete_contact_capture(self):
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp)
            _clearance_reports(run_dir, every_step=True)
            result = evaluate_run(self.config, _metrics(), run_dir)
            clearance = next(row for row in result['metrics']
                             if row['id'] == 'full_body_clearance_and_contact')
            self.assertEqual(clearance['status'], 'PASS')
            _clearance_reports(run_dir, every_step=False)
            result = evaluate_run(self.config, _metrics(), run_dir)
            clearance = next(row for row in result['metrics']
                             if row['id'] == 'full_body_clearance_and_contact')
            self.assertEqual(clearance['status'], 'INSUFFICIENT')

    def test_clearance_margin_or_contact_breach_fails_numeric_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp)
            _clearance_reports(run_dir, clearance_m=0.05)
            result = evaluate_run(self.config, _metrics(), run_dir)
            clearance = next(row for row in result['metrics']
                             if row['id'] == 'full_body_clearance_and_contact')
            self.assertEqual(clearance['status'], 'FAIL')
            _clearance_reports(run_dir, contact_count=1)
            result = evaluate_run(self.config, _metrics(), run_dir)
            clearance = next(row for row in result['metrics']
                             if row['id'] == 'full_body_clearance_and_contact')
            self.assertEqual(clearance['status'], 'FAIL')

    def test_component_geometry_supersedes_legacy_whole_vehicle_cylinder(self):
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp)
            _clearance_report_with_v2_field_names(run_dir, clearance_m=0.0)
            _interval_report(run_dir, lower_bound=0.18, solver_state_min=0.186)
            result = evaluate_run(self.config, _metrics(), run_dir)
            clearance = next(row for row in result['metrics']
                             if row['id'] == 'full_body_clearance_and_contact')
            self.assertEqual(clearance['status'], 'PASS')
            self.assertEqual(clearance['comparisons'][0]['value'], 0.186)
            self.assertTrue(clearance['legacy_clearance_report_is_diagnostic_only'])

    def test_raw_classification_does_not_treat_unpartitioned_free_voxels_as_occluded(self):
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp)
            (run_dir / 'n10-box-map-snapshot-analysis.json').write_text(json.dumps({
                'snapshot_matches_live_observer_epoch_map_frame': True,
                'snapshot_roi': {
                    'inside_box_voxel_counts_by_raw_class': {
                        'unknown': 1739, 'known_free': 34, 'raw_occupied': 19,
                    },
                    'truth_occluded_known_free_voxel_count': None,
                },
            }))
            result = evaluate_run(self.config, _metrics(), run_dir)
            classification = next(row for row in result['metrics']
                                  if row['id'] == 'raw_map_classification')
            self.assertEqual(classification['status'], 'INSUFFICIENT')
            self.assertEqual(
                classification['known_free_voxels_inside_box_observed'], 34)
            self.assertIn('fully contained', classification['reason'])

            snapshot = json.loads(
                (run_dir / 'n10-box-map-snapshot-analysis.json').read_text())
            snapshot['snapshot_source_coverage'] = {'covered': True}
            snapshot['snapshot_roi']['voxel_cell_geometry'] = {
                'all_corners_inside_box_counts_by_raw_class': {
                    'unknown': 0, 'known_free': 0, 'raw_occupied': 0,
                },
                'center_inside_but_cell_not_fully_contained_counts_by_raw_class': {
                    'unknown': 1739, 'known_free': 34, 'raw_occupied': 19,
                },
                'qualification': 'geometric only',
            }
            (run_dir / 'n10-box-map-snapshot-analysis.json').write_text(
                json.dumps(snapshot))
            result = evaluate_run(self.config, _metrics(), run_dir)
            classification = next(row for row in result['metrics']
                                  if row['id'] == 'raw_map_classification')
            self.assertEqual(classification['status'], 'PASS')
            self.assertEqual(classification['truth_occluded_known_free_voxel_count'], 0)
            self.assertIn('all eight transformed voxel corners',
                          classification['truth_occluded_count_method'])

            snapshot = json.loads(
                (run_dir / 'n10-box-map-snapshot-analysis.json').read_text())
            snapshot['snapshot_roi']['voxel_cell_geometry'][
                'all_corners_inside_box_counts_by_raw_class']['known_free'] = 13
            (run_dir / 'n10-box-map-snapshot-analysis.json').write_text(
                json.dumps(snapshot))
            result = evaluate_run(self.config, _metrics(), run_dir)
            classification = next(row for row in result['metrics']
                                  if row['id'] == 'raw_map_classification')
            self.assertEqual(classification['status'], 'FAIL')
            self.assertEqual(
                classification['truth_occluded_known_free_voxel_count'], 13)
            self.assertEqual(
                classification['known_free_voxels_inside_box_observed'], 34)

            snapshot['snapshot_roi']['truth_occluded_known_free_voxel_count'] = 0
            (run_dir / 'n10-box-map-snapshot-analysis.json').write_text(
                json.dumps(snapshot))
            result = evaluate_run(self.config, _metrics(), run_dir)
            classification = next(row for row in result['metrics']
                                  if row['id'] == 'raw_map_classification')
            self.assertEqual(classification['status'], 'PASS')
            snapshot['snapshot_roi']['truth_occluded_known_free_voxel_count'] = 1
            (run_dir / 'n10-box-map-snapshot-analysis.json').write_text(
                json.dumps(snapshot))
            result = evaluate_run(self.config, _metrics(), run_dir)
            classification = next(row for row in result['metrics']
                                  if row['id'] == 'raw_map_classification')
            self.assertEqual(classification['status'], 'FAIL')

    def test_partial_prohibited_contact_is_reported_as_failure_not_missing_data(self):
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp)
            (run_dir / 'n10-contact-evaluation-partial.json').write_text(json.dumps({
                'classification': 'partial contact record',
                'result': {
                    'sensor_topics_ready': True,
                    'prohibited_contact_event_count': 2,
                    'passed': False,
                },
                'terminal_status': {
                    'bridge_phase': 'LANDING',
                    'armed': True,
                    'landed': False,
                    'control_enabled': True,
                },
            }))
            result = evaluate_run(self.config, _metrics(), run_dir)
            clearance = next(row for row in result['metrics']
                             if row['id'] == 'full_body_clearance_and_contact')
            self.assertEqual(clearance['status'], 'FAIL')
            self.assertTrue(clearance['direct_safety_failure'])
            self.assertEqual(result['overall_status'], 'FAIL')

    def test_observed_planner_fault_without_terminal_state_fails_offline_metric(self):
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp)
            (run_dir / 'postflight-px4-bridge-readback.json').write_text(json.dumps({
                'latest': {
                    'bridge': {
                        'phase': 'LANDING',
                        'reason': 'planner_fault:full_curve_depth_odom_timeout',
                        'landed': False,
                        'armed': True,
                        'control_enabled': True,
                    },
                    'px4_status': {'failsafe': True, 'nav_state': 12},
                },
                'vehicle_remained_disarmed': False,
                'control_samples_zero': False,
            }))
            result = evaluate_run(self.config, _metrics(), run_dir)
            fault = next(row for row in result['metrics']
                         if row['id'] == 'fault_exit_to_terminal_px4_state')
            self.assertEqual(fault['status'], 'FAIL')
            self.assertTrue(fault['direct_safety_failure'])
            self.assertEqual(result['overall_status'], 'FAIL')

    def test_authorized_emergency_disarm_does_not_qualify_native_fault_landing(self):
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp)
            (run_dir / 'postflight-px4-bridge-readback.json').write_text(json.dumps({
                'latest': {
                    'bridge': {
                        'phase': 'LANDED', 'reason': 'planner_fault:depth_timeout',
                        'landed': True, 'armed': False, 'control_enabled': False,
                    },
                    'px4_status': {'arming_state': 1, 'nav_state': 14},
                    'land_detected': {'landed': True},
                },
                'vehicle_remained_disarmed': True,
                'control_samples_zero': True,
                'zero_control_after_terminal': True,
                'no_old_epoch_goal_or_trajectory': True,
            }))
            (run_dir / 'emergency-disarm-safe-terminal.json').write_text(json.dumps({
                'classification': 'authorized emergency-disarm closeout; not native landing',
                'command_count_requested': 1,
            }))
            result = evaluate_run(self.config, _metrics(), run_dir)
            fault = next(row for row in result['metrics']
                         if row['id'] == 'fault_exit_to_terminal_px4_state')
            self.assertEqual(fault['status'], 'FAIL')
            self.assertTrue(fault['direct_safety_failure'])
            self.assertTrue(fault['terminal_readback']['emergency_closeout_used'])
            self.assertFalse(fault['required_terminal_readback_complete'])
            self.assertEqual(result['overall_status'], 'FAIL')

    def test_resource_samples_before_safe_session_terminal_remain_insufficient(self):
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp)
            (run_dir / 'n10-resource-observation.json').write_text(json.dumps({
                'run_id': run_dir.name,
                'samples': [{'wall_elapsed_s': 1.0}],
                'wall_duration_s': 1.0,
                'terminal_flight_record_observed': True,
                'safe_session_terminal_observed': False,
            }))
            result = evaluate_run(self.config, _metrics(), run_dir)
            resource = next(row for row in result['metrics']
                            if row['id'] == 'resource_and_queue_behavior')
            self.assertEqual(resource['status'], 'INSUFFICIENT')
            self.assertFalse(resource['safe_session_terminal_observed'])
            self.assertIn('verified safe session closeout', resource['reason'])

    def test_resource_capacity_uses_cgroup_quota_and_memory_limit(self):
        self.assertEqual(cgroup_cpu_quota_capacity('250000 100000'), 2.5)
        self.assertIsNone(cgroup_cpu_quota_capacity('max 100000'))
        self.assertIsNone(cgroup_cpu_quota_capacity('invalid'))
        self.assertEqual(cgroup_numeric_limit('1048576'), 1048576.0)
        self.assertIsNone(cgroup_numeric_limit('max'))

    def test_resource_metric_passes_within_quota_and_fails_above_it(self):
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp) / 'run-1'
            resource_path, platform, metrics = _resource_capacity_fixture(run_dir)
            result = resource_and_queue_behavior_result(
                self.config, metrics, run_dir, platform)
            self.assertEqual(result['status'], 'PASS')
            self.assertEqual(result['available_cpu_capacity_cores'], 1.5)
            self.assertEqual(result['available_memory_capacity_bytes'], 1048576.0)
            self.assertEqual(result['vins_queue_capacity_status'], 'UNKNOWN_BY_SOURCE')

            resource = json.loads(resource_path.read_text())
            for sample in resource['samples']:
                sample['cgroup']['cpu_max'] = '25000 100000'
            resource_path.write_text(json.dumps(resource))
            platform['run_binding']['resource_observation_sha256'] = sha256(resource_path)
            result = resource_and_queue_behavior_result(
                self.config, metrics, run_dir, platform)
            self.assertEqual(result['status'], 'FAIL')
            self.assertTrue(result['direct_safety_failure'])

    def test_native_resource_requires_real_fields_and_flight_interval(self):
        config=json.loads((ROOT/'config/acceptance_n11.json').read_text())
        with tempfile.TemporaryDirectory() as temp:
            run_dir=Path(temp)/'run-1'
            resource_path,platform,metrics=_resource_capacity_fixture(run_dir)
            result=resource_and_queue_behavior_result(config,metrics,run_dir,platform)
            self.assertEqual(result['status'],'INSUFFICIENT')
            self.assertIn('flight_source_interval_missing',result['native_pending_work']['missing_or_inconsistent'])
    def test_native_resource_can_pass_and_preserves_cpu_failure(self):
        config=json.loads((ROOT/'config/acceptance_n11.json').read_text())
        from tools.test_n11_native_work_queue import rows
        with tempfile.TemporaryDirectory() as temp:
            run_dir=Path(temp)/'run-1'
            resource_path,platform,metrics=_resource_capacity_fixture(run_dir)
            resource=json.loads(resource_path.read_text());native=rows()[:2]
            queue=run_dir/'n10-vins-queue-telemetry.jsonl'
            existing=[json.loads(l) for l in queue.read_text().splitlines()]
            for i,row in enumerate(existing):
                row['source_stamp_ns']=native[i]['source_stamp_ns']
                row['queue_metrics']['work']=native[i]['queue_metrics']['work']
            queue.write_text(''.join(json.dumps(r)+'\n' for r in existing))
            resource['vins_queue_telemetry_artifact']['sha256']=sha256(queue)
            patch='dependencies/patches/vins/0021-readonly-native-work-queue.patch'
            resource['configured_queue_capacities']['source_sha256'][patch]=sha256(ROOT/patch)
            metrics['segments']={'prestream_to_landed':{'start_source_ns':native[0]['source_stamp_ns'],'end_source_ns':native[-1]['source_stamp_ns']}}
            for cpu,status in [('150000 100000','PASS'),('25000 100000','FAIL')]:
                for sample in resource['samples']:sample['cgroup']['cpu_max']=cpu
                resource_path.write_text(json.dumps(resource));platform['run_binding']['resource_observation_sha256']=sha256(resource_path)
                result=resource_and_queue_behavior_result(config,metrics,run_dir,platform)
                self.assertEqual(result['native_pending_work']['status'],'PASS')
                self.assertEqual(result['status'],status)

    def test_event_deadline_is_strict_at_source_timestamp_boundary(self):
        before = gate('event_deadline', [
            compare('ready_command_source_ns', 99, 100, '<', 'ns')], 'candidate')
        on_boundary = gate('event_deadline', [
            compare('ready_command_source_ns', 100, 100, '<', 'ns')], 'candidate')
        self.assertEqual(before['status'], 'PASS')
        self.assertEqual(on_boundary['status'], 'FAIL')

    def test_dynamic_replanning_requires_active_identity_and_preboundary_ready_command(self):
        with tempfile.TemporaryDirectory() as temp:
            valid_dir = Path(temp) / 'run-valid'
            report, tracking, tracking_metric, clearance_metric = _dynamic_replan_fixture(
                valid_dir, first_safe_command_ns=90_000_000_000)
            valid = dynamic_replanning_result(
                self.config, {'runtime_contract_sha256': 'runtime-contract-test-hash'},
                valid_dir, report, tracking, tracking_metric, clearance_metric)
            self.assertEqual(valid['status'], 'PASS')
            self.assertTrue(valid['pre_cloud_deadline_reference_matches_active_ready_command'])
            self.assertEqual(valid['first_safe_READY_command_deadline_slack_sim_s'], 10.0)

            boundary_dir = Path(temp) / 'run-boundary'
            report, tracking, tracking_metric, clearance_metric = _dynamic_replan_fixture(
                boundary_dir, first_safe_command_ns=100_000_000_000)
            boundary = dynamic_replanning_result(
                self.config, {'runtime_contract_sha256': 'runtime-contract-test-hash'},
                boundary_dir, report, tracking, tracking_metric, clearance_metric)
            self.assertEqual(boundary['status'], 'FAIL')
            self.assertTrue(boundary['pre_cloud_deadline_reference_matches_active_ready_command'])
            self.assertEqual(boundary['first_safe_READY_command_source_stamp_ns'], 100_000_000_000)

    def test_missing_event_deadline_and_platform_capacity_stay_offline_insufficient(self):
        run_dir = Path('/tmp/n10-no-replan-or-platform-capacity')
        result = evaluate_run(self.config, _metrics(), run_dir)
        dynamic = next(row for row in result['metrics']
                       if row['id'] == 'dynamic_replanning')
        resource = next(row for row in result['metrics']
                        if row['id'] == 'resource_and_queue_behavior')
        self.assertEqual(dynamic['status'], 'INSUFFICIENT')
        self.assertFalse(dynamic['runtime_gate_added'])
        self.assertEqual(resource['status'], 'INSUFFICIENT')
        self.assertFalse(resource['runtime_gate_added'])

    def test_observer_identity_binding_requires_all_reports_to_match_one_run(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / 'run-1'
            run.mkdir()
            stack = Path(temp) / 'run-1-stack/session'
            stack.mkdir(parents=True)
            identity = {
                'run_id': 'run-1', 'runtime_contract_sha256': 'contract-1',
                'goal_id': 'goal-1', 'epoch': 'epoch-1', 'map_id': 'epoch-1-map-1',
                'frame_id': 'odom_epoch-1', 'complete': True,
                'missing_fields': [], 'conflicts': [],
            }
            (run / 'n10-run-manifest.json').write_text(json.dumps({
                'run_id': 'run-1', 'runtime_contract_sha256': 'contract-1'}))
            (run / 'runtime-contract.json').write_text(json.dumps({'sha256': 'contract-1'}))
            (stack / 'session.json').write_text(json.dumps({'epoch': 'epoch-1'}))
            (run / 'flight.json').write_text(json.dumps({'goal_id': 'goal-1'}))
            (run / 'n10-map-point-queries.json').write_text(json.dumps({
                'identity': {'epoch': 'epoch-1', 'map_id': 'epoch-1-map-1',
                             'frame_id': 'odom_epoch-1'},
                'run_identity': identity,
            }))
            regular = (
                'debug-truth-evaluation.json', 'alignment-observation.json',
                'planner-observation.json', 'bridge-observation.json',
                'n09-contact-observation.json', 'n10-resource-observation.json',
                'n10-sensor-capture-evaluation.json',
            )
            for name in regular:
                data = {'run_identity': identity}
                if name == 'n10-sensor-capture-evaluation.json':
                    data['status'] = 'PASS'
                (run / name).write_text(json.dumps(data))
            (run / 'n10-live-obstacle-observation.json').write_text(json.dumps({
                'run_id': 'run-1', 'runtime_contract_baseline_sha256': 'contract-1',
                'goal_id': 'goal-1', 'epoch': 'epoch-1',
                'map_id_at_goal': 'epoch-1-map-1',
            }))
            row = observer_identity_binding_result(self.config, run)
            self.assertEqual(row['status'], 'PASS')
            self.assertFalse(row['runtime_control_effect'])
            (run / 'n10-map-point-queries.json').unlink()
            row = observer_identity_binding_result(self.config, run)
            self.assertEqual(row['status'], 'PASS')
            self.assertEqual(row['missing_optional_observer_reports'],
                             ['n10-map-point-queries.json'])
            (run / 'n10-map-point-queries.json').write_text(json.dumps({
                'identity': identity, 'run_identity': identity,
            }))
            changed = json.loads((run / 'planner-observation.json').read_text())
            changed['run_identity']['map_id'] = 'other-epoch-map'
            (run / 'planner-observation.json').write_text(json.dumps(changed))
            row = observer_identity_binding_result(self.config, run)
            self.assertEqual(row['status'], 'INSUFFICIENT')
            self.assertEqual(row['identity_mismatches']['planner-observation.json'],
                             'identity_tuple_differs_from_run')

    def test_map_surface_uses_identity_bound_arrays_and_reports_observed_faces(self):
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp)
            faces = {
                'x_negative': {
                    'surface_center_error_sample_count': 20,
                    'surface_center_error_max_m': 0.05,
                },
                'y_negative': {
                    'surface_center_error_sample_count': 12,
                    'surface_center_error_max_m': 0.08,
                },
                'x_positive': {
                    'surface_center_error_sample_count': 0,
                    'surface_center_error_max_m': None,
                },
            }
            snapshot = {
                'snapshot_matches_live_observer_epoch_map_frame': True,
                'snapshot_source_coverage': {'covered': False},
                'snapshot_roi': {
                    'surface_face_samples': faces,
                    'inside_box_voxel_counts_by_raw_class': {
                        'unknown': 10, 'known_free': 0, 'raw_occupied': 4,
                    },
                    'truth_occluded_known_free_voxel_count': 0,
                },
                'point_query_archive': {'present': False, 'query_count': 0},
            }
            (run_dir / 'n10-box-map-snapshot-analysis.json').write_text(json.dumps(snapshot))
            result = evaluate_run(self.config, _metrics(), run_dir)
            rows = {row['id']: row for row in result['metrics']}
            self.assertEqual(rows['raw_map_surface_geometry']['status'], 'INSUFFICIENT')
            self.assertEqual(rows['raw_map_classification']['status'], 'INSUFFICIENT')
            snapshot['snapshot_source_coverage'] = {'covered': True}
            (run_dir / 'n10-box-map-snapshot-analysis.json').write_text(json.dumps(snapshot))
            result = evaluate_run(self.config, _metrics(), run_dir)
            rows = {row['id']: row for row in result['metrics']}
            self.assertEqual(rows['raw_map_surface_geometry']['status'], 'PASS')
            self.assertEqual(rows['raw_map_classification']['status'], 'PASS')
            self.assertEqual(rows['raw_map_surface_geometry']['observed_faces'],
                             ['x_negative', 'y_negative'])
            self.assertEqual(rows['raw_map_surface_geometry']['unobserved_faces'],
                             ['x_positive', 'y_positive', 'z_negative', 'z_positive'])
            self.assertTrue(rows['raw_map_surface_geometry'][
                'point_queries_are_optional_diagnostics'])
            snapshot['snapshot_roi']['surface_face_samples']['y_negative'][
                'surface_center_error_max_m'] = 0.11
            (run_dir / 'n10-box-map-snapshot-analysis.json').write_text(json.dumps(snapshot))
            result = evaluate_run(self.config, _metrics(), run_dir)
            rows = {row['id']: row for row in result['metrics']}
            self.assertEqual(rows['raw_map_surface_geometry']['status'], 'FAIL')
            snapshot['snapshot_roi']['surface_face_samples']['x_negative'][
                'surface_center_error_sample_count'] = 0
            snapshot['snapshot_roi']['surface_face_samples']['y_negative'][
                'surface_center_error_sample_count'] = 0
            (run_dir / 'n10-box-map-snapshot-analysis.json').write_text(json.dumps(snapshot))
            result = evaluate_run(self.config, _metrics(), run_dir)
            rows = {row['id']: row for row in result['metrics']}
            self.assertEqual(rows['raw_map_surface_geometry']['status'], 'INSUFFICIENT')

    def test_identity_evidence_binds_contract_goal_epoch_and_map(self):
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp) / 'run-1'
            run_dir.mkdir()
            (run_dir / 'runtime-contract.json').write_text(json.dumps({'sha256': 'contract-hash'}))
            (run_dir / 'flight.json').write_text(json.dumps({
                'goal_id': 'goal-1', 'localization_epoch': 'epoch-1',
            }))
            (run_dir / 'n10-live-obstacle-observation.json').write_text(json.dumps({
                'run_id': 'run-1', 'goal_id': 'goal-1', 'epoch': 'epoch-1',
                'map_id_at_goal': 'epoch-1-map-1',
            }))
            evidence = identity_evidence('run-1', _metrics(), run_dir)
            self.assertTrue(evidence['runtime_contract_matches_calibration_record'])
            self.assertTrue(evidence['goal_epoch_map_identity_is_bound'])

    def test_archived_input_mutation_is_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp)
            source = run_dir / 'flight.json'
            source.write_text('{}')
            from tools.debug_truth.evaluate_n10_acceptance import sha256
            metrics = {'input_sha256': {'flight.json': sha256(source)}}
            self.assertTrue(archived_input_hashes(metrics, run_dir)['matches'])
            source.write_text('{"changed": true}')
            self.assertFalse(archived_input_hashes(metrics, run_dir)['matches'])




class ScopedCalibrationSummaryTests(unittest.TestCase):
    def test_excluded_missing_fault_keeps_its_status_without_blocking_required_coverage(self):
        config={'status':'frozen','metrics':{'fault':{'required':False}}}
        result=summarize_required_metrics(config,[{'id':'normal','status':'PASS'},
                                                {'id':'fault','status':'INSUFFICIENT'}])
        self.assertEqual(result['overall_status'],'PASS')
        self.assertEqual(result['metrics'][1]['status'],'INSUFFICIENT')
        self.assertEqual(result['excluded_from_required_calibration'],['fault'])

    def test_required_missing_data_still_insufficient(self):
        result=summarize_required_metrics({'status':'frozen'},[{'id':'normal','status':'INSUFFICIENT'}])
        self.assertEqual(result['overall_status'],'INSUFFICIENT')

    def test_exclusion_never_hides_an_observed_direct_failure(self):
        config={'status':'frozen','metrics':{'fault':{'required':False}}}
        result=summarize_required_metrics(config,[{'id':'fault','status':'FAIL','direct_safety_failure':True}])
        self.assertEqual(result['overall_status'],'FAIL')

    def test_draft_never_passes_due_to_exclusion(self):
        config={'status':'draft','metrics':{'fault':{'required':False}}}
        self.assertEqual(summarize_required_metrics(config,[{'id':'fault','status':'INSUFFICIENT'}])['overall_status'],'INSUFFICIENT')

if __name__ == '__main__':
    unittest.main()
