#!/usr/bin/env python3
"""Read PX4 ULog parameters, EKF2 aiding flags, GNSS flags and final vehicle state."""
import argparse
import hashlib
import json
from pathlib import Path

from pyulog import ULog
from importlib.metadata import version


EV_FLAGS = ('cs_ev_pos', 'cs_ev_yaw', 'cs_ev_vel', 'cs_ev_hgt')
GNSS_FLAGS = ('cs_gnss_pos', 'cs_gnss_vel', 'cs_gnss_yaw', 'cs_gps_hgt')
PARAMETERS = ('EKF2_EV_CTRL', 'EKF2_GPS_CTRL', 'SIM_GZ_EN_ODOM', 'UXRCE_DDS_SYNCT')


def dataset(ulog, name):
    rows = [item for item in ulog.data_list if item.name == name]
    return sorted(rows, key=lambda item: item.multi_id)


def summarize_flags(data):
    timestamps = data.get('timestamp')
    if timestamps is None or not len(timestamps):
        raise ValueError('ULog estimator_status_flags has no timestamp samples')
    airborne = data.get('cs_in_air')
    if airborne is None:
        raise ValueError('ULog estimator_status_flags lacks cs_in_air')
    airborne_mask = airborne.astype(bool)
    if not airborne_mask.any():
        raise ValueError('ULog contains no estimator airborne samples')
    airborne_times = timestamps[airborne_mask]
    report = {
        'multi_id': None,
        'total_samples': int(len(timestamps)),
        'airborne_samples': int(airborne_mask.sum()),
        'airborne_start_timestamp_us': int(airborne_times[0]),
        'airborne_end_timestamp_us': int(airborne_times[-1]),
        'flags': {},
    }
    for name in (*EV_FLAGS, *GNSS_FLAGS):
        values = data.get(name)
        if values is None:
            report['flags'][name] = {'present': False}
            continue
        all_values = values.astype(bool)
        air_values = all_values[airborne_mask]
        report['flags'][name] = {
            'present': True,
            'true_samples_total': int(all_values.sum()),
            'total_samples': int(len(all_values)),
            'true_samples_airborne': int(air_values.sum()),
            'airborne_samples': int(len(air_values)),
            'airborne_true_fraction': float(air_values.mean()),
            'airborne_all_true': bool(air_values.all()),
        }
    return report


def analyze(path):
    path = Path(path).resolve()
    ulog = ULog(str(path))
    flags_topics = dataset(ulog, 'estimator_status_flags')
    if not flags_topics:
        raise ValueError('ULog lacks estimator_status_flags')
    flags = []
    for item in flags_topics:
        row = summarize_flags(item.data)
        row['multi_id'] = int(item.multi_id)
        flags.append(row)
    selected = max(flags, key=lambda row: (
        row['flags'].get('cs_ev_pos', {}).get('true_samples_airborne', 0)
        + row['flags'].get('cs_ev_yaw', {}).get('true_samples_airborne', 0),
        row['airborne_samples']))

    status_topics = dataset(ulog, 'vehicle_status')
    if not status_topics:
        raise ValueError('ULog lacks vehicle_status')
    status = status_topics[0].data
    arming = status.get('arming_state')
    status_timestamps = status.get('timestamp')
    if arming is None or status_timestamps is None or not len(arming):
        raise ValueError('ULog vehicle_status lacks arming_state')
    arming_counts = {str(int(value)): int((arming == value).sum())
                     for value in sorted(set(map(int, arming)))}
    land_topics = dataset(ulog, 'vehicle_land_detected')
    if not land_topics or 'landed' not in land_topics[0].data:
        raise ValueError('ULog lacks vehicle_land_detected.landed')
    landed = land_topics[0].data['landed']
    final_disarmed = int(arming[-1]) == 1
    final_landed = bool(landed[-1])
    params = {name: ulog.initial_parameters.get(name) for name in PARAMETERS}
    parameter_checks = {
        'EKF2_EV_CTRL_is_15': params['EKF2_EV_CTRL'] == 15,
        'EKF2_GPS_CTRL_is_0': params['EKF2_GPS_CTRL'] == 0,
        'SIM_GZ_EN_ODOM_is_0': params['SIM_GZ_EN_ODOM'] == 0,
        'UXRCE_DDS_SYNCT_is_0': params['UXRCE_DDS_SYNCT'] == 0,
    }
    selected_flags = selected['flags']
    ev_checks = {
        name + '_observed_airborne': bool(selected_flags.get(name, {}).get(
            'true_samples_airborne', 0) > 0)
        for name in ('cs_ev_pos', 'cs_ev_yaw')
    }
    gnss_checks = {
        name + '_never_active': bool(selected_flags.get(name, {}).get('present')
            and selected_flags[name]['true_samples_total'] == 0)
        for name in GNSS_FLAGS
    }
    groundtruth_datasets = sorted({item.name for item in ulog.data_list
                                   if 'groundtruth' in item.name.lower()
                                   or 'ground_truth' in item.name.lower()})
    checks = {
        **parameter_checks,
        **ev_checks,
        **gnss_checks,
        'final_px4_state_disarmed': final_disarmed,
        'final_px4_land_detector_landed': final_landed,
    }
    return {
        'schema': 'n07-px4-ulog-analysis/v1',
        'scope': __doc__,
        'qualification': 'ULog evidence only; GNSS and truth absence are cross-checked with ROS graph and simulator parameters.',
        'ulog_path': str(path),
        'ulog_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'pyulog_version': version('pyulog'),
        'duration_s': float((ulog.last_timestamp - ulog.start_timestamp) / 1e6),
        'initial_parameters': params,
        'estimator_status_flags_instances': flags,
        'selected_instance_multi_id': selected['multi_id'],
        'vehicle_status': {
            'sample_count': int(len(arming)),
            'arming_state_counts': arming_counts,
            'final_arming_state': int(arming[-1]),
            'final_arming_timestamp_us': int(status_timestamps[-1]),
        },
        'vehicle_land_detected': {
            'sample_count': int(len(landed)),
            'final_landed': final_landed,
        },
        'groundtruth_named_ulog_datasets': groundtruth_datasets,
        'interpretation': 'A simulator truth dataset in ULog is a recorded signal, not proof that project nodes consumed it. SIM_GZ_EN_ODOM, ROS graph and configured VINS-only input establish the online path.',
        'checks': checks,
        'passed': all(checks.values()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ulog', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.ulog)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({
        'passed': result['passed'],
        'ulog_sha256': result['ulog_sha256'],
        'initial_parameters': result['initial_parameters'],
        'selected_instance_multi_id': result['selected_instance_multi_id'],
        'checks': result['checks'],
    }, indent=2, sort_keys=True))
    if not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
