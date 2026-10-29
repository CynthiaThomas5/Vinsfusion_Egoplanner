import unittest
import numpy as np
from tools.debug_truth.evaluate_n08_braking import (audit_forward_return,
                                                    _reference_samples,
                                                    measure,
                                                    measure_cancel_stop)

class BrakingEvaluationTests(unittest.TestCase):
    def return_fixture(self, yaw_return):
        truth=[]
        for stamp in range(500_000_000,3_500_000_001,20_000_000):
            t=(stamp-500_000_000)/1e9
            if t<=1.0:
                yaw=np.pi*t
                x=0.0
            else:
                yaw=yaw_return
                x=-.2*(t-1.0)
            truth.append({'stamp_ns':stamp,'xyz':[x,0.,1.],
                          'q_xyzw':[0.,0.,float(np.sin(yaw/2)),float(np.cos(yaw/2))]})
        flight={'post_goal_hold_end_sim_ns':500_000_000,
                'yaw_turn_goal':{'goal_id':'turn','start_sim_ns':500_000_000,
                                 'target_yaw_enu':float(np.pi)},
                'yaw_turn_result':{'success':True},
                'yaw_turn_observed':{'end_sim_ns':1_500_000_000,
                                     'absolute_yaw_error_rad':0.0},
                'yaw_reorientation_precheck':{'center_xyz_m':[0.,0.,1.]},
                'return_goal_start_sim_ns':1_500_000_000,
                'return_completed_sim_ns':3_500_000_000}
        return flight,truth

    def fixture(self, never_stop=False):
        t=np.arange(0,10.02,.02)
        speed=lambda x: np.where(x<0,0,np.where(x<1,.1*x,np.where(x<4,.1,np.where(x<5,.1*(5-x),0))))
        rv=speed(t);ra=np.gradient(rv,.02);rp=np.cumsum(rv)*.02
        av=np.full(len(t),.08) if never_stop else speed(t-.3)
        ap=np.cumsum(av)*.02
        refs=[{'source_stamp_ns':int(round((x+1)*1e9)),
               'position_enu':[float(p),0.,0.], 'velocity_enu_m_s':[float(v),0.,0.],
               'acceleration_enu_m_s2':[float(a),0.,0.]}
              for x,p,v,a in zip(t,rp,rv,ra)]
        truth=[{'stamp_ns':int(round((x+1)*1e9)),'xyz':[float(p),0.,0.]}
               for x,p in zip(t,ap)]
        return refs,truth
    def test_known_delayed_stop_measures_independent_distance_and_delay(self):
        ref,truth=self.fixture();report,_=measure(ref,truth,1000000000,10000000000,
             {'rotation':np.eye(3).tolist(),'translation_m':[0,0,0]})
        self.assertTrue(report['passed'])
        m=report['metrics']
        self.assertGreater(m['response_delay_to_sustained_deceleration_s'],.15)
        self.assertLess(m['response_delay_to_sustained_deceleration_s'],.4)
        self.assertGreater(m['actual_distance_from_reference_braking_start_m'],.055)
        self.assertLess(m['actual_distance_from_reference_braking_start_m'],.09)
        self.assertAlmostEqual(m['actual_net_horizontal_displacement_m'],.4,places=2)
    def test_actual_vector_speed_is_checked_against_declared_trial_limit(self):
        ref,truth=self.fixture()
        report,_=measure(ref,truth,1000000000,10000000000,actual_vector_speed_limit=.07)
        self.assertFalse(report['checks']['actual_vector_speed_within_trial_limit'])
        self.assertAlmostEqual(report['metrics']['actual_vector_speed_limit_m_s'],.07)
    def test_cancel_stop_uses_event_time_and_requires_replacement_spline_hold(self):
        times=np.arange(0,2.02,.02)
        speed=np.where(times<.8,.05,np.where(times<1.3,.05*(1.3-times)/.5,0.))
        acceleration=np.gradient(speed,.02)
        x=np.cumsum(speed)*.02
        curve=[{'elapsed_sim_s':float(t),'actual_horizontal_speed_m_s':float(v),
                'actual_signed_speed_derivative_m_s2':float(a),
                'actual_world_xyz_m':[float(p),0.,0.]}
               for t,v,a,p in zip(times,speed,acceleration,x)]
        flight={'goal_start_sim_ns':1_000_000_000,
                'metrics':{'actual_stop_elapsed_sim_s':1.32,'actual_stop_observed':True},
                'cancel_stop':{'request_sim_ns':1_800_000_000,
                    'remaining_forward_corridor_m':.45,
                    'px4_horizontal_speed_m_s':.05,'ego_reference_vector_speed_m_s':.05,
                    'ego_longitudinal_acceleration_m_s2':0.,'cancel_acknowledged':True,
                    'action_result':{'status':5,'success':False,'outcome':'canceled',
                                     'reason':'caller_cancel'},
                    'old_trajectory_id':8,'stop_trajectory_id':9,
                    'stop_spline_certified':True,'old_trajectory_resumed':False,
                    'bridge_active_after_stop_hold':True}}
        result=measure_cancel_stop(curve,flight,[.04,.06],flight['metrics'],.5)
        self.assertTrue(all(result['checks'].values()),result['checks'])
        self.assertGreater(result['metrics']['cancel_to_stop_elapsed_sim_s'],.4)
        self.assertLess(result['metrics']['remaining_forward_corridor_m_at_cancel'],.5)

    def test_cancel_outcome_and_reason_are_checked_in_their_correct_fields(self):
        ref,truth=self.fixture()
        times=np.arange(0,2.02,.02)
        speed=np.where(times<.8,.05,np.where(times<1.3,.05*(1.3-times)/.5,0.))
        acceleration=np.gradient(speed,.02);x=np.cumsum(speed)*.02
        curve=[{'elapsed_sim_s':float(t),'actual_horizontal_speed_m_s':float(v),
                'actual_signed_speed_derivative_m_s2':float(a),
                'actual_world_xyz_m':[float(p),0.,0.]}
               for t,v,a,p in zip(times,speed,acceleration,x)]
        flight={'goal_start_sim_ns':1_000_000_000,
                'metrics':{'actual_stop_elapsed_sim_s':1.32,'actual_stop_observed':True},
                'cancel_stop':{'request_sim_ns':1_800_000_000,
                    'remaining_forward_corridor_m':.55,
                    'px4_horizontal_speed_m_s':.05,'ego_reference_vector_speed_m_s':.05,
                    'ego_longitudinal_acceleration_m_s2':0.,'cancel_acknowledged':True,
                    'action_result':{'status':5,'success':False,'outcome':'canceled',
                                     'reason':'caller_cancel'},
                    'old_trajectory_id':8,'stop_trajectory_id':9,
                    'stop_spline_certified':True,'old_trajectory_resumed':False,
                    'bridge_active_after_stop_hold':True}}
        result=measure_cancel_stop(curve,flight,[.04,.06],flight['metrics'],.5)
        self.assertTrue(result['checks']['navigation_action_canceled'])
        flight['cancel_stop']['action_result']={
            'status':5,'success':False,'outcome':'caller_cancel','reason':'canceled'}
        result=measure_cancel_stop(curve,flight,[.04,.06],flight['metrics'],.5)
        self.assertFalse(result['checks']['navigation_action_canceled'])
    def test_continuing_motion_does_not_count_as_a_stop(self):
        ref,truth=self.fixture(never_stop=True);report,_=measure(ref,truth,1000000000,10000000000)
        self.assertFalse(report['passed']);self.assertFalse(report['metrics']['actual_stop_observed'])
    def test_truth_gap_is_not_interpolated_away(self):
        ref,truth=self.fixture();del truth[200:230]
        with self.assertRaisesRegex(ValueError,'gap exceeds'):
            measure(ref,truth,1000000000,10000000000)
    def test_source_regression_is_not_sorted_or_repaired(self):
        ref,truth=self.fixture();truth[150]['stamp_ns']=truth[149]['stamp_ns']-1
        with self.assertRaisesRegex(ValueError,'strictly increasing'):
            measure(ref,truth,1000000000,10000000000)
    def test_identical_reference_repeat_adds_no_new_time_sample(self):
        ref,truth=self.fixture();ref.insert(40,dict(ref[39]))
        report,_=measure(ref,truth,1000000000,10000000000)
        self.assertTrue(report['passed'])
        self.assertEqual(report['metrics']['reference_identical_source_repeats'],1)
    def test_conflicting_equal_stamp_reference_is_not_repaired(self):
        ref,truth=self.fixture();other=dict(ref[39]);other['position_enu']=[999,0,0];ref.insert(40,other)
        with self.assertRaisesRegex(ValueError,'conflicting reference'):
            measure(ref,truth,1000000000,10000000000)
    def test_same_stamp_change_is_kept_only_for_live_certified_new_trajectory(self):
        old={'goal_id':'g','epoch':'e','trajectory_id':8,'source_stamp_ns':100,
             'position_enu':[0.,0.,1.],'velocity_enu_m_s':[.05,0.,0.],
             'acceleration_enu_m_s2':[0.,0.,0.],'yaw_enu':0.}
        new={'goal_id':'g','epoch':'e','trajectory_id':9,'source_stamp_ns':100,
             'position_enu':[.00049,0.,1.],'velocity_enu_m_s':[.05017,0.,0.],
             'acceleration_enu_m_s2':[.00003,0.,0.],'yaw_enu':.001575}
        rows,repeats,handoffs=_reference_samples([old,new],{9:100})
        self.assertEqual(rows,[new])
        self.assertEqual(repeats,0)
        self.assertEqual(len(handoffs),1)
        self.assertAlmostEqual(handoffs[0]['position_delta_m'],.00049)
        self.assertAlmostEqual(handoffs[0]['velocity_delta_m_s'],.00017)
        self.assertAlmostEqual(handoffs[0]['yaw_delta_rad'],.001575)
    def test_same_stamp_different_trajectory_without_matching_spline_certificate_fails(self):
        old={'goal_id':'g','epoch':'e','trajectory_id':8,'source_stamp_ns':100,
             'position_enu':[0.,0.,1.],'velocity_enu_m_s':[.05,0.,0.],
             'acceleration_enu_m_s2':[0.,0.,0.]}
        new=dict(old,trajectory_id=9,position_enu=[.001,0.,1.])
        with self.assertRaisesRegex(ValueError,'conflicting reference'):
            _reference_samples([old,new],{9:99})
    def test_same_trajectory_yaw_conflict_at_equal_stamp_fails(self):
        old={'goal_id':'g','epoch':'e','trajectory_id':8,'source_stamp_ns':100,
             'position_enu':[0.,0.,1.],'velocity_enu_m_s':[.05,0.,0.],
             'acceleration_enu_m_s2':[0.,0.,0.],'yaw_enu':0.}
        changed=dict(old,yaw_enu=.01)
        with self.assertRaisesRegex(ValueError,'conflicting reference'):
            _reference_samples([old,changed],{8:100})
    def test_reference_time_regression_is_not_sorted(self):
        ref,truth=self.fixture();ref[40]['source_stamp_ns']=ref[39]['source_stamp_ns']-1
        with self.assertRaisesRegex(ValueError,'strictly increasing'):
            measure(ref,truth,1000000000,10000000000)
    def test_return_motion_along_turned_body_forward_axis_passes(self):
        flight,truth=self.return_fixture(np.pi)
        result=audit_forward_return(flight,truth)
        self.assertTrue(all(result['checks'].values()))
        self.assertEqual(result['metrics']['truth_return_backward_intervals'],0)
    def test_return_motion_backwards_against_body_heading_fails(self):
        flight,truth=self.return_fixture(0.0)
        result=audit_forward_return(flight,truth)
        self.assertFalse(result['checks']['return_motion_forward'])
if __name__=='__main__':unittest.main()
