"""User#500: translation RPE has no numeric rejection limit; retain other checks."""
import copy,json,unittest
from pathlib import Path
from tools.debug_truth.evaluate_n10_acceptance import evaluate_run
from tools.test_n10_acceptance import _metrics,_stat
ROOT=Path(__file__).resolve().parents[1]
class N12RpePolicyTests(unittest.TestCase):
 def setUp(self):
  self.current=json.loads((ROOT/'config/acceptance_n12.json').read_text())
  self.legacy=json.loads((ROOT/'config/acceptance_n11.json').read_text())
 def result(self,cfg,metrics):
  report=evaluate_run(cfg,metrics,Path('/tmp/n12-rpe-policy-fixture'))
  return next(x for x in report['metrics'] if x['id']=='raw_vio_rpe_10s')
 def test_large_translation_is_measured_without_numeric_rejection(self):
  m=_metrics();m['segments']['goal_motion_and_arrival_dwell']['relative_pose_error']['10s']['translation_error_m']=_stat(2.)
  r=self.result(self.current,m);self.assertEqual(r['status'],'PASS')
  self.assertFalse(r['translation_numeric_limit_enabled'])
  self.assertEqual(r['translation_measurements'][0]['value'],2.)
  self.assertFalse(any('translation' in x['metric'] for x in r['comparisons']))
 def test_historical_config_retains_original_result(self):
  m=_metrics();m['segments']['goal_motion_and_arrival_dwell']['relative_pose_error']['10s']['translation_error_m']=_stat(.059407)
  self.assertEqual(self.result(self.legacy,m)['status'],'FAIL')
 def test_rotation_limit_remains(self):
  m=_metrics();m['segments']['requested_active_hold']['relative_pose_error']['10s']['rotation_error_deg']=_stat(.6)
  self.assertEqual(self.result(self.current,m)['status'],'FAIL')
 def test_missing_translation_is_insufficient(self):
  m=_metrics();del m['segments']['requested_active_hold']['relative_pose_error']['10s']['translation_error_m']
  self.assertEqual(self.result(self.current,m)['status'],'INSUFFICIENT')
 def test_missing_supported_pairs_is_insufficient(self):
  m=_metrics();m['segments']['goal_motion_and_arrival_dwell']['relative_pose_error']['10s']['supported_pairs']=0
  self.assertEqual(self.result(self.current,m)['status'],'INSUFFICIENT')
 def test_all_other_metric_configurations_equal(self):
  a=copy.deepcopy(self.legacy['metrics']);b=copy.deepcopy(self.current['metrics'])
  del a['raw_vio_rpe_10s'];del b['raw_vio_rpe_10s'];del a['raw_map_surface_geometry'];del b['raw_map_surface_geometry'];self.assertEqual(a,b)
  self.assertEqual(self.current['metrics']['raw_vio_rpe_10s']['thresholds'],{'rotation_p95_max_deg':.5})
 def test_arrival_failure_remains(self):
  m=_metrics();m['arrival']['independent_goal_dwell_status']='FAIL'
  r=evaluate_run(self.current,m,Path('/tmp/n12-rpe-policy-fixture'))
  self.assertEqual(next(x for x in r['metrics'] if x['id']=='arrival_position_yaw_dwell')['status'],'FAIL')
if __name__=='__main__':unittest.main()
