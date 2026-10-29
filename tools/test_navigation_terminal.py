import copy
import unittest
from write_navigation_terminal import terminal_record

class NavigationTerminalTests(unittest.TestCase):
    def setUp(self):
        self.flight={'goal_id':'goal','localization_epoch':'epoch'}
        self.readback={'expected_goal_id':'goal','expected_epoch':'epoch','latest':{'bridge':{'phase':'LANDED','landed':True,'armed':False,'control_enabled':False},'px4_status':{'arming_state':1},'land_detected':{'landed':True}},'zero_control_after_terminal':True,'no_old_epoch_goal_or_trajectory':True,'terminal_state_duration_wall_s':12,'terminal_state_violation_count':0}
    def test_independent_safe_terminal(self):
        self.assertTrue(terminal_record(self.readback,self.flight)['safe_to_stop_project_container'])
    def test_missing_short_or_wrong_identity_never_safe(self):
        for field,value in [('expected_goal_id','other'),('expected_epoch','other'),('zero_control_after_terminal',False),('terminal_state_duration_wall_s',9),('terminal_state_violation_count',1)]:
            with self.subTest(field=field):
                row=copy.deepcopy(self.readback);row[field]=value
                self.assertFalse(terminal_record(row,self.flight)['safe_to_stop_project_container'])
    def test_armed_or_enabled_never_safe(self):
        for key in ['armed','control_enabled']:
            row=copy.deepcopy(self.readback);row['latest']['bridge'][key]=True
            self.assertFalse(terminal_record(row,self.flight)['safe_to_stop_project_container'])
