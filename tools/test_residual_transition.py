import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent/'debug_truth'))
from evaluate_residual_transition import decompose, transition, total_transition


class ResidualDecompositionTests(unittest.TestCase):
    def sample(self):
        return {'stamp_ns':1,'final_cost':50,'residual_components':100,'input_features':20,
                'stereo_features':15,'continued_tracks':12,'long_tracks':10,
                'cost_components':{'evaluation_ok':True,'evaluation_seconds':.001,
                    'marginalization':{'cost':40,'residual_components':20},
                    'imu':{'cost':5,'residual_components':30},'visual':{'cost':5,'residual_components':50}}}

    def test_groups_reproduce_normalized_squared_total(self):
        d=decompose(self.sample())
        self.assertAlmostEqual(d['normalized_cost'],1)
        self.assertAlmostEqual(sum(x['normalized_squared_contribution'] for x in d['groups'].values()),1)
        self.assertAlmostEqual(d['groups']['marginalization']['cost_fraction'],.8)

    def test_inconsistent_or_missing_diagnostics_rejected(self):
        for key,value in [('evaluation_ok',False),('visual',{'cost':6,'residual_components':50}),
                          ('visual',{'cost':5,'residual_components':49}),
                          ('visual',{'cost':float('nan'),'residual_components':50})]:
            p=self.sample();p['cost_components'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):decompose(p)

    def test_flight_callback_preserves_source_groups_and_biases(self):
        import json,time
        from types import SimpleNamespace
        try:
            from run_vio_ego_flight import EgoFlightProbe
        except ModuleNotFoundError as exc:
            self.skipTest('ROS runtime unavailable: '+str(exc))
        metric=self.sample();metric['accel_bias_norm']=.02;metric['gyro_bias_norm']=.001
        fake=SimpleNamespace(started_wall=time.monotonic(),vins_quality_history=[],_count=lambda _:None)
        EgoFlightProbe._on_vins_telemetry(fake,SimpleNamespace(data=json.dumps(metric)))
        row=fake.vins_quality_history[-1]
        self.assertEqual(row['cost_components'],metric['cost_components'])
        self.assertEqual(row['accel_bias_norm'],.02)
        self.assertEqual(row['gyro_bias_norm'],.001)
        self.assertAlmostEqual(row['normalized_cost'],1)

    def test_constant_cost_count_change_is_not_cost_increase(self):
        p=self.sample();previous=decompose(p)
        for name in ['marginalization','imu','visual']:
            p['cost_components'][name]['residual_components']*=2
        p['residual_components']*=2
        current=decompose(p);delta=transition(previous,current)
        self.assertAlmostEqual(sum(delta['cost_change_contribution'].values()),0)
        self.assertAlmostEqual(delta['residual_count_change_contribution'],-.5)
        self.assertAlmostEqual(delta['total_squared_cost_change'],-.5)

    def test_lower_total_cost_can_cross_threshold_when_count_falls(self):
        delta=total_transition(50,100,49,90)
        self.assertLess(delta['cost_change_contribution'],0)
        self.assertGreater(delta['residual_count_change_contribution'],0)
        self.assertAlmostEqual(delta['cost_change_contribution']+delta['residual_count_change_contribution'],delta['total_squared_cost_change'])
        self.assertGreater(delta['total_squared_cost_change'],0)

    def test_trigger_only_mode_keeps_previous_total_without_inventing_groups(self):
        import json,tempfile
        from evaluate_residual_transition import evaluate
        previous=self.sample();previous.update(stamp_ns=9,solve_current=True,cost_components=None)
        current=self.sample();current.update(stamp_ns=10,final_cost=55,solve_current=True)
        current['cost_components']['visual']['cost']=10
        flight={'result':'FAIL','vins_quality_history':[previous,current],
                'localization_quality_history':[{'stamp_ns':10,'reason':'normalized_cost_exceeded'}]}
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp)
            (run/'flight.json').write_text(json.dumps(flight))
            (run/'vins-diagnostics.json').write_text(json.dumps({'cost_groups_mode':'1'}))
            report,rows=evaluate(run)
            self.assertEqual(len(rows),1)
            self.assertIsNone(report['previous'])
            self.assertEqual(report['previous_solver_total']['stamp_ns'],9)
            self.assertAlmostEqual(report['trigger_total_transition']['cost_change_contribution'],.1)
            self.assertTrue(report['quality_crossing_observed'])
