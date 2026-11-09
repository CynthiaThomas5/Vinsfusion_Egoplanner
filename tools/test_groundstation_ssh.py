#!/usr/bin/env python3
"""Foxy serialization -> SSH -> Jazzy decoding; fixture only, no ROS publishers."""
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'diagnostics'))
from groundstation_map import decode_cloud
from builtin_interfaces.msg import Time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--host',default='uav-nano')
parser.add_argument('--root',default='/home/jetson/D435i-VINS-EGO-ROS2-hardware')
args = parser.parse_args()
code = '''import base64,json,zlib
from rclpy.serialization import serialize_message
from sensor_msgs.msg import PointCloud2
m=PointCloud2();m.header.frame_id='odom_'+'a'*32
m.width=2;m.height=1;m.point_step=12;m.row_step=24;m.data=bytes(range(24))
print(json.dumps(dict(kind='map',epoch='a'*32,payload=base64.b64encode(zlib.compress(serialize_message(m))).decode())))
'''
result = subprocess.run(['ssh','-o','BatchMode=yes',args.host,
    'cd '+shlex.quote(args.root)+'; source tools/hardware-env.bash; python3 -'],
    input=code,text=True,capture_output=True,check=True,timeout=20)
decoded = decode_cloud(json.loads(result.stdout),'a'*32,Time(sec=42))
assert decoded.width == 2 and bytes(decoded.data) == bytes(range(24))
assert decoded.header.frame_id == 'hardware_display' and decoded.header.stamp.sec == 42
print('Native Foxy -> actual SSH -> Jazzy map decoding PASS (synthetic, zero ROS publishers)')
