#!/usr/bin/env python3
"""Stage a profile-specific airframe using the shared no-GNSS PX4 SITL parameters."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/own/uav_sim'))
from uav_sim.geometry import px4_sensor_mount  # noqa: E402


def _number(value):
    return format(float(value), '.9g')


def stage(project_root, px4_build, profile='debug_truth'):
    project_root = Path(project_root).resolve()
    px4_build = Path(px4_build).resolve()
    config_path = project_root / 'config/components/px4_bridge/ekf2_debug_truth.json'
    config = json.loads(config_path.read_text(encoding='utf-8'))
    clock_config = json.loads(
        (project_root / 'config/components/px4_bridge/debug_truth.json')
        .read_text(encoding='utf-8'))
    if config.get('profile') != 'debug_truth':
        raise ValueError('shared PX4 parameter source is invalid')
    if profile == 'debug_truth':
        autostart_id = config.get('autostart_id')
    elif profile == 'vio_closed_loop':
        profile_path = project_root / 'config/profiles/vio_closed_loop.json'
        bridge_path = project_root / 'config/components/px4_bridge/vio_closed_loop.json'
        runtime_profile = json.loads(profile_path.read_text(encoding='utf-8'))
        bridge_config = json.loads(bridge_path.read_text(encoding='utf-8'))
        if (runtime_profile.get('name') != profile
                or runtime_profile.get('ground_truth_online_allowed') is not False
                or runtime_profile.get('px4_debug_position_allowed') is not False
                or runtime_profile.get('gps_position_aiding_allowed') is not False
                or runtime_profile.get('mapping_localization') != 'vins'
                or runtime_profile.get('planner_localization') != 'vins'
                or runtime_profile.get('px4_position_source') != 'vins_external_odometry'
                or bridge_config.get('profile') != profile
                or any('debug_truth' in key for key in bridge_config)
                or bridge_config.get('localization_status_topic') != '/localization/status'
                or bridge_config.get('optimized_odometry_topic')
                != '/localization/optimized_imu_odom'):
            raise ValueError('VIO profile must prohibit truth and GPS aiding')
        autostart_id = bridge_config.get('px4_autostart_id')
        if autostart_id == config.get('autostart_id'):
            raise ValueError('VIO must use an isolated PX4 autostart ID')
    else:
        raise ValueError('unsupported PX4 parameter overlay profile')
    if type(autostart_id) is not int or autostart_id <= 4000:
        raise ValueError('autostart_id must be an isolated custom SITL ID')
    base = config.get('base_airframe')
    if base != '4001_gz_x500':
        raise ValueError('unexpected base airframe')
    airframe_dir = px4_build / 'etc/init.d-posix/airframes'
    source = airframe_dir / base
    if not source.is_file():
        raise FileNotFoundError('PX4 build does not contain the pinned x500 airframe')

    mount_path = project_root / config['mount_model_sdf']
    mount = px4_sensor_mount(mount_path)
    params = config['parameters']
    required = {'EKF2_EV_CTRL', 'EKF2_GPS_CTRL', 'EKF2_HGT_REF',
                'COM_ARM_WO_GPS', 'COM_RC_IN_MODE', 'COM_OBL_RC_ACT',
                'COM_OF_LOSS_T', 'NAV_DLL_ACT', 'SIM_GZ_EN_ODOM',
                'UXRCE_DDS_SYNCT'}
    if set(params) != required:
        raise ValueError('debug_truth parameter set is incomplete or unexpected')
    if params['EKF2_EV_CTRL'] != 15 or params['EKF2_GPS_CTRL'] != 0:
        raise ValueError('debug_truth must enable full EV fusion and disable GNSS aiding')
    if (params['COM_ARM_WO_GPS'] != 2 or params['COM_RC_IN_MODE'] != 4
            or params['NAV_DLL_ACT'] != 0 or params['COM_OBL_RC_ACT'] != 4):
        raise ValueError('headless SITL arming and loss-action values are unsafe or incomplete')
    if params['SIM_GZ_EN_ODOM'] != 0:
        raise ValueError('PX4 Gazebo truth odometry must be disabled; only the debug adapter may feed EV')
    if (type(clock_config.get('uxrce_dds_time_sync_enabled')) is not bool
            or params['UXRCE_DDS_SYNCT']
            != int(clock_config['uxrce_dds_time_sync_enabled'])):
        raise ValueError('PX4 uXRCE timestamp sync must match the Gazebo clock profile')

    if profile == 'vio_closed_loop':
        limits = json.loads((project_root / 'config/components/px4_bridge/flight_limits.json').read_text())['parameters']
        if set(limits) != {'MPC_Z_VEL_MAX_UP'} or not 0 < limits['MPC_Z_VEL_MAX_UP'] <= 0.5:
            raise ValueError('Invalid validated VIO ascent limit')
        params = {**params, **limits}

    lines = [
        '# Generated for the ' + profile + ' profile from the shared PX4 SITL parameter source.',
        '# D435i lever arm source SHA256: ' + mount['model_sha256'],
        '# Do not edit this generated file; regenerate it from project config.',
        '#!/bin/sh',
        'PX4_SIM_MODEL=${PX4_SIM_MODEL:=' + config['sim_model'] + '}',
        '. ${R}etc/init.d-posix/airframes/' + base,
    ]
    for name, value in params.items():
        lines.append('param set %s %s' % (name, _number(value)))
    for name, index in (('EKF2_EV_POS_X', 0), ('EKF2_EV_POS_Y', 1),
                        ('EKF2_EV_POS_Z', 2)):
        lines.append('param set %s %s' % (name, _number(mount['translation_frd_m'][index])))
    lines.append('')
    destination = airframe_dir / ('%d_gz_x500_d435i_%s' % (autostart_id, profile))
    destination.write_text('\n'.join(lines), encoding='utf-8')
    destination.chmod(0o755)
    return {
        'path': str(destination),
        'profile': profile,
        'autostart_id': autostart_id,
        'parameters': {**params,
                       'EKF2_EV_POS_X': mount['translation_frd_m'][0],
                       'EKF2_EV_POS_Y': mount['translation_frd_m'][1],
                       'EKF2_EV_POS_Z': mount['translation_frd_m'][2]},
        'mount_model_sha256': mount['model_sha256'],
        'script_sha256': __import__('hashlib').sha256(destination.read_bytes()).hexdigest(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-root', default=str(ROOT))
    parser.add_argument('--px4-build', required=True)
    parser.add_argument('--profile', choices=('debug_truth', 'vio_closed_loop'),
                        default='debug_truth')
    parser.add_argument('--output')
    args = parser.parse_args()
    report = stage(args.project_root, args.px4_build, profile=args.profile)
    payload = json.dumps(report, indent=2, sort_keys=True) + '\n'
    if args.output:
        Path(args.output).write_text(payload, encoding='utf-8')
    print(payload, end='')


if __name__ == '__main__':
    main()
