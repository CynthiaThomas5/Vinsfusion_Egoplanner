"""Synthetic validator fixtures; never count these as SLAM or flight evidence."""
import json
from pathlib import Path
import tempfile
import unittest

from check_loop_observation import evaluate


def fixture(run):
    namespace, frame = '/loop_observer/s_test', 'loop_test_map'
    poses = [{'source_ns': k*10_000_000, 'xyz': [float(k), 0., 0.]} for k in range(12)]
    odom = [{'source_ns': k*10_000_000, 'frame': frame, 'xyz': [float(k), 0., 0.]} for k in range(125)]
    raw = [dict(p, kind='raw_odom') for p in odom]
    state = {'keyframes': 12, 'loop_candidates': 0, 'verified_loops': 0, 'optimizations': 0,
             'image_buffer': 1, 'pose_buffer': 0, 'point_buffer': 0, 'max_image_pose_gap_ns': 1}
    observation = {'epoch': 'test', 'status': [state], 'paths': [{'frame': frame, 'count': 12}],
        'clouds': [{'frame': frame, 'count': 1}], 'odometry': odom,
        'last_path': {'poses': poses}, 'last_cloud': {'xyz': [[2., 1., 0.]]},
        'last_markers': [{'frame': frame} for _ in range(11)],
        'observer_node_publishers': [[namespace+'/pose_graph', ['MarkerArray']]],
        'observer_node_subscriptions': [['/vins_raw/s_test/'+name, ['test']] for name in [
            'odometry', 'keyframe_pose', 'keyframe_point', 'extrinsic']],
        'cpu_ticks_per_second': 100,
        'process_resources': [{'cpu_ticks': 1, 'wall_s': 0., 'hwm_kib': 1024},
                              {'cpu_ticks': 2, 'wall_s': 1., 'hwm_kib': 1024}]}
    documents = {'loop-observation.json': observation,
        'loop-observer-manifest.json': {'namespace': namespace, 'map_frame': frame, 'epoch': 'test',
            'session': {'namespace': '/vins_raw/s_test'}, 'limits': {'queue_limit': 64, 'max_keyframes': 1000},
            'executable_sha256': 'fixture'},
        'qualification.json': {'passed': True, 'runtime_contract_sha256': 'fixture'},
        'flight.json': {'landed_and_disarmed': True},
        'alignment-observation.json': {'samples': raw}}
    for name, data in documents.items():
        (run/name).write_text(json.dumps(data))
    (run/'loop-backend-exit-code').write_text('0\n')
    return observation


class LoopObservationCheckTest(unittest.TestCase):
    def test_success_report_serializes_without_numpy_scalar_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp); fixture(run)
            report = evaluate(run)
            self.assertTrue(report['passed'])
            json.dumps(report, allow_nan=False)

    def test_control_output_bad_frame_or_failed_exit_cannot_pass(self):
        for fault in ['control_output', 'frame', 'exit']:
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as tmp:
                run = Path(tmp); data = fixture(run)
                if fault == 'control_output':
                    data['observer_node_publishers'].append(['/fmu/in/trajectory_setpoint', ['test']])
                elif fault == 'frame':
                    data['paths'][0]['frame'] = 'odom_test'
                else:
                    (run/'loop-backend-exit-code').write_text('2\n')
                (run/'loop-observation.json').write_text(json.dumps(data))
                self.assertFalse(evaluate(run)['passed'])


if __name__ == '__main__':
    unittest.main()
