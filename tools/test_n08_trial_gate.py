import json
import math
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from n08_trial_gate import (certify_trial_capsule,
                            certify_forward_trial_corridor,trial_limits,
                            raw_vehicle_reachable_query,
                            certify_trial_reference_tube,
                            certify_trial_turn_approach,
                            trial_takeoff_velocity_settled,
                            candidate_landing_pose_from_ground_planes,
                            trial_fixed_heading_deviation_rad,
                            trial_fixed_heading_within_bound,
                            TRIAL_FORWARD_INITIAL_REVERSE_BOUND_M,
                            remaining_forward_corridor_distance)
from evaluate_n08_curve_certificate import raw_sphere_query

class TrialGateTests(unittest.TestCase):
    def test_candidate_landing_pose_projects_only_raw_plane_and_imu_standoff(self):
        home={'center_xyz_m':[0.0,0.0,0.35]}
        home_plane={'valid':True,'coefficients_ax_by_c_m':[0.0,0.0,-0.35],
                    'residual_p95_m':0.01}
        candidate_plane={'valid':True,'coefficients_ax_by_c_m':[0.02,0.0,-0.34],
                          'residual_p95_m':0.02}
        result=candidate_landing_pose_from_ground_planes(
            home,home_plane,candidate_plane,[0.6,0.1],0.2)
        self.assertAlmostEqual(result['imu_standoff_above_raw_ground_m'],0.7)
        self.assertAlmostEqual(result['candidate_ground_plane_z_m'],-0.328)
        self.assertAlmostEqual(result['center_xyz_m'][2],0.372)
        self.assertFalse(result['actual_ground_confirmed'])

    def test_candidate_landing_pose_refuses_invalid_plane_or_nonpositive_standoff(self):
        home={'center_xyz_m':[0.0,0.0,0.0]}
        plane={'valid':True,'coefficients_ax_by_c_m':[0.0,0.0,0.0],
               'residual_p95_m':0.0}
        with self.assertRaisesRegex(ValueError,'standoff_invalid'):
            candidate_landing_pose_from_ground_planes(home,plane,plane,[.2,0.],0.)
        with self.assertRaisesRegex(ValueError,'candidate_ground_plane_not_valid'):
            candidate_landing_pose_from_ground_planes(
                {**home,'center_xyz_m':[0,0,.3]},plane,{**plane,'valid':False},[.2,0.],0.)

    def test_takeoff_settle_keeps_total_speed_gate_and_limits_vertical_drift(self):
        self.assertFalse(trial_takeoff_velocity_settled(
            {'vx':0.0,'vy':0.0,'vz':0.023}))
        self.assertTrue(trial_takeoff_velocity_settled(
            {'vx':0.004,'vy':0.003,'vz':0.009}))

    def test_takeoff_settle_rejects_total_speed_over_existing_limit(self):
        self.assertFalse(trial_takeoff_velocity_settled(
            {'vx':0.029,'vy':0.0,'vz':0.009}))

    def test_takeoff_settle_rejects_nonfinite_velocity(self):
        self.assertFalse(trial_takeoff_velocity_settled(
            {'vx':0.0,'vy':0.0,'vz':float('nan')}))

    def test_fixed_heading_trial_wraps_yaw_and_enforces_geometry_bound(self):
        self.assertLess(trial_fixed_heading_deviation_rad(-math.pi+.001,
                                                          math.pi-.001),.003)
        self.assertTrue(trial_fixed_heading_within_bound(0.0,.018))
        self.assertFalse(trial_fixed_heading_within_bound(0.0,.020))
        self.assertFalse(trial_fixed_heading_within_bound(0.0,float('nan')))

    def recorded_n08_curve(self):
        knots=np.asarray([
            -5.333333333333333,-3.5555555555555554,-1.7777777777777777,
            0.0,1.7777777777777777,3.5555555555555554,5.333333333333333,
            7.111111111111111,8.88888888888889,10.666666666666668,
            12.444444444444446,14.222222222222225,16.000000000000004,
            17.777777777777782,19.55555555555556],dtype=float)
        control=np.asarray([
            [0.03448752364600186,0.009563252142242653,0.962366794976033],
            [0.02812954316234457,0.009307116332985622,0.925599942018188],
            [0.025374021495334985,0.009062492283932272,0.8902727999457188],
            [0.07462041576672358,0.009005526661198507,0.8785614578213133],
            [0.18151114930294107,0.009109362376008744,0.886313845742855],
            [0.32423138175429256,0.009286038185039628,0.90197267037312],
            [0.46737185430208256,0.009453726928064832,0.9165080511201578],
            [0.5753778944398912,0.00956931112079607,0.9257387098240173],
            [0.6262142400789069,0.009617637180525093,0.9292792406835814],
            [0.6262142400789069,0.009617637180525093,0.9292792406835814],
            [0.6262142400789069,0.009617637180525093,0.9292792406835814]],dtype=float)
        start=np.asarray([0.02621424007890691,0.009617637180525093,
                          0.9292792406835814])
        return knots,control,start

    def recorded_n08_initial_backward_spline(self):
        knots=np.asarray([
            -5.333333333333333,-3.5555555555555554,-1.7777777777777777,
            0.0,1.7777777777777777,3.5555555555555554,5.333333333333333,
            7.111111111111111,8.88888888888889,10.666666666666668,
            12.444444444444446,14.222222222222225,16.000000000000004,
            17.777777777777782,19.55555555555556],dtype=float)
        control=np.asarray([
            [-0.0515220251828862,0.011893365005242965,0.9018726922697018],
            [-0.0599417291005827,0.014627783641994355,0.8934295032166688],
            [-0.06473895364622313,0.01725498840668754,0.8853283197131101],
            [-0.016336056086925087,0.018162746511701463,0.8826987366513147],
            [0.09107045614806762,0.017629985559473,0.8847033894129543],
            [0.23524164366405764,0.016467721337241812,0.888771269836993],
            [0.3802040892733155,0.015338115721459617,0.8927414692599991],
            [0.48975172404104306,0.014577919764859263,0.8954536108475442],
            [0.5413395401583492,0.014250122745239001,0.8966373468551535],
            [0.5413395401583492,0.014250122745239001,0.8966373468551535],
            [0.5413395401583492,0.014250122745239001,0.8966373468551535]],dtype=float)
        start=np.asarray([-0.05866045984165084,0.014250122745239001,
                          0.8966373468551535])
        return knots,control,start

    def test_actual_curve_certificate_accepts_recorded_curve_inside_5cm_tube(self):
        knots,control,start=self.recorded_n08_curve()
        control_hull_radius=np.linalg.norm(control[:,1:]-start[1:],axis=1).max()
        self.assertGreater(control_hull_radius,.05)
        result=certify_trial_reference_tube(knots,control,3,start,.6)
        self.assertTrue(result['passed'],result)
        self.assertLessEqual(result['curve_lateral_vertical_deviation_max_m']
                             +result['between_sample_displacement_bound_m'],.05)
        self.assertGreaterEqual(result['curve_x_delta_min_m']
                                -result['between_sample_displacement_bound_m'],-.05-1e-9)
        self.assertLessEqual(result['curve_x_delta_max_m']
                             +result['between_sample_displacement_bound_m'],.65+1e-9)

    def test_forward_single_goal_uses_bounded_initial_reverse_allowance(self):
        knots,control,start=self.recorded_n08_curve()
        result=certify_trial_reference_tube(
            knots,control,3,start,.6,
            minimum_forward_delta_m=-TRIAL_FORWARD_INITIAL_REVERSE_BOUND_M)
        self.assertTrue(result['passed'],result)
        self.assertEqual(result['forward_x_bounds_relative_to_start_m'][0],-.005)
        control[:,0]-=.05
        rejected=certify_trial_reference_tube(
            knots,control,3,start,.6,
            minimum_forward_delta_m=-TRIAL_FORWARD_INITIAL_REVERSE_BOUND_M)
        self.assertFalse(rejected['passed'])
        self.assertEqual(rejected['reason'],
                         'sampled_curve_outside_continuous_tube_bound')

    def test_measured_initial_spline_passes_only_with_bounded_reverse_geometry(self):
        knots,control,start=self.recorded_n08_initial_backward_spline()
        result=certify_trial_reference_tube(
            knots,control,3,start,.6,
            minimum_forward_delta_m=-TRIAL_FORWARD_INITIAL_REVERSE_BOUND_M)
        self.assertTrue(result['passed'],result)
        self.assertAlmostEqual(result['curve_x_delta_min_m'],-.0025316,places=5)
        self.assertGreaterEqual(
            result['minimum_sample_clearance_m'],
            result['continuous_required_sample_clearance_m'])
        control[:,0]-=.003
        rejected=certify_trial_reference_tube(
            knots,control,3,start,.6,
            minimum_forward_delta_m=-TRIAL_FORWARD_INITIAL_REVERSE_BOUND_M)
        self.assertFalse(rejected['passed'])
        self.assertEqual(rejected['limiting_boundary'],'rear_x')

    def test_actual_curve_outside_5cm_tube_is_rejected(self):
        knots,control,start=self.recorded_n08_curve()
        control[:,1]+=0.06
        result=certify_trial_reference_tube(knots,control,3,start,.6)
        self.assertFalse(result['passed'])
        self.assertEqual(result['reason'],'sampled_curve_outside_continuous_tube_bound')

    def test_coarse_sampling_fails_closed_when_continuous_margin_is_unproven(self):
        knots,control,start=self.recorded_n08_curve()
        result=certify_trial_reference_tube(
            knots,control,3,start,.6,max_sample_spacing_m=.1)
        self.assertFalse(result['passed'])
        self.assertGreater(result['continuous_required_sample_clearance_m'],
                           result['minimum_sample_clearance_m'])

    def test_terminal_hold_clearance_is_required_beyond_goal(self):
        raw={'origin_m':[-3,-3,-3],'resolution_m':0.1,
             'occupancy':np.zeros((70,60,60),dtype=np.int8)}
        self.assertTrue(certify_trial_capsule(raw,[0,0,0],[.6,0,0],.73,.25,0)['passed'])
        # A voxel beyond the reference endpoint still intersects its hold sphere.
        raw['occupancy'][45,30,30]=-1
        self.assertFalse(certify_trial_capsule(raw,[0,0,0],[.6,0,0],.73,.25,0)['passed'])

    def test_directional_forward_corridor_keeps_full_margin_and_ignores_only_rear_blind_zone(self):
        raw={'origin_m':[-3,-3,-1],'resolution_m':0.1,
             'occupancy':np.zeros((60,60,40),dtype=np.int8)}
        start=np.asarray([.05,0.0,.9])
        # This rear cell intersects the symmetric body+0.25m capsule, but is
        # outside the translated forward-only swept envelope.
        raw['occupancy'][20,30,19]=-1
        symmetric=certify_trial_capsule(raw,start,[.6,0,0],
                                        .730617917,.25,0)
        self.assertFalse(symmetric['passed'])
        directional=certify_forward_trial_corridor(
            raw,start,[.6,0,0],.730617917,.25,.15)
        self.assertTrue(directional['passed'],directional)
        self.assertEqual(directional['tracking_margin_m'],.25)
        self.assertEqual(directional['start_hold']['reason'],'free')
        self.assertEqual(directional['terminal_hold']['reason'],'free')
        self.assertEqual(directional['required_queries'],25)
        self.assertEqual(directional['vehicle_geometry'],
                         'locked_x500_d435i_sdf_collision_primitives')
        self.assertAlmostEqual(directional['spatial_uncertainty_margin_m'],
                               .2486820464,places=8)
        self.assertGreater(directional['remaining_geometric_slack_m'],.01)
        self.assertTrue(all(q['unknown_count']==0 and q['occupied_count']==0
                            for q in directional['queries']))

    def test_directional_corridor_accounts_for_initial_reverse_within_same_margin(self):
        raw={'origin_m':[-3,-3,-1],'resolution_m':0.1,
             'occupancy':np.zeros((60,60,40),dtype=np.int8)}
        result=certify_forward_trial_corridor(
            raw,[.05,0.0,.9],[.6,0,0],.730617917,.25,.15)
        expected=np.hypot(.075+.0125,.05)+.15
        self.assertTrue(result['passed'],result)
        self.assertEqual(result['initial_reverse_allowance_m'],.005)
        self.assertAlmostEqual(result['reachable_center_bound_m'],expected)
        self.assertEqual(result['yaw_deviation_bound_rad'],.019)
        self.assertGreater(result['remaining_geometric_slack_m'],.01)
        self.assertLessEqual(result['reachable_center_bound_m'],
                             result['tracking_margin_m']+result['query_spacing_m']/2)

    def test_directional_forward_corridor_still_rejects_unknown_in_reachable_volume(self):
        raw={'origin_m':[-3,-3,-1],'resolution_m':0.1,
             'occupancy':np.zeros((60,60,40),dtype=np.int8)}
        start=np.asarray([.05,0.0,.9])
        # This voxel lies inside the physical base/rotor envelope at the start.
        raw['occupancy'][30,30,19]=-1
        result=certify_forward_trial_corridor(
            raw,start,[.6,0,0],.730617917,.25,.15)
        self.assertFalse(result['passed'])
        self.assertEqual(result['start_hold']['reason'],'unknown')

    def test_directional_forward_corridor_rejects_forward_unknown(self):
        raw={'origin_m':[-3,-3,-1],'resolution_m':0.1,
             'occupancy':np.zeros((60,60,40),dtype=np.int8)}
        start=np.asarray([.05,0.0,.9])
        raw['occupancy'][38,30,19]=-1
        result=certify_forward_trial_corridor(
            raw,start,[.6,0,0],.730617917,.25,.15)
        self.assertFalse(result['passed'])
        self.assertTrue(any(query['reason']=='unknown'
                            for query in result['queries']))

    def test_directional_corridor_rejects_occupied_cell_in_reachable_volume(self):
        raw={'origin_m':[-3,-3,-1],'resolution_m':0.1,
             'occupancy':np.zeros((60,60,40),dtype=np.int8)}
        raw['occupancy'][38,30,19]=100
        result=certify_forward_trial_corridor(
            raw,[.05,0.0,.9],[.6,0,0],.730617917,.25,.15)
        self.assertFalse(result['passed'])
        self.assertTrue(any(query['reason']=='occupied'
                            for query in result['queries']))

    def test_vehicle_shape_query_checks_full_terminal_hold_margin(self):
        raw={'origin_m':[-3,-3,-1],'resolution_m':0.1,
             'occupancy':np.zeros((60,60,40),dtype=np.int8)}
        raw['occupancy'][36,30,19]=-1
        result=raw_vehicle_reachable_query(
            raw,[.65,0.0,.9],0.0,(0.0,0.0),0.0,.25)
        self.assertEqual(result['reason'],'unknown')
        self.assertGreater(result['unknown_count'],0)

    def test_directional_corridor_rejects_locked_vehicle_envelope_mismatch(self):
        raw={'origin_m':[-3,-3,-1],'resolution_m':0.1,
             'occupancy':np.zeros((60,60,40),dtype=np.int8)}
        with self.assertRaisesRegex(ValueError,'vehicle_envelope_mismatch'):
            certify_forward_trial_corridor(
                raw,[.05,0.0,.9],[.6,0,0],.70,.25,.15)

    def test_directional_corridor_rejects_yaw_bound_outside_fixed_heading_scope(self):
        raw={'origin_m':[-3,-3,-1],'resolution_m':0.1,
             'occupancy':np.zeros((60,60,40),dtype=np.int8)}
        with self.assertRaisesRegex(ValueError,'invalid_forward_trial_corridor'):
            certify_forward_trial_corridor(
                raw,[.05,0.0,.9],[.6,0,0],.730617917,.25,.15,
                yaw_deviation_bound_rad=.02)

    def test_directional_corridor_rejects_outside_map_reachable_envelope(self):
        raw={'origin_m':[-1,-1,0],'resolution_m':0.1,
             'occupancy':np.zeros((20,20,20),dtype=np.int8)}
        result=certify_forward_trial_corridor(
            raw,[-.5,0.0,.9],[.6,0,0],.730617917,.25,.15)
        self.assertFalse(result['passed'])
        self.assertEqual(result['start_hold']['reason'],'outside_map')
    def test_outside_map_is_not_a_clear_trial(self):
        raw={'origin_m':[-1,-1,-1],'resolution_m':0.1,
             'occupancy':np.zeros((20,20,20),dtype=np.int8)}
        self.assertFalse(certify_trial_capsule(raw,[0,0,0],[.6,0,0],.73,.25,0)['passed'])
    def test_protocol_rejects_unbounded_or_sideways_motion(self):
        root=Path(__file__).resolve().parents[1]
        planner=json.loads((root/'config/components/mapping/n08_low_speed_trial.json').read_text())
        profile={'target_offset_enu_m':[.6,0,0],'n08_braking_trial':{
            'braking_kind':'planned_terminal_stop',
            'tracking_margin_m':.25,'forward_stopping_extension_m':0,
            'cancel_stop_distance_envelope_m':.5,
            'actual_vector_speed_limit_m_s':.12,'maximum_tracking_error_m':.15,
            'post_goal_hold_sim_s':3,'turn_approach_distance_m':.22}}
        limits=trial_limits(profile,planner)
        self.assertLess(limits['conservative_vector_velocity_limit_m_s'],.183)
        self.assertEqual(limits['turn_approach_distance_m'],.22)
        profile['target_offset_enu_m']=[.6,.1,0]
        with self.assertRaises(ValueError):trial_limits(profile,planner)

    def test_cancel_stop_envelope_must_be_bounded_by_forward_trial_limit(self):
        root=Path(__file__).resolve().parents[1]
        planner=json.loads((root/'config/components/mapping/n08_low_speed_trial.json').read_text())
        profile=json.loads((root/'config/components/navigation/n08_forward_braking_trial_goal.json').read_text())
        self.assertEqual(trial_limits(profile,planner)['cancel_stop_distance_envelope_m'],.5)
        profile['n08_braking_trial']['cancel_stop_distance_envelope_m']=.61
        with self.assertRaisesRegex(ValueError,'trial_outside_calibrated_protocol'):
            trial_limits(profile,planner)

    def test_cancel_reserve_uses_remaining_distance_along_forward_axis(self):
        start=np.asarray([0.,0.,1.])
        self.assertAlmostEqual(
            remaining_forward_corridor_distance(start,[.1,.02,1.01],[.6,0.,0.]),.5)
        with self.assertRaisesRegex(ValueError,'invalid_forward_corridor_pose'):
            remaining_forward_corridor_distance(start,[0.,0.,1.],[.6,.01,0.])

    def test_turn_approach_clears_rear_unknown_only_after_raw_capsule_admission(self):
        raw={'origin_m':[-3,-3,-1],'resolution_m':0.1,
             'occupancy':np.zeros((60,60,40),dtype=np.int8)}
        # A rear-side unknown voxel band, matching the location that refused #267.
        raw['occupancy'][25,27:33,16:22]=-1
        start=np.asarray([.603947056,.0,.937042004])
        turn_radius=.730617917+.25+.05
        initial=raw_sphere_query(raw,start,turn_radius)
        self.assertEqual(initial['reason'],'unknown')
        result=certify_trial_turn_approach(
            raw,start,0.0,.22,.730617917,.25,turn_radius)
        self.assertTrue(result['passed'],result)
        self.assertEqual(result['forward_capsule']['required_queries'],9)
        self.assertEqual(result['candidate_turn_hold']['reason'],'free')

    def test_turn_approach_rejects_unknown_in_hop_or_candidate_hold(self):
        raw={'origin_m':[-3,-3,-1],'resolution_m':0.1,
             'occupancy':np.zeros((60,60,40),dtype=np.int8)}
        raw['occupancy'][25,27:33,16:22]=-1
        start=np.asarray([.603947056,0.0,.937042004])
        turn_radius=.730617917+.25+.05
        # An unknown ahead intersects the certified approach capsule.
        raw['occupancy'][37,30,19]=-1
        result=certify_trial_turn_approach(
            raw,start,0.0,.22,.730617917,.25,turn_radius)
        self.assertFalse(result['passed'])
        self.assertNotEqual(result['forward_capsule']['queries'][-1]['reason'],'free')

    def test_turn_approach_rejects_displacements_below_ego_path_minimum(self):
        raw={'origin_m':[-3,-3,-1],'resolution_m':0.1,
             'occupancy':np.zeros((60,60,40),dtype=np.int8)}
        with self.assertRaises(ValueError):
            certify_trial_turn_approach(
                raw,[.6,0,.9],0.0,.12,.73,.25,1.03)
if __name__=='__main__':unittest.main()
