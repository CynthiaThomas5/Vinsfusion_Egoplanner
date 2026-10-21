#!/usr/bin/env python3
"""Read-only fixed-fixture ROS sensor calibration probe; never publishes control."""
import argparse
from array import array
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics
import sys
import time

import rclpy
from rclpy.qos import qos_profile_sensor_data, QoSProfile, DurabilityPolicy
from sensor_msgs.msg import Image, CameraInfo, Imu
from rosgraph_msgs.msg import Clock
from tf2_msgs.msg import TFMessage
from uav_sim.geometry import calibration


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=15)
    args = parser.parse_args()
    expected = calibration(args.project_root / 'simulation/models/d435i/model.sdf')
    rclpy.init()
    node = rclpy.create_node('d435i_readonly_sensor_probe')
    import numpy as np
    import cv2
    stereo_images = {}
    stereo_pair = []
    stamps, frames, encodings, sizes, infos = defaultdict(list), {}, {}, {}, {}
    accelerations, gyros, depths, clock = [], [], [], []
    transforms = {}
    def stamp(header):
        return header.stamp.sec * 1000000000 + header.stamp.nanosec
    def sample(name, msg):
        stamps[name].append(stamp(msg.header))
        frames[name] = msg.header.frame_id
    def image(name, msg):
        sample(name, msg)
        if name in ['infra1', 'infra2'] and not stereo_pair:
            key = stamp(msg.header)
            stereo_images.setdefault(key, {})[name] = np.frombuffer(bytes(msg.data), dtype=np.uint8).reshape(msg.height, msg.step)[:, :msg.width].copy()
            if len(stereo_images[key]) == 2:
                stereo_pair.extend([stereo_images[key]['infra1'], stereo_images[key]['infra2']])
                stereo_images.clear()
            elif len(stereo_images) > 8:
                del stereo_images[min(stereo_images)]
        encodings[name], sizes[name] = msg.encoding, [msg.width, msg.height]
        if name == 'depth' and msg.encoding == '32FC1':
            values = array('f')
            # Inspect a central 9x9 patch using row stride; preserve declared endianness.
            for y in range(msg.height//2-4, msg.height//2+5):
                offset = y * msg.step + (msg.width//2-4) * 4
                row = array('f', bytes(msg.data[offset:offset+36]))
                if bool(msg.is_bigendian) != (sys.byteorder == 'big'):
                    row.byteswap()
                values.extend(row)
            depths.extend(v for v in values if math.isfinite(v) and v > 0)
    def info(name, msg):
        sample(name + '_info', msg)
        infos[name] = {'K': list(msg.k), 'width': msg.width, 'height': msg.height}
    def imu(msg):
        sample('imu', msg)
        accelerations.append([msg.linear_acceleration.x, msg.linear_acceleration.y, msg.linear_acceleration.z])
        gyros.append([msg.angular_velocity.x, msg.angular_velocity.y, msg.angular_velocity.z])
    subscriptions = []
    for name, topic in [('infra1', 'infra1/image_rect'), ('infra2', 'infra2/image_rect'), ('depth', 'depth'), ('color', 'color/image_raw')]:
        subscriptions.append(node.create_subscription(Image, '/sensors/d435i/' + topic, lambda m, n=name: image(n, m), qos_profile_sensor_data))
        subscriptions.append(node.create_subscription(CameraInfo, '/sensors/d435i/' + name + '/camera_info', lambda m, n=name: info(n, m), qos_profile_sensor_data))
    subscriptions.append(node.create_subscription(Imu, '/sensors/d435i/imu', imu, qos_profile_sensor_data))
    subscriptions.append(node.create_subscription(Clock, '/clock', lambda m: clock.append(m.clock.sec*1000000000+m.clock.nanosec), qos_profile_sensor_data))
    subscriptions.append(node.create_subscription(TFMessage, '/tf_static', lambda m: transforms.update({t.child_frame_id: {'parent': t.header.frame_id, 'translation': [t.transform.translation.x, t.transform.translation.y, t.transform.translation.z]} for t in m.transforms}), QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)))
    start = time.monotonic()
    while time.monotonic()-start < args.seconds:
        rclpy.spin_once(node, timeout_sec=.1)
    checks = {}
    names = ['infra1', 'infra2', 'depth', 'color']
    for name in names:
        checks[name + '_data'] = len(stamps[name]) >= 3
        checks[name + '_frame'] = frames.get(name) == expected['cameras'][name]['frame']
        checks[name + '_info_frame'] = frames.get(name + '_info') == expected['cameras'][name]['frame']
        checks[name + '_size'] = sizes.get(name) == [expected['cameras'][name]['width'], expected['cameras'][name]['height']]
        checks[name + '_intrinsics'] = name in infos and max(abs(a-b) for a,b in zip(infos[name]['K'], expected['cameras'][name]['K'])) < 1e-4
    checks['encodings'] = encodings == dict(infra1='mono8', infra2='mono8', depth='32FC1', color='rgb8')
    checks['depth_meters_plane'] = bool(depths) and abs(statistics.median(depths)-3.0) < .01
    checks['imu_gravity'] = len(accelerations) >= 20 and all(abs(statistics.mean(a[i] for a in accelerations)-v) < .02 for i,v in enumerate([0,0,9.80665]))
    checks['imu_zero_rotation'] = bool(gyros) and max(math.sqrt(sum(v*v for v in g)) for g in gyros) < .001
    checks['imu_frame'] = frames.get('imu') == expected['imu']['frame']
    checks['fixed_tf'] = all(s['frame'] in transforms and transforms[s['frame']]['parent'] == 'd435i_link' and max(abs(a-b) for a,b in zip(transforms[s['frame']]['translation'], s['translation'])) < 1e-9 for s in [expected['imu'], *expected['cameras'].values()])
    checks['clock_advances'] = len(clock)>2 and clock[-1]>clock[0]
    checks['monotonic_source_stamps'] = all(all(b>a for a,b in zip(values, values[1:])) for values in stamps.values())
    paired = set(stamps['infra1']) & set(stamps['infra2'])
    checks['stereo_paired'] = len(paired)>=3 and len(paired)/max(len(stamps['infra1']),len(stamps['infra2']),1) >= .9
    checks['source_sim_time'] = bool(clock) and all(values and max(values) <= clock[-1]+100000000 for values in stamps.values())
    disparity = None
    if stereo_pair:
        left, right = stereo_pair
        scores = cv2.matchTemplate(right[140:340, 190:450], left[140:340, 220:420], cv2.TM_SQDIFF_NORMED)[0]
        index = int(np.argmin(scores))
        offset = 0.0
        if 0 < index < len(scores)-1:
            a,b,c = map(float, scores[index-1:index+2])
            if a-2*b+c > 1e-12:
                offset = .5*(a-c)/(a-2*b+c)
        disparity = 30-index-offset
    expected_disparity = expected['cameras']['infra1']['K'][0]*expected['stereo_baseline_m']/3
    checks['stereo_geometric_disparity'] = disparity is not None and abs(disparity-expected_disparity)<.5
    checks = {name: bool(value) for name, value in checks.items()}
    report = {'scope': 'Static ideal sensor fixture only; not flight or VIO acceptance', 'result': 'PASS' if all(checks.values()) else 'FAIL', 'checks': checks,
              'model_sha256': expected['model_sha256'], 'counts': {n:len(v) for n,v in stamps.items()},
              'source_rates_hz': {n:(len(v)-1)*1e9/(v[-1]-v[0]) for n,v in stamps.items() if len(v)>1 and v[-1]>v[0]},
              'frames':frames, 'encodings':encodings, 'camera_info': infos, 'static_tf':transforms,
              'disparity_px':disparity, 'expected_disparity_px':expected_disparity, 'stereo_paired_count':len(paired), 'depth_median_m':statistics.median(depths) if depths else None,
              'imu_mean_acceleration': [statistics.mean(a[i] for a in accelerations) for i in range(3)] if accelerations else None,
              'clock_range_ns':[clock[0],clock[-1]] if clock else [], 'wall_seconds':time.monotonic()-start}
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'result':report['result'], 'failed':[k for k,v in checks.items() if not v]}))
    node.destroy_node()
    rclpy.shutdown()
    return 0 if report['result']=='PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
