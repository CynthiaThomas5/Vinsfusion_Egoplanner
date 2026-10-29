import copy
import json
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe_preflight_scan import (PROFILE_CHOICES, _confirm_fixture_removed,
                                  _localization_gate_diagnostic,
                                  fixture_pose_returned, validate_profile)

ROOT=Path(__file__).resolve().parents[1]
MODEL=ROOT/'simulation/models/preflight_scan_fixture/model.sdf'


class ScanProfileTests(unittest.TestCase):
    def setUp(self):
        self.policy=json.loads((ROOT/'config/components/simulation/preflight_scan.json').read_text())

    def test_localization_diagnostic_ignores_receipt_age_but_keeps_identity_checks(self):
        from types import SimpleNamespace
        tracking=1
        valid=SimpleNamespace(state=tracking,valid=True,reason='tracking',epoch='epoch-a',
                              source_stamp=SimpleNamespace(sec=12,nanosec=34))
        good=_localization_gate_diagnostic(valid,'epoch-a',9.0,9.2,tracking,123)
        self.assertFalse(good['failed'])
        self.assertEqual(good['failures'],[])
        self.assertEqual(good['source_stamp_ns'],12_000_000_034)
        stale_but_valid=_localization_gate_diagnostic(valid,'epoch-a',1.0,99.0,tracking,123)
        self.assertFalse(stale_but_valid['failed'])
        bad_samples=[
            (None,'epoch-a',9.0,9.2,['missing']),
            (SimpleNamespace(**{**vars(valid),'valid':False}),'epoch-a',9.0,9.2,['invalid']),
            (SimpleNamespace(**{**vars(valid),'state':2}),'epoch-a',9.0,9.2,['not_tracking']),
            (valid,'epoch-b',9.0,9.2,['epoch_mismatch']),
        ]
        for sample,expected,received,now,reasons in bad_samples:
            with self.subTest(reasons=reasons):
                diagnostic=_localization_gate_diagnostic(
                    sample,expected,received,now,tracking,123)
                self.assertTrue(diagnostic['failed'])
                self.assertEqual(diagnostic['failures'],reasons)

    def test_canonical_profile(self):
        validate_profile(self.policy,MODEL)
        validate_profile(self.policy,MODEL,"coverage")
        validate_profile(self.policy,MODEL,"n06_extended_reach")
        validate_profile(self.policy,MODEL,"n06_extended_reach_slow_x")
        validate_profile(self.policy,MODEL,"n06_extended_reach_slow_x_pitch60")
        validate_profile(self.policy,MODEL,"n06_extended_reach_slow_x_pitch60_single_yaw")
        validate_profile(self.policy,MODEL,"n06_extended_reach_slow_x_pitch45_yaw0")
        validate_profile(self.policy,MODEL,"n06_full_airframe_retreat_240")
        validate_profile(self.policy,MODEL,"n06_full_airframe_retreat_240_translation_only")
        validate_profile(self.policy,MODEL,"n06_full_airframe_retreat_240_segmented_actual_return")
        validate_profile(self.policy,MODEL,"n06_full_airframe_retreat_240_oblique_site_view")
        validate_profile(self.policy,MODEL,"n06_full_airframe_retreat_240_oblique_separated_return")
        validate_profile(self.policy,MODEL,"n06_full_airframe_retreat_240_oblique_early_view")
        validate_profile(self.policy,MODEL,"n07_default_spawn_translation_only")
        validate_profile(self.policy,MODEL,"n07_default_spawn_bidirectional_translation_only")
        validate_profile(self.policy,MODEL,"n07_spawn_minus65_retreat_150_translation_only")
        validate_profile(self.policy,MODEL,"n07_spawn_minus65_retreat_180_translation_only")
        validate_profile(self.policy,MODEL,"n07_spawn_minus65_retreat_180_yaw015rad_view")
        validate_profile(self.policy,MODEL,"n07_spawn_minus65_retreat_180_yaw015rad_return_view")
        validate_profile(self.policy,MODEL,"n07_spawn_minus65_retreat_180_pitch045_view")
        validate_profile(self.policy,MODEL,"n07_spawn_minus65_retreat_180_pitch045_return_view")
        validate_profile(self.policy,MODEL,"n08_overhead_negative_side_view")
        validate_profile(self.policy,MODEL,
                         "n08_overhead_free_sector_with_negative_side_view")
        validate_profile(self.policy,MODEL,
                         "n08_overhead_free_sector_with_negative_side_recovery")
        validate_profile(self.policy,MODEL,"n08_overhead_rear_facing_view")
        validate_profile(self.policy,MODEL,"n08_overhead_rear_down_view")
        validate_profile(self.policy,MODEL,"n08_overhead_rear_down_slow_yaw_return")
        validate_profile(self.policy,MODEL,
                         "n08_overhead_free_sector_negative_y_rear_short_hold_slow_descent")
        validate_profile(self.policy,MODEL,
                         "n08_overhead_free_sector_negative_y_rear_short_hold_slow_return_slow_descent")
        validate_profile(self.policy,MODEL,
                         "n08_overhead_free_sector_negative_y_rear_short_hold_low_rear_view")
        validate_profile(self.policy,MODEL,
                         "n08_overhead_free_sector_negative_y_rear_short_hold_low_rear_view_separated_pitch")
        validate_profile(self.policy,MODEL,"drift")
        validate_profile(self.policy,MODEL,"loop_revisit")

    def test_profile_choice_is_available_to_fixture_runner(self):
        self.assertIn('n06_full_airframe_retreat_240_oblique_early_view',
                      PROFILE_CHOICES)
        self.assertIn('n07_default_spawn_translation_only',
                      PROFILE_CHOICES)
        self.assertIn('n07_default_spawn_bidirectional_translation_only',
                      PROFILE_CHOICES)
        self.assertIn('n07_spawn_minus65_retreat_150_translation_only',
                      PROFILE_CHOICES)
        self.assertIn('n07_spawn_minus65_retreat_180_translation_only',
                      PROFILE_CHOICES)
        self.assertIn('n07_spawn_minus65_retreat_180_yaw015rad_view',
                      PROFILE_CHOICES)
        self.assertIn('n07_spawn_minus65_retreat_180_yaw015rad_return_view',
                      PROFILE_CHOICES)
        self.assertIn('n07_spawn_minus65_retreat_180_pitch045_view',
                      PROFILE_CHOICES)
        self.assertIn('n07_spawn_minus65_retreat_180_pitch045_return_view',
                      PROFILE_CHOICES)
        self.assertIn('n08_overhead_negative_side_view',PROFILE_CHOICES)
        self.assertIn('n08_overhead_free_sector_with_negative_side_view',
                      PROFILE_CHOICES)
        self.assertIn('n08_overhead_free_sector_with_negative_side_recovery',
                      PROFILE_CHOICES)
        self.assertIn('n08_overhead_rear_facing_view',PROFILE_CHOICES)
        self.assertIn('n08_overhead_rear_down_view',PROFILE_CHOICES)
        self.assertIn('n08_overhead_rear_down_slow_yaw_return',PROFILE_CHOICES)
        self.assertIn('n08_overhead_free_sector_view_decoupled_return',
                      PROFILE_CHOICES)
        self.assertIn(
            'n08_overhead_free_sector_view_decoupled_slow_vertical_return',
            PROFILE_CHOICES)
        self.assertIn(
            'n08_overhead_free_sector_view_decoupled_slow_vertical_return_negative_side',
            PROFILE_CHOICES)
        self.assertIn('n08_overhead_free_sector_negative_side_slow_descent',
                      PROFILE_CHOICES)
        self.assertIn(
            'n08_overhead_free_sector_negative_y_rear_short_hold_slow_descent',
            PROFILE_CHOICES)
        self.assertIn(
            'n08_overhead_free_sector_negative_y_rear_short_hold_slow_return_slow_descent',
            PROFILE_CHOICES)
        self.assertIn(
            'n08_overhead_free_sector_negative_y_rear_short_hold_slow_return_segmented_neutral_descent',
            PROFILE_CHOICES)
        self.assertIn(
            'n08_overhead_free_sector_negative_y_rear_short_hold_low_rear_view',
            PROFILE_CHOICES)
        self.assertIn(
            'n08_overhead_free_sector_negative_y_rear_short_hold_low_rear_view_separated_pitch',
            PROFILE_CHOICES)

    def test_n08_decoupled_return_only_splits_the_yaw_pitch_return(self):
        baseline=self.policy['n08_overhead_free_sector_view_profile']
        candidate=self.policy[
            'n08_overhead_free_sector_view_decoupled_return_profile']
        self.assertEqual(candidate[:11],baseline[:11])
        self.assertEqual(candidate[13:],baseline[12:])
        self.assertEqual(candidate[11],{
            'duration_sim_s':12,'target':[0,1.0,math.pi/2,0]})
        self.assertEqual(candidate[12],{
            'duration_sim_s':12,'target':[0,1.0,0,0]})
        self.assertEqual(len(candidate),16)
        validate_profile(self.policy,MODEL,
                         'n08_overhead_free_sector_view_decoupled_return')

    def test_n08_slow_vertical_return_changes_only_the_final_return_duration(self):
        baseline=self.policy[
            'n08_overhead_free_sector_view_decoupled_return_profile']
        candidate=self.policy[
            'n08_overhead_free_sector_view_decoupled_slow_vertical_return_profile']
        self.assertEqual(candidate[:-2],baseline[:-2])
        self.assertEqual(candidate[-2]['target'],baseline[-2]['target'])
        self.assertEqual(candidate[-2]['duration_sim_s'],20)
        self.assertEqual(candidate[-1],baseline[-1])
        validate_profile(self.policy,MODEL,
            'n08_overhead_free_sector_view_decoupled_slow_vertical_return')

    def test_n08_negative_side_adds_only_a_negative_y_view_and_return(self):
        baseline=self.policy[
            'n08_overhead_free_sector_view_decoupled_slow_vertical_return_profile']
        candidate=self.policy[
            'n08_overhead_free_sector_view_decoupled_slow_vertical_return_negative_side_profile']
        self.assertEqual(candidate[:13],baseline[:13])
        self.assertEqual(candidate[13:16],[
            {'duration_sim_s':16,'target':[0,1.0,-math.pi/2,0]},
            {'duration_sim_s':18,'target':[0,1.0,-math.pi/2,0]},
            {'duration_sim_s':16,'target':[0,1.0,0,0]},
        ])
        self.assertEqual(candidate[16:],baseline[13:])
        validate_profile(self.policy,MODEL,
            'n08_overhead_free_sector_view_decoupled_slow_vertical_return_negative_side')

    def test_n08_negative_side_slow_descent_changes_only_first_vertical_return_duration(self):
        baseline=self.policy[
            'n08_overhead_free_sector_view_decoupled_slow_vertical_return_negative_side_profile']
        candidate=self.policy[
            'n08_overhead_free_sector_negative_side_slow_descent_profile']
        self.assertEqual(candidate[:16],baseline[:16])
        self.assertEqual(candidate[16]['target'],baseline[16]['target'])
        self.assertEqual(candidate[16]['duration_sim_s'],20)
        self.assertEqual(candidate[17:],baseline[17:])
        validate_profile(self.policy,MODEL,
                         'n08_overhead_free_sector_negative_side_slow_descent')

    def test_n08_negative_side_profile_preserves_overhead_scan_and_has_only_negative_horizontal_yaw(self):
        baseline=self.policy['n08_overhead_positive_side_view_profile']
        candidate=self.policy['n08_overhead_negative_side_view_profile']
        self.assertEqual(candidate[:9],baseline[:9])
        self.assertEqual([stage['target'][2:] for stage in candidate[9:]], [
            [-math.pi/2,0],[-math.pi/2,0],[0,0],[0,0],[0,0],[0,0],[0,0]])
        validate_profile(self.policy,MODEL,'n08_overhead_negative_side_view')

    def test_n08_free_sector_negative_side_extension_adds_only_one_side_view_and_return(self):
        baseline=self.policy['n08_overhead_free_sector_view_profile']
        candidate=self.policy[
            'n08_overhead_free_sector_with_negative_side_view_profile']
        self.assertEqual(candidate[:12],baseline[:12])
        self.assertEqual(candidate[12:15],[
            {'duration_sim_s':16,'target':[0,1.0,-math.pi/2,0]},
            {'duration_sim_s':18,'target':[0,1.0,-math.pi/2,0]},
            {'duration_sim_s':12,'target':[0,1.0,0,0]},
        ])
        self.assertEqual(candidate[15:],baseline[12:])
        validate_profile(self.policy,MODEL,
            'n08_overhead_free_sector_with_negative_side_view')

    def test_n08_negative_side_recovery_adds_only_a_level_hold_before_descent(self):
        baseline=self.policy[
            'n08_overhead_free_sector_with_negative_side_view_profile']
        candidate=self.policy[
            'n08_overhead_free_sector_with_negative_side_recovery_profile']
        self.assertEqual(candidate[:15],baseline[:15])
        self.assertEqual(candidate[15],{
            'duration_sim_s':15,'target':[0,1.0,0,0]})
        self.assertEqual(candidate[16:],baseline[15:])
        validate_profile(self.policy,MODEL,
            'n08_overhead_free_sector_with_negative_side_recovery')

    def test_n08_negative_side_short_dwell_changes_only_stationary_observation_time(self):
        baseline=self.policy[
            'n08_overhead_free_sector_with_negative_side_view_profile']
        candidate=self.policy[
            'n08_overhead_free_sector_negative_side_short_dwell_profile']
        self.assertEqual(len(candidate),len(baseline))
        for index,(source,target) in enumerate(zip(baseline,candidate)):
            expected=copy.deepcopy(source)
            if index==13:
                expected['duration_sim_s']=8
            self.assertEqual(target,expected)
        validate_profile(self.policy,MODEL,
                         'n08_overhead_free_sector_negative_side_short_dwell')

    def test_n08_negative_y_side_view_reuses_the_qualified_route_duration(self):
        baseline=self.policy['n08_overhead_free_sector_view_profile']
        candidate=self.policy[
            'n08_overhead_free_sector_negative_y_side_view_profile']
        self.assertEqual(len(candidate),len(baseline))
        self.assertEqual(candidate[:9],baseline[:9])
        self.assertEqual(candidate[9],{
            'duration_sim_s':12,'target':[0,1.0,-math.pi/2,0]})
        self.assertEqual(candidate[10],{
            'duration_sim_s':18,'target':[0,1.0,-math.pi/2,0]})
        self.assertEqual(candidate[11:],baseline[11:])
        validate_profile(self.policy,MODEL,
                         'n08_overhead_free_sector_negative_y_side_view')

    def test_n08_negative_y_rear_view_turns_in_quarter_turns_and_returns_to_forward(self):
        baseline=self.policy[
            'n08_overhead_free_sector_negative_y_side_view_profile']
        candidate=self.policy[
            'n08_overhead_free_sector_negative_y_rear_view_profile']
        self.assertEqual(candidate[:9],baseline[:9])
        self.assertEqual(candidate[9:14],[
            {'duration_sim_s':12,'target':[0,1.0,-math.pi/2,0]},
            {'duration_sim_s':18,'target':[0,1.0,-math.pi,0]},
            {'duration_sim_s':12,'target':[0,1.0,-math.pi,0]},
            {'duration_sim_s':12,'target':[0,1.0,-math.pi/2,0]},
            {'duration_sim_s':12,'target':[0,1.0,0,0]},
        ])
        self.assertEqual(candidate[14:],baseline[12:])
        validate_profile(self.policy,MODEL,
                         'n08_overhead_free_sector_negative_y_rear_view')

    def test_n08_negative_y_rear_short_hold_changes_only_rear_dwell(self):
        baseline=self.policy[
            'n08_overhead_free_sector_negative_y_rear_view_profile']
        candidate=self.policy[
            'n08_overhead_free_sector_negative_y_rear_short_hold_profile']
        self.assertEqual(len(candidate),len(baseline))
        for index,(source,target) in enumerate(zip(baseline,candidate)):
            expected=copy.deepcopy(source)
            if index==11:
                expected['duration_sim_s']=4
            self.assertEqual(target,expected)
        validate_profile(self.policy,MODEL,
                         'n08_overhead_free_sector_negative_y_rear_short_hold')

    def test_n08_negative_y_rear_short_hold_slow_descent_changes_only_descent_duration(self):
        baseline=self.policy[
            'n08_overhead_free_sector_negative_y_rear_short_hold_profile']
        candidate=self.policy[
            'n08_overhead_free_sector_negative_y_rear_short_hold_slow_descent_profile']
        self.assertEqual(len(candidate),len(baseline))
        for index,(source,target) in enumerate(zip(baseline,candidate)):
            expected=copy.deepcopy(source)
            if index==14:
                expected['duration_sim_s']=12
            self.assertEqual(target,expected)
        self.assertEqual(sum(x['duration_sim_s'] for x in candidate),
                         sum(x['duration_sim_s'] for x in baseline)+4)
        validate_profile(self.policy,MODEL,
                         'n08_overhead_free_sector_negative_y_rear_short_hold_slow_descent')

    def test_n08_negative_y_rear_scan_slow_return_changes_only_stage7_duration(self):
        baseline=self.policy[
            'n08_overhead_free_sector_negative_y_rear_short_hold_slow_descent_profile']
        candidate=self.policy[
            'n08_overhead_free_sector_negative_y_rear_short_hold_slow_return_slow_descent_profile']
        self.assertEqual(len(candidate),len(baseline))
        for index,(source,target) in enumerate(zip(baseline,candidate)):
            expected=copy.deepcopy(source)
            if index==7:
                expected['duration_sim_s']=100
            self.assertEqual(target,expected)
        self.assertEqual(sum(x['duration_sim_s'] for x in candidate),
                         sum(x['duration_sim_s'] for x in baseline)+40)
        validate_profile(self.policy,MODEL,
                         'n08_overhead_free_sector_negative_y_rear_short_hold_slow_return_slow_descent')

    def test_n08_low_rear_view_moves_descent_before_rear_observation(self):
        baseline=self.policy[
            'n08_overhead_free_sector_negative_y_rear_short_hold_slow_return_slow_descent_profile']
        candidate=self.policy[
            'n08_overhead_free_sector_negative_y_rear_short_hold_low_rear_view_profile']
        self.assertEqual(candidate[:10],baseline[:10])
        self.assertEqual(candidate[10:13],baseline[14:17])
        rear=copy.deepcopy(baseline[10:14])
        for stage in rear:
            stage['target'][1]=0
        rear[0]['target'][3]=-0.35
        rear[1]['target'][3]=-0.35
        self.assertEqual(candidate[13:],rear)
        self.assertEqual(sum(x['duration_sim_s'] for x in candidate),
                         sum(x['duration_sim_s'] for x in baseline))
        validate_profile(self.policy,MODEL,
                         'n08_overhead_free_sector_negative_y_rear_short_hold_low_rear_view')

    def test_n08_slow_return_pitch_down_changes_only_descent_view(self):
        baseline=self.policy[
            'n08_overhead_free_sector_negative_y_rear_short_hold_slow_return_slow_descent_profile']
        candidate=self.policy[
            'n08_overhead_free_sector_negative_y_rear_short_hold_slow_return_pitch_down_descent_profile']
        self.assertEqual(len(candidate),19)
        self.assertEqual(candidate[:14],baseline[:14])
        self.assertEqual(candidate[14:],[
            {'duration_sim_s':8,'target':[0,1.0,0,-0.35]},
            {'duration_sim_s':12,'target':[0,0.5,0,-0.35]},
            {'duration_sim_s':7,'target':[0,0,0,-0.35]},
            {'duration_sim_s':8,'target':[0,0,0,0]},
            {'duration_sim_s':5,'target':[0,0,0,0]},
        ])
        self.assertEqual(sum(x['duration_sim_s'] for x in candidate),478)
        validate_profile(self.policy,MODEL,
                         'n08_overhead_free_sector_negative_y_rear_short_hold_slow_return_pitch_down_descent')

    def test_n08_segmented_neutral_descent_adds_settling_dwell_only(self):
        baseline=self.policy[
            'n08_overhead_free_sector_negative_y_rear_short_hold_slow_return_slow_descent_profile']
        candidate=self.policy[
            'n08_overhead_free_sector_negative_y_rear_short_hold_slow_return_segmented_neutral_descent_profile']
        self.assertEqual(candidate[:14],baseline[:14])
        expected=[]
        for step in range(1,11):
            z=round(1.0-step*0.1,1)
            target=[0,z,0,0]
            expected.append({'duration_sim_s':2.4 if step<=5 else 1.4,
                             'target':target})
            expected.append({'duration_sim_s':2,'target':target[:]})
        expected.append({'duration_sim_s':5,'target':[0,0,0,0]})
        self.assertEqual(candidate[14:],expected)
        self.assertEqual(sum(x['duration_sim_s'] for x in candidate),
                         sum(x['duration_sim_s'] for x in baseline)+20)
        validate_profile(self.policy,MODEL,
                         'n08_overhead_free_sector_negative_y_rear_short_hold_slow_return_segmented_neutral_descent')

    def test_n08_low_rear_view_splits_rear_yaw_into_two_stages(self):
        baseline=self.policy[
            'n08_overhead_free_sector_negative_y_rear_short_hold_low_rear_view_profile']
        candidate=self.policy[
            'n08_overhead_free_sector_negative_y_rear_short_hold_low_rear_view_separated_pitch_profile']
        self.assertEqual(candidate[:13],baseline[:13])
        self.assertEqual(candidate[13:],[
            {'duration_sim_s':8,'target':[0,0,-math.pi/2,-0.35]},
            {'duration_sim_s':18,'target':[0,0,-math.pi,-0.35]},
            {'duration_sim_s':4,'target':[0,0,-math.pi,-0.35]},
            {'duration_sim_s':12,'target':[0,0,-math.pi/2,-0.35]},
            {'duration_sim_s':12,'target':[0,0,0,-0.35]},
            {'duration_sim_s':8,'target':[0,0,0,0]},
        ])
        self.assertEqual(sum(x['duration_sim_s'] for x in candidate),
                         sum(x['duration_sim_s'] for x in baseline)+16)
        validate_profile(self.policy,MODEL,
                         'n08_overhead_free_sector_negative_y_rear_short_hold_low_rear_view_separated_pitch')

    def test_n08_low_rear_neutral_yaw_moves_pitch_only_at_stationary_rear_view(self):
        baseline=self.policy[
            'n08_overhead_free_sector_negative_y_rear_short_hold_low_rear_view_profile']
        candidate=self.policy[
            'n08_overhead_free_sector_negative_y_rear_short_hold_low_rear_view_neutral_yaw_pitch_only_rear_profile']
        self.assertEqual(candidate[:13],baseline[:13])
        self.assertEqual(candidate[13:],[
            {'duration_sim_s':12,'target':[0,0,-math.pi/2,0]},
            {'duration_sim_s':18,'target':[0,0,-math.pi,0]},
            {'duration_sim_s':8,'target':[0,0,-math.pi,-0.35]},
            {'duration_sim_s':4,'target':[0,0,-math.pi,-0.35]},
            {'duration_sim_s':8,'target':[0,0,-math.pi,0]},
            {'duration_sim_s':12,'target':[0,0,-math.pi/2,0]},
            {'duration_sim_s':12,'target':[0,0,0,0]},
        ])
        self.assertEqual(sum(x['duration_sim_s'] for x in candidate),490)
        validate_profile(self.policy,MODEL,
                         'n08_overhead_free_sector_negative_y_rear_short_hold_low_rear_view_neutral_yaw_pitch_only_rear')

    def test_n08_low_rear_midheight_changes_only_turn_altitude(self):
        baseline=self.policy[
            'n08_overhead_free_sector_negative_y_rear_short_hold_low_rear_view_neutral_yaw_pitch_only_rear_profile']
        candidate=self.policy[
            'n08_overhead_free_sector_negative_y_rear_short_hold_low_rear_view_midheight_yaw_pitch_only_rear_profile']
        self.assertEqual(candidate[:13],baseline[:13])
        self.assertEqual(candidate[13:],[
            {'duration_sim_s':12,'target':[0,0.5,0,0]},
            {'duration_sim_s':12,'target':[0,0.5,-math.pi/2,0]},
            {'duration_sim_s':18,'target':[0,0.5,-math.pi,0]},
            {'duration_sim_s':8,'target':[0,0.5,-math.pi,-0.35]},
            {'duration_sim_s':4,'target':[0,0.5,-math.pi,-0.35]},
            {'duration_sim_s':8,'target':[0,0.5,-math.pi,0]},
            {'duration_sim_s':12,'target':[0,0.5,-math.pi/2,0]},
            {'duration_sim_s':12,'target':[0,0.5,0,0]},
            {'duration_sim_s':12,'target':[0,0,0,0]},
            {'duration_sim_s':5,'target':[0,0,0,0]},
        ])
        self.assertEqual(sum(x['duration_sim_s'] for x in candidate),519)
        validate_profile(self.policy,MODEL,
                         'n08_overhead_free_sector_negative_y_rear_short_hold_low_rear_view_midheight_yaw_pitch_only_rear')

    def test_n08_rear_facing_profile_extends_negative_yaw_in_90_degree_steps(self):
        baseline=self.policy['n08_overhead_negative_side_view_profile']
        candidate=self.policy['n08_overhead_rear_facing_view_profile']
        self.assertEqual(candidate[:9],baseline[:9])
        self.assertEqual([stage['target'][2:] for stage in candidate[9:16]], [
            [-math.pi/2,0],[-math.pi/2,0],[-math.pi,0],[-math.pi,0],
            [-math.pi/2,0],[0,0],[0,0]])
        validate_profile(self.policy,MODEL,'n08_overhead_rear_facing_view')

    def test_n08_rear_down_profile_adds_only_a_downward_pitch_observation_at_rear_yaw(self):
        baseline=self.policy['n08_overhead_rear_facing_view_profile']
        candidate=self.policy['n08_overhead_rear_down_view_profile']
        self.assertEqual(candidate[:13],baseline[:13])
        self.assertEqual([stage['target'][2:] for stage in candidate[13:16]], [
            [-math.pi,0.45],[-math.pi,0.45],[-math.pi,0]])
        self.assertEqual(candidate[16:],baseline[13:])
        validate_profile(self.policy,MODEL,'n08_overhead_rear_down_view')

    def test_n08_slow_yaw_return_changes_only_the_failed_return_stage_duration(self):
        baseline=self.policy['n08_overhead_rear_down_view_profile']
        candidate=self.policy['n08_overhead_rear_down_slow_yaw_return_profile']
        self.assertEqual(len(candidate),22)
        for index,(source,target) in enumerate(zip(baseline,candidate)):
            expected=copy.deepcopy(source)
            if index==16:
                expected['duration_sim_s']=48
            self.assertEqual(target,expected)
        validate_profile(self.policy,MODEL,'n08_overhead_rear_down_slow_yaw_return')

    def test_n07_default_spawn_profile_keeps_the_known_translation_without_attitude_change(self):
        baseline=self.policy['n06_full_airframe_retreat_240_oblique_early_view_profile']
        candidate=self.policy['n07_default_spawn_translation_only_profile']
        self.assertEqual(len(candidate),len(baseline))
        self.assertEqual([stage['duration_sim_s'] for stage in candidate],
                         [stage['duration_sim_s'] for stage in baseline])
        for source,target in zip(baseline,candidate):
            self.assertEqual(target['target'][0],min(1.2,-source['target'][0]))
            self.assertEqual(target['target'][1],source['target'][1])
            self.assertEqual(target['target'][2:],[0,0])
            self.assertEqual(target.get('start_from_actual',False),
                             source.get('start_from_actual',False))
        self.assertEqual(max(stage['target'][0] for stage in candidate),1.2)
        validate_profile(self.policy,MODEL,'n07_default_spawn_translation_only')

    def test_n07_bidirectional_scan_observes_both_sides_without_attitude_change(self):
        candidate=self.policy['n07_default_spawn_bidirectional_translation_only_profile']
        self.assertEqual([stage['target'][0] for stage in candidate],
                         [0,0,-0.8,-0.8,1.2,1.2,0,0,0,0,0])
        self.assertEqual([stage['duration_sim_s'] for stage in candidate],
                         [3,12,50,20,100,60,60,15,8,7,5])
        self.assertTrue(all(stage['target'][2:] == [0,0] for stage in candidate))
        self.assertEqual([index for index,stage in enumerate(candidate)
                          if stage.get('start_from_actual')],[3,4,5,6,7])
        validate_profile(self.policy,MODEL,'n07_default_spawn_bidirectional_translation_only')

    def test_n07_shorter_retreat_keeps_zero_attitude_and_same_phase_times(self):
        profile=self.policy['n07_spawn_minus65_retreat_150_translation_only_profile']
        self.assertEqual([leg['duration_sim_s'] for leg in profile],
                         [3,12,100,100,15,5])
        self.assertEqual([leg['target'] for leg in profile], [
            [0,0,0,0], [0,1.0,0,0], [-1.5,1.0,0,0],
            [0,1.0,0,0], [0,0.5,0,0], [0,0,0,0]])
        self.assertTrue(all(leg['target'][2:] == [0,0] for leg in profile))
        self.assertEqual(max(abs(leg['target'][0]) for leg in profile),1.5)
        validate_profile(self.policy,MODEL,'n07_spawn_minus65_retreat_150_translation_only')

    def test_n07_18m_retreat_changes_only_the_observation_distance(self):
        baseline=self.policy['n07_spawn_minus65_retreat_150_translation_only_profile']
        candidate=self.policy['n07_spawn_minus65_retreat_180_translation_only_profile']
        self.assertEqual([leg['duration_sim_s'] for leg in candidate],
                         [leg['duration_sim_s'] for leg in baseline])
        expected=[leg['target'][:] for leg in baseline]
        expected[2][0]=-1.8
        self.assertEqual([leg['target'] for leg in candidate],expected)
        self.assertTrue(all(leg['target'][2:] == [0,0] for leg in candidate))
        validate_profile(self.policy,MODEL,'n07_spawn_minus65_retreat_180_translation_only')

    def test_n07_18m_yaw_view_adds_only_a_remote_yaw_observation(self):
        baseline=self.policy['n07_spawn_minus65_retreat_180_translation_only_profile']
        candidate=self.policy['n07_spawn_minus65_retreat_180_yaw015rad_view_profile']
        self.assertEqual([leg['duration_sim_s'] for leg in candidate],
                         [3,12,100,10,15,10,100,15,5])
        self.assertEqual([leg['target'] for leg in candidate], [
            [0,0,0,0], [0,1.0,0,0], [-1.8,1.0,0,0],
            [-1.8,1.0,0.15,0], [-1.8,1.0,0.15,0],
            [-1.8,1.0,0,0], [0,1.0,0,0], [0,0.5,0,0], [0,0,0,0]])
        self.assertEqual(candidate[2]['target'],baseline[2]['target'])
        self.assertEqual(candidate[6]['target'],baseline[3]['target'])
        self.assertTrue(all(leg['target'][3] == 0 for leg in candidate))
        self.assertEqual(max(abs(leg['target'][0]) for leg in candidate),1.8)
        self.assertAlmostEqual(max(abs(leg['target'][2]) for leg in candidate),0.15)
        validate_profile(self.policy,MODEL,'n07_spawn_minus65_retreat_180_yaw015rad_view')

    def test_n07_18m_yaw_return_view_changes_only_yaw_reset_timing(self):
        baseline=self.policy['n07_spawn_minus65_retreat_180_yaw015rad_view_profile']
        candidate=self.policy['n07_spawn_minus65_retreat_180_yaw015rad_return_view_profile']
        self.assertEqual(sum(leg['duration_sim_s'] for leg in candidate),
                         sum(leg['duration_sim_s'] for leg in baseline))
        expected=[leg['target'][:] for leg in baseline]
        expected[5]=[0,1.0,0.15,0]
        self.assertEqual([leg['target'] for leg in candidate],expected)
        self.assertEqual(candidate[5]['duration_sim_s'],baseline[6]['duration_sim_s'])
        self.assertEqual(candidate[6]['duration_sim_s'],baseline[5]['duration_sim_s'])
        self.assertEqual(candidate[5]['target'][2],0.15)
        self.assertEqual(candidate[6]['target'],[0,1.0,0,0])
        self.assertTrue(all(leg['target'][3] == 0 for leg in candidate))
        self.assertEqual(max(abs(leg['target'][0]) for leg in candidate),1.8)
        validate_profile(self.policy,MODEL,'n07_spawn_minus65_retreat_180_yaw015rad_return_view')

    def test_n07_18m_pitch_view_changes_only_remote_pitch_observation(self):
        baseline=self.policy['n07_spawn_minus65_retreat_180_translation_only_profile']
        candidate=self.policy['n07_spawn_minus65_retreat_180_pitch045_view_profile']
        self.assertEqual([leg['duration_sim_s'] for leg in candidate],
                         [3,12,100,10,15,10,100,15,5])
        self.assertEqual([leg['target'] for leg in candidate], [
            [0,0,0,0], [0,1.0,0,0], [-1.8,1.0,0,0],
            [-1.8,1.0,0,0.45], [-1.8,1.0,0,0.45],
            [-1.8,1.0,0,0], [0,1.0,0,0], [0,0.5,0,0], [0,0,0,0]])
        self.assertEqual(candidate[2]['target'],baseline[2]['target'])
        self.assertEqual(candidate[6]['target'],baseline[3]['target'])
        self.assertTrue(all(leg['target'][2] == 0 for leg in candidate))
        self.assertEqual(max(abs(leg['target'][0]) for leg in candidate),1.8)
        self.assertEqual(max(leg['target'][3] for leg in candidate),0.45)
        self.assertEqual(candidate[5]['target'][3],0)
        self.assertEqual(candidate[6]['target'][3],0)
        validate_profile(self.policy,MODEL,'n07_spawn_minus65_retreat_180_pitch045_view')

    def test_n07_pitch_return_view_changes_only_pitch_reset_timing(self):
        baseline=self.policy['n07_spawn_minus65_retreat_180_pitch045_view_profile']
        candidate=self.policy['n07_spawn_minus65_retreat_180_pitch045_return_view_profile']
        self.assertEqual(sum(leg['duration_sim_s'] for leg in candidate),
                         sum(leg['duration_sim_s'] for leg in baseline))
        expected=[leg['target'][:] for leg in baseline]
        expected[5]=[0,1.0,0,0.45]
        expected[6]=[0,1.0,0,0]
        self.assertEqual([leg['target'] for leg in candidate],expected)
        self.assertEqual(candidate[5]['duration_sim_s'],baseline[6]['duration_sim_s'])
        self.assertEqual(candidate[6]['duration_sim_s'],baseline[5]['duration_sim_s'])
        self.assertEqual(candidate[5]['target'][0],0)
        self.assertEqual(candidate[5]['target'][3],0.45)
        self.assertEqual(candidate[6]['target'][3],0)
        self.assertTrue(all(leg['target'][2] == 0 for leg in candidate))
        self.assertEqual(max(abs(leg['target'][0]) for leg in candidate),1.8)
        validate_profile(self.policy,MODEL,'n07_spawn_minus65_retreat_180_pitch045_return_view')

    def test_n06_extended_reach_changes_only_x_reach_within_fixture_limit(self):
        coverage=self.policy['coverage_profile']
        extended=self.policy['n06_extended_reach_profile']
        self.assertEqual(len(coverage),len(extended))
        for baseline,candidate in zip(coverage,extended):
            self.assertEqual(baseline['duration_sim_s'],candidate['duration_sim_s'])
            self.assertEqual(baseline['target'][1:],candidate['target'][1:])
            self.assertIn(baseline['target'][0],(0,1.2))
            expected_x=0 if baseline['target'][0] == 0 else 1.4
            self.assertEqual(candidate['target'][0],expected_x)
        maximum=max(stage['target'][0] for stage in extended)
        self.assertEqual(maximum,1.4)
        validate_profile(self.policy,MODEL,'n06_extended_reach')
        unsafe=copy.deepcopy(self.policy)
        unsafe['n06_extended_reach_profile'][2]['target'][0]=1.51
        with self.assertRaises(ValueError):
            validate_profile(unsafe,MODEL,'n06_extended_reach')

    def test_n06_slow_x_reach_preserves_path_and_doubles_x_phase_times(self):
        baseline=self.policy['n06_extended_reach_profile']
        slow=self.policy['n06_extended_reach_slow_x_profile']
        self.assertEqual(len(baseline),len(slow))
        for index,(fast,candidate) in enumerate(zip(baseline,slow)):
            expected_time=30 if index in (2,8) else fast['duration_sim_s']
            self.assertEqual(candidate['duration_sim_s'],expected_time)
            self.assertEqual(candidate['target'],fast['target'])
        validate_profile(self.policy,MODEL,'n06_extended_reach_slow_x')

    def test_n06_pitch60_changes_only_pitch_extent_within_fixture_limit(self):
        baseline=self.policy['n06_extended_reach_slow_x_profile']
        candidate=self.policy['n06_extended_reach_slow_x_pitch60_profile']
        self.assertEqual(len(baseline),len(candidate))
        for index,(fast,tilted) in enumerate(zip(baseline,candidate)):
            self.assertEqual(fast['duration_sim_s'],tilted['duration_sim_s'])
            self.assertEqual(fast['target'][:3],tilted['target'][:3])
            expected_pitch=0.6 if fast['target'][3] == 0.45 else (
                -0.6 if fast['target'][3] == -0.45 else fast['target'][3])
            self.assertEqual(tilted['target'][3],expected_pitch)
        validate_profile(self.policy,MODEL,'n06_extended_reach_slow_x_pitch60')

    def test_single_yaw_profile_keeps_equivalent_final_body_pose(self):
        baseline=self.policy['n06_extended_reach_slow_x_pitch60_profile']
        candidate=self.policy['n06_extended_reach_slow_x_pitch60_single_yaw_profile']
        self.assertEqual(len(baseline),len(candidate))
        for index,(source,target) in enumerate(zip(baseline,candidate)):
            self.assertEqual(source['duration_sim_s'],target['duration_sim_s'])
            self.assertEqual(source['target'][:2],target['target'][:2])
            self.assertEqual(source['target'][3],target['target'][3])
            expected_yaw=(2*math.pi if index >= 8 else source['target'][2])
            self.assertAlmostEqual(target['target'][2],expected_yaw)
        validate_profile(self.policy,MODEL,'n06_extended_reach_slow_x_pitch60_single_yaw')

    def test_pitch45_profile_moves_pitch_sweep_to_yaw_zero_orientation(self):
        baseline=self.policy['n06_extended_reach_slow_x_profile']
        candidate=self.policy['n06_extended_reach_slow_x_pitch45_yaw0_profile']
        self.assertEqual(len(baseline),len(candidate))
        self.assertEqual(sum(leg['duration_sim_s'] for leg in baseline),
                         sum(leg['duration_sim_s'] for leg in candidate))
        self.assertEqual([leg['target'][0:2] for leg in baseline],
                         [leg['target'][0:2] for leg in candidate])
        self.assertEqual([leg['duration_sim_s'] for leg in candidate[5:8]],
                         [leg['duration_sim_s'] for leg in baseline[4:7]])
        self.assertEqual([leg['target'][3] for leg in candidate[5:8]],
                         [leg['target'][3] for leg in baseline[4:7]])
        self.assertEqual([leg['target'][2] for leg in candidate],
                         [0,0,0,math.pi,2*math.pi,2*math.pi,2*math.pi,
                          2*math.pi,2*math.pi,0,0,0])
        validate_profile(self.policy,MODEL,'n06_extended_reach_slow_x_pitch45_yaw0')

    def test_full_airframe_retreat_matches_observed_sensor_reach_with_safe_return(self):
        baseline=self.policy['n06_extended_reach_slow_x_profile']
        candidate=self.policy['n06_full_airframe_retreat_240_profile']
        self.assertEqual(len(baseline),len(candidate))
        self.assertEqual(candidate[2]['target'][0],-2.4)
        self.assertEqual(candidate[8]['target'][0],0)
        self.assertGreaterEqual(candidate[2]['target'][0],-2.5)
        for index,(source,target) in enumerate(zip(baseline,candidate)):
            self.assertEqual(target['target'][1:],source['target'][1:])
            if index in (2,3,4,5,6,7):
                self.assertEqual(target['target'][0],-2.4)
            self.assertEqual(target['duration_sim_s'],
                             50 if index in (2,8) else source['duration_sim_s'])
        validate_profile(self.policy,MODEL,'n06_full_airframe_retreat_240')
        unsafe=copy.deepcopy(self.policy)
        unsafe['n06_full_airframe_retreat_240_profile'][2]['target'][0]=-2.51
        with self.assertRaises(ValueError):
            validate_profile(unsafe,MODEL,'n06_full_airframe_retreat_240')

    def test_full_airframe_translation_only_profile_keeps_yaw_pitch_fixed(self):
        profile=self.policy['n06_full_airframe_retreat_240_translation_only_profile']
        self.assertEqual([leg['duration_sim_s'] for leg in profile],[3,12,100,100,15,5])
        self.assertEqual([leg['target'] for leg in profile], [
            [0,0,0,0], [0,1.0,0,0], [-2.4,1.0,0,0],
            [0,1.0,0,0], [0,0,0,0], [0,0,0,0]])
        self.assertTrue(all(leg['target'][2:] == [0,0] for leg in profile))
        validate_profile(self.policy,MODEL,'n06_full_airframe_retreat_240_translation_only')

    def test_segmented_full_airframe_return_starts_each_leg_from_actual_joint_state(self):
        profile=self.policy['n06_full_airframe_retreat_240_segmented_actual_return_profile']
        self.assertEqual(len(profile),12)
        self.assertEqual([leg['target'][0] for leg in profile],
                         [0,0,-1.2,-2.4,-2.4,-1.2,0,0,0,0,0,0])
        self.assertEqual([index for index,leg in enumerate(profile)
                          if leg.get('start_from_actual')],[3,4,5,6])
        self.assertTrue(all(leg['target'][2:] == [0,0] for leg in profile))
        validate_profile(self.policy,MODEL,
                         'n06_full_airframe_retreat_240_segmented_actual_return')
        invalid=copy.deepcopy(self.policy)
        invalid['n06_full_airframe_retreat_240_segmented_actual_return_profile'][5][
            'start_from_actual']='true'
        with self.assertRaises(ValueError):
            validate_profile(invalid,MODEL,
                             'n06_full_airframe_retreat_240_segmented_actual_return')

    def test_oblique_site_view_adds_only_pitch_at_far_observation_point(self):
        baseline=self.policy['n06_full_airframe_retreat_240_segmented_actual_return_profile']
        candidate=self.policy['n06_full_airframe_retreat_240_oblique_site_view_profile']
        self.assertEqual(len(candidate),12)
        self.assertEqual([leg['duration_sim_s'] for leg in candidate],
                         [leg['duration_sim_s'] for leg in baseline])
        for index,(source,target) in enumerate(zip(baseline,candidate)):
            self.assertEqual(target['target'][:3],source['target'][:3])
            self.assertAlmostEqual(target['target'][3],
                                   0.45 if index==4 else source['target'][3])
        self.assertEqual([index for index,leg in enumerate(candidate)
                          if leg.get('start_from_actual')],[3,4,5,6])
        validate_profile(self.policy,MODEL,'n06_full_airframe_retreat_240_oblique_site_view')

    def test_oblique_separated_return_resets_pitch_before_x_return(self):
        baseline=self.policy['n06_full_airframe_retreat_240_segmented_actual_return_profile']
        candidate=self.policy['n06_full_airframe_retreat_240_oblique_separated_return_profile']
        self.assertEqual(len(candidate),12)
        self.assertEqual(sum(leg['duration_sim_s'] for leg in candidate),
                         sum(leg['duration_sim_s'] for leg in baseline))
        self.assertEqual([leg['duration_sim_s'] for leg in candidate],
                         [3,12,60,100,15,15,60,60,15,8,7,5])
        self.assertEqual([leg['target'] for leg in candidate], [
            [0,0,0,0], [0,1.0,0,0], [-1.2,1.0,0,0], [-2.4,1.0,0,0],
            [-2.4,1.0,0,0.45], [-2.4,1.0,0,0], [-1.2,1.0,0,0],
            [0,1.0,0,0], [0,1.0,0,0], [0,0.5,0,0], [0,0,0,0], [0,0,0,0]])
        self.assertEqual([index for index,leg in enumerate(candidate)
                          if leg.get('start_from_actual')],[3,4,5,6,7])
        validate_profile(self.policy,MODEL,
                         'n06_full_airframe_retreat_240_oblique_separated_return')

    def test_oblique_early_view_aims_at_takeoff_floor_before_far_translation(self):
        baseline=self.policy['n06_full_airframe_retreat_240_segmented_actual_return_profile']
        candidate=self.policy['n06_full_airframe_retreat_240_oblique_early_view_profile']
        self.assertEqual(len(candidate),12)
        self.assertEqual(sum(leg['duration_sim_s'] for leg in candidate),
                         sum(leg['duration_sim_s'] for leg in baseline))
        self.assertEqual([leg['duration_sim_s'] for leg in candidate],
                         [3,12,60,15,100,15,15,60,60,8,7,5])
        self.assertEqual([leg['target'] for leg in candidate], [
            [0,0,0,0], [0,1.0,0,0], [-1.2,1.0,0,0],
            [-1.2,1.0,0,0.45], [-2.4,1.0,0,0.45],
            [-2.4,1.0,0,0.45], [-2.4,1.0,0,0],
            [-1.2,1.0,0,0], [0,1.0,0,0],
            [0,0.5,0,0], [0,0,0,0], [0,0,0,0]])
        self.assertEqual([index for index,leg in enumerate(candidate)
                          if leg.get('start_from_actual')],[3,4,5,6,7,8])
        validate_profile(self.policy,MODEL,'n06_full_airframe_retreat_240_oblique_early_view')

    def test_fixture_return_accepts_yaw_equivalent_but_checks_other_axes(self):
        self.assertTrue(fixture_pose_returned({
            'x': (0.001, 0.001), 'z': (0.002, 0.002),
            'yaw': (2*math.pi+0.003, 0.003), 'pitch': (-0.001, 0.002)}))
        self.assertFalse(fixture_pose_returned({
            'x': (0, 0), 'z': (0, 0), 'yaw': (math.pi, 0), 'pitch': (0, 0)}))
        self.assertFalse(fixture_pose_returned({
            'x': (0.02, 0), 'z': (0, 0), 'yaw': (2*math.pi, 0), 'pitch': (0, 0)}))
        self.assertFalse(fixture_pose_returned({
            'x': (0, 0), 'z': (0, 0), 'yaw': (2*math.pi, 0.04), 'pitch': (0, 0)}))

    def test_drift_rejects_missing_return_or_moving_reference(self):
        p=copy.deepcopy(self.policy)
        p['drift_profile']=[leg for leg in p['drift_profile'] if leg.get('cycle')!=3]
        with self.assertRaises(ValueError):validate_profile(p,MODEL,'drift')
        p=copy.deepcopy(self.policy)
        reference=next(leg for leg in p['drift_profile'] if leg.get('label')=='reference')
        reference['target']=[.1,.6,0,0]
        with self.assertRaises(ValueError):validate_profile(p,MODEL,'drift')

    def test_invalid_durations(self):
        for value in (0,-1,float('inf'),float('nan'),True,'1'):
            p=copy.deepcopy(self.policy);p['smoke_profile'][0]['duration_sim_s']=value
            with self.assertRaises(ValueError):validate_profile(p,MODEL)

    def test_target_bounds_and_shape(self):
        for target in ([0.,-1.,0.,0.],[0.,0.,8.,0.],[0.,0.,0.,1.],
                       [float('nan'),0.,0.,0.],[True,0.,0.,0.],[],None):
            p=copy.deepcopy(self.policy);p['smoke_profile'][0]['target']=target
            with self.assertRaises(ValueError):validate_profile(p,MODEL)

    @patch('probe_preflight_scan._gz_model_names', return_value={'x500_d435i_0'})
    def test_detached_fixture_absence_resolves_without_remove_ack(self, _):
        result=_confirm_fixture_removed('preflight_scan_fixture',False)
        self.assertTrue(result['scene_model_absent'])
        self.assertFalse(result['remove_service_acknowledged'])

    @patch('probe_preflight_scan._gz_model_names', return_value={'preflight_scan_fixture'})
    def test_fixture_still_in_scene_is_not_confirmed_removed(self, _):
        result=_confirm_fixture_removed('preflight_scan_fixture',False,timeout_s=0)
        self.assertFalse(result['scene_model_absent'])


if __name__=='__main__':unittest.main()
