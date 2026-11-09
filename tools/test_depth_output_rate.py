#!/usr/bin/env python3
"""Affected ROS integration check: conversion, source identity, and optional output cap."""
from pathlib import Path
import struct
import subprocess
import time

from ament_index_python.packages import get_package_prefix
import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


def check(cap):
    node = rclpy.create_node('depth_output_rate_probe')
    messages = []
    sent = set()
    topic = '/hw05_conversion_probe'
    publisher = node.create_publisher(Image, topic + '/native', qos_profile_sensor_data)
    subscription = node.create_subscription(Image, topic + '/meters', messages.append,
                                             qos_profile_sensor_data)
    binary = Path(get_package_prefix('uav_sensor_interface')) / 'lib/uav_sensor_interface/d435i_depth_to_meters_cpp'
    child = subprocess.Popen([str(binary), '--ros-args', '-r', '__node:=hw05_conversion_subject',
        '-p', f'input_topic:={topic}/native', '-p', f'output_topic:={topic}/meters',
        '-p', f'max_output_rate_hz:={cap}'])
    try:
        deadline = time.monotonic() + 10
        while node.count_subscribers(topic + '/native') != 1 or node.count_publishers(topic + '/meters') != 1:
            assert child.poll() is None and time.monotonic() < deadline, 'conversion node not ready'
            rclpy.spin_once(node, timeout_sec=0.05)
        for index in range(60):
            msg = Image()
            msg.header.frame_id = 'native_depth_optical'
            msg.header.stamp.sec = 100 + index // 20
            msg.header.stamp.nanosec = (index % 20) * 50_000_000
            sent.add((msg.header.stamp.sec, msg.header.stamp.nanosec))
            msg.width, msg.height, msg.step = 2, 1, 4
            msg.encoding = '16UC1'
            msg.data = struct.pack('<HH', 0, 250)
            publisher.publish(msg)
            until = time.monotonic() + 0.05
            while time.monotonic() < until:
                rclpy.spin_once(node, timeout_sec=0.005)
        until = time.monotonic() + 0.4
        while time.monotonic() < until:
            rclpy.spin_once(node, timeout_sec=0.02)
        if cap:
            assert 8 <= len(messages) <= 17, (cap, len(messages))
        else:
            assert len(messages) == 60, len(messages)
        stamps = [(m.header.stamp.sec, m.header.stamp.nanosec) for m in messages]
        assert stamps == sorted(set(stamps)) and set(stamps) <= sent
        for msg in messages:
            assert msg.header.frame_id == 'native_depth_optical'
            assert (msg.encoding, msg.width, msg.height, msg.step) == ('32FC1', 2, 1, 8)
            assert struct.unpack('<ff', bytes(msg.data)) == (0.0, 0.25)
        print(f'PASS cap={cap} native=60 metric={len(messages)}; zero, units, frame and source stamps preserved')
    finally:
        child.terminate()
        child.wait(timeout=10)
        node.destroy_subscription(subscription)
        node.destroy_node()


if __name__ == '__main__':
    rclpy.init()
    try:
        check(0.0)
        check(5.0)
    finally:
        rclpy.shutdown()
