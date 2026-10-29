#!/usr/bin/env python3
"""Independent derived view for N16: raw archive is never an output directory."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.debug_truth.evaluate_n16_run import evaluate_evidence
from tools.debug_truth.evaluate_n16_formal import assess


def prepare(source,output_root,config,release):
    source=Path(source).resolve();view=Path(output_root).resolve()/source.name;view.mkdir(parents=True,exist_ok=False)
    exclude={'arrival-evaluation.json','odometry-evaluation.json','odometry-errors.csv','n16-all-goal-arrivals.json',
             'n16-evidence.json','n16-formal-evaluation.json','n16-plot-manifest.json','n16-resource-queue-latency.png','n16-vio-and-actual-motion.png'}
    for p in source.iterdir():
        if p.name in exclude or p.name.endswith('.log'):continue
        if p.name=='n11-static-map':shutil.copytree(p,view/p.name)
        else:(view/p.name).symlink_to(p,target_is_directory=p.is_dir())
    stack=source.parent/(source.name+'-stack')
    if stack.exists() and not (view.parent/stack.name).exists():(view.parent/stack.name).symlink_to(stack,target_is_directory=True)
    obs=json.loads((source/'n11-static-map-observation.json').read_text());identity=obs['run_identity']
    alias=view/'n10-live-obstacle-observation.json'
    if alias.is_symlink():alias.unlink()
    alias.write_text(json.dumps({'schema':'n16-static-identity-compatibility/v1','run_identity':identity,
        'run_id':source.name,'runtime_contract_baseline_sha256':identity['runtime_contract_sha256'],
        'goal_id':identity['goal_id'],'epoch':identity['epoch'],'map_id_at_goal':identity['map_id'],
        'source_report':'n11-static-map-observation.json','world_mutation_commands':[]},indent=2)+'\n')
    errors=[]
    def command(tool):
        logfile=view/(Path(tool).stem+'.log')
        with logfile.open('w') as stream:r=subprocess.run([sys.executable,str(ROOT/tool),str(view)],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
        if r.returncode:errors.append({'tool':tool,'exit_code':r.returncode})
    command('tools/debug_truth/evaluate_odometry.py')
    evidence=evaluate_evidence(view,config);(view/'n16-evidence.json').write_text(json.dumps(evidence,indent=2,allow_nan=False)+'\n')
    command('tools/debug_truth/plot_n16_run.py')
    formal=assess(view,config,release)
    (view/'n16-formal-evaluation.json').write_text(json.dumps(formal,indent=2,allow_nan=False)+'\n')
    metadata={'schema':'n16-independent-evaluation-view/v1','source':str(source),'view':str(view),'errors':errors,
              'core_evidence_status':evidence['overall_status'],'raw_archive_outputs_written':False,
              'config_sha256':hashlib.sha256(Path(config).read_bytes()).hexdigest()}
    (view/'n16-evaluation-view.json').write_text(json.dumps(metadata,indent=2)+'\n');return metadata

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--output-root',type=Path,required=True)
    p.add_argument('--config',type=Path,default=ROOT/'config/acceptance_n16.json');p.add_argument('--release',type=Path,default=ROOT/'docs/protocols/n16-continuous-load.json');a=p.parse_args();print(json.dumps(prepare(a.source,a.output_root,a.config,a.release)))
