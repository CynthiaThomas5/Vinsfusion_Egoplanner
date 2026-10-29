"""User#520 removes minimum-clearance numeric rejection, preserving evidence/contact."""
import copy,json,tempfile,unittest
from pathlib import Path
from tools.debug_truth.evaluate_n10_acceptance import evaluate_run,continuous_clearance_evidence,tracking_clearance_budget_result,dynamic_replanning_result
from tools.debug_truth.evaluate_n10_replan_geometry import replan_clearance_policy
from tools.test_n10_acceptance import _metrics,_clearance_reports,_interval_report,_dynamic_replan_fixture
from tools import test_n10_acceptance as fixtures
ROOT=Path(__file__).resolve().parents[1]
class N13ClearancePolicy(unittest.TestCase):
 def setUp(self):
  self.new=json.loads((ROOT/'config/history/acceptance_n13_revision12.json').read_text());self.old=json.loads((ROOT/'config/acceptance_n12.json').read_text())
 def body(self,c,run):return next(x for x in evaluate_run(c,_metrics(),run)['metrics'] if x['id']=='full_body_clearance_and_contact')
 def test_only_authorized_clearance_keys_changed(self):
  old=copy.deepcopy(self.old['metrics']);new=copy.deepcopy(self.new['metrics'])
  for name,keys in {'ego_tracking_error':['minimum_actual_component_clearance_m'],'ego_tracking_clearance_budget':['minimum_actual_component_clearance_m'],'full_body_clearance_and_contact':['minimum_full_body_clearance_m'],'dynamic_replanning':['minimum_full_body_clearance_m','minimum_planner_centerline_body_margin_m']}.items():
   block='thresholds' if name=='full_body_clearance_and_contact' else 'acceptance_thresholds'
   for key in keys:del old[name][block][key]
   new[name]['method']=old[name]['method'];new[name]['evidence_status']=old[name]['evidence_status'];self.assertFalse(new[name].pop('clearance_numeric_limit_enabled'))
  self.assertEqual(old,new)
 def test_five_cm_passes_new_policy_but_legacy_fails(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);_clearance_reports(r,clearance_m=.05);_interval_report(r,lower_bound=.04,solver_state_min=.05)
   self.assertEqual(self.body(self.new,r)['status'],'PASS');self.assertEqual(self.body(self.old,r)['status'],'FAIL')
   self.assertFalse(any(x['metric']=='minimum_full_body_clearance_m' for x in self.body(self.new,r)['comparisons']))
 def test_negative_conservative_bound_is_diagnostic_not_zero_gate(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);_clearance_reports(r,clearance_m=.03);_interval_report(r,lower_bound=-.01,solver_state_min=.03);p=r/'n10-interval-clearance-bound.json';d=json.loads(p.read_text());d.update(status='INSUFFICIENT_AIRBORNE_BOUND',interval_bound_verified=False);p.write_text(json.dumps(d))
   m=self.body(self.new,r);self.assertEqual(m['status'],'PASS');self.assertEqual(m['continuous_interval_evidence']['minimum_no_contact_interval_clearance_m'],-.01);self.assertFalse(m['continuous_interval_evidence']['numeric_limit_enabled'])
 def test_collision_fails_even_without_clearance_report(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);_clearance_reports(r,contact_count=1);(r/'n10-interval-clearance-bound.json').unlink();(r/'n10-clearance-evaluation.json').unlink();m=self.body(self.new,r);self.assertEqual(m['status'],'FAIL');self.assertTrue(m['direct_safety_failure'])
 def test_missing_measurement_insufficient(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);_clearance_reports(r);p=r/'n10-interval-clearance-bound.json';d=json.loads(p.read_text());d['airborne_intervals']['min_clearance_lower_bound_m']=None;p.write_text(json.dumps(d));self.assertEqual(self.body(self.new,r)['status'],'INSUFFICIENT')
 def test_missing_physics_partition_insufficient(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);_clearance_reports(r);_interval_report(r,complete_partition=False);self.assertEqual(self.body(self.new,r)['status'],'INSUFFICIENT')
 def test_changed_ledger_insufficient(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);_clearance_reports(r);(r/'debug-truth-kinematics.jsonl').write_text('tampered');self.assertEqual(continuous_clearance_evidence(r,None)['status'],'INSUFFICIENT')
 def tracking(self,c,r,report):return tracking_clearance_budget_result(c,{'runtime_contract_sha256':'contract-hash'},r,report)
 def test_tracking_small_gap_measured_without_gate(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t)/'run-1';d=fixtures.N10AcceptanceTests()._tracking_budget_report(r);d['minimum_actual_body_clearance']['actual_body_clearance_to_nearest_obstacle_m']=.02;self.assertEqual(self.tracking(self.new,r,d)['status'],'PASS');self.assertEqual(self.tracking(self.old,r,d)['status'],'FAIL')
 def test_missing_tracking_clearance_insufficient(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t)/'run-1';d=fixtures.N10AcceptanceTests()._tracking_budget_report(r);d['minimum_actual_body_clearance'].clear();self.assertEqual(self.tracking(self.new,r,d)['status'],'INSUFFICIENT')
 def test_truth_gap_still_checked(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t)/'run-1';d=fixtures.N10AcceptanceTests()._tracking_budget_report(r);d['interval']['maximum_truth_bracket_gap_sim_s']=.005;self.assertEqual(self.tracking(self.new,r,d)['status'],'FAIL')
 def test_replan_policy_removes_extra_ten_cm_not_deadline(self):
  self.assertEqual(replan_clearance_policy(),(.1,.1));self.assertEqual(replan_clearance_policy(ROOT/'config/history/acceptance_n13_revision12.json'),(None,0.0))
 def test_replan_old_margin_policy_not_silently_reused(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);d,tr,tm,cm=_dynamic_replan_fixture(r);m=dynamic_replanning_result(self.new,{'runtime_contract_sha256':'runtime-contract-test-hash'},r,d,tr,tm,cm);self.assertEqual(m['status'],'INSUFFICIENT')
 def test_replan_small_clearance_keeps_deadline_and_contact_checks(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);d,tr,tm,cm=_dynamic_replan_fixture(r);g=d['planner_centerline_geometry'];g['required_full_body_clearance_m']=None;g['clearance_numeric_limit_enabled']=False;g['replanning_deadline']['additional_body_clearance_m']=0.0;g['first_trajectory_with_required_body_clearance_after_cloud']['minimum_centerline_body_margin_m']=.01;g['post_margin_qualified_spline_geometry']['minimum_centerline_body_margin_m']=-.01
   m=dynamic_replanning_result(self.new,{'runtime_contract_sha256':'runtime-contract-test-hash'},r,d,tr,tm,cm);self.assertEqual(m['status'],'PASS');self.assertFalse(any('clearance_m' in x['metric'] for x in m['comparisons']))
 def test_new_policy_replan_at_collision_deadline_still_fails(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);d,tr,tm,cm=_dynamic_replan_fixture(r,first_safe_command_ns=100_000_000_000);g=d['planner_centerline_geometry'];g['required_full_body_clearance_m']=None;g['clearance_numeric_limit_enabled']=False;g['replanning_deadline']['additional_body_clearance_m']=0.0
   self.assertEqual(dynamic_replanning_result(self.new,{'runtime_contract_sha256':'runtime-contract-test-hash'},r,d,tr,tm,cm)['status'],'FAIL')
 def test_new_policy_replan_prohibited_contact_still_fails(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);d,tr,tm,cm=_dynamic_replan_fixture(r);g=d['planner_centerline_geometry'];g['required_full_body_clearance_m']=None;g['clearance_numeric_limit_enabled']=False;g['replanning_deadline']['additional_body_clearance_m']=0.0;cm['observed_prohibited_contact_event_count']=1
   self.assertEqual(dynamic_replanning_result(self.new,{'runtime_contract_sha256':'runtime-contract-test-hash'},r,d,tr,tm,cm)['status'],'FAIL')
 def test_observed_collision_not_hidden_by_missing_replan_measurements(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);d,tr,tm,cm=_dynamic_replan_fixture(r);cm['status']='FAIL';cm['observed_prohibited_contact_event_count']=1;cm['continuous_interval_evidence']={}
   m=dynamic_replanning_result(self.new,{'runtime_contract_sha256':'runtime-contract-test-hash'},r,d,tr,tm,cm);self.assertEqual(m['status'],'FAIL');self.assertTrue(m['direct_safety_failure'])
if __name__=='__main__':unittest.main()
