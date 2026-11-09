#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'diagnostics'))
from analyze_imu_timing import analyze

def row(second,age,offset=100000000000):
 mono=second*1000000000;system=mono+offset
 return {'kind':'imu','source_ns':system-age,'system_ns':system,'monotonic_ns':mono}
# Startup and steady faults remain distinct; future timestamps are never clamped.
r=analyze([row(0,-40000000),row(1,5000000),row(6,-1200000),row(7,1000000)])
assert r['all']['beyond_future_tolerance']==2 and r['steady']['beyond_future_tolerance']==1
assert r['all']['source_age_s']['min']==-.04
assert r['steady']['realtime_minus_monotonic_range_s']==0
# A realtime clock step is observable separately from strictly increasing monotonic.
r=analyze([row(0,1000000),row(6,1000000,99990000000),row(7,1000000,99990000000)])
assert r['all']['realtime_minus_monotonic_step_s']['min']==-.01
assert r['monotonic_nonincreasing']==0
try:analyze([row(0,1)])
except ValueError:pass
else:raise AssertionError('short sample accepted')
print('Startup exclusion, future source, system-clock step and short-input checks PASS')
