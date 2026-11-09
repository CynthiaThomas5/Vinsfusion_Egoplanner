#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'diagnostics'))
from analyze_sdk_clock import analyze,ns
assert ns('1792456844267.2538')==1792456844267253800
frames=[];trace=[]
for i in range(3):
 stamp=str(100000+i*5)
 frames.append({'kind':'Gyro','domain':'Global Time','sdk_ms':stamp,'system_ns':str(ns(stamp)-2000000),'monotonic_ns':str(i*5000000)})
 trace.append({'converted_ms':stamp,'raw_ms':str(i*5),'system_ns':str(ns(stamp)-3000000),'reader':'r','raw_domain':'0','ready':'1'})
x=analyze(frames,trace,skip_s=0)['streams']['Gyro']
assert x['unique_trace_matches']==3 and x['future_gt_1ms']==3
assert x['reader_age_s']['median']==-.003
assert x['raw_intervals_s']['median']==.005 and x['mapping_offset_step_s']['max']==0
# Ambiguous equal SDK timestamps must never be assigned an invented raw frame.
x=analyze(frames,trace+trace,skip_s=0)['streams']['Gyro'];assert x['unique_trace_matches']==0 and x['ambiguous_trace_matches']==3
try:analyze([])
except ValueError:pass
else:raise AssertionError('empty input accepted')
print('Exact clock precision, same-frame join, conversion age, ambiguity checks PASS')
