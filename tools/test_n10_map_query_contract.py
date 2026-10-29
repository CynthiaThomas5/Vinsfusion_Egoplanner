import unittest
from types import SimpleNamespace
import json
from pathlib import Path
import tempfile

from tools.n10_map_query_contract import (
    PLANNING_OCCUPANCY_SERVICE,
    RAW_OCCUPANCY_SERVICE,
    radius_for_service,
    response_capture_error,
    response_query_geometry,
    resolve_point_query_identity,
)


class N10MapQueryContractTests(unittest.TestCase):
    def test_raw_sphere_and_planning_point_use_distinct_radii(self):
        self.assertEqual(radius_for_service(RAW_OCCUPANCY_SERVICE, 0.05), 0.05)
        self.assertEqual(radius_for_service(PLANNING_OCCUPANCY_SERVICE, 0.05), 0.0)
        for radius in (0.0, -0.1, 2.01, float('nan')):
            with self.assertRaises(ValueError):
                radius_for_service(RAW_OCCUPANCY_SERVICE, radius)

    def test_matching_identity_does_not_make_rejected_query_valid(self):
        row = {
            'service': RAW_OCCUPANCY_SERVICE,
            'identity_matches_request': True,
            'request': {
                'expected_epoch': 'epoch', 'expected_map_id': 'epoch-map',
                'frame_id': 'odom_epoch', 'radius_m': 0.05,
                'xyz_odom_m': [1.0, 2.0, 3.0],
            },
            'response': {
                'accepted': False, 'reason': 'invalid_query',
                'epoch': 'epoch', 'map_id': 'epoch-map',
                'header_frame_id': 'odom_epoch', 'radius_m': 0.0,
                'center_xyz_odom_m': [1.0, 2.0, 3.0],
            },
        }
        self.assertEqual(response_capture_error(row), 'service_rejected:invalid_query')
        row['response'].update(accepted=True, reason='ok', radius_m=0.05)
        self.assertEqual(response_capture_error(row), '')

    def test_response_must_echo_request_geometry(self):
        row = {
            'service': PLANNING_OCCUPANCY_SERVICE,
            'identity_matches_request': True,
            'request': {
                'expected_epoch': 'epoch', 'expected_map_id': 'epoch-map',
                'frame_id': 'odom_epoch', 'radius_m': 0.0,
                'xyz_odom_m': [1.0, 2.0, 3.0],
            },
            'response': {
                'accepted': True, 'reason': 'unobserved_not_occupied',
                'epoch': 'epoch', 'map_id': 'epoch-map',
                'header_frame_id': 'odom_epoch', 'radius_m': 0.0,
                'center_xyz_odom_m': [1.0, 2.0, 3.0],
            },
        }
        self.assertEqual(response_capture_error(row), '')
        row['response']['center_xyz_odom_m'] = [1.1, 2.0, 3.0]
        self.assertEqual(response_capture_error(row), 'response_center_mismatch')

    def test_ros_query_response_geometry_serializes_center_and_radius(self):
        response = SimpleNamespace(
            center=SimpleNamespace(x=1.0, y=2.0, z=3.0),
            radius_m=0.05,
        )
        self.assertEqual(response_query_geometry(response), {
            'center_xyz_odom_m': [1.0, 2.0, 3.0],
            'radius_m': 0.05,
        })

    def test_point_query_spec_binds_goal_identity_before_flight_record_exists(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / 'run-1'
            run.mkdir()
            (run / 'runtime-contract.json').write_text(json.dumps({'sha256': 'contract-1'}))
            (run / 'n10-run-manifest.json').write_text(json.dumps({
                'run_id': 'run-1', 'runtime_contract_sha256': 'contract-1'}))
            epoch = 'epoch-1'
            spec = {
                'goal_id': 'goal-1', 'epoch': epoch,
                'map_id': f'{epoch}-map-1', 'frame_id': f'odom_{epoch}',
                'run_identity': {
                    'run_id': 'run-1', 'runtime_contract_sha256': 'contract-1',
                    'goal_id': 'goal-1', 'epoch': epoch,
                    'map_id': f'{epoch}-map-1', 'frame_id': f'odom_{epoch}',
                },
            }
            identity, conflicts = resolve_point_query_identity(run, spec)
            self.assertTrue(identity['complete'])
            self.assertEqual(identity['goal_id'], 'goal-1')
            self.assertEqual(conflicts, {})
            spec['run_identity']['goal_id'] = 'different-goal'
            _identity, conflicts = resolve_point_query_identity(run, spec)
            self.assertIn('goal_id', conflicts)


if __name__ == '__main__':
    unittest.main()
