#!/usr/bin/env python3
"""Generate a fresh VINS session configuration from the single SDF geometry source."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/own/uav_sim'))
from uav_sim.geometry import calibration


def generate(root, output, epoch=None):
    rig = calibration(root / 'simulation/models/d435i/model.sdf')
    settings_path = root / 'config/components/localization/vins_sim.json'
    settings = json.loads(settings_path.read_text())
    if settings['imu'] != 1 or settings['num_of_cam'] != 2 or settings['estimate_extrinsic'] != 0:
        raise ValueError('This profile requires stereo + IMU with fixed model extrinsics')
    if output.exists():
        raise FileExistsError(f'Refusing to overwrite session: {output}')
    output.mkdir(parents=True)
    epoch = epoch or uuid.uuid4().hex
    settings.update(output_path=str(output), pose_graph_save_path=str(output / 'pose_graph'),
                    cam0_calib='left.yaml', cam1_calib='right.yaml',
                    image_width=rig['cameras']['infra1']['width'], image_height=rig['cameras']['infra1']['height'],
                    world_frame_id=f'vins_{epoch}_world', body_frame_id=f'vins_{epoch}_imu',
                    camera_frame_id=f'vins_{epoch}_left_optical')
    text = '%YAML:1.0\n---\n' + ''.join(f'{key}: {json.dumps(value)}\n' for key,value in settings.items())
    for index, (name, filename) in enumerate([('infra1','left.yaml'), ('infra2','right.yaml')]):
        cam = rig['cameras'][name]
        k = cam['K']
        content = f'''%YAML:1.0
---
model_type: PINHOLE
camera_name: {name}
image_width: {cam['width']}
image_height: {cam['height']}
distortion_parameters:
   k1: 0.0
   k2: 0.0
   p1: 0.0
   p2: 0.0
projection_parameters:
   fx: {k[0]}
   fy: {k[4]}
   cx: {k[2]}
   cy: {k[5]}
'''
        (output / filename).write_text(content)
        rotation = cam['R_body_optical']
        translation = [a-b for a,b in zip(cam['translation'], rig['imu']['translation'])]
        matrix = [value for row in range(3) for value in [*rotation[row*3:row*3+3], translation[row]]] + [0,0,0,1]
        text += f'body_T_cam{index}: !!opencv-matrix\n   rows: 4\n   cols: 4\n   dt: d\n   data: {json.dumps(matrix)}\n'
    (output/'vins.yaml').write_text(text)
    manifest = {'epoch':epoch, 'namespace':'/vins_raw/s_'+epoch,
                'model_sha256':rig['model_sha256'], 'settings_sha256':hashlib.sha256(settings_path.read_bytes()).hexdigest(),
                'files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob('*.yaml')},
                'qualification':'Generated ideal simulation configuration; not runtime qualified'}
    (output/'session.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(generate(ROOT, args.output.resolve())))
