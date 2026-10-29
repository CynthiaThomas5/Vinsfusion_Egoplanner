#!/usr/bin/env python3
"""Create an isolated derived-output view; never write through archive links."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import shutil
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))

OUTPUTS={'arrival-evaluation.json','arrival-evaluation-simtime-v2.json',
         'odometry-evaluation.json','odometry-errors.csv','n10-vins-velocity-evaluation.json',
         'n10-tracking-clearance-relation.json','n11-run-metrics.json',
         'n13-scene-acceptance.json','n14-scene-acceptance.json','n10-acceptance-evaluation.json'}


def prepare(source, output_root, config, release,
            formal_tool='tools/debug_truth/evaluate_n13_run.py',
            formal_report='n13-scene-acceptance.json'):
    source=Path(source).resolve();view=Path(output_root).resolve()/source.name
    view.mkdir(parents=True,exist_ok=False)
    originals={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
               for p in source.iterdir() if p.is_file() and p.name in OUTPUTS}
    for p in source.iterdir():
        if p.name == 'n11-static-map' and p.is_dir():
            shutil.copytree(p, view/p.name)
        elif p.name not in OUTPUTS:
            (view/p.name).symlink_to(p,target_is_directory=p.is_dir())
    stack=source.parent/(source.name+'-stack')
    if stack.exists() and not (view.parent/stack.name).exists():
        (view.parent/stack.name).symlink_to(stack,target_is_directory=True)
    observation=json.loads((source/'n11-static-map-observation.json').read_text())
    identity=observation['run_identity']
    alias=view/'n10-live-obstacle-observation.json'
    if alias.is_symlink():alias.unlink()
    alias.write_text(json.dumps({'schema':'n13-static-observer-compatibility/v1',
        'source_report':'n11-static-map-observation.json', 'run_identity':identity,
        'run_id':source.name,'runtime_contract_baseline_sha256':identity['runtime_contract_sha256'],
        'goal_id':identity['goal_id'],'epoch':identity['epoch'],'map_id_at_goal':identity['map_id'],
        'obstacle':{},'gazebo_create':{'acknowledged':False},'world_mutation_commands':[]},indent=2)+'\n')
    world_alias=view/'n10-dynamic-clearance-world.sdf'
    if world_alias.is_symlink():world_alias.unlink()
    world_alias.symlink_to(source/'vio_initialization.sdf')
    errors=[]
    def command(tool,*args):
        logfile=view/(Path(tool).stem+'.log')
        if logfile.is_symlink():logfile.unlink()
        with logfile.open('w') as out:
            r=subprocess.run([sys.executable,str(ROOT/tool),str(view),*map(str,args)],
                             cwd=ROOT,stdout=out,stderr=subprocess.STDOUT)
        if r.returncode:errors.append({'tool':tool,'exit_code':r.returncode,'log':str(logfile)})
    command('tools/debug_truth/evaluate_arrival.py','--acceptance-config',Path(config).resolve())
    arrival=view/'arrival-evaluation.json'
    if arrival.exists():(view/'arrival-evaluation-simtime-v2.json').write_bytes(arrival.read_bytes())
    command('tools/debug_truth/evaluate_odometry.py')
    command('tools/debug_truth/evaluate_n10_vins_velocity.py')
    command('tools/debug_truth/evaluate_n10_tracking_clearance.py','--output',view/'n10-tracking-clearance-relation.json')
    try:
        from tools.debug_truth.evaluate_n10_cross_run_calibration import evaluate_run
        metrics=evaluate_run(view)
        (view/'n11-run-metrics.json').write_text(json.dumps({'schema':'n10-cross-run-calibration-pair/v1',
            'classification':'one independent N13 run; no pooled samples','runs':[metrics]},indent=2,allow_nan=False)+'\n')
    except (OSError,ValueError,KeyError,TypeError) as exc:
        errors.append({'tool':'cross_run_calibration','error':repr(exc)})
    if (view/'n11-run-metrics.json').exists():
        command(formal_tool,'--metrics',view/'n11-run-metrics.json',
                '--config',Path(config).resolve(),'--release',Path(release).resolve(),
                '--output',view/formal_report)
    unchanged=all(hashlib.sha256((source/name).read_bytes()).hexdigest()==h
                  for name,h in originals.items())
    if not unchanged:raise RuntimeError('source archive changed during evaluation')
    report={'schema':'n13-derived-view/v1','source':str(source),'view':str(view),
            'errors':errors,'source_existing_derived_reports_unchanged':unchanged,
            'source_derived_report_sha256':originals,'runtime_control_effect':False}
    (view/'n13-evaluation-view.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path)
    p.add_argument('--output-root',type=Path,required=True)
    p.add_argument('--config',type=Path,default=ROOT/'config/acceptance_n13.json')
    p.add_argument('--release',type=Path,default=ROOT/'docs/protocols/n13-staggered-obstacles.json')
    a=p.parse_args();print(json.dumps(prepare(a.source,a.output_root,a.config,a.release)))
