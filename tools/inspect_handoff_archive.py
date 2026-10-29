#!/usr/bin/env python3
"""Read persisted RGB-D/map-status CDR without publishing or replaying ROS topics."""
import argparse,hashlib,json
from pathlib import Path


def inspect_archive(bag, expected_epoch=None):
    import rosbag2_py
    from rclpy.serialization import deserialize_message
    from rosidl_runtime_py.utilities import get_message
    reader=rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=str(bag),storage_id='mcap'),rosbag2_py.ConverterOptions('cdr','cdr'))
    types={r.name:r.type for r in reader.get_all_topics_and_types()};statuses={};frames=[];errors=[]
    while reader.has_next():
        topic,payload,receipt=reader.read_next()
        if topic not in ['/mapping/rgbd_keyframes','/mapping/status']:continue
        msg=deserialize_message(payload,get_message(types[topic]))
        if expected_epoch and msg.epoch!=expected_epoch:raise ValueError('archive contains a different epoch')
        if topic=='/mapping/status':
            statuses[(msg.epoch,msg.map_id)]={'calibration_sha256':msg.calibration_sha256,'input_config_sha256':msg.input_config_sha256,'max_rgbd_delta_s':msg.keyframe_max_rgbd_stamp_delta_s}
        else:
            from probe_handoff_interfaces import keyframe_report
            row=keyframe_report(msg);row['serialized_sha256']=hashlib.sha256(payload).hexdigest();row['image_sha256']={name:hashlib.sha256(bytes(getattr(msg,name).data)).hexdigest() for name in ['color','depth']};row['camera_K']={name:list(getattr(msg,name+'_camera_info').k) for name in ['color','depth']}
            row['image_payload_layout_valid']=all(len(getattr(msg,k).data)==getattr(msg,k).height*getattr(msg,k).step and getattr(msg,k).width>0 for k in ['color','depth'])
            row['source_pose_valid']=all(row[k]['pose_finite'] and row[k]['pose_frame']=='odom_'+msg.epoch and row[k]['pose_stamp_ns']==row[k]['stamp_ns'] and row[k]['frame']==row[k]['camera_info_frame'] for k in ['color','depth']);frames.append(row)
    for f in frames:
        status=statuses.get((f['epoch'],f['map_id']))
        if not status or not status['input_config_sha256'] or status['calibration_sha256']!=f['calibration_sha256']:errors.append('keyframe map/calibration/config identity unavailable or mismatched')
        elif f['rgbd_stamp_delta_s']>status['max_rgbd_delta_s']:errors.append('RGB-D source stamp delta exceeds declared matching interval')
        if not f['image_payload_layout_valid'] or not f['source_pose_valid']:errors.append('invalid image layout or source-time pose')
    return {'schema':'persisted-handoff-archive-inspection/v1','archive':str(Path(bag)),'passed':bool(frames) and bool(statuses) and not errors,'frame_count':len(frames),'frames':frames,'map_identities':[{'epoch':k[0],'map_id':k[1],**v} for k,v in statuses.items()],'errors':sorted(set(errors)),'publishes_ros_topics':False,'scope':'actual CDR payload/CameraInfo/poses/map/config readback; no relocalization claim'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('bag',type=Path);p.add_argument('--expected-epoch');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    report=inspect_archive(a.bag,a.expected_epoch);a.output.write_text(json.dumps(report,indent=2)+'\n');print('PASS' if report['passed'] else 'INSUFFICIENT');raise SystemExit(0 if report['passed'] else 1)
