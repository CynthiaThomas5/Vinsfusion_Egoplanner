#!/usr/bin/env python3
"""Reconstruct pinned dependencies and patches from dependencies/sources.json."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fetch(root, source, target):
    target = Path(target).resolve()
    if target.exists():
        raise FileExistsError(f'{target} already exists; refusing to overwrite')
    patches = source.get('patches', [])
    if set(patches) != set(source.get('patch_sha256', {})):
        raise ValueError('Patch list and hash manifest disagree: ' + source['id'])
    for rel in patches:
        if digest(root / rel) != source['patch_sha256'][rel]:
            raise ValueError('Patch hash mismatch: ' + rel)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.' + target.name + '-', dir=target.parent) as tmp:
        upstream = Path(tmp) / 'upstream'
        subprocess.run(['git', 'clone', '--no-checkout', source['url'], str(upstream)], check=True)
        subprocess.run(['git', '-C', str(upstream), 'checkout', '--detach', source['target_revision']], check=True)
        revision = subprocess.check_output(['git', '-C', str(upstream), 'rev-parse', 'HEAD'], text=True).strip()
        if revision != source['target_revision']:
            raise ValueError('Source revision mismatch: ' + source['id'])
        license_file = source.get('license_file', 'LICENSE')
        if source.get('license_sha256') and digest(upstream / license_file) != source['license_sha256']:
            raise ValueError('License hash mismatch: ' + source['id'])
        if source.get('recursive_submodules'):
            subprocess.run(['git', '-C', str(upstream), 'submodule', 'update', '--init', '--recursive'], check=True)
        for rel in patches:
            context = source.get('patch_contexts', {}).get(rel, {'working_directory': '.', 'strip': 1})
            cmd = ['patch', '--batch', '--forward', f"-p{context['strip']}", '-d', str(upstream / context['working_directory']), '-i', str(root / rel)]
            if context.get('binary'):
                cmd.append('--binary')
            subprocess.run(cmd + ['--dry-run'], check=True)
            subprocess.run(cmd, check=True)
        for rel, expected in source.get('patched_files_sha256', {}).items():
            if digest(upstream / rel) != expected:
                raise ValueError('Patched source hash mismatch: ' + rel)
        packages = source.get('package_roots')
        if packages:
            result = Path(tmp) / 'result'
            result.mkdir()
            shutil.copyfile(upstream / license_file, result / license_file)
            for src, dst in packages.items():
                shutil.copytree(upstream / src, result / dst)
            result.rename(target)
        else:
            upstream.rename(target)
    return {'id': source['id'], 'revision': revision, 'target': str(target),
            'patch_sha256': source.get('patch_sha256', {})}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', action='append', help='dependency id; repeat to select several')
    parser.add_argument('--target', type=Path, help='fresh target, allowed with exactly one --source')
    args = parser.parse_args()
    sources = [s for s in json.loads((ROOT / 'dependencies/sources.json').read_text())['sources']
               if s.get('target_revision') and s.get('url') and s.get('target')]
    selected = args.source or [s['id'] for s in sources]
    if set(selected) - {s['id'] for s in sources}:
        parser.error('Unknown source id')
    if args.target and len(selected) != 1:
        parser.error('--target requires exactly one --source')
    for source in sources:
        if source['id'] not in selected:
            continue
        target = args.target or ROOT / source['target']
        if not target.is_absolute():
            target = ROOT / target
        print(json.dumps(fetch(ROOT, source, target)), flush=True)


if __name__ == '__main__':
    main()
