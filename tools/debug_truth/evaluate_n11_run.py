#!/usr/bin/env python3
"""Build a transparent N11 reanalysis view and invoke frozen numerical methods."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import shutil
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/debug_truth')]
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('run',type=Path);p.add_argument('--output-root',type=Path,required=True);p.add_argument('--config',type=Path,default=ROOT/'config/acceptance.json');a=p.parse_args();a.config=a.config.resolve()
 source=a.run.resolve();view=a.output_root.resolve()/source.name;view.mkdir(parents=True,exist_ok=False)
 for path in source.iterdir():
  if path.name=='n11-static-map': shutil.copytree(path,view/path.name,copy_function=shutil.copyfile)
  else: (view/path.name).symlink_to(path,target_is_directory=path.is_dir())
 stack=source.parent/(source.name+'-stack')
 if stack.exists(): (view.parent/stack.name).symlink_to(stack,target_is_directory=True)
 obs=load(source/'n11-static-map-observation.json');identity=obs['run_identity']
 alias={'schema':'n11-static-observer-compatibility-view/v1','source_report':'n11-static-map-observation.json','source_sha256':sha(source/'n11-static-map-observation.json'),
 'run_id':source.name,'runtime_contract_baseline_sha256':identity['runtime_contract_sha256'],
 'goal_id':identity['goal_id'],'epoch':identity['epoch'],'map_id_at_goal':identity['map_id'],
 'run_identity':identity,'obstacle':{},'gazebo_create':{'acknowledged':False},'world_mutation_commands':[]}
 (view/'n10-live-obstacle-observation.json').write_text(json.dumps(alias,indent=2)+'\n')
 (view/'n10-dynamic-clearance-world.sdf').symlink_to(source/'vio_initialization.sdf')
 errors=[]
 def command(tool,*args):
  logfile=view/(Path(tool).stem+'.log')
  with logfile.open('w') as out:
   result=subprocess.run([sys.executable,str(ROOT/tool),str(view),*map(str,args)],cwd=ROOT,stdout=out,stderr=subprocess.STDOUT)
  if result.returncode: errors.append({'tool':tool,'exit_code':result.returncode,'log':str(logfile)})
 command('tools/debug_truth/evaluate_arrival.py','--acceptance-config',a.config)
 if (view/'arrival-evaluation.json').is_file(): (view/'arrival-evaluation-simtime-v2.json').write_bytes((view/'arrival-evaluation.json').read_bytes())
 command('tools/debug_truth/evaluate_odometry.py')
 command('tools/debug_truth/evaluate_n10_vins_velocity.py')
 try:
  from n09_contact_evaluation import evaluate_contacts
  flight=load(view/'flight.json')
  phases=[json.loads(line) for line in (view/'bridge-alignment-timeline.jsonl').read_text().splitlines() if line.strip()]
  contacts=evaluate_contacts(load(view/'n09-contact-observation.json'),load(view/'n09-contact-model-manifest.json'),phases,int(flight['goal']['source_ns']))
  (view/'vehicle-contact-evaluation.json').write_text(json.dumps(contacts,indent=2)+'\n')
 except Exception as exc:errors.append({'tool':'contact_evaluation','error':repr(exc)})
 command('tools/debug_truth/evaluate_n10_clearance.py','--world-sdf',view/'vio_initialization.sdf')
 command('tools/debug_truth/evaluate_n10_interval_clearance_bound.py','--world-sdf',view/'vio_initialization.sdf','--vehicle-model',view/'n10-source-x500-model.sdf')
 command('tools/debug_truth/evaluate_n10_tracking_clearance.py','--output',view/'n10-tracking-clearance-relation.json')
 command('tools/debug_truth/evaluate_n11_static_map.py','--config',a.config,'--output',view/'n11-static-map-evaluation.json')
 from evaluate_n10_cross_run_calibration import evaluate_run
 try:
  metrics=evaluate_run(view)
  (view/'n11-run-metrics.json').write_text(json.dumps({'schema':'n10-cross-run-calibration-pair/v1','classification':'one independent N11 run; no pooled samples','runs':[metrics]},indent=2,allow_nan=False)+'\n')
 except Exception as exc:errors.append({'tool':'cross_run.evaluate_run','error':repr(exc)})
 # Capacity is observed on this host, then bound to this run's resource record.
 template=load(ROOT/'artifacts/reanalysis/n10-20261028-460-component-geometry/n10-platform-capacity.json')
 mem_kib=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemTotal:')))
 capacity=template['platform'];capacity['memory_total_bytes']=mem_kib*1024;capacity['effective_memory_capacity_bytes']=mem_kib*1024
 import datetime
 template['observed_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 resource=source/'n10-resource-observation.json';report=load(resource)
 template['run_binding'].update(run_id=source.name,runtime_contract_sha256=load(source/'runtime-contract.json')['sha256'],resource_observation_sha256=sha(resource))
 (view/'n10-platform-capacity.json').write_text(json.dumps(template,indent=2)+'\n')
 if (view/'n11-run-metrics.json').is_file():
  argv=[sys.executable,str(ROOT/'tools/debug_truth/evaluate_n10_acceptance.py'),'--config',str(a.config),'--calibration-report',str(view/'n11-run-metrics.json'),'--run-dir',str(view),'--run-id',source.name,'--platform-capacity-report',str(view/'n10-platform-capacity.json'),'--output',str(view/'n10-acceptance-evaluation.json')]
  with (view/'common-acceptance.log').open('w') as out:
   result=subprocess.run(argv,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT)
  if result.returncode:errors.append({'tool':'common_acceptance','exit_code':result.returncode})
 (view/'n11-reanalysis-view.json').write_text(json.dumps({'source_run':str(source),'view':str(view),'aliases':{'n10-live-obstacle-observation.json':'actual static observer identity only; no injected obstacle claimed','n10-dynamic-clearance-world.sdf':'exact active static world'},'errors':errors,'evaluator_sha256':sha(__file__)},indent=2)+'\n')
 print(json.dumps({'view':str(view),'errors':errors}))
if __name__=='__main__':main()
