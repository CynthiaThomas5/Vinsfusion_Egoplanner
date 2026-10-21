"""Derive the ideal, aligned rig calibration and fixed TF from its SDF source."""
import hashlib
import math
from pathlib import Path
import xml.etree.ElementTree as ET


def calibration(model_path):
    path = Path(model_path)
    model = ET.fromstring(path.read_bytes()).find('model')
    sensors = model.findall('link/sensor')
    result = {'model_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'body_frame': 'd435i_link', 'cameras': {}}
    for sensor in sensors:
        pose = [float(x) for x in sensor.findtext('pose').split()]
        if pose[3:] != [0.0, 0.0, 0.0]:
            raise ValueError('Only aligned camera/IMU mounts are supported by this calibration generator')
        if sensor.get('type') == 'imu':
            result['imu'] = {'frame': sensor.findtext('gz_frame_id'), 'translation': pose[:3]}
            continue
        camera = sensor.find('camera')
        width, height = (int(camera.findtext('image/' + key)) for key in ['width', 'height'])
        focal = width / (2 * math.tan(float(camera.findtext('horizontal_fov')) / 2))
        result['cameras'][sensor.get('name')] = {
            'frame': sensor.findtext('gz_frame_id'), 'translation': pose[:3],
            'width': width, 'height': height,
            'K': [focal, 0, width/2, 0, focal, height/2, 0, 0, 1],
            'R_body_optical': [0, 0, 1, -1, 0, 0, 0, -1, 0]}
    if set(result['cameras']) != {'infra1', 'infra2', 'depth', 'color'} or 'imu' not in result:
        raise ValueError('Expected exactly the stereo, aligned depth, color and IMU rig')
    left, right = (result['cameras'][key]['translation'] for key in ['infra1', 'infra2'])
    result['stereo_baseline_m'] = math.dist(left, right)
    return result


def robot_description(model_path):
    rig = calibration(model_path)
    robot = ET.Element('robot', name='d435i')
    ET.SubElement(robot, 'link', name=rig['body_frame'])
    for sensor in [rig['imu'], *rig['cameras'].values()]:
        frame = sensor['frame']
        ET.SubElement(robot, 'link', name=frame)
        joint = ET.SubElement(robot, 'joint', name=frame + '_joint', type='fixed')
        ET.SubElement(joint, 'parent', link=rig['body_frame'])
        ET.SubElement(joint, 'child', link=frame)
        ET.SubElement(joint, 'origin', xyz=' '.join(map(str, sensor['translation'])),
                      rpy='0 0 0' if sensor is rig['imu'] else f'{-math.pi/2} 0 {-math.pi/2}')
    return ET.tostring(robot, encoding='unicode')


def px4_sensor_mount(model_path):
    """Derive the PX4 FRD lever arm from the x500-with-D435i source SDF."""
    path = Path(model_path)
    root = ET.fromstring(path.read_bytes())
    model = root.find('model')
    if model is None or model.get('name') != 'x500_d435i':
        raise ValueError('Expected the x500_d435i model SDF')
    joint = model.find("joint[@name='d435i_mount']")
    if joint is None or joint.get('type') != 'fixed':
        raise ValueError('Expected the fixed d435i_mount joint')
    if (joint.findtext('parent'), joint.findtext('child')) != (
            'base_link', 'd435i_link'):
        raise ValueError('D435i mount must connect PX4 base_link to d435i_link')
    pose_text = joint.findtext('pose')
    if not pose_text:
        raise ValueError('d435i_mount must define its pose relative to base_link')
    pose = tuple(float(value) for value in pose_text.split())
    if len(pose) != 6 or not all(math.isfinite(value) for value in pose):
        raise ValueError('d435i_mount pose must contain six finite values')
    x, y, z, roll, pitch, yaw = pose
    if any(abs(value) > 1e-9 for value in (roll, pitch, yaw)):
        raise ValueError('PX4 lever arm derivation currently requires aligned body axes')

    include = next((item for item in model.findall('include')
                    if item.findtext('uri') == 'model://d435i'), None)
    if include is None or not include.findtext('pose'):
        raise ValueError('Expected a posed model://d435i include')
    include_pose = tuple(float(value) for value in include.findtext('pose').split())
    if len(include_pose) != 6 or any(
            abs(actual - expected) > 1e-9
            for actual, expected in zip(include_pose, pose)):
        raise ValueError('D435i include pose and mount joint pose disagree')

    # SDF model coordinates use FLU; PX4's base_link is FRD.
    return {
        'model_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'parent_frame': 'base_link',
        'sensor_frame': 'd435i_imu',
        'translation_frd_m': [x, -y, -z],
    }
