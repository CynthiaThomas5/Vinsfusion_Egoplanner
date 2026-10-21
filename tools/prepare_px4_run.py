#!/usr/bin/env python3
"""Prepare a run-local PX4 tree without importing historical mutable state."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def prepare(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if not (source / 'bin/px4').is_file():
        raise ValueError('Source build must contain bin/px4')
    if destination.is_relative_to(source):
        raise ValueError('Run directory must be outside the source build')
    destination.mkdir(parents=True, exist_ok=False)
    for item in source.iterdir():
        target = destination / item.name
        if item.name in ('parameters.bson', 'parameters_backup.bson', 'dataman'):
            continue
        if item.name in ('log', 'eeprom'):
            target.mkdir()
        elif item.name in ('etc', 'rootfs'):
            shutil.copytree(item, target, symlinks=True)
        else:
            target.symlink_to(item, target_is_directory=item.is_dir())
    rootfs = destination / 'rootfs'
    rootfs.mkdir(exist_ok=True)
    etc = rootfs / 'etc'
    if etc.is_dir() and not etc.is_symlink():
        shutil.rmtree(etc)
    else:
        etc.unlink(missing_ok=True)
    etc.symlink_to('../etc')
    for name in ('parameters.bson', 'parameters_backup.bson', 'dataman'):
        (rootfs / name).unlink(missing_ok=True)
    for name in ('log', 'eeprom'):
        path = rootfs / name
        if path.is_symlink():
            path.unlink()
        elif path.exists():
            shutil.rmtree(path)
        path.mkdir()
    return {'source_build': str(source), 'run_build': str(destination),
            'px4_working_directory': str(destination),
            'source_mutable_sha256': {
                name: hashlib.sha256((source / name).read_bytes()).hexdigest()
                for name in ('parameters.bson', 'parameters_backup.bson', 'dataman')
                if (source / name).is_file()},
            'imported_parameter_or_mission_state': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-build', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    report = prepare(args.source_build, args.output)
    args.report.write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
