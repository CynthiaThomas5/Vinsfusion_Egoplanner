#!/usr/bin/env python3
"""Join the two live map checks and unarmed support scan into N05 evidence."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(run_dir):
    run_dir = Path(run_dir).resolve()
    inputs = json.loads((run_dir/'n05-run-inputs.json').read_text())
    before = json.loads((run_dir/'n05-before/n05-live-entry-check.json').read_text())
    after = json.loads((run_dir/'n05-after/n05-live-entry-check.json').read_text())
    before_replay = json.loads((run_dir/'n05-before/n05-offline-entry-replay.json').read_text())
    after_replay = json.loads((run_dir/'n05-after/n05-offline-entry-replay.json').read_text())
    post_dir = run_dir/'n05-post-release'
    post_report_path = post_dir/'n05-live-entry-check.json'
    post_error_path = post_dir/'n05-live-entry-check-error.json'
    post_report = json.loads(post_report_path.read_text()) if post_report_path.is_file() else None
    post_error = json.loads(post_error_path.read_text()) if post_error_path.is_file() else None
    post_replay_path = post_dir/'n05-offline-entry-replay.json'
    post_replay = json.loads(post_replay_path.read_text()) if post_replay_path.is_file() else None
    ready = json.loads((run_dir/'n05-prescan-ready.json').read_text())
    fixture = json.loads((run_dir/'fixture-result.json').read_text())
    scene = json.loads((run_dir/'n05-layout-scene.json').read_text())
    removal_path = run_dir/'n05-fixture-removal-verification.json'
    removal_audit = json.loads(removal_path.read_text()) if removal_path.is_file() else None
    layout = inputs['layout_id']
    same_epoch = before['identity']['epoch'] == after['identity']['epoch']
    same_map = before['identity']['map_id'] == after['identity']['map_id']
    scan_identity_matches = (ready['epoch'] == after['identity']['epoch']
                             and ready['map_id'] == after['identity']['map_id'])
    layout_matches = (scene['layout_id'] == layout == ready['layout_id']
                      and fixture['n05_layout']['layout_id'] == layout)
    unarmed = (fixture['vehicle_states']
               and set(fixture['vehicle_states']) == {1})
    runner_removal_confirmed = bool(
        fixture.get('fixture_removed')
        and fixture.get('fixture_removal_confirmation', {}).get('scene_model_absent', True)
        and not fixture.get('fixture_may_remain_attached'))
    independent_removal_confirmed = bool(removal_audit and
        removal_audit.get('fixture_model') == fixture.get('fixture_model', 'preflight_scan_fixture')
        and removal_audit.get('independent_gazebo_model_list_query', {}).get('fixture_model_present') is False
        and removal_audit.get('px4_bridge_status', {}).get('phase') == 'DISABLED'
        and removal_audit.get('px4_bridge_status', {}).get('armed') is False
        and removal_audit.get('px4_bridge_status', {}).get('control_enabled') is False
        and removal_audit.get('px4_bridge_status', {}).get('landed') is True)
    detached = ('detached' in fixture['attachment_states']
                and not fixture['fixture_may_remain_attached']
                and (runner_removal_confirmed or independent_removal_confirmed))
    fixture_stages = json.loads((run_dir/'fixture-stages.json').read_text())
    profile_complete = (len(fixture_stages) == fixture['completed_stages']
                       and fixture['completed_stages'] > 0
                       and fixture['n05_live_check_completed'])
    online_offline_match = (
        before['online_offline_result_identical']
        and after['online_offline_result_identical']
        and before_replay['matches_online_result']
        and after_replay['matches_online_result'])
    if post_replay is not None:
        online_offline_match = online_offline_match and post_replay['matches_online_result']
    post_release_recorded = post_report is not None or post_error is not None
    post_identity_matches = bool(post_report and
        post_report['identity']['epoch'] == before['identity']['epoch']
        and post_report['identity']['map_id'] == before['identity']['map_id'])
    post_pose_shift_m = None
    post_pose_within_budget = False
    if post_report:
        p0 = after['state']['body_pose_imu_m']['center_xyz_m']
        p1 = post_report['state']['body_pose_imu_m']['center_xyz_m']
        post_pose_shift_m = math.sqrt(sum((float(a)-float(b))**2 for a,b in zip(p0,p1)))
        policy = json.loads((Path(__file__).resolve().parents[1]
                             /'config/components/navigation/vehicle_envelope.json').read_text())
        post_pose_within_budget = (
            math.isfinite(post_pose_shift_m)
            and post_pose_shift_m <= policy['spatial_budget']['combined_uncertainty_margin_m'])
    post_admission = (post_report or {}).get('online_admission', {})
    transfer_gate_passed = bool(post_report and post_identity_matches
                                and post_pose_within_budget
                                and post_admission.get('accepted'))
    report = {
        'schema': 'n05-unarmed-layout-run/v1',
        'run_id': inputs['run_id'],
        'layout_id': layout,
        'qualification': 'unarmed full-airframe support scan and raw-map entry diagnostic only; not flight approval',
        'run_inputs_sha256': sha256(run_dir/'n05-run-inputs.json'),
        'world_layout_sha256': sha256(run_dir/'n05-layout-scene.json'),
        'source_code_hashes': inputs['file_sha256'],
        'identity': {
            'epoch_before': before['identity']['epoch'],
            'epoch_after': after['identity']['epoch'],
            'map_id_before': before['identity']['map_id'],
            'map_id_after': after['identity']['map_id'],
            'same_epoch': same_epoch, 'same_map_id': same_map,
            'scan_identity_matches_after_snapshot': scan_identity_matches,
        },
        'before_scan': {
            'admission': before['online_admission'],
            'archive_sha256': before['snapshot']['archive_sha256'],
            'offline_replay': before_replay,
        },
        'after_scan': {
            'admission': after['online_admission'],
            'archive_sha256': after['snapshot']['archive_sha256'],
            'offline_replay': after_replay,
        },
        'post_release': {
            'check_attempted': post_release_recorded,
            'check_available': post_report is not None,
            'check_error': post_error,
            'admission': post_admission or None,
            'offline_replay': post_replay,
            'same_epoch_and_map_id': post_identity_matches,
            'body_pose_shift_from_attached_snapshot_m': post_pose_shift_m,
            'body_pose_shift_within_spatial_budget': post_pose_within_budget,
            'transfer_gate_passed': transfer_gate_passed,
        },
        'fixture': fixture,
        'fixture_removal_audit': removal_audit,
        'layout_scene': scene,
        'control_or_goal_published': False,
        'debug_truth_subscribed': False,
        'checks': {
            'layout_identity_consistent': layout_matches,
            'same_epoch_before_after': same_epoch,
            'same_map_id_before_after': same_map,
            'scan_identity_matches_after_snapshot': scan_identity_matches,
            'vehicle_disarmed_for_all_recorded_states': bool(unarmed),
            'support_detached_and_fixture_absent': detached,
            'fixture_runner_profile_completed': profile_complete,
            'online_and_offline_checks_identical': bool(online_offline_match),
            'post_release_check_recorded': post_release_recorded,
            'post_release_same_identity': post_identity_matches,
            'post_release_pose_within_budget': post_pose_within_budget,
            'post_release_entry_accepted': bool(post_admission.get('accepted')),
            'control_and_navigation_goal_absent': True,
            'debug_truth_absent_from_online_inputs': True,
        },
        'diagnostic_pass': bool(layout_matches and same_epoch and same_map
                                and scan_identity_matches and unarmed and detached
                                and profile_complete and online_offline_match
                                and post_release_recorded),
    }
    output = run_dir/'n05-run-summary.json'
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    args = parser.parse_args()
    report = summarize(args.run_dir)
    print(json.dumps({'run_id': report['run_id'], 'layout_id': report['layout_id'],
                      'diagnostic_pass': report['diagnostic_pass'],
                      'before_admission': report['before_scan']['admission']['reason'],
                      'after_admission': report['after_scan']['admission']['reason'],
                      'checks': report['checks']},indent=2,ensure_ascii=False))
    return 0 if report['diagnostic_pass'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
