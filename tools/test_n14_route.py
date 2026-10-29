import unittest
from tools.debug_truth.evaluate_n14_route import passage


def rows(points,stamps=None):
    return [{'source_stamp_ns':s,'xyz':p,'trajectory_id':1} for s,p in zip(stamps or range(1,len(points)+1),points)]

class CorridorTests(unittest.TestCase):
    def test_complete_inside_passage(self):
        r=passage(rows([[-4,0,1],[0,.3,1],[4,0,1]]),'xyz')
        self.assertTrue(r['sampled_center_path_within_passage'])
        self.assertLess(r['entry_source_ns'],r['exit_source_ns'])

    def test_outside_detour_not_counted(self):
        r=passage(rows([[-4,2,1],[0,2,1],[4,2,1]]),'xyz')
        self.assertFalse(r['sampled_center_path_within_passage'])

    def test_flyover_not_counted(self):
        r=passage(rows([[-4,0,4],[0,0,4],[4,0,4]]),'xyz')
        self.assertFalse(r['sampled_center_path_within_passage'])

    def test_exit_missing_insufficient(self):
        with self.assertRaisesRegex(ValueError,'entry_or_exit'):
            passage(rows([[-4,0,1],[0,0,1],[2,0,1]]),'xyz')

    def test_duplicate_preserved(self):
        r=passage(rows([[-4,0,1],[-4,0,1],[0,0,1],[4,0,1]],[1,1,2,3]),'xyz')
        self.assertTrue(r['sampled_center_path_within_passage'])

    def test_same_stamp_entry_ambiguous(self):
        with self.assertRaisesRegex(ValueError,'ambiguous_same_stamp'):
            passage(rows([[-4,0,1],[0,0,1],[4,0,1]],[1,1,2]),'xyz')
