#!/usr/bin/env python3
"""Run the pinned loop backend in a separate namespace; never route it to control."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve(root, run_id, prefix, configuration='config/components/localization/loop_observer.json'):
    root, prefix = Path(root).resolve(), Path(prefix).resolve()
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}', run_id):
        raise ValueError('Invalid run id')
    run = root/'artifacts/runs'/run_id
    directory = run.parent/(run_id+'-stack')/'session'
    session = json.loads((directory/'session.json').read_text())
    epoch = session['epoch']
    if (not re.fullmatch('[0-9a-f]{32}', epoch)
            or session['namespace'] != '/vins_raw/s_'+epoch):
        raise ValueError('Invalid immutable VINS session identity')
    for name, digest in session['files_sha256'].items():
        if Path(name).name != name or sha256(directory/name) != digest:
            raise ValueError('Session file hash mismatch')
    for path, key in [('simulation/models/d435i/model.sdf', 'model_sha256'),
                      ('config/components/localization/vins_sim.json', 'settings_sha256')]:
        if sha256(root/path) != session[key]:
            raise ValueError('Session differs from project calibration/settings')
    settings = json.loads((root/'config/components/localization/vins_sim.json').read_text())
    if (settings['imu'] != 1 or settings['num_of_cam'] != 2 or settings['estimate_extrinsic'] != 0
            or settings['load_previous_pose_graph'] != 0 or settings['save_image'] != 0):
        raise ValueError('Observer requires one fresh stereo-IMU session without saved images/graphs')
    cfg = (root/configuration).resolve()
    if not cfg.is_relative_to(root/'config/components/localization') or cfg.suffix != '.json':
        raise ValueError('Observer configuration must be a localization JSON source')
    limits = json.loads(cfg.read_text())
    if (limits.get('mode') != 'observation_only'
            or type(limits.get('queue_limit')) is not int or not 16 <= limits['queue_limit'] <= 256
            or type(limits.get('max_keyframes')) is not int or not 1 <= limits['max_keyframes'] <= 2000
            or type(limits.get('minimum_distance_m')) not in (int, float)
            or not math.isfinite(limits['minimum_distance_m']) or limits['minimum_distance_m'] <= 0):
        raise ValueError('Invalid observer mode/resource limits')
    executable = prefix/'lib/loop_fusion/loop_fusion_node'
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise FileNotFoundError('Build the real loop_fusion_node before starting')
    dependencies = root/'dependencies/sources.json'
    source = next(x for x in json.loads(dependencies.read_text())['sources'] if x['id'] == 'vins_fusion')
    resources = {}
    for name in ['brief_k10L6.bin', 'brief_pattern.yml']:
        installed = prefix/'share/loop_fusion/support_files'/name
        if sha256(installed) != source['patched_files_sha256']['support_files/'+name]:
            raise ValueError('Installed BRIEF resource hash mismatch')
        resources[name] = sha256(installed)
    namespace = '/loop_observer/s_'+epoch
    frame = 'loop_'+epoch+'_map'
    command = [str(executable), str(directory/'vins.yaml'), '--ros-args',
               '-r', '__ns:='+namespace, '-p', 'use_sim_time:=true', '-p', 'map_frame:='+frame]
    for name in ['odometry', 'keyframe_pose', 'keyframe_point', 'extrinsic']:
        command += ['-r', name+':='+session['namespace']+'/'+name]
    for name in ['queue_limit', 'max_keyframes', 'minimum_distance_m']:
        command += ['-p', name+':='+str(limits[name])]
    manifest = {'scope': __doc__, 'run_id': run_id, 'epoch': epoch,
                'namespace': namespace, 'map_frame': frame, 'command': command,
                'limits': limits, 'installed_resources_sha256': resources,
                'configuration_source': str(cfg.relative_to(root)),
                'executable_sha256': sha256(executable), 'session': session,
                'configuration_sha256': sha256(cfg), 'dependencies_sha256': sha256(dependencies),
                'control_or_tf_outputs': False,
                'qualification': 'Transport observation only; not loop accuracy or map reuse acceptance'}
    return run, command, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_id')
    parser.add_argument('--config', default='config/components/localization/loop_observer.json')
    args = parser.parse_args()
    from ament_index_python.packages import get_package_prefix
    root = Path(__file__).resolve().parents[1]
    run, command, manifest = resolve(root, args.run_id, get_package_prefix('loop_fusion'), args.config)
    # One observer per epoch: restarting must not silently appear to retain its graph.
    with (run/'.loop-observer-used').open('x') as marker:
        marker.write(manifest['epoch']+'\n')
    (run/'loop-observer-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (run/'loop-observer.pid').write_text(str(os.getpid())+'\n')
    os.execv(command[0], command)


if __name__ == '__main__':
    main()
