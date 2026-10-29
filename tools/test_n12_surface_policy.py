"""User#508 surface diagnostic policy retains evidence and safety criteria."""
import copy,json,unittest,importlib.util
from pathlib import Path
from tools.map_surface_policy import surface_error_result
ROOT=Path(__file__).resolve().parents[1]
class SurfacePolicy(unittest.TestCase):
 def test_large_error_is_diagnostic(self):
  r=surface_error_result([.138455,1.2],{});self.assertEqual(r['status'],'PASS');self.assertEqual(r['maximum_observed_error_m'],1.2);self.assertFalse(r['numeric_limit_enabled'])
 def test_legacy_limit_still_fails(self):
  self.assertEqual(surface_error_result([.138455],{'surface_center_error_sample_max_m':.1})['status'],'FAIL')
 def test_no_measurements_still_insufficient(self):self.assertEqual(surface_error_result([],{})['status'],'INSUFFICIENT')
 def test_bad_measurements_still_insufficient(self):
  for v in [None,float('nan'),float('inf'),-.1,True]:self.assertEqual(surface_error_result([v],{})['status'],'INSUFFICIENT')
 def test_missing_identity_or_coverage_cannot_pass(self):self.assertEqual(surface_error_result([.01],{},False)['status'],'INSUFFICIENT')
 def test_only_authorized_metric_configs_changed_since_legacy(self):
  old=json.loads((ROOT/'config/acceptance_n11.json').read_text())['metrics'];new=json.loads((ROOT/'config/acceptance_n12.json').read_text())['metrics'];
  for key in ['raw_map_surface_geometry','raw_vio_rpe_10s']:del old[key];del new[key]
  self.assertEqual(old,new)
 def test_actual_clearance_and_classification_still_required(self):
  c=json.loads((ROOT/'config/acceptance_n12.json').read_text())['metrics'];self.assertEqual(c['full_body_clearance_and_contact']['thresholds']['minimum_full_body_clearance_m'],.1);self.assertEqual(c['raw_map_classification']['thresholds']['truth_occluded_raw_free_count_max'],0)
if __name__=='__main__':unittest.main()
