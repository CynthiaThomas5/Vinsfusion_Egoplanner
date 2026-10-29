import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent/'debug_truth'))
from evaluate_n10_precontact import sample_at, decompose_positions, stamps_for, canonical_commands

class PrecontactTests(unittest.TestCase):
    def test_supported_interpolation_and_exact_endpoints(self):
        rows=[{'stamp':10,'p':[0,0,0]},{'stamp':20,'p':[2,4,6]}]
        value,gap=sample_at(rows,[10,20],15,'p',10)
        np.testing.assert_allclose(value,[1,2,3]);self.assertEqual(gap,10)
        value,gap=sample_at(rows,[10,20],10,'p',1)
        np.testing.assert_allclose(value,[0,0,0]);self.assertEqual(gap,0)

    def test_gaps_extrapolation_and_nonmonotonic_data_rejected(self):
        rows=[{'stamp':10,'p':[0,0,0]},{'stamp':20,'p':[2,4,6]}]
        for stamp,limit in [(9,10),(21,10),(15,9)]:
            with self.assertRaises(ValueError): sample_at(rows,[10,20],stamp,'p',limit)
        with self.assertRaises(ValueError):stamps_for(rows+rows,'stamp')

    def test_conflicting_same_stamp_is_not_resolved_by_last_writer(self):
        a={'source_stamp_ns':10,'position_enu':[0,0,0],'trajectory_id':1,'wall_elapsed_s':1}
        b={**a,'wall_elapsed_s':2}
        c={**a,'source_stamp_ns':20}
        d={**c,'position_enu':[1,0,0]}
        rows,ambiguous,collapsed=canonical_commands([a,b,c,d])
        self.assertEqual(collapsed,1)
        self.assertEqual(len(ambiguous),1)
        self.assertEqual(ambiguous[0]['source_stamp_ns'],20)
        with self.assertRaises(ValueError):sample_at(rows,[10,20],20,'position_enu',10)
        with self.assertRaises(ValueError):sample_at(rows,[10,20],15,'position_enu',10)

    def test_vectors_add_but_scalar_errors_must_not_be_added(self):
        d=decompose_positions([1,1,0],[1,0,0],[0,0,0])
        self.assertEqual(d['vio_error_m'],1)
        self.assertEqual(d['command_minus_estimate_m'],1)
        self.assertAlmostEqual(d['command_minus_truth_m'],2**.5)
        self.assertEqual(d['vector_sum_closure_error_m'],0)

if __name__=='__main__':unittest.main()
