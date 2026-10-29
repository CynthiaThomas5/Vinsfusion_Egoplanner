"""Read-only Gazebo-model-origin to D435i IMU conversion for offline evaluators.

OdometryPublisher's robot_base_frame labels the message; it does not select a
link. Only the fixed, identity-checked model geometry below selects the point.
Raw archives and their source stamps are never changed.
"""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'gazebo-model-to-imu-reference/v1'
MODEL = 'simulation/models/x500_d435i/model.sdf'
CAMERA = 'simulation/models/d435i/model.sdf'
BASE = 'external/PX4-Autopilot/Tools/simulation/gz/models/x500_base/model.sdf'


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _pose(element):
    values = np.asarray([float(x) for x in (element.text or '').split()], dtype=float)
    if values.shape != (6,) or not np.isfinite(values).all():
        raise ValueError('invalid_reference_pose')
    # Current single-camera model has aligned rigid axes. Fail on a new model
    # rather than silently ignore a nonzero mount/link rotation.
    if np.any(np.abs(values[3:]) > 1e-12):
        raise ValueError('rotated_reference_model_not_supported')
    return values[:3]


def model_to_imu_contract(run, root=ROOT):
    run, root = Path(run), Path(root)
    runtime = json.loads((run / 'runtime-contract.json').read_text())
    files = runtime.get('files', {})
    candidates = (run / 'n10-source-x500-model.sdf', root / MODEL)
    model = next((p for p in candidates if p.is_file() and sha256(p) == files.get(MODEL)), None)
    if model is None:
        raise ValueError('frozen_truth_model_source_missing_or_hash_mismatch')
    camera, base = root / CAMERA, root / BASE
    if sha256(camera) != files.get(CAMERA):
        raise ValueError('truth_camera_source_hash_mismatch')
    contact = json.loads((run / 'n09-contact-model-manifest.json').read_text())
    if sha256(base) != contact.get('source_sha256', {}).get(BASE):
        raise ValueError('truth_base_model_not_bound_to_run')
    wrapper = ET.parse(model).getroot().find('model')
    plugin = wrapper.find("plugin[@name='gz::sim::systems::OdometryPublisher']")
    if plugin is None or plugin.findtext('dimensions') != '3':
        raise ValueError('unsupported_truth_publisher')
    if plugin.find('xyz_offset') is not None or plugin.find('rpy_offset') is not None:
        raise ValueError('truth_publisher_offset_requires_explicit_conversion')
    if float(plugin.findtext('gaussian_noise', '0')) != 0:
        raise ValueError('noisy_truth_not_supported')
    base_node = ET.parse(base).getroot().find('model')
    base_position = _pose(base_node.find('pose'))
    base_link = base_node.find("link[@name='base_link']")
    if base_link.find('pose') is not None:
        base_position += _pose(base_link.find('pose'))
    mount = wrapper.find("joint[@name='d435i_mount']/pose")
    if mount is None or mount.get('relative_to') != 'base_link':
        raise ValueError('missing_base_relative_imu_mount')
    include = wrapper.find("include[uri='model://d435i']/pose")
    if include is None or include.get('relative_to') != 'base_link':
        raise ValueError('missing_camera_include_pose')
    mount_position = _pose(mount)
    if not np.allclose(mount_position, _pose(include), atol=1e-12, rtol=0):
        raise ValueError('camera_include_mount_disagree')
    camera_node = ET.parse(camera).getroot().find("model/link[@name='d435i_link']")
    camera_position = np.zeros(3)
    if camera_node.find('pose') is not None:
        camera_position += _pose(camera_node.find('pose'))
    sensor = camera_node.find("sensor[@name='imu']")
    if sensor is None:
        raise ValueError('missing_imu_sensor')
    if sensor.find('pose') is not None:
        camera_position += _pose(sensor.find('pose'))
    lever = base_position + mount_position + camera_position
    return {'schema': SCHEMA, 'conversion_tool_sha256': sha256(Path(__file__)),
            'raw_pose_reference': 'gazebo_model_origin',
            'output_pose_reference': 'd435i_imu', 'model_origin_to_imu_m': lever.tolist(),
            'source_sha256': {MODEL: sha256(model), CAMERA: sha256(camera), BASE: sha256(base)},
            'raw_twist_semantics': 'body-frame rolling-mean velocities; not instantaneous endpoint state',
            'velocity_comparison': 'differentiate converted IMU positions at source time; do not use raw twist as world velocity'}


def convert_model_samples(samples, lever):
    """Translate the reference point at each actual attitude, without refitting."""
    lever = np.asarray(lever, dtype=float)
    if lever.shape != (3,) or not np.isfinite(lever).all():
        raise ValueError('invalid_model_to_imu_translation')
    result = []
    for sample in samples:
        if sample.get('pose_reference') is not None:
            raise ValueError('truth_already_converted_or_unknown_reference')
        q = np.asarray(sample['q_xyzw'], dtype=float)
        if q.shape != (4,) or not np.isfinite(q).all() or abs(np.linalg.norm(q)-1) > 1e-5:
            raise ValueError('invalid_truth_quaternion')
        x,y,z,w=q/np.linalg.norm(q)
        rotation=np.asarray([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
                             [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
                             [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])
        position=np.asarray(sample['xyz'],dtype=float)
        if position.shape != (3,) or not np.isfinite(position).all():
            raise ValueError('invalid_truth_position')
        row=dict(sample)
        row['xyz']=(position+rotation@lever).tolist()
        row['pose_reference']='d435i_imu'
        # These fields remain in the raw archive; exposing them on transformed
        # poses would imply an unperformed point/frame velocity conversion.
        row.pop('linear_velocity_xyz_m_s',None)
        row.pop('angular_velocity_xyz_rad_s',None)
        result.append(row)
    return result


def imu_truth_samples(run, report):
    declared=(report.get('truth_payload_semantics') or {}).get('pose_reference')
    if declared not in (None, 'gazebo_model_origin'):
        raise ValueError('raw_truth_reference_declaration_mismatch')
    contract=model_to_imu_contract(run)
    return convert_model_samples(report.get('samples') or [], contract['model_origin_to_imu_m']), contract


def require_same_truth_reference(report, contract):
    reference=report.get('truth_reference_contract') or {}
    if any(reference.get(k)!=contract.get(k) for k in ('schema','output_pose_reference','model_origin_to_imu_m','source_sha256','conversion_tool_sha256')):
        raise ValueError('dependent_report_uses_old_or_different_truth_reference')


def fixed_prestream_alignment(run, samples):
    """Use the same latest-raw-before-PRESTREAM anchor as raw VIO evaluation."""
    from evaluate_vins_motion import rotation
    from evaluate_vio_quality_alignment import _interpolate_position, _interpolate_quaternion, _unit_quaternion
    run=Path(run)
    observation=json.loads((run/'alignment-observation.json').read_text())
    phases=[json.loads(line) for line in (run/'bridge-alignment-timeline.jsonl').read_text().splitlines() if line.strip()]
    starts=[int(p['stamp_ns']) for p in phases if p['phase']=='PRESTREAM']
    if len(starts)!=1:
        raise ValueError('need_one_prestream_alignment_anchor')
    raw=[r for r in observation['samples'] if r['kind']=='raw_odom']
    epoch=observation['epoch']
    if (observation['raw_topic']!=f'/vins_raw/s_{epoch}/odometry'
            or any(r['frame_id']!=f'vins_{epoch}_world'
                   or r['child_frame_id']!=f'vins_{epoch}_imu' for r in raw)):
        raise ValueError('raw_alignment_frame_or_epoch_mismatch')
    times=[int(r['source_ns']) for r in raw]
    if any(b<=a for a,b in zip(times,times[1:])):
        raise ValueError('nonmonotonic_raw_alignment_samples')
    before=[r for r in raw if int(r['source_ns'])<starts[0]]
    if not before:
        raise ValueError('no_raw_pose_before_prestream')
    anchor=before[-1];stamp=int(anchor['source_ns'])
    if starts[0]-stamp>150_000_000:
        raise ValueError('prestream_alignment_reference_too_old')
    truth_t=np.asarray([int(r['stamp_ns']) for r in samples],dtype=np.int64)
    if len(truth_t)<3 or np.any(np.diff(truth_t)<=0):
        raise ValueError('nonmonotonic_truth_alignment_samples')
    positions=np.asarray([r['xyz'] for r in samples],dtype=float)
    quaternions=np.asarray([r['q_xyzw'] for r in samples],dtype=float)
    position,gap=_interpolate_position(truth_t,positions,stamp)
    if gap>40_000_000:
        raise ValueError('truth_alignment_bracket_gap_exceeds_limit')
    quaternion=_interpolate_quaternion(truth_t,quaternions,stamp)
    align=rotation(quaternion)@rotation(_unit_quaternion(anchor['q_xyzw'])).T
    translation=position-align@np.asarray(anchor['xyz'],dtype=float)
    return align,translation,{'method':'latest raw VINS pose strictly before PRESTREAM; one scale-one SE(3)',
                              'reference_source_ns':stamp,'truth_bracket_gap_sim_s':gap/1e9,
                              'age_before_prestream_sim_s':(starts[0]-stamp)/1e9}
