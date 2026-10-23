import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
from probe_preflight_scan import _confirm_fixture_removed, validate_profile

ROOT=Path(__file__).resolve().parents[1]
MODEL=ROOT/'simulation/models/preflight_scan_fixture/model.sdf'


class ScanProfileTests(unittest.TestCase):
    def setUp(self):
        self.policy=json.loads((ROOT/'config/components/simulation/preflight_scan.json').read_text())

    def test_canonical_profile(self):
        validate_profile(self.policy,MODEL)
        validate_profile(self.policy,MODEL,"coverage")
        validate_profile(self.policy,MODEL,"drift")
        validate_profile(self.policy,MODEL,"loop_revisit")

    def test_drift_rejects_missing_return_or_moving_reference(self):
        p=copy.deepcopy(self.policy)
        p['drift_profile']=[leg for leg in p['drift_profile'] if leg.get('cycle')!=3]
        with self.assertRaises(ValueError):validate_profile(p,MODEL,'drift')
        p=copy.deepcopy(self.policy)
        reference=next(leg for leg in p['drift_profile'] if leg.get('label')=='reference')
        reference['target']=[.1,.6,0,0]
        with self.assertRaises(ValueError):validate_profile(p,MODEL,'drift')

    def test_invalid_durations(self):
        for value in (0,-1,float('inf'),float('nan'),True,'1'):
            p=copy.deepcopy(self.policy);p['smoke_profile'][0]['duration_sim_s']=value
            with self.assertRaises(ValueError):validate_profile(p,MODEL)

    def test_target_bounds_and_shape(self):
        for target in ([0.,-1.,0.,0.],[0.,0.,8.,0.],[0.,0.,0.,1.],
                       [float('nan'),0.,0.,0.],[True,0.,0.,0.],[],None):
            p=copy.deepcopy(self.policy);p['smoke_profile'][0]['target']=target
            with self.assertRaises(ValueError):validate_profile(p,MODEL)

    @patch('probe_preflight_scan._gz_model_names', return_value={'x500_d435i_0'})
    def test_detached_fixture_absence_resolves_without_remove_ack(self, _):
        result=_confirm_fixture_removed('preflight_scan_fixture',False)
        self.assertTrue(result['scene_model_absent'])
        self.assertFalse(result['remove_service_acknowledged'])

    @patch('probe_preflight_scan._gz_model_names', return_value={'preflight_scan_fixture'})
    def test_fixture_still_in_scene_is_not_confirmed_removed(self, _):
        result=_confirm_fixture_removed('preflight_scan_fixture',False,timeout_s=0)
        self.assertFalse(result['scene_model_absent'])


if __name__=='__main__':unittest.main()
