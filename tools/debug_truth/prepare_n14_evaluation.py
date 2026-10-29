#!/usr/bin/env python3
"""Create the N14 independent derived view using the validated shared pipeline."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.debug_truth.prepare_n13_evaluation import prepare

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path)
    p.add_argument('--output-root',type=Path,required=True)
    p.add_argument('--config',type=Path,default=ROOT/'config/acceptance_n14.json')
    p.add_argument('--release',type=Path,default=ROOT/'docs/protocols/n14-corridor.json')
    a=p.parse_args();print(json.dumps(prepare(a.source,a.output_root,a.config,a.release,
        formal_tool='tools/debug_truth/evaluate_n14_run.py',formal_report='n14-scene-acceptance.json')))
