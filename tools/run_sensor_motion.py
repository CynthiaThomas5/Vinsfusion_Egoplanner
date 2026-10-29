#!/usr/bin/env python3
"""Debug-only sensor rig excitation; truth is recorded, never used for motion feedback."""
import argparse
import json
import math
from pathlib import Path
import signal
import time
from gz.transport13 import Node
from gz.msgs10.clock_pb2 import Clock
from gz.msgs10.pose_v_pb2 import Pose_V
from gz.msgs10.imu_pb2 import IMU
from gz.msgs10.entity_wrench_pb2 import EntityWrench
from gz.msgs10.entity_pb2 import Entity
import xml.etree.ElementTree as ET


DEFAULT_PROFILE_PATH = (Path(__file__).resolve().parents[1]
                       / 'config/components/simulation/sensor_motion.json')
DEFAULT_PROFILE = json.loads(DEFAULT_PROFILE_PATH.read_text())
STOP_REQUESTED = False


def request_stop(_signum, _frame):
    """Request a safe stop so the finally block can clear force and save data."""
    global STOP_REQUESTED
    STOP_REQUESTED = True


def motion(elapsed, profile=None):
    profile = DEFAULT_PROFILE if profile is None else profile
    phase_elapsed = elapsed - profile['initial_hold_seconds']
    if phase_elapsed < 0:
        return [0.] * len(profile['phase_signs'][0])
    if 'phase_durations_seconds' in profile:
        durations = profile['phase_durations_seconds']
        if len(durations) != len(profile['phase_signs']):
            raise ValueError('phase_durations_seconds must match phase_signs')
        phase_end = 0.0
        for phase, duration in enumerate(durations):
            if not math.isfinite(duration) or duration <= 0:
                raise ValueError('phase durations must be finite and positive')
            phase_end += duration
            if (phase_elapsed < phase_end
                    and not math.isclose(phase_elapsed, phase_end,
                                         rel_tol=0.0, abs_tol=1e-9)):
                break
        else:
            return [0.] * len(profile['phase_signs'][0])
    else:
        phase = int(phase_elapsed // profile['phase_seconds'])
    # Piecewise world accelerations, realized by forces; pairs return velocity to zero.
    if not 0 <= phase < len(profile['phase_signs']):
        return [0.] * len(profile['phase_signs'][0])
    acceleration = (profile['world_acceleration_and_angular_acceleration']
                    if 'world_acceleration_and_angular_acceleration' in profile
                    else profile['world_acceleration_and_yaw_acceleration'])
    return [s*a for s,a in zip(profile['phase_signs'][phase], acceleration)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--profile',type=Path,
                        default=DEFAULT_PROFILE_PATH)
    args = parser.parse_args()
    profile = json.loads(args.profile.read_text())
    if 'phase_durations_seconds' in profile:
        durations = profile['phase_durations_seconds']
        if len(durations) != len(profile['phase_signs']):
            raise ValueError('phase_durations_seconds must match phase_signs')
        numeric_durations = [float(value) for value in durations]
        if any(not math.isfinite(value) or value <= 0 for value in numeric_durations):
            raise ValueError('phase durations must be finite and positive')
        required_stop = float(profile['initial_hold_seconds']) + sum(numeric_durations)
        if not math.isfinite(required_stop) or float(profile['stop_seconds']) < required_stop:
            raise ValueError('stop_seconds must include every configured phase')
    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
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
    inertia = [float(model.findtext(f'model/link/inertial/inertia/{axis}'))
               for axis in ('ixx', 'iyy', 'izz')]
    publisher = node.advertise('/world/sensor_calibration/wrench/persistent',EntityWrench)
    clear = node.advertise('/world/sensor_calibration/wrench/clear',Entity)
    entity = Entity(name='sensor_fixture',type=Entity.MODEL)
    previous = [0.,0.,0.,0.,0.,0.]
    start=time.monotonic()
    try:
        while (not STOP_REQUESTED
               and time.monotonic()-start<profile['wall_timeout_seconds']):
            if len(clock)>1:
                elapsed=clock[1]-clock[0]
                values=motion(elapsed, profile)
                if len(values) == 4:  # Preserve the original translation+yaw profile.
                    values = values[:3] + [0.0, 0.0, values[3]]
                if values != previous:
                    delta = [a-b for a,b in zip(values,previous)]
                    msg=EntityWrench()
                    msg.entity.CopyFrom(entity)
                    msg.wrench.force.x,msg.wrench.force.y,msg.wrench.force.z = [mass*a for a in delta[:3]]
                    msg.wrench.torque.x = inertia[0]*delta[3]
                    msg.wrench.torque.y = inertia[1]*delta[4]
                    msg.wrench.torque.z = inertia[2]*delta[5]
                    # Persistent wrenches add: publish only deltas at phase boundaries.
                    publisher.publish(msg)
                    commands.append({'stamp':clock[1],
                                     'world_acceleration_and_angular_acceleration':values,
                                     'delta_wrench':[mass*d for d in delta[:3]]
                                     +[inertia[i]*delta[3+i] for i in range(3)]})
                    previous = values
                if elapsed>=profile['stop_seconds']:
                    break
            time.sleep(profile['command_period_seconds'])
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
