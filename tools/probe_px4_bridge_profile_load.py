#!/usr/bin/env python3
"""Instantiate a service-gated PX4 bridge profile and audit its inputs."""

import argparse
from pathlib import Path

import rclpy
from uav_px4_bridge.px4_bridge_node import Px4BridgeNode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-root', required=True, type=Path)
    parser.add_argument('--profile', choices=('debug_truth', 'vio_closed_loop'),
                        required=True)
    args = parser.parse_args()
    root = args.project_root.resolve()
    profile = args.profile
    config = root / 'config/components/px4_bridge' / (profile + '.json')
    frame = (root / 'config/components/px4_bridge/frames.json'
             if profile == 'debug_truth'
             else root / 'config/components/px4_bridge/frames_vio_closed_loop.json')
    profile_path = root / 'config/profiles' / (profile + '.json')
    rclpy.init(args=[
        '--ros-args',
        '-p', 'profile_path:=' + str(profile_path),
        '-p', 'bridge_config_path:=' + str(config),
        '-p', 'frame_contract_path:=' + str(frame),
    ])
    node = None
    try:
        node = Px4BridgeNode()
        expected = (('/clock', '/debug_truth/localization_status',
                     '/debug_truth/optimized_imu_odom')
                    if profile == 'debug_truth'
                    else ('/clock', '/localization/status',
                          '/localization/optimized_imu_odom'))
        actual = (node.clock_topic, node.localization_topic, node.odometry_topic)
        if actual != expected:
            raise RuntimeError(f'{profile} source topic mismatch: {actual!r}')
        topics = sorted(subscription.topic_name for subscription in node._subscriptions)
        if profile == 'vio_closed_loop' and any('debug_truth' in topic for topic in topics):
            raise RuntimeError('VIO profile subscribed to a truth topic')
        if node.supervisor.phase != node.supervisor.DISABLED:
            raise RuntimeError('PX4 control did not start disabled')
        print(f'PROFILE_LOAD_PASS profile={profile}')
        print('source_topics=' + ','.join(actual))
        print('truth_input_subscribed=' + str(any('debug_truth' in t for t in topics)).lower())
        print('control_phase=' + node.supervisor.phase)
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
