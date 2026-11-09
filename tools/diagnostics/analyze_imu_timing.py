#!/usr/bin/env python3
"""Analyze native sensor source/receipt clocks without changing source timestamps."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def quantiles(values):
    data=sorted(values)
    if not data:return None
    def q(p):
        x=(len(data)-1)*p;lo=int(x);hi=min(lo+1,len(data)-1)
        return data[lo]+(data[hi]-data[lo])*(x-lo)
    return {'min':data[0],'p01':q(.01),'median':q(.5),'p99':q(.99),'max':data[-1]}


def analyze(rows, startup_s=5., tolerance_s=.001):
    samples=[(int(r['source_ns']),int(r['system_ns']),int(r['monotonic_ns']))
             for r in rows if r['kind']=='imu']
    if len(samples)<2:raise ValueError('At least two IMU samples required')
    origin=samples[0][2]
    def summarize(data):
        ages=[(system-source)/1e9 for source,system,mono in data]
        future=[(mono-origin)/1e9 for source,system,mono in data if system-source < -round(tolerance_s*1e9)]
        offsets=[system-mono for source,system,mono in data]
        return {'samples':len(data),'source_age_s':quantiles(ages),
                'beyond_future_tolerance':len(future),'first_future_elapsed_s':future[0] if future else None,
                'last_future_elapsed_s':future[-1] if future else None,
                'realtime_minus_monotonic_range_s':(max(offsets)-min(offsets))/1e9 if offsets else None,
                'realtime_minus_monotonic_step_s':quantiles([(b-a)/1e9 for a,b in zip(offsets,offsets[1:])])}
    return {'span_s':(samples[-1][2]-origin)/1e9,'startup_exclusion_s':startup_s,
            'future_tolerance_s':tolerance_s,'all':summarize(samples),
            'steady':summarize([r for r in samples if (r[2]-origin)/1e9>=startup_s]),
            'source_nonincreasing':sum(b[0]<=a[0] for a,b in zip(samples,samples[1:])),
            'monotonic_nonincreasing':sum(b[2]<=a[2] for a,b in zip(samples,samples[1:]))}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('csv',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    with args.csv.open() as f:result=analyze(csv.DictReader(f))
    result['input']=str(args.csv);result['sha256']=hashlib.sha256(args.csv.read_bytes()).hexdigest()
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
