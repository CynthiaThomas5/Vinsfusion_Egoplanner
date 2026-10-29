import copy
import json
import unittest
from pathlib import Path
from tools.n11_native_work_queue import evaluate_native_work

LIMITS=json.loads((Path(__file__).resolve().parents[1]/'config/acceptance_n11.json').read_text())['metrics']['resource_and_queue_behavior']['thresholds']

def rows():
    return [{'source_stamp_ns':1_000_000_000+i*66_666_667,'queue_metrics':{
        'feature_current_before_feature_dequeue':1,'acc_current_before_feature_dequeue':25+i,
        'work':{'schema':'vins-native-pending-work/v1','sequence':i+1,'waiting_features':0,
                'pending_feature_span_ns':0,'interval_endpoint_ns':1_000_000_000+i*66_666_667,
                'latest_imu_before_ns':1_050_000_000+i*66_666_667,
                'oldest_imu_after_ns':1_002_000_000+i*66_666_667,'remaining_imu_after_interval':14}}}
        for i in range(4)]

class NativeWorkTest(unittest.TestCase):
    def test_raw_count_growth_is_not_pending_work(self):
        self.assertEqual(evaluate_native_work(rows(),LIMITS)['status'],'PASS')
    def test_actual_pending_work_exceeds_budget(self):
        r=rows();r[-1]['queue_metrics']['work']['waiting_features']=3
        r[-1]['queue_metrics']['feature_current_before_feature_dequeue']=4
        self.assertEqual(evaluate_native_work(r,LIMITS)['status'],'FAIL')
    def test_lag_and_span_fail(self):
        for field in ['latest_imu_before_ns','pending_feature_span_ns']:
            r=rows();w=r[-1]['queue_metrics']['work']
            w[field]=(w['interval_endpoint_ns'] if field.startswith('latest') else 0)+210_000_000
            self.assertEqual(evaluate_native_work(r,LIMITS)['status'],'FAIL')
    def test_stale_imu_fails(self):
        r=rows();r[1]['queue_metrics']['work']['oldest_imu_after_ns']=0
        self.assertEqual(evaluate_native_work(r,LIMITS)['status'],'FAIL')
    def test_missing_or_corrupt_data_is_insufficient(self):
        for invalid in [None,{},[],True]:
            r=rows();r[1]['queue_metrics']['work']=invalid
            self.assertEqual(evaluate_native_work(r,LIMITS)['status'],'INSUFFICIENT')
        self.assertEqual(evaluate_native_work([],LIMITS)['status'],'INSUFFICIENT')
    def test_sequence_gap_is_insufficient(self):
        r=rows();r[2]['queue_metrics']['work']['sequence']=9
        self.assertEqual(evaluate_native_work(r,LIMITS)['status'],'INSUFFICIENT')
    def test_source_gap_is_insufficient(self):
        r=rows();r[-1]['source_stamp_ns']+=300_000_000
        self.assertEqual(evaluate_native_work(r,LIMITS)['status'],'INSUFFICIENT')
    def test_full_flight_coverage_required(self):
        r=rows()
        self.assertEqual(evaluate_native_work(r,LIMITS,0,r[-1]['source_stamp_ns'])['status'],'INSUFFICIENT')
        self.assertEqual(evaluate_native_work(r,LIMITS,r[0]['source_stamp_ns'],r[-1]['source_stamp_ns']+1)['status'],'INSUFFICIENT')
    def test_fail_preserved_even_with_missing_data(self):
        r=rows();r[0]['queue_metrics']['work']={};r[-1]['queue_metrics']['work']['oldest_imu_after_ns']=0
        self.assertEqual(evaluate_native_work(r,LIMITS)['status'],'FAIL')

if __name__=='__main__':unittest.main()
