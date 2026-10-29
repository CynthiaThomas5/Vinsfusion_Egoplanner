#!/usr/bin/env python3
"""Fingerprint the source/configuration and actual installed runtime used by a run."""
import argparse
import hashlib
import json
from pathlib import Path


def snapshot(root):
    root = Path(root).resolve()
    files = {}
    for folder in ['src/own', 'config', 'simulation']:
        for path in sorted((root / folder).rglob('*')):
            if path.is_file() and not any(p in ['__pycache__', 'local'] for p in path.relative_to(root).parts):
                files[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    for path in sorted((root / 'tools').rglob('*')):
        relative = path.relative_to(root)
        if (path.is_file() and path.suffix in {'.py', '.sh'}
                and not path.name.startswith('test_')
                and '__pycache__' not in relative.parts):
            files[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    for path in sorted((root / 'install').rglob('*')):
        if path.is_file() and (path.suffix == '.py' or '.so' in path.name or path.name in ['vins_node','loop_fusion_node','ego_planner_node','traj_server','navigation_supervisor','MicroXRCEAgent']):
            files[path.relative_to(root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    runtime = json.loads((root / 'config/runtime.json').read_text())
    for rel in [runtime['px4_build'] + '/bin/px4','dependencies/sources.json']:
        files[rel] = hashlib.sha256((root / rel).read_bytes()).hexdigest()
    return {'files':files,'sha256':hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);args=p.parse_args()
    root=Path(__file__).resolve().parents[1];args.output.write_text(json.dumps(snapshot(root),indent=2)+'\n')
