#!/usr/bin/env python3
"""Record/check source and installed artifact identity for a fresh Nano build."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

RUNTIME_PACKAGES=('uav_sensor_interface','uav_sim','uav_localization',
                  'uav_mapping','uav_navigation','uav_px4_bridge')

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def source_inventory(root):
    files=[]
    for base in (root/'src',root/'dependencies/patches'):
        if not base.exists():
            continue
        for path in sorted(base.rglob('*')):
            if not path.is_file() or any(part in ('.git','__pycache__','build','install')
                                          for part in path.parts):
                continue
            files.append((path.relative_to(root).as_posix(),digest(path)))
    for relative in ('dependencies/sources.json','config/hardware/realsense_sdk.json'):
        path=root/relative
        if path.is_file(): files.append((relative,digest(path)))
    aggregate=hashlib.sha256()
    for relative,sha in files:
        aggregate.update(relative.encode()+b'\0'+sha.encode()+b'\n')
    return {'file_count':len(files),'sha256':aggregate.hexdigest()}


def command_version(command):
    try:
        result=subprocess.run(command,check=True,text=True,stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)
        return result.stdout.splitlines()[0]
    except (OSError,subprocess.CalledProcessError,IndexError):
        return 'unavailable'


def toolchain_identity():
    return {'machine':platform.machine(),'ros_distro':os.environ.get('ROS_DISTRO',''),
            'compiler':command_version([os.environ.get('CXX','c++'),'--version']),
            'cmake':command_version(['cmake','--version']),
            'python':sys.version.split()[0]}


def dependency_identity():
    prefix=Path(os.environ.get(
        'HW_DEPENDENCY_PREFIX','/home/jetson/realsense_debug/vins_integration'))
    roots=(prefix/'ceres21/lib',
           prefix/'opencv42/usr/lib/aarch64-linux-gnu')
    libraries=[]
    for root in roots:
        if root.is_dir():
            patterns=('libceres.so*','libgflags.so*','libglog.so*','libopencv_*.so*')
            for pattern in patterns:
                for path in sorted(root.glob(pattern)):
                    if path.is_file():
                        libraries.append((str(path),digest(path)))
    return {'prefix':str(prefix.resolve()),'libraries':libraries}


def installed_artifacts(install):
    matches=list(install.rglob('d435i_depth_to_meters_cpp'))
    if len(matches)!=1 or not matches[0].is_file():
        raise FileNotFoundError('Expected one installed depth converter under '+str(install))
    binary=matches[0]
    artifacts={binary.relative_to(install).as_posix():digest(binary)}
    for package in RUNTIME_PACKAGES:
        for base in (install/'share'/package, install/'lib'/package):
            if not base.is_dir():
                continue
            for path in sorted(base.rglob('*')):
                if (path.is_file() and '__pycache__' not in path.parts
                        and path.suffix != '.pyc'):
                    artifacts[path.relative_to(install).as_posix()]=digest(path)
    for package in ('loop_fusion','ego_planner','vins'):
        for directory in install.rglob(package):
            if (not directory.is_dir() or directory.name != package
                    or directory.parent.name != 'lib'):
                continue
            for path in sorted(directory.rglob('*')):
                if (path.is_file() and
                        (os.access(path,os.X_OK) or '.so' in path.name or path.suffix=='.a')):
                    artifacts[path.relative_to(install).as_posix()]=digest(path)
    return dict(sorted(artifacts.items()))


def verify_installed_runtime_sources(root,install):
    mismatches=[]
    for package in RUNTIME_PACKAGES:
        source=root/'src/own'/package
        share=install/'share'/package
        for category in ('launch','config'):
            source_dir=source/category
            if not source_dir.is_dir():
                continue
            source_files={path.relative_to(source_dir).as_posix():path
                          for path in source_dir.rglob('*')
                          if path.is_file() and '__pycache__' not in path.parts
                          and path.suffix != '.pyc'}
            installed_dir=share/category
            installed_files={path.relative_to(installed_dir).as_posix():path
                             for path in installed_dir.rglob('*')
                             if path.is_file() and '__pycache__' not in path.parts
                             and path.suffix != '.pyc'} if installed_dir.is_dir() else {}
            if set(source_files)!=set(installed_files):
                mismatches.append(str(source_dir)+' file set differs from '+str(installed_dir))
            for relative,path in source_files.items():
                target=installed_files.get(relative)
                if target is None or path.read_bytes()!=target.read_bytes():
                    mismatches.append(str(path)+' differs from installed runtime file')
        source_xml=source/'package.xml'
        installed_xml=share/'package.xml'
        if source_xml.is_file() and (not installed_xml.is_file()
                                     or source_xml.read_bytes()!=installed_xml.read_bytes()):
            mismatches.append(str(source_xml)+' differs from installed package manifest')
    return mismatches


def expected(root,install):
    mismatches=verify_installed_runtime_sources(root,install)
    if mismatches:
        raise RuntimeError('Installed launch/config/package files differ from source: '
                           +'; '.join(mismatches))
    return {'schema':1,'source':source_inventory(root),
            'toolchain':toolchain_identity(),
            'dependencies':dependency_identity(),
            'installed_artifacts':installed_artifacts(install)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=('write','check'))
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--install-base',type=Path,required=True)
    args=parser.parse_args()
    root=args.root.resolve(); install=args.install_base.resolve()
    manifest_path=install/'.hardware-build.json'
    current=expected(root,install)
    if args.operation=='write':
        manifest_path.write_text(json.dumps(current,indent=2)+'\n')
        print('Wrote hardware build identity:',manifest_path)
        return
    saved=json.loads(manifest_path.read_text())
    if saved!=current:
        raise SystemExit('Hardware install identity mismatch; rebuild into a fresh install prefix')
    print('Hardware source, toolchain and sensor binary identities match')


if __name__=='__main__': main()
