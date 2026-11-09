#!/usr/bin/env python3
"""Resolve the small set of canonical ground hardware runtime profiles."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys


def read_device_identity(root):
    rig_path = Path(root) / 'config/hardware/rig.json'
    rig = json.loads(rig_path.read_text())
    identity = rig.get('identity', {})
    result = {
        'api_serial': identity.get('api_serial'),
        'asic_usb_serial': identity.get('asic_usb_serial'),
    }
    if any(not isinstance(value, str) or not value.isdigit()
           for value in result.values()):
        raise ValueError('rig.json must define numeric API and ASIC/USB serial identities')
    return result


def hardware_config_hashes(root):
    root=Path(root)
    config=root/'config/hardware'
    return {path.relative_to(root).as_posix():hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(config.glob('*')) if path.is_file()}


def read_realsense_deployment(root):
    path=Path(root)/'config/hardware/realsense_sdk.json'
    profile=json.loads(path.read_text())
    deployment=profile.get('deployment',{})
    required=('ros_overlay','wrapper_source_dir','wrapper_install_prefix',
              'wrapper_version','wrapper_source_commit','wrapper_library_sha256',
              'sdk_source_dir','hid_sensitivity_patch','hid_sensitivity_patch_sha256')
    if profile.get('schema')!=1 or any(not deployment.get(key) for key in required):
        raise ValueError('RealSense deployment profile is incomplete')
    patch=Path(root)/profile['clock_patch']
    if hashlib.sha256(patch.read_bytes()).hexdigest()!=profile['clock_patch_sha256']:
        raise ValueError('Project RealSense patch hash does not match profile')
    return {'overlay':deployment['ros_overlay'],
            'wrapper_source_dir':deployment['wrapper_source_dir'],
            'wrapper_prefix':deployment['wrapper_install_prefix'],
            'wrapper_version':deployment['wrapper_version'],
            'wrapper_commit':deployment['wrapper_source_commit'],
            'wrapper_sha256':deployment['wrapper_library_sha256'],
            'sdk_source_dir':deployment['sdk_source_dir'],
            'sdk_patch':deployment['hid_sensitivity_patch'],
            'sdk_patch_sha256':deployment['hid_sensitivity_patch_sha256'],
            'sdk_lib':str(Path(root)/profile['library_dir']),
            'sdk_version':profile['version'],
            'sdk_commit':profile['base_commit'],
            'sdk_sha256':profile['library_sha256']}


def parse_realsense_devices(output):
    """Parse identity fields within each `rs-enumerate-devices -c` device block."""
    records=[]
    current=None
    fields={'Serial Number':'api_serial',
            'Asic Serial Number':'asic_usb_serial',
            'Physical Port':'physical_port'}
    for line in output.splitlines():
        if line.strip()=='Device info:':
            if current is not None:
                records.append(current)
            current={}
            continue
        if current is None or ':' not in line:
            continue
        key,value=line.strip().split(':',1)
        name=fields.get(key.strip())
        if name is None:
            continue
        value=value.strip()
        if name in current:
            current[name]=None
        else:
            current[name]=value
    if current is not None:
        records.append(current)
    return records


def match_observed_device_identity(expected, enumeration):
    matches=[record for record in parse_realsense_devices(enumeration)
             if record.get('api_serial')==expected['api_serial']
             and record.get('asic_usb_serial')==expected['asic_usb_serial']]
    if len(matches)!=1:
        raise ValueError('Enumeration must contain exactly one device record matching rig API and ASIC serials')
    return matches[0]


def selected_install_base(root):
    root=Path(root)
    configured=os.environ.get('HW_HARDWARE_INSTALL')
    if configured:
        return Path(configured).resolve()
    active=root/'hardware_install'
    if active.exists() or active.is_symlink():
        return active.resolve(strict=False)
    return (root/'install').resolve()


def session_preflighted(root, session_id, install_base):
    try:
        state=json.loads((Path(root)/'.runtime/hardware-session.json').read_text())
    except (OSError,ValueError):
        return False
    if not (state.get('operation','session')=='session'
            and state.get('session_id')==session_id
            and state.get('phase') in ('starting','running','cleanup_required')
            and Path(state.get('install_base','')).resolve()==Path(install_base).resolve()):
        return False
    try:
        return (state.get('device_identity')==read_device_identity(root)
                and state.get('config_sha256')==hardware_config_hashes(root))
    except (OSError,ValueError,TypeError):
        return False


def resolve_depth_output_profile(root, layer):
    root = Path(root)
    if layer in ('sensors', 'perception'):
        relative = 'config/hardware/sensor_runtime.json'
    elif layer == 'map':
        relative = 'config/hardware/mapping.json'
    elif layer in ('plan', 'ev', 'control', 'full-load'):
        relative = 'config/hardware/planner.json'
    else:
        raise ValueError('Unknown hardware layer: '+str(layer))
    profile = json.loads((root/relative).read_text())
    rate = profile.get('depth_output_rate_hz')
    if isinstance(rate, bool) or not isinstance(rate, (int, float)) or not math.isfinite(rate) or rate < 0:
        raise ValueError('Invalid depth_output_rate_hz in '+relative)
    return {'path':relative, 'rate_hz':float(rate)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--device-identity', action='store_true')
    group.add_argument('--depth-rate-layer', choices=(
        'sensors','perception','map','plan','ev','control','full-load'))
    group.add_argument('--install-base', action='store_true')
    group.add_argument('--session-preflighted', metavar='SESSION_ID')
    group.add_argument('--match-device-identity', action='store_true')
    group.add_argument('--realsense-value', choices=(
        'overlay','wrapper_source_dir','wrapper_prefix','wrapper_version',
        'wrapper_commit','wrapper_sha256','sdk_source_dir','sdk_patch',
        'sdk_patch_sha256','sdk_lib','sdk_version','sdk_commit','sdk_sha256'))
    parser.add_argument('--install-path')
    parser.add_argument('--api-serial')
    parser.add_argument('--asic-usb-serial')
    args = parser.parse_args()
    if args.install_base:
        print(selected_install_base(args.root))
    elif args.session_preflighted:
        if not session_preflighted(args.root,args.session_preflighted,
                                   args.install_path or os.environ.get('HW_HARDWARE_INSTALL','')):
            raise SystemExit('Session does not own this preflighted hardware install')
    elif args.match_device_identity:
        if not args.api_serial or not args.asic_usb_serial:
            raise SystemExit('--match-device-identity requires both expected serials')
        observed=match_observed_device_identity(
            {'api_serial':args.api_serial,'asic_usb_serial':args.asic_usb_serial},
            sys.stdin.read())
        print(observed['api_serial'])
        print(observed['asic_usb_serial'])
        print(observed.get('physical_port',''))
    elif args.realsense_value:
        print(read_realsense_deployment(args.root)[args.realsense_value])
    elif args.device_identity:
        identity = read_device_identity(args.root)
        print(identity['api_serial'])
        print(identity['asic_usb_serial'])
    else:
        print(resolve_depth_output_profile(args.root,args.depth_rate_layer)['rate_hz'])


if __name__ == '__main__':
    main()
