import unittest
from tools.n09_contact_evaluation import evaluate_contacts

class FullMissionContactTests(unittest.TestCase):
    def test_contact_between_goals_cannot_hide_before_last_goal(self):
        report={'ready':True,'expected_topics':['body'],'advertised_topics':['body'],'events':[
            {'stamp_ns':200,'topic':'body','pairs':[{'collision1':'body','collision2':'ground_plane'}]},
            {'stamp_ns':400,'topic':'body','pairs':[{'collision1':'body','collision2':'ground_plane'}]}]}
        manifest={'sensor_topics':['body']}
        phases=[{'stamp_ns':0,'phase':'ACTIVE'},{'stamp_ns':350,'phase':'LANDING'}]
        self.assertEqual(evaluate_contacts(report,manifest,phases,100)['prohibited_contact_event_count'],1)
        self.assertEqual(evaluate_contacts(report,manifest,phases,300)['prohibited_contact_event_count'],0)
