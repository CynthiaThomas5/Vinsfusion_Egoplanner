import json
from pathlib import Path
import unittest
from flight_profile import legs, attempts


class FlightProfileTests(unittest.TestCase):
    def test_default_and_loop_profiles(self):
        root = Path(__file__).resolve().parents[1]/'config/components/navigation'
        single = legs(json.loads((root/'room_crossing_goal.json').read_text()))
        loop_config = json.loads((root/'room_loop_goal.json').read_text())
        with self.assertRaisesRegex(ValueError, 'disabled'):
            legs(loop_config)
        loop = legs({**single[0], 'position_tolerance_m':.07, 'dwell_s':2.5, 'goals': [{'target_offset_enu_m':[x,0,0]} for x in [1,0,.5]]})
        self.assertEqual(len(single), 1)
        self.assertEqual([x['target_offset_enu_m'][0] for x in loop], [1, 0, .5])
        self.assertTrue(all(x['position_tolerance_m'] == .07 and x['dwell_s'] == 2.5 for x in loop))

    def test_malformed_or_unbounded_profiles_rejected(self):
        for config in [{'goals': []}, {'goals': [{}]*4}, {'target_offset_enu_m': [0, 0]},
                       {'target_offset_enu_m': [0, 0, float('nan')]},
                       {'target_offset_enu_m': [True, 0, 0]}]:
            with self.subTest(config=config), self.assertRaises(ValueError):
                legs(config)

    def test_failed_second_goal_does_not_inherit_first_completion(self):
        first={'goal_id':'first','action_success':True,'goal_completed_source_ns':10}
        flight={'goal_id':'second','action_success':False,'goal_completed_source_ns':10,'legs':[first]}
        result=attempts(flight)
        self.assertEqual(len(result),2)
        self.assertNotIn('goal_completed_source_ns',result[-1])
        self.assertEqual(result[0],first)
        self.assertEqual(len(attempts({'goal_id':'first','legs':[first]})),1)

    def test_long_mission_requires_explicit_duration_and_remains_bounded(self):
        from flight_profile import navigation_duration_requirement
        config={'goals':[{'target_offset_enu_m':[12 if i%2==0 else 0,0,.1]} for i in range(24)],
                'continuous_navigation_min_sim_s':600}
        self.assertEqual(len(legs(config)),24)
        self.assertEqual(navigation_duration_requirement(config),600)
        with self.assertRaises(ValueError):legs({**config,'goals':config['goals']+[config['goals'][0]]})
        with self.assertRaises(ValueError):legs({**config,'continuous_navigation_min_sim_s':0})
        for value in [True,-1,float('nan'),'600']:
            with self.subTest(value=value),self.assertRaises(ValueError):
                navigation_duration_requirement({'continuous_navigation_min_sim_s':value})

    def test_navigation_duration_uses_source_time_and_exact_boundary(self):
        from flight_profile import navigation_elapsed_sim_s
        self.assertLess(navigation_elapsed_sim_s(10,600000000009),600)
        self.assertEqual(navigation_elapsed_sim_s(10,600000000010),600)
        with self.assertRaises(ValueError):navigation_elapsed_sim_s(20,10)
