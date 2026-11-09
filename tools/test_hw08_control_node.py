#!/usr/bin/env python3
"""Isolated ROS hardware-control node check. Run only with ROS_DOMAIN_ID=83.

Synthetic mount/telemetry, no Agent or physical PX4. Verifies the existing
supervisor stays disabled and mount yaw is applied before local registration.
"""
import copy
import json
import math
import os
from pathlib import Path
import tempfile
import time

import rclpy
from rclpy.serialization import serialize_message
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry
from px4_msgs.msg import (TimesyncStatus, VehicleAttitude, VehicleLocalPosition,
    VehicleStatus, VehicleLandDetected, EstimatorStatusFlags, VehicleOdometry,
    VehicleCommand, OffboardControlMode, TrajectorySetpoint)
from uav_interfaces.msg import LocalizationStatus, PositionCommand
from uav_interfaces.srv import EnableOffboard
from uav_px4_bridge.px4_bridge_node import Px4BridgeNode
from uav_px4_bridge.rigid_body import rotation_quaternion
from uav_px4_bridge.trajectory import position_command_to_ned


def main():
    assert os.environ.get('ROS_DOMAIN_ID') == '83', 'Requires isolated domain 83'
    root = Path(__file__).resolve().parents[1]
    actual = json.loads((root/'config/hardware/rig.json').read_text())
    fixture = copy.deepcopy(actual)
    matrix=actual['airframe_mount'].get('bench_observation', {}).get('approximate_transform', {}).get(
        'T_fc_imu_candidate',[0,0,1,.2,1,0,0,.01,0,1,0,0,0,0,0,1])
    fixture['airframe_mount'] = dict(status='MEASURED',control_usable=True,
        propeller_envelope_measured=False, qualification='SYNTHETIC_TEST_ONLY',
        T_airframe_imu=matrix)
    epoch = 'a'*32
    with tempfile.TemporaryDirectory() as directory:
        rig = Path(directory)/'rig.json'
        rig.write_text(json.dumps(fixture))
        args = ['--ros-args']
        for key,value in dict(profile_path=root/'config/hardware/px4_profile.json',
            bridge_config_path=root/'config/hardware/px4_bridge_control.json',
            frame_contract_path=root/'config/components/px4_bridge/frames_vio_closed_loop.json',
            rig_config=rig).items():
            args += ['-p',f'{key}:={value}']
        rclpy.init(args=args)
        bridge, observer = None, None
        try:
            bridge = Px4BridgeNode()
            assert bridge.odometry_topic == '/localization/imu_odom'
            observer = rclpy.create_node('hw08_control_fixture_observer')
            counts = dict(ev=0,mode=0,setpoint=0,command=0)
            subs = []
            for key,typ,topic in [('ev',VehicleOdometry,'vehicle_visual_odometry'),
                    ('mode',OffboardControlMode,'offboard_control_mode'),
                    ('setpoint',TrajectorySetpoint,'trajectory_setpoint'),
                    ('command',VehicleCommand,'vehicle_command')]:
                def receive(msg,key=key): counts[key] += 1
                subs.append(observer.create_subscription(typ,'/fmu/in/'+topic,
                                                         receive,qos_profile_sensor_data))
            assert '/clock' not in [x.topic_name for x in bridge.subscriptions]
            # Explicit enable must fail without EV/localization readiness.
            response = bridge._on_enable(EnableOffboard.Request(enable=True), EnableOffboard.Response())
            assert not response.accepted
            yaw = math.pi/2+.37
            rbi=[matrix[i*4:i*4+3] for i in range(3)]
            qwi = rotation_quaternion([[rbi[i][j]*(1 if i==0 else -1) for j in range(3)] for i in range(3)])
            started = time.monotonic()
            end = started+5.
            disabled_counts = None
            while time.monotonic() < end:
                now, mono = time.time_ns(), time.monotonic_ns()
                stamp = now-50000000
                sync = TimesyncStatus(timestamp=now//1000,source_protocol=2,
                    estimated_offset=-now//1000+100000000,round_trip_time=1000)
                bridge._on_timesync(sync)
                health = LocalizationStatus(epoch=epoch,valid=True,state=LocalizationStatus.TRACKING)
                bridge._on_localization(health)
                odom = Odometry()
                odom.header.frame_id='odom_'+epoch;odom.child_frame_id='d435i_imu_'+epoch
                odom.header.stamp.sec=stamp//1000000000;odom.header.stamp.nanosec=stamp%1000000000
                odom.pose.pose.position.x=matrix[3];odom.pose.pose.position.y=-matrix[7];odom.pose.pose.position.z=-matrix[11]
                q=odom.pose.pose.orientation;q.x,q.y,q.z,q.w=qwi
                bridge._on_serialized_hardware_odometry(serialize_message(odom))
                status=VehicleStatus(timestamp=now//1000,arming_state=VehicleStatus.ARMING_STATE_DISARMED,
                                     pre_flight_checks_pass=True)
                bridge._on_vehicle_status(status)
                local=VehicleLocalPosition(timestamp=now//1000,x=3.,y=4.,z=-.2,
                    xy_valid=True,z_valid=True,heading_good_for_control=True,heading=yaw)
                bridge._on_local_position(local)
                bridge._on_attitude(VehicleAttitude(timestamp=now//1000,
                    q=[math.cos(yaw/2),0.,0.,math.sin(yaw/2)]))
                bridge._on_estimator_flags(EstimatorStatusFlags(timestamp=now//1000,
                    cs_ev_pos=counts['ev']>0,cs_ev_hgt=counts['ev']>0,cs_ev_yaw=counts['ev']>0,cs_yaw_align=True))
                bridge._on_land_detected(VehicleLandDetected(timestamp=now//1000,landed=True))
                if disabled_counts is None and time.monotonic()-started >= 3.:
                    disabled_counts = dict(counts)
                    assert counts['mode']==counts['setpoint']==counts['command']==0, counts
                    response = bridge._on_enable(EnableOffboard.Request(enable=True), EnableOffboard.Response())
                    assert response.accepted, response.reason
                rclpy.spin_once(bridge,timeout_sec=.001)
                rclpy.spin_once(observer,timeout_sec=.001)
            assert counts['ev'] > 10, counts
            assert disabled_counts is not None
            assert counts['mode']>0 and counts['setpoint']>0 and counts['command']>0, counts
            assert bridge.alignment is not None
            assert abs(bridge.alignment.yaw_offset_ned-.37)<1e-6, bridge.alignment
            assert bridge.alignment_drift_m<1e-6
            cmd=PositionCommand(epoch=epoch,goal_id='fixture',trajectory_id=1,trajectory_flag=1,yaw=0.)
            cmd.header.frame_id='odom_'+epoch
            cmd.position.x=matrix[3];cmd.position.y=-matrix[7];cmd.position.z=-matrix[11]
            output=position_command_to_ned(cmd,bridge.profile,bridge.frame_contract,expected_epoch=epoch,
                origin_offset_ned=bridge.alignment.origin_offset_ned,
                yaw_offset_ned=bridge.alignment.yaw_offset_ned,
                sensor_leverarm_body_frd=bridge.sensor_leverarm_frd)
            assert max(abs(a-b) for a,b in zip(output.position,(3,4,-.2)))<1e-6,output
            # Receipt freshness and command source-age failures remain active.
            saved_receipt=bridge.timesync_receipt_ns
            bridge.timesync_receipt_ns=time.monotonic_ns()-3000000000
            assert not bridge._timesync_fresh()
            bridge.timesync_receipt_ns=saved_receipt
            bridge.position_command=cmd
            bridge.position_command_receipt_ns=time.monotonic_ns()
            assert not bridge._trajectory_is_ready(time.monotonic_ns())
            assert bridge.trajectory_fault=='trajectory_stale_or_future'
            print(json.dumps(dict(scope='isolated synthetic domain83; no physical PX4',
                counts=counts,disabled_counts=disabled_counts,alignment_yaw_rad=bridge.alignment.yaw_offset_ned,
                alignment_drift_m=bridge.alignment_drift_m,body_setpoint=output.position,
                supervisor=bridge.supervisor.phase,clock_subscription=False)))
        finally:
            if bridge: bridge.destroy_node()
            if observer: observer.destroy_node()
            rclpy.shutdown()


if __name__=='__main__':
    main()
