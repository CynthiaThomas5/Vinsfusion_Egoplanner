#!/usr/bin/env python3
"""Generate a fresh VINS session configuration from the single SDF geometry source."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/own/uav_sim'))
from uav_sim.geometry import load_rig


DEFAULT_SIM_RIG = 'simulation/models/d435i/model.sdf'
DEFAULT_SIM_SETTINGS = 'config/components/localization/vins_sim.json'
DEFAULT_HARDWARE_SETTINGS = 'config/components/localization/vins_hardware.json'


def _project_file(root, value):
    path = Path(value)
    if '..' in path.parts:
        raise ValueError('Rig and settings files must be inside the project root')
    path = path if path.is_absolute() else root / path
    if root not in path.parents:
        raise ValueError('Rig and settings files must be inside the project root')
    if not path.is_file():
        raise FileNotFoundError(path)
    return path, path.relative_to(root).as_posix()


def generate(root, output, epoch=None, rig_config=None, settings_config=None):
    root = Path(root).resolve()
    rig_config = rig_config or DEFAULT_SIM_RIG
    rig_path, rig_relative = _project_file(root, rig_config)
    rig = load_rig(rig_path)
    if settings_config is None:
        settings_config = (DEFAULT_HARDWARE_SETTINGS if rig_path.suffix.lower() == '.json'
                           else DEFAULT_SIM_SETTINGS)
    settings_path, settings_relative = _project_file(root, settings_config)
    settings = json.loads(settings_path.read_text())
    opencv_threads = settings.pop('opencv_threads', None)
    if rig['source_kind'] == 'hardware_json' and (type(opencv_threads) is not int
            or not 1 <= opencv_threads <= 4):
        raise ValueError('Hardware VINS requires explicit opencv_threads in [1,4]')
    if settings['imu'] != 1 or settings['num_of_cam'] != 2 or settings['estimate_extrinsic'] != 0:
        raise ValueError('This profile requires stereo + IMU with fixed rig extrinsics')
    if rig['source_kind'] == 'hardware_json':
        if settings.get('known_zero_gyro_bias') != 0:
            raise ValueError('Hardware VINS settings must not assume a known zero gyro bias')
        streams = rig['streams']
        imu_output = rig['imu']['correction_chain'][0]['output_topic']
        if (settings.get('imu_topic') != imu_output
                or settings.get('image0_topic') != streams['infra1']['image_topic']
                or settings.get('image1_topic') != streams['infra2']['image_topic']):
            raise ValueError('Hardware VINS topics must match the selected rig streams')
    if (rig['cameras']['infra1']['width'] != rig['cameras']['infra2']['width']
            or rig['cameras']['infra1']['height'] != rig['cameras']['infra2']['height']):
        raise ValueError('Stereo image sizes differ in the selected rig')
    if output.exists():
        raise FileExistsError(f'Refusing to overwrite session: {output}')
    epoch = epoch or uuid.uuid4().hex
    if not re.fullmatch(r'[0-9a-f]{32}', epoch):
        raise ValueError('epoch must be 32 lowercase hexadecimal characters')
    output.mkdir(parents=True)
    settings.update(output_path=str(output), pose_graph_save_path=str(output / 'pose_graph'),
                    cam0_calib='left.yaml', cam1_calib='right.yaml',
                    image_width=rig['cameras']['infra1']['width'], image_height=rig['cameras']['infra1']['height'],
                    world_frame_id=f'vins_{epoch}_world', body_frame_id=f'vins_{epoch}_imu',
                    camera_frame_id=f'vins_{epoch}_left_optical')
    rig_sha256 = hashlib.sha256(rig_path.read_bytes()).hexdigest()
    settings_sha256 = hashlib.sha256(settings_path.read_bytes()).hexdigest()
    text = (f'%YAML:1.0\n---\n'
            f'# calibration_rig_sha256: {rig_sha256}\n'
            f'# settings_sha256: {settings_sha256}\n'
            + ''.join(f'{key}: {json.dumps(value)}\n' for key,value in settings.items()))
    for index, (name, filename) in enumerate([('infra1','left.yaml'), ('infra2','right.yaml')]):
        cam = rig['cameras'][name]
        k = cam['K']
        distortion = cam.get('D', [0.0, 0.0, 0.0, 0.0])
        content = f'''%YAML:1.0
---
# calibration_rig_sha256: {rig_sha256}
model_type: PINHOLE
camera_name: {name}
image_width: {cam['width']}
image_height: {cam['height']}
distortion_parameters:
   k1: {distortion[0]}
   k2: {distortion[1]}
   p1: {distortion[2]}
   p2: {distortion[3]}
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
                'rig_config':rig_relative, 'rig_sha256':rig_sha256,
                'settings_config':settings_relative, 'settings_sha256':settings_sha256,
                'calibration_id':rig_sha256,
                'files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.glob('*.yaml')},
                'qualification':('PROVISIONAL hardware configuration; not runtime qualified'
                                 if rig['source_kind'] == 'hardware_json'
                                 else 'Generated ideal simulation configuration; not runtime qualified')}
    if rig['source_kind'] == 'hardware_json':
        health_relative = 'config/components/localization/health_hardware.json'
        health_path = root / health_relative
        manifest['runtime'] = {'opencv_threads': opencv_threads}
        manifest['health_config'] = health_relative
        manifest['health_sha256'] = hashlib.sha256(health_path.read_bytes()).hexdigest()
    if rig['source_kind'] == 'simulation_sdf':
        manifest['model_sha256'] = rig['model_sha256']
    (output/'session.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--rig-config', type=Path)
    parser.add_argument('--settings-config', type=Path)
    args = parser.parse_args()
    print(json.dumps(generate(ROOT, args.output.resolve(), rig_config=args.rig_config,
                              settings_config=args.settings_config)))
