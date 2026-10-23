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
        loop = legs({**single[0], 'goals': [{'target_offset_enu_m':[x,0,0]} for x in [1,0,.5]]})
        self.assertEqual(len(single), 1)
        self.assertEqual([x['target_offset_enu_m'][0] for x in loop], [1, 0, .5])
        self.assertTrue(all(x['position_tolerance_m'] == .1 and x['dwell_s'] == 1 for x in loop))

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
