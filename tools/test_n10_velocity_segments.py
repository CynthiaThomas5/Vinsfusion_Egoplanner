import unittest
from tools.debug_truth.evaluate_n10_vins_velocity import velocity_phase_windows

class VelocitySegmentsTests(unittest.TestCase):
    def test_completed_hold_and_landing_are_separate(self):
        x=velocity_phase_windows({'post_goal_hold':{'completed':True,'requested_sim_s':20}},10_000_000_000,100_000_000_000,126_000_000_000)
        self.assertEqual(x['post_goal_active_hold'],(100_000_000_000,120_000_000_000))
        self.assertEqual(x['landing'],(120_000_000_000,126_000_000_000))

    def test_missing_hold_is_insufficient_not_goal_to_landed_hold(self):
        x=velocity_phase_windows({},1,2,10)
        self.assertIsNone(x['post_goal_active_hold']);self.assertIsNone(x['landing'])

    def test_unfinished_or_inconsistent_hold_cannot_supply_support(self):
        x=velocity_phase_windows({'post_goal_hold':{'completed':False,'requested_sim_s':20}},1,2,30_000_000_000)
        self.assertIsNone(x['post_goal_active_hold'])
        with self.assertRaises(ValueError):
            velocity_phase_windows({'post_goal_hold':{'completed':True,'requested_sim_s':20}},1,2,10)

if __name__=='__main__':unittest.main()
