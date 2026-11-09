#!/usr/bin/env python3
"""Map transport checks with real standard ROS serialization, no live network."""
import base64
from pathlib import Path
import sys
import zlib
sys.path.insert(0,str(Path(__file__).resolve().parent/'diagnostics'))
from groundstation_map import decode_cloud
from rclpy.serialization import serialize_message
from sensor_msgs.msg import PointCloud2
from builtin_interfaces.msg import Time

epoch = 'a'*32
msg = PointCloud2(); msg.header.frame_id = 'odom_'+epoch
msg.width = 2; msg.point_step = 12; msg.row_step = 24
msg.data = bytes(range(24))
row = {'kind':'map','epoch':epoch,
       'payload':base64.b64encode(zlib.compress(serialize_message(msg))).decode()}
decoded = decode_cloud(row,epoch,Time(sec=42))
assert decoded.header.frame_id == 'hardware_display' and decoded.header.stamp.sec == 42
assert bytes(decoded.data) == bytes(msg.data) and decoded.width == 2
for bad in (dict(row,epoch='b'*32),dict(row,kind='control'),dict(row,payload='!')):
    try: decode_cloud(bad,epoch,Time())
    except ValueError: pass
    else: raise AssertionError('Invalid map packet accepted')
msg.header.frame_id = 'world'
row['payload'] = base64.b64encode(zlib.compress(serialize_message(msg))).decode()
try: decode_cloud(row,epoch,Time())
except ValueError: pass
else: raise AssertionError('Wrong source frame accepted')
print('Map bytes/arrival stamp and epoch/frame/corruption checks PASS')
