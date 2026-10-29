"""N14 scene binding for the shared read-only functional acceptance evaluator."""
import hashlib
import json
from pathlib import Path
from tools.debug_truth.evaluate_n14_route import evaluate


def scene_navigation(config,run_dir):
    run=Path(run_dir);root=Path(__file__).resolve().parents[1];policy=config['scene_protocol']
    row={'id':'n14_scene_navigation','status':'INSUFFICIENT',
         'evidence_status':'direct_navigation_contract','runtime_control_effect':False}
    try:world=json.loads((run/'world.json').read_text())
    except (OSError,ValueError):world={}
    evaluator=root/'tools/debug_truth/evaluate_n14_route.py'
    checks={'released_protocol':policy.get('status')=='ready',
            'evaluator_matches_release':policy.get('evaluator_sha256')==hashlib.sha256(evaluator.read_bytes()).hexdigest(),
            'world_matches_release':bool(policy.get('world_geometry_sha256')) and world.get('project_geometry_sha256')==policy.get('world_geometry_sha256')}
    row['checks']=checks
    if not all(checks.values()):
        row['missing_evidence']=[k for k,v in checks.items() if not v];return row
    report=evaluate(run)
    row.update(status=report['status'],route=report)
    names=['flight.json','runtime-contract.json','arrival-evaluation.json','n11-static-map-observation.json',
           'n11-launch-record.json','vio_initialization.sdf','n10-tracking-clearance-relation.json',
           'planner-observation.json','world.json']
    row['input_sha256']={name:hashlib.sha256((run/name).read_bytes()).hexdigest() for name in names if (run/name).is_file()}
    if row['status']=='FAIL':row['direct_safety_failure']=True
    return row
