"""Derive the ideal, aligned rig calibration and fixed TF from its SDF source."""
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET


def calibration(model_path):
    path = Path(model_path)
    data = path.read_bytes()
    model = ET.fromstring(data).find('model')
    sensors = model.findall('link/sensor')
    digest = hashlib.sha256(data).hexdigest()
    result = {'model_sha256': digest, 'calibration_sha256': digest,
              'source_kind': 'simulation_sdf',
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
            'frame': sensor.findtext('gz_frame_id'),
            'image_frame': sensor.findtext('gz_frame_id'),
            'camera_info_frame': sensor.findtext('gz_frame_id'),
            'translation': pose[:3],
            'width': width, 'height': height,
            'K': [focal, 0, width/2, 0, focal, height/2, 0, 0, 1],
            'D': [0.0, 0.0, 0.0, 0.0, 0.0],
            'R_body_optical': [0, 0, 1, -1, 0, 0, 0, -1, 0]}
    if set(result['cameras']) != {'infra1', 'infra2', 'depth', 'color'} or 'imu' not in result:
        raise ValueError('Expected exactly the stereo, aligned depth, color and IMU rig')
    left, right = (result['cameras'][key]['translation'] for key in ['infra1', 'infra2'])
    result['stereo_baseline_m'] = math.dist(left, right)
    return result


def _det3(rotation):
    a, b, c, d, e, f, g, h, i = rotation
    return a*(e*i-f*h) - b*(d*i-f*g) + c*(d*h-e*g)


def _hardware_rig(path):
    data = path.read_bytes()
    config = json.loads(data)
    if config.get('schema_version') != 1:
        raise ValueError('Unsupported hardware rig schema_version')
    body_frame = config.get('body_frame')
    imu = config.get('imu')
    cameras = config.get('cameras')
    if not isinstance(body_frame, str) or not body_frame or not isinstance(imu, dict):
        raise ValueError('Hardware rig requires a body_frame and IMU object')
    if not isinstance(cameras, dict) or not {'infra1', 'infra2', 'depth'} <= cameras.keys():
        raise ValueError('Hardware rig requires infra1, infra2 and depth cameras')
    if imu.get('frame') != body_frame:
        raise ValueError('Hardware rig body_frame must match its IMU reference frame')

    result_cameras = {}
    for name, camera in cameras.items():
        if not isinstance(camera, dict):
            raise ValueError(f'{name} camera must be an object')
        width, height = camera.get('width'), camera.get('height')
        if type(width) is not int or type(height) is not int or width <= 0 or height <= 0:
            raise ValueError(f'{name} camera dimensions must be positive integers')
        if any(not isinstance(camera.get(key), str) or not camera[key]
               for key in ('frame', 'image_frame', 'camera_info_frame')):
            raise ValueError(f'{name} camera requires optical, image and CameraInfo frame ids')
        for key, size in (('K', 9), ('D', 5), ('R', 9), ('P', 12), ('T_imu_optical', 16)):
            values = camera.get(key)
            if (not isinstance(values, list) or len(values) != size
                    or not all(type(value) in (int, float) and math.isfinite(value)
                               for value in values)):
                raise ValueError(f'{name} camera {key} must contain {size} finite numbers')
        if camera['K'][0] <= 0 or camera['K'][4] <= 0:
            raise ValueError(f'{name} camera focal lengths must be positive')
        matrix = camera['T_imu_optical']
        if any(abs(actual - expected) > 1e-9
               for actual, expected in zip(matrix[12:], [0.0, 0.0, 0.0, 1.0])):
            raise ValueError(f'{name} camera transform must be homogeneous')
        rotation = [matrix[row*4+column] for row in range(3) for column in range(3)]
        for row in range(3):
            for column in range(3):
                dot = sum(rotation[row*3+axis]*rotation[column*3+axis]
                          for axis in range(3))
                if abs(dot - (1.0 if row == column else 0.0)) > 2e-3:
                    raise ValueError(f'{name} camera transform rotation is not orthonormal')
        if abs(_det3(rotation) - 1.0) > 2e-3:
            raise ValueError(f'{name} camera transform rotation must have determinant +1')
        result_cameras[name] = {
            **camera,
            'translation': [matrix[3], matrix[7], matrix[11]],
            'R_body_optical': rotation,
        }

    baseline = math.dist(result_cameras['infra1']['translation'],
                         result_cameras['infra2']['translation'])
    declared = config.get('stereo_baseline_m')
    if (type(declared) not in (int, float) or not math.isfinite(declared)
            or declared <= 0 or abs(baseline - declared) > 1e-6):
        raise ValueError('Hardware rig stereo baseline disagrees with camera transforms')
    right = result_cameras['infra2']
    projected_baseline = -right['P'][3] / right['K'][0]
    camera_info_baseline = config.get('stereo_baseline_camera_info_m')
    if (type(camera_info_baseline) not in (int, float)
            or abs(projected_baseline - camera_info_baseline) > 1e-8
            or abs(projected_baseline - baseline) > 1e-6):
        raise ValueError('Hardware rig stereo baseline disagrees with right CameraInfo projection')
    streams = config.get('streams', {})
    depth_stream = streams.get('depth', {})
    if (depth_stream.get('output_encoding') != '32FC1'
            or depth_stream.get('output_unit') != 'metres'
            or type(depth_stream.get('metres_per_input_unit')) not in (int, float)
            or depth_stream['metres_per_input_unit'] <= 0):
        raise ValueError('Hardware rig depth output must be metric 32FC1')
    mount = config.get('airframe_mount')
    if not isinstance(mount, dict):
        raise ValueError('Hardware rig requires an airframe_mount status')
    if mount.get('status') == 'UNMEASURED':
        if mount.get('T_airframe_imu') is not None or mount.get('control_usable') is not False:
            raise ValueError('Unmeasured hardware airframe mount must stay unavailable to control')
    elif mount.get('status') == 'MEASURED':
        if mount.get('T_airframe_imu') is None or mount.get('control_usable') is not True:
            raise ValueError('Measured hardware airframe mount must provide a control transform')
    else:
        raise ValueError('Hardware airframe_mount status must be MEASURED or UNMEASURED')

    digest = hashlib.sha256(data).hexdigest()
    return {
        'calibration_sha256': digest,
        'source_sha256': digest,
        'source_kind': 'hardware_json',
        'qualification': config.get('status', 'UNQUALIFIED'),
        'body_frame': body_frame,
        'imu': {**imu, 'translation': [0.0, 0.0, 0.0]},
        'cameras': result_cameras,
        'streams': streams,
        'stereo_baseline_m': baseline,
        'rgb_enabled': bool(streams.get('color', {}).get('enabled', False)),
        'airframe_mount': mount,
    }


def load_rig(path):
    """Read either the real hardware JSON rig or the existing simulation SDF."""
    path = Path(path)
    if path.suffix.lower() == '.json':
        return _hardware_rig(path)
    return calibration(path)


def load_session_rig(project_root, session, rig_config=None):
    """Resolve and hash-check the rig identity recorded by a VINS session."""
    root = Path(project_root).resolve()
    recorded = session.get('rig_config')
    if rig_config and recorded and Path(rig_config).as_posix() != recorded:
        raise ValueError('Explicit rig config differs from the VINS session')
    relative = recorded or rig_config or 'simulation/models/d435i/model.sdf'
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('Session rig path must be project-relative')
    path = root / path
    if root not in path.parents:
        raise ValueError('Session rig path must stay inside the project root')
    rig = load_rig(path)
    expected = session.get('rig_sha256', session.get('model_sha256'))
    if expected and rig['calibration_sha256'] != expected:
        raise ValueError('Session rig hash mismatch')
    if session.get('calibration_id') and rig['calibration_sha256'] != session['calibration_id']:
        raise ValueError('Session calibration identity mismatch')
    return rig


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
    joint_pose = joint.find('pose')
    if joint_pose.get('relative_to') != 'base_link':
        raise ValueError('d435i_mount pose must be expressed relative to base_link')
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
    include_pose_element = include.find('pose')
    if include_pose_element.get('relative_to') != 'base_link':
        raise ValueError('D435i include pose must be expressed relative to base_link')
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
