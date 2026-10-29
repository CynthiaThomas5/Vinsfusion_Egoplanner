import unittest
from tools.n16_resource_evidence import series_summary

class ResourceEvidenceTests(unittest.TestCase):
    def test_burst_returns_to_baseline(self):
        r=series_summary([(i,100 if i==8 else 1) for i in range(16)])
        self.assertEqual(r['maximum'],100)
        self.assertFalse(r['persistent_separated_envelope_growth'])
    def test_persistent_envelope_growth_requires_review(self):
        self.assertTrue(series_summary([(i,i) for i in range(16)])['persistent_separated_envelope_growth'])
    def test_constant_queue_not_growth(self):
        self.assertFalse(series_summary([(i,8) for i in range(16)])['persistent_separated_envelope_growth'])
    def test_missing_not_imputed(self):
        self.assertEqual(series_summary([(0,None),(1,None)])['status'],'INSUFFICIENT')
    def test_nonmonotonic_rejected(self):
        self.assertEqual(series_summary([(0,1),(1,2),(1,3),(2,4)])['status'],'INSUFFICIENT')
