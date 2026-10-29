#!/usr/bin/env python3
"""Bounded stationary VINS observation: subscriptions only, no control or fixture."""
import argparse
import json
from pathlib import Path
import time


def main():
    import rclpy
    from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, qos_profile_sensor_data
    from nav_msgs.msg import Odometry
    from px4_msgs.msg import VehicleStatus
    from std_msgs.msg import String
    from uav_interfaces.msg import LocalizationStatus

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    bridge = json.loads((root/'config/components/px4_bridge/debug_truth.json').read_text())
    rclpy.init()
    node = rclpy.create_node('readonly_prior_idle', parameter_overrides=[
        rclpy.parameter.Parameter('use_sim_time', value=True)])
    latest, states = {}, []
    qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)

    def vehicle(message):
        latest['vehicle'] = (message.arming_state, time.monotonic())
        states.append(message.arming_state)

    node.create_subscription(VehicleStatus, bridge['vehicle_status_topic'], vehicle, qos_profile_sensor_data)
    node.create_subscription(LocalizationStatus, '/localization/status',
                             lambda m: latest.update(loc=m, receipt=time.monotonic()), qos)
    outcome, error, epoch, start_ns, end_ns = 'failed', '', '', None, None
    with (args.run/'idle-vins.jsonl').open('x') as metrics, (args.run/'idle-odometry.jsonl').open('x') as odom:
        try:
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                rclpy.spin_once(node, timeout_sec=.02)
                loc = latest.get('loc')
                state, receipt = latest.get('vehicle', (None, 0))
                if (loc is not None and loc.valid and loc.state == LocalizationStatus.TRACKING
                        and state == VehicleStatus.ARMING_STATE_DISARMED
                        and node.get_clock().now().nanoseconds > 0
                        and time.monotonic()-receipt < bridge['px4_status_max_receipt_age_wall_s']):
                    epoch = loc.epoch
                    break
            else:
                raise RuntimeError('no healthy DISARMED initial state')

            def on_odom(message):
                p, q, stamp = message.pose.pose.position, message.pose.pose.orientation, message.header.stamp
                odom.write(json.dumps({'source_ns': stamp.sec*10**9+stamp.nanosec,
                                       'frame': message.header.frame_id, 'xyz': [p.x, p.y, p.z],
                                       'q_xyzw': [q.x, q.y, q.z, q.w]})+'\n')

            node.create_subscription(String, f'/vins_raw/s_{epoch}/estimator_telemetry',
                                     lambda m: metrics.write(m.data+'\n'), 10)
            node.create_subscription(Odometry, f'/vins_raw/s_{epoch}/odometry', on_odom, qos_profile_sensor_data)
            start_ns = node.get_clock().now().nanoseconds
            previous = start_ns
            deadline = time.monotonic()+600
            while True:
                rclpy.spin_once(node, timeout_sec=.02)
                end_ns = node.get_clock().now().nanoseconds
                if end_ns < previous or time.monotonic() > deadline:
                    raise RuntimeError('clock regression or wall deadline')
                previous = end_ns
                loc = latest['loc']
                state, receipt = latest['vehicle']
                if (state != VehicleStatus.ARMING_STATE_DISARMED
                        or time.monotonic()-receipt > bridge['px4_status_max_receipt_age_wall_s']):
                    raise RuntimeError('fresh DISARMED status required')
                if (not loc.valid or loc.epoch != epoch or loc.state != LocalizationStatus.TRACKING
                        ):
                    raise RuntimeError('same-epoch valid tracking localization required')
                if end_ns-start_ns >= 200_000_000_000:
                    break
            outcome = 'stationary_observation_completed'
        except Exception as exc:
            error = str(exc)
            raise
        finally:
            report = {'scope': __doc__, 'outcome': outcome, 'error': error, 'epoch': epoch,
                      'start_ns': start_ns, 'end_ns': end_ns, 'vehicle_states': sorted(set(states)),
                      'vehicle_status_samples': len(states), 'ros_or_gazebo_publishers_created': 0}
            (args.run/'idle-result.json').write_text(json.dumps(report, indent=2)+'\n')
            print(json.dumps(report))
            node.destroy_node()
            rclpy.shutdown()


if __name__ == '__main__':
    main()
