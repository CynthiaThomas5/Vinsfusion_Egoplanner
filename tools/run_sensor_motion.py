#!/usr/bin/env python3
"""Debug-only sensor rig excitation; truth is recorded, never used for motion feedback."""
import argparse
import json
from pathlib import Path
import time
from gz.transport13 import Node
from gz.msgs10.clock_pb2 import Clock
from gz.msgs10.pose_v_pb2 import Pose_V
from gz.msgs10.imu_pb2 import IMU
from gz.msgs10.entity_wrench_pb2 import EntityWrench
from gz.msgs10.entity_pb2 import Entity
import xml.etree.ElementTree as ET


PROFILE = json.loads((Path(__file__).resolve().parents[1]/'config/components/simulation/sensor_motion.json').read_text())

def motion(elapsed):
    phase = int((elapsed-PROFILE['initial_hold_seconds'])//PROFILE['phase_seconds'])
    # Piecewise world accelerations, realized by forces; pairs return velocity to zero.
    if not 0 <= phase < len(PROFILE['phase_signs']):
        return [0.,0.,0.,0.]
    return [s*a for s,a in zip(PROFILE['phase_signs'][phase],PROFILE['world_acceleration_and_yaw_acceleration'])]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    node = Node()
    clock, truth, imu, commands = [], [], [], []
    def on_clock(msg):
        stamp = msg.sim.sec+msg.sim.nsec*1e-9
        if not clock:
            clock.append(stamp)
        if len(clock)==1:
            clock.append(stamp)
        else:
            clock[1] = stamp
    def on_pose(msg):
        for pose in msg.pose:
            if pose.name == 'sensor_fixture':
                stamp = pose.header.stamp.sec+pose.header.stamp.nsec*1e-9
                p,q=pose.position,pose.orientation
                truth.append({'stamp':stamp, 'position':[p.x,p.y,p.z], 'quaternion':[q.x,q.y,q.z,q.w]})
    def on_imu(msg):
        t=msg.header.stamp.sec+msg.header.stamp.nsec*1e-9
        a,g=msg.linear_acceleration,msg.angular_velocity
        imu.append({'stamp':t, 'acceleration':[a.x,a.y,a.z], 'gyro':[g.x,g.y,g.z]})
    node.subscribe(Clock,'/clock',on_clock)
    node.subscribe(Pose_V,'/model/sensor_fixture/pose',on_pose)
    node.subscribe(IMU,'/sensors/d435i/imu',on_imu)
    model = ET.parse(Path(__file__).resolve().parents[1]/'simulation/models/d435i/model.sdf')
    mass = float(model.findtext('model/link/inertial/mass'))
    izz = float(model.findtext('model/link/inertial/inertia/izz'))
    publisher = node.advertise('/world/sensor_calibration/wrench/persistent',EntityWrench)
    clear = node.advertise('/world/sensor_calibration/wrench/clear',Entity)
    entity = Entity(name='sensor_fixture',type=Entity.MODEL)
    previous = [0.,0.,0.,0.]
    start=time.monotonic()
    try:
        while time.monotonic()-start<PROFILE['wall_timeout_seconds']:
            if len(clock)>1:
                elapsed=clock[1]-clock[0]
                values=motion(elapsed)
                if values != previous:
                    delta = [a-b for a,b in zip(values,previous)]
                    msg=EntityWrench()
                    msg.entity.CopyFrom(entity)
                    msg.wrench.force.x,msg.wrench.force.y,msg.wrench.force.z = [mass*a for a in delta[:3]]
                    msg.wrench.torque.z = izz*delta[3]
                    # Persistent wrenches add: publish only deltas at phase boundaries.
                    publisher.publish(msg)
                    commands.append({'stamp':clock[1], 'world_acceleration_command':values, 'delta_wrench':[mass*d for d in delta[:3]]+[izz*delta[3]]})
                    previous = values
                if elapsed>=PROFILE['stop_seconds']:
                    break
            time.sleep(PROFILE['command_period_seconds'])
    finally:
        clear.publish(entity)
        for topic in ['/clock', '/model/sensor_fixture/pose', '/sensors/d435i/imu']:
            node.unsubscribe(topic)
        del publisher
        del clear
        del node
        args.output.write_text(json.dumps({'scope':'Physics force-driven debug sensor rig; no truth feedback or PX4 control', 'clock':clock,
            'truth':truth,'imu':imu,'commands':commands, 'wall_seconds':time.monotonic()-start},indent=2)+'\n')
    print(json.dumps({'truth_samples':len(truth),'imu_samples':len(imu),'clock':clock}))


if __name__ == '__main__':
    main()
