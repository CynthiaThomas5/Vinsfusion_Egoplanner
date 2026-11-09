#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src/own/uav_localization'))
from uav_localization.health import Health
budget={'source_age_budget_s':.868306,'receipt_age_budget_s':.615998,'enforce_source_age':False}
for receipt,expected in [(1.,True),(.1,False)]:
 h=Health({'status_period_wall_s':.05,'freshness':{'mode':'gate','streams':{'optimized':budget}}},0.)
 h.state='TRACKING';h.samples={'optimized':(1,receipt,1)}
 assert h.enforce_freshness(2_000_000_000,1.)==expected
 if not expected:assert h.reason=='optimized_receipt_stale'
 assert h.age_metrics(2_000_000_000,1.)['optimized']['source_age_s']>1.9
h=Health({'status_period_wall_s':.05,'freshness':{'mode':'gate','streams':{'optimized':budget}}},0.)
h.state='TRACKING';h.samples={'optimized':(3_000_000_000,1.,1)}
assert not h.enforce_freshness(2_000_000_000,1.) and h.reason=='optimized_future_source_stamp'
print('3 source-age policy cases PASS: old source observed, receipt loss rejected, future source rejected')

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src/own/uav_px4_bridge'))
from uav_px4_bridge.time_mapping import SystemClockMapper, TimeMappingError
from types import SimpleNamespace
sync=SimpleNamespace(timestamp=10_000_000,source_protocol=2,round_trip_time=1000,estimated_offset=-1_000_000)
m=SystemClockMapper(.868306,.02,.05,enforce_source_age=False)
assert m.to_px4(8_000_000_000,10_000_000_000,10_000_000_000,sync,10_000_000_000,2.,10000).sample_age_wall_s==2.
try:m.to_px4(10_100_000_000,10_000_000_000,10_000_000_000,sync,10_000_000_000,2.,10000)
except TimeMappingError:pass
else:raise AssertionError('future stamp accepted')
print('Hardware mapper disabled-age/future cases PASS')
