#!/usr/bin/env python3
"""Resolve geometry, spawn and mission together from one project scene registry."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def resolve_scene(root, name=None):
    root = Path(root).resolve()
    source = root/'config/components/simulation/scenes.json'
    registry = json.loads(source.read_text())
    if registry['schema'] != 1:
        raise ValueError('unsupported scene registry')
    name = name or registry['default_scene']
    if name not in registry['scenes']:
        raise ValueError('unknown scene: '+str(name))
    result = dict(registry['scenes'][name])
    for key in ('geometry', 'spawn_config', 'goal_profile'):
        rel = result[key]
        if not rel and key == 'spawn_config':
            continue
        if not isinstance(rel, str) or not rel or Path(rel).is_absolute():
            raise ValueError('scene paths must be project-relative')
        if not (root/rel).resolve().is_relative_to(root):
            raise ValueError('scene path escapes project root')
    result.update(scene=name, registry_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--project-root', type=Path, default=ROOT)
    p.add_argument('--scene', default='')
    p.add_argument('--field', choices=('scene','geometry','spawn_config','goal_profile'))
    args = p.parse_args()
    result = resolve_scene(args.project_root, args.scene)
    print(result[args.field] if args.field else json.dumps(result))
