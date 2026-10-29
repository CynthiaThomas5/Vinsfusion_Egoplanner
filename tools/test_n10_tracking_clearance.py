import json
import tempfile
import unittest
from pathlib import Path

from tools.debug_truth.evaluate_n10_tracking_clearance import (
    component_tracking_clearances,
    evaluate,
)


class N10ComponentTrackingGeometryTests(unittest.TestCase):
    def test_component_sphere_clearance_is_paired_to_actual_attitude(self):
        rows = [{
            'source_stamp_ns': 10,
            'truth_xyz_world_m': [0.0, 0.0, 0.0],
            'command_xyz_world_m': [0.5, 0.0, 0.0],
            'q_xyzw': [0.0, 0.0, 0.0, 1.0],
        }]
        components = [{
            'name': 'rotor_0',
            'center_model_origin_m': [0.0, 0.0, 0.0],
            'enclosing_sphere_radius_m': 0.1,
        }]
        obstacles = [{
            'name': 'test_cylinder/link/collision',
            'kind': 'vertical_cylinder',
            'center_xyz_m': [1.0, 0.0, 0.0],
            'radius_m': 0.2,
            'z_min_m': -1.0,
            'z_max_m': 1.0,
        }]
        result = component_tracking_clearances(
            rows, components, obstacles, [0.0, 0.0, 0.0]
        )[0]
        self.assertAlmostEqual(result['actual_component_clearance_m'], 0.7)
        self.assertAlmostEqual(
            result['command_clearance_to_actual_nearest_component_obstacle_m'], 0.2
        )
        self.assertAlmostEqual(
            result['minimum_command_component_clearance_any_obstacle_m'], 0.2
        )
        self.assertEqual(result['nearest_actual_component'], 'rotor_0')


class N10IncompleteTrackingClearanceTests(unittest.TestCase):
    def test_aborted_action_keeps_missing_clearance_samples_insufficient(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory) / 'n10-aborted'
            run.mkdir()
            (run / 'flight.json').write_text(json.dumps({
                'run_id': run.name,
                'goal_id': 'goal-1',
                'localization_epoch': 'epoch-1',
                'goal': {'source_ns': 100},
                'action_success': False,
                'goal_completed_source_ns': None,
                'failure': 'navigation_action_not_successful:bridge_ev_position_not_fused',
                'action_result': {
                    'outcome': 'aborted',
                    'success': False,
                    'reason': 'bridge_ev_position_not_fused',
                },
            }))
            (run / 'debug-truth-evaluation.json').write_text(json.dumps({'samples': []}))
            (run / 'runtime-contract.json').write_text(json.dumps({'sha256': 'runtime-id'}))
            (run / 'n10-dynamic-clearance-world.sdf').write_text('<sdf/>\n')
            (run / 'n10-live-obstacle-observation.json').write_text(json.dumps({
                'run_id': run.name,
                'goal_id': 'goal-1',
                'epoch': 'epoch-1',
                'map_id_at_goal': 'epoch-1-map-1',
            }))
            output = run / 'tracking.json'

            report = evaluate(run, output)

            self.assertTrue(output.is_file())
            self.assertEqual(report['status'], 'FAIL')
            self.assertEqual(report['native_action']['reason'], 'bridge_ev_position_not_fused')
            self.assertIsNone(report['interval']['goal_completion_source_ns'])
            self.assertEqual(report['tracking_error_m']['count'], 0)
            self.assertIsNone(report['translation_only_clearance_budget']['negative_sample_fraction'])


if __name__ == '__main__':
    unittest.main()
