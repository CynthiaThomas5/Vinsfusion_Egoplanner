"""Decode only standard VINS visualization messages for isolated RViz topics."""
import base64
import json
import zlib
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import Image,PointCloud
from nav_msgs.msg import Odometry
from visualization_msgs.msg import MarkerArray
from rosidl_runtime_py.set_message import set_message_fields

TYPES={'camera':MarkerArray,'points':PointCloud,'history':PointCloud,'image':Image,'body':Odometry}
MAX_BYTES=8*1024*1024


def decode_visual(row,epoch,stamp):
    if row.get('epoch')!=epoch or row.get('kind') not in TYPES:
        raise ValueError('Visualization epoch/kind mismatch')
    payload=row['payload']
    if len(payload)>MAX_BYTES*2:raise ValueError('Visualization payload too large')
    compressed=base64.b64decode(payload,validate=True)
    if row.get('format')=='jpeg':
        import cv2
        import numpy as np
        if row['kind']!='image' or row.get('source_frame')!='vins_'+epoch+'_world':
            raise ValueError('JPEG kind/frame mismatch')
        data=cv2.imdecode(np.frombuffer(compressed,dtype=np.uint8),cv2.IMREAD_COLOR)
        if data is None or data.shape!=(240,640,3):raise ValueError('Invalid preview JPEG')
        msg=Image();msg.header.frame_id='hardware_display';msg.header.stamp=stamp
        msg.height,msg.width=data.shape[:2];msg.encoding='bgr8';msg.step=msg.width*3;msg.data=data.tobytes()
        return msg
    decoder=zlib.decompressobj()
    data=decoder.decompress(compressed,MAX_BYTES+1)
    if len(data)>MAX_BYTES or not decoder.eof or decoder.unused_data:
        raise ValueError('Invalid/oversized compressed visualization')
    if row['kind']=='camera':
        if row.get('format')!='marker_json':raise ValueError('Camera markers require schema-safe JSON')
        # Foxy Marker lacks the newer Humble texture/mesh fields; do not deserialize
        # its CDR as a Humble message. The common named fields retain exact geometry.
        msg=MarkerArray();set_message_fields(msg,json.loads(data))
    else:
        if row.get('format')!='cdr':raise ValueError('Expected standard sensor CDR')
        msg=deserialize_message(data,TYPES[row['kind']])
    headers=[m.header for m in msg.markers] if row['kind']=='camera' else [msg.header]
    if any(h.frame_id!='vins_'+epoch+'_world' for h in headers):
        raise ValueError('Visualization source world differs from session')
    # Display world is the same gravity-aligned VINS world, with an isolated name.
    # Header time is display arrival time; the relay never modifies source messages.
    for h in headers:h.frame_id='hardware_display';h.stamp=stamp
    return msg
