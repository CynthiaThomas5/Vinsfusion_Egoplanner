#!/usr/bin/env python3
"""Summarize the recorded ground window without inventing unobserved samples."""
import json
import sys
from pathlib import Path
p=Path(sys.argv[1]);events=[json.loads(s) for s in (p/'load.jsonl').read_text().splitlines()]
samples=[e for e in events if e['kind']=='sample'];bridge=[e['data'] for e in events if e['kind']=='bridge'];summary=json.loads((p/'load-summary.json').read_text())
def stats(a):
 a=sorted(x for x in a if x is not None)
 return None if not a else {'min':a[0],'p95':a[int(.95*(len(a)-1))],'p99':a[int(.99*(len(a)-1))],'max':a[-1]}
resources={};temps={}
for e in samples:
 for item in e['data']['resources']['processes']:
  d=resources.setdefault(str(item['pid']),{'cmd':item['cmd'],'rss_bytes':[],'cpu_percent':[]})
  for k in ('rss_bytes','cpu_percent'):d[k].append(item[k])
 for k,v in e['data']['resources']['temperature_c'].items():temps.setdefault(k,[]).append(v)
for d in resources.values():
 for k in ('rss_bytes','cpu_percent'):d[k]=stats(d[k])
report={'summary':summary,'source_age_reporting':'Percentiles below summarize per-2s interval statistics, not exact all-message quantiles.',
 'interval_odom_age_p95_s':stats([e['data'].get('odom_age_s',{}).get('p95') for e in samples]),
 'interval_odom_age_p99_s':stats([e['data'].get('odom_age_s',{}).get('p99') for e in samples]),
 'observed_odom_age_max_s':max(e['data'].get('odom_age_s',{}).get('max',0) for e in samples),
 'pending_depth':stats([e['data']['map']['pending_depth_count'] for e in samples if e['data']['map']]),
 'map_first':next(e['data']['map'] for e in samples if e['data']['map']), 'map_last':samples[-1]['data']['map'],
 'bridge_last':bridge[-1], 'resources':resources,'temperature_c':{k:stats(v) for k,v in temps.items()},
 'graph':[e['data'] for e in events if e['kind']=='graph']}
(p/'analysis.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('resources','graph')},indent=2))
