#!/usr/bin/env python3
"""Join identical SDK frame timestamps to diagnostic reader calls (no restamping)."""
import argparse
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from analyze_imu_timing import quantiles


def ns(ms):return int(Decimal(ms)*1000000)


def analyze(frames, traces=(), skip_s=5.):
    frames=list(frames);traces=list(traces)
    if not frames:raise ValueError('No frames')
    start=min(int(r['monotonic_ns']) for r in frames)
    index={}
    for r in traces:index.setdefault(Decimal(r['converted_ms']),[]).append(r)
    result={}
    for kind in sorted(set(r['kind'] for r in frames)):
        rows=[r for r in frames if r['kind']==kind and (int(r['monotonic_ns'])-start)/1e9>=skip_s]
        ages=[(int(r['system_ns'])-ns(r['sdk_ms']))/1e9 for r in rows]
        joined=[];ambiguous=0
        for r in rows:
            candidates=index.get(Decimal(r['sdk_ms']),[])
            if len(candidates)==1:joined.append((r,candidates[0]))
            elif candidates:ambiguous+=1
        raw_intervals=[];mapping_steps=[];last={};future_examples=[]
        for r,t in joined:
            raw_ns=ns(t['raw_ms']);mapped_ns=ns(t['converted_ms']);reader=t['reader']
            previous=last.get(reader)
            if previous is not None:
                raw_intervals.append((raw_ns-previous[0])/1e9)
                mapping_steps.append(((mapped_ns-raw_ns)-previous[1])/1e9)
            last[reader]=(raw_ns,mapped_ns-raw_ns)
            reader_age=(int(t['system_ns'])-mapped_ns)/1e9
            if reader_age < -.001 and len(future_examples)<5:
                future_examples.append({'frame':r,'reader_call':t,'reader_age_s':reader_age})
        result[kind]={'samples':len(rows),'domains':sorted(set(r['domain'] for r in rows)),
            'callback_age_s':quantiles(ages),'future_gt_1ms':sum(a<-.001 for a in ages),
            'unique_trace_matches':len(joined),'ambiguous_trace_matches':ambiguous,
            'reader_age_s':quantiles([(int(t['system_ns'])-ns(t['converted_ms']))/1e9 for r,t in joined]),
            'raw_intervals_s':quantiles(raw_intervals),'mapping_offset_step_s':quantiles(mapping_steps),
            'raw_nonincreasing':sum(v<=0 for v in raw_intervals),
            'raw_domains':sorted(set(t['raw_domain'] for r,t in joined)),
            'ready_values':sorted(set(t['ready'] for r,t in joined)),
            'future_examples':future_examples}
    return {'span_s':(max(int(r['monotonic_ns']) for r in frames)-start)/1e9,
            'skip_s':skip_s,'streams':result}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('frames',type=Path);p.add_argument('--trace',type=Path);p.add_argument('--skip-seconds',type=float,default=5.);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    with args.frames.open() as f:frames=list(csv.DictReader(f))
    traces=[]
    if args.trace:
        with args.trace.open() as f:traces=list(csv.DictReader(f))
    result=analyze(frames,traces,skip_s=args.skip_seconds)
    result['inputs']={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in (args.frames,args.trace) if f}
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:{a:b for a,b in v.items() if a!='future_examples'} for k,v in result['streams'].items()},indent=2))


if __name__=='__main__':main()
