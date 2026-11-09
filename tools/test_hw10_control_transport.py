#!/usr/bin/env python3
"""High-rate hardware control EV input is throttled before decoding, source stamp intact."""
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src/own/uav_px4_bridge'))
from uav_px4_bridge.px4_bridge_node import Px4BridgeNode
from nav_msgs.msg import Odometry
from rclpy.serialization import serialize_message
m=Odometry();m.header.stamp.sec=10;m.header.stamp.nanosec=123
seen=[];now=[1000000000]
n=SimpleNamespace(config={'ev_rate_hz':30.},hardware_ev_attempt_ns=None,
 _now_ns=lambda:now[0],_on_odometry=seen.append)
data=serialize_message(m)
for _ in range(200):
 Px4BridgeNode._on_serialized_hardware_odometry(n,data);now[0]+=5000000
assert 28<=len(seen)<=30 and all(x.header.stamp.nanosec==123 for x in seen)
with patch('uav_px4_bridge.px4_bridge_node.deserialize_message',side_effect=AssertionError('decoded rate-dropped sample')):
 now[0]=n.hardware_ev_attempt_ns+1
 Px4BridgeNode._on_serialized_hardware_odometry(n,data)
print('Hardware control raw throttle, original source stamp, pre-decode drop PASS')
