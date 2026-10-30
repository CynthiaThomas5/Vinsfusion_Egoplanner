#!/usr/bin/env python3
"""Resolve and record the effective PX4 Gazebo spawn pose."""

import argparse
import hashlib
import json
import math
from pathlib import Path
from scene_config import resolve_scene


def _validated_pose(values):
    if not isinstance(values, (list, tuple)) or len(values) != 6:
        raise ValueError('spawn pose must contain x,y,z,roll,pitch,yaw')
    pose = tuple(float(value) for value in values)
    if not all(math.isfinite(value) for value in pose):
        raise ValueError('spawn pose values must all be finite')
    return pose


def resolve_spawn_pose(project_root, config_path=None, scene_name=None):
    root = Path(project_root).resolve()
    if not config_path and scene_name:
        config_path = resolve_scene(root, scene_name)['spawn_config']
    if config_path:
        candidate = Path(config_path)
        if candidate.is_absolute():
            raise ValueError('spawn config path must be project-relative')
        source = (root / candidate).resolve()
        if not source.is_relative_to(root) or not source.is_file():
            raise ValueError('spawn config must be an existing project-relative file')
        document = json.loads(source.read_text(encoding='utf-8'))
        pose = _validated_pose(document.get('spawn_pose_xyzrpy'))
        return {
            'schema': 'sim-spawn-pose/v1',
            'source': str(source.relative_to(root)),
            'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'qualification': document.get('qualification', ''),
            'spawn_pose_xyzrpy': list(pose),
        }

    source = root / 'config/runtime.json'
    document = json.loads(source.read_text(encoding='utf-8'))
    try:
        values = [float(value.strip()) for value in document['spawn_pose'].split(',')]
    except (AttributeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError('config/runtime.json spawn_pose must be comma-separated numeric values') from exc
    pose = _validated_pose(values)
    return {
        'schema': 'sim-spawn-pose/v1',
        'source': 'config/runtime.json',
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'qualification': 'Default project spawn pose.',
        'spawn_pose_xyzrpy': list(pose),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-root', default='.')
    parser.add_argument('--config', default='')
    parser.add_argument('--report', required=True)
    parser.add_argument('--scene', default='')
    args = parser.parse_args()
    record = resolve_spawn_pose(args.project_root, args.config or None, args.scene or None)
    report = Path(args.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(record, indent=2, allow_nan=False) + '\n',
                      encoding='utf-8')
    print(','.join(format(value, '.12g')
                   for value in record['spawn_pose_xyzrpy']))


if __name__ == '__main__':
    main()
