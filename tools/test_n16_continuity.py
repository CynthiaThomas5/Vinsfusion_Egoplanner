import copy
import unittest
from tools.n16_continuity import assess_continuity


def fixture():
    f={'continuous_navigation':{'start_source_ns':0,'end_source_ns':600000000000,'observed_sim_s':600.},
       'localization_epoch':'epoch','action_success':True,'landed_and_disarmed':True,'legs':[]}
    commands=[];splines=[]
    for i,(start,end) in enumerate([(0,300000000000),(300000000001,600000000000)]):
        gid=str(i);f['legs'].append({'goal_id':gid,'goal':{'frame':'odom_epoch'},'action_success':True,
                                   'goal_start_sim_ns':start,'goal_completed_source_ns':end})
        commands.append({'goal_id':gid,'epoch':'epoch','flag':1,'source_stamp_ns':start+1,
                         'trajectory_id':i,'velocity_enu_m_s':[.4,0,0]})
        splines.append({'goal_id':gid,'epoch':'epoch','traj_id':i})
    return [f,[{'stamp_ns':0,'phase':'ACTIVE','armed':True,'landed':False}],commands,splines,[0,600000000000]]


class ContinuousMissionTests(unittest.TestCase):
    def test_complete_source_window(self):self.assertEqual(assess_continuity(*fixture())['status'],'PASS')
    def test_short_window_insufficient(self):
        a=fixture();a[0]['continuous_navigation']['end_source_ns']-=1
        self.assertEqual(assess_continuity(*a)['status'],'INSUFFICIENT')
    def test_stitched_flights_fail(self):
        a=fixture();a[1].append({'stamp_ns':200000000000,'phase':'LANDED','armed':False,'landed':True})
        self.assertEqual(assess_continuity(*a)['status'],'FAIL')
    def test_epoch_mix_fails(self):
        a=fixture();a[0]['legs'][1]['goal']['frame']='odom_other'
        self.assertEqual(assess_continuity(*a)['status'],'FAIL')
    def test_hold_without_motion_does_not_qualify(self):
        a=fixture()
        for c in a[2]:c['velocity_enu_m_s']=[0,0,0]
        self.assertEqual(assess_continuity(*a)['status'],'INSUFFICIENT')
    def test_missing_truth_not_imputed(self):
        a=fixture();a[4]=[0,500000000000]
        self.assertEqual(assess_continuity(*a)['status'],'INSUFFICIENT')
    def test_wrong_trajectory_identity_not_accepted(self):
        a=fixture();a[3][1]['epoch']='other'
        self.assertEqual(assess_continuity(*a)['status'],'INSUFFICIENT')
    def test_explicit_five_minute_duration(self):
        a=fixture();a[0]['continuous_navigation'].update(end_source_ns=300000000000,observed_sim_s=300.)
        a[0]['legs'][0]['goal_completed_source_ns']=150000000000
        a[0]['legs'][1].update(goal_start_sim_ns=150000000001,goal_completed_source_ns=300000000000)
        a[2][1]['source_stamp_ns']=150000000002;a[4]=[0,300000000000]
        self.assertEqual(assess_continuity(*a,required_sim_s=300)['status'],'PASS')
        self.assertEqual(assess_continuity(*a,required_sim_s=600)['status'],'INSUFFICIENT')
