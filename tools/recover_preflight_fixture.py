#!/usr/bin/env python3
"""Return and remove a detached-safe N05 support fixture while PX4 is disarmed.

This helper publishes only Gazebo fixture joint targets and its detach topic.
It never publishes PX4 control, Offboard, or navigation-goal messages.
"""
import argparse
import json
import math
from pathlib import Path
import re
import subprocess
import time


ROOT = Path(__file__).resolve().parents[1]
AXES = ('x', 'z', 'yaw', 'pitch')


def _gz_model_names(timeout_s=10.0):
    result = subprocess.run(['gz', 'model', '--list'], capture_output=True,
                            text=True, timeout=timeout_s, check=False)
    if result.returncode != 0:
        raise RuntimeError('Gazebo model-list query failed: '+result.stderr[-500:])
    return set(re.findall(r'^\s*-\s+([^\s]+)\s*$', result.stdout, re.MULTILINE))


def _rpy_blend(fraction):
    fraction = min(1.0, max(0.0, fraction))
    return .5 - .5 * math.cos(math.pi * fraction)


def _persisted_attachment_is_current(fixture_report, fixture_present,
                                     release_marker_exists, scanner_running):
    return bool(
        fixture_present and not release_marker_exists and not scanner_running
        and fixture_report.get('attachment_states')
        and fixture_report['attachment_states'][-1] == 'attached'
        and fixture_report.get('fixture_may_remain_attached') is True
        and fixture_report.get('fixture_removed') is False
        and fixture_report.get('n05_live_check_completed') is False)


def main():
    import gz.transport13 as transport
    from gz.msgs10.boolean_pb2 import Boolean
    from gz.msgs10.double_pb2 import Double
    from gz.msgs10.empty_pb2 import Empty
    from gz.msgs10.entity_pb2 import Entity
    from gz.msgs10.model_pb2 import Model
    from gz.msgs10.stringmsg_pb2 import StringMsg
    import rclpy
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data, QoSProfile, ReliabilityPolicy, DurabilityPolicy
    from px4_msgs.msg import VehicleStatus
    from rosgraph_msgs.msg import Clock
    from uav_interfaces.msg import Px4BridgeStatus

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir', type=Path, required=True)
    parser.add_argument('--wall-timeout-s', type=float, default=120.0)
    args = parser.parse_args()
    if not math.isfinite(args.wall_timeout_s) or args.wall_timeout_s < 10:
        raise ValueError('--wall-timeout-s must be finite and at least 10 seconds')
    run_dir = args.run_dir.resolve()
    if not run_dir.is_dir() or not str(run_dir).startswith(str(ROOT/'artifacts/runs')):
        raise ValueError('--run-dir must point to an existing project run directory')

    policy = json.loads((ROOT/'config/components/simulation/preflight_scan.json').read_text())
    bridge_policy = json.loads((ROOT/'config/components/px4_bridge/debug_truth.json').read_text())
    freshness = bridge_policy['px4_status_max_receipt_age_wall_s']
    bridge_freshness = min(.5, bridge_policy['status_period_wall_s'] * 5.0)
    fixture_name = policy['fixture_model']
    model_names = _gz_model_names()
    if fixture_name not in model_names:
        raise RuntimeError(f'{fixture_name} is not present in the live Gazebo scene')
    fixture_result_path = run_dir/'fixture-result.json'
    if not fixture_result_path.is_file():
        raise RuntimeError('fixture-result.json is required before recovery')
    previous_fixture_report = json.loads(fixture_result_path.read_text())
    release_marker = run_dir/'n05-release-fixture'
    process_list = subprocess.run(['ps', '-eo', 'args'], capture_output=True,
                                  text=True, timeout=5.0, check=False).stdout
    scanner_token = 'probe_preflight_scan.py --run '+str(run_dir)
    scanner_running = any(scanner_token in line for line in process_list.splitlines())
    persisted_attachment = _persisted_attachment_is_current(
        previous_fixture_report, fixture_name in model_names,
        release_marker.exists(), scanner_running)

    rclpy.init()
    ros = Node('n05_support_fixture_recovery', parameter_overrides=[
        rclpy.parameter.Parameter('use_sim_time', value=True)])
    gz = transport.Node()
    state = {'vehicle': None, 'vehicle_receipt': 0.0,
             'bridge': None, 'bridge_receipt': 0.0,
             'clock': 0, 'joints': {}, 'attachment': []}
    if persisted_attachment:
        # The detachable-joint status publisher emits transitions only, not a
        # latched current value. Reuse the final recorded `attached` transition
        # only when there was no release request, scanner, or model removal.
        state['attachment'] = ['attached']
    events = []
    qos_bridge = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                            durability=DurabilityPolicy.VOLATILE)

    def on_vehicle(msg):
        state['vehicle'] = msg
        state['vehicle_receipt'] = time.monotonic()

    def on_bridge(msg):
        state['bridge'] = msg
        state['bridge_receipt'] = time.monotonic()

    def on_clock(msg):
        state['clock'] = msg.clock.sec * 1_000_000_000 + msg.clock.nanosec

    def on_joints(msg):
        for joint in msg.joint:
            if joint.name in AXES:
                state['joints'][joint.name] = (joint.axis1.position, joint.axis1.velocity)

    ros.create_subscription(VehicleStatus, bridge_policy['vehicle_status_topic'],
                            on_vehicle, qos_profile_sensor_data)
    ros.create_subscription(Px4BridgeStatus, bridge_policy['status_topic'],
                            on_bridge, qos_bridge)
    ros.create_subscription(Clock, '/clock', on_clock, qos_profile_sensor_data)
    gz.subscribe(Model, policy['joint_state_topic'], on_joints)
    gz.subscribe(StringMsg, policy['attachment_status_topic'],
                 lambda msg: state['attachment'].append(msg.data))
    publishers = {axis: gz.advertise('/preflight_scan/'+axis, Double) for axis in AXES}
    detach_pub = gz.advertise('/preflight_scan/detach', Empty)
    report = {
        'schema': 'n05-support-fixture-recovery/v1',
        'scope': 'Gazebo fixture joints/detach only; no PX4 control or navigation goal',
        'run_id': run_dir.name,
        'fixture_model': fixture_name,
        'outcome': 'failed',
        'fixture_joint_commands': 0,
        'attachment_states': [],
        'attachment_confirmation_source': (
            'persisted attached event + fixture model present + no release marker/scanner'
            if persisted_attachment else 'live Gazebo attachment transition'),
        'control_or_goal_published': False,
        'vehicle_states': [],
        'error': '',
    }

    def safe_state():
        now = time.monotonic()
        vehicle = state['vehicle']
        bridge = state['bridge']
        if (vehicle is None or now-state['vehicle_receipt'] > freshness
                or vehicle.arming_state != VehicleStatus.ARMING_STATE_DISARMED):
            raise RuntimeError('fresh PX4 DISARMED status is required for fixture recovery')
        if (bridge is None or now-state['bridge_receipt'] > bridge_freshness
                or bridge.armed or bridge.control_enabled or bridge.phase != 'DISABLED'
                or not bridge.landed):
            raise RuntimeError('fresh bridge DISABLED/disarmed/landed state is required')
        report['vehicle_states'].append(int(vehicle.arming_state))
        report['last_bridge_state'] = {
            'phase': bridge.phase, 'armed': bool(bridge.armed),
            'control_enabled': bool(bridge.control_enabled), 'landed': bool(bridge.landed),
            'epoch': bridge.epoch,
        }

    def spin_step(require_attached=True):
        rclpy.spin_once(ros, timeout_sec=.03)
        safe_state()
        if require_attached and state['attachment'] and state['attachment'][-1] != 'attached':
            raise RuntimeError('fixture detached during recovery return movement')
        if state['clock'] <= 0:
            raise RuntimeError('Gazebo simulation clock is unavailable during fixture recovery')
        return state['clock'] / 1e9

    try:
        deadline = time.monotonic() + min(30.0, args.wall_timeout_s)
        while time.monotonic() < deadline:
            rclpy.spin_once(ros, timeout_sec=.05)
            if (state['vehicle'] is not None and state['bridge'] is not None
                    and len(state['joints']) == len(AXES) and state['attachment']):
                safe_state()
                if state['attachment'][-1] != 'attached':
                    raise RuntimeError('fixture attachment is not confirmed attached')
                break
        else:
            missing = []
            for name, value in (('vehicle_status', state['vehicle']),
                                ('bridge_status', state['bridge']),
                                ('joint_state', state['joints'] if len(state['joints']) == len(AXES) else None),
                                ('attachment', state['attachment'] or None)):
                if value is None:
                    missing.append(name)
            raise TimeoutError('timed out waiting for attached fixture and fresh disarmed state; '
                               f'missing={missing}; persisted_attachment={persisted_attachment}')

        initial = {axis: state['joints'][axis][0] for axis in AXES}
        limits = {'x': (0.0, 1.5), 'z': (0.0, 1.0),
                  'yaw': (-7.0, 7.0), 'pitch': (-0.7, 0.7)}
        for axis, value in initial.items():
            if not math.isfinite(value) or not limits[axis][0] <= value <= limits[axis][1]:
                raise RuntimeError(f'fixture {axis} joint is outside its modeled range: {value}')
        report['initial_joints'] = initial
        report['initial_sim_clock_ns'] = state['clock']
        begin = spin_step()
        duration = 5.0
        wall_deadline = time.monotonic() + args.wall_timeout_s
        while True:
            now_sim = spin_step()
            fraction = (now_sim-begin)/duration
            blend = _rpy_blend(fraction)
            for axis in AXES:
                value = initial[axis] * (1.0-blend)
                message = Double()
                message.data = value
                publishers[axis].publish(message)
                report['fixture_joint_commands'] += 1
            joints_ready = all(abs(state['joints'][axis][0]) <= .02
                               and abs(state['joints'][axis][1]) <= .04 for axis in AXES)
            if fraction >= 1.0 and joints_ready:
                break
            if time.monotonic() >= wall_deadline:
                raise TimeoutError('timed out returning support fixture to its initial position')
            time.sleep(.03)

        report['returned_joints'] = {axis: list(state['joints'][axis]) for axis in AXES}
        if state['attachment'][-1] != 'attached':
            raise RuntimeError('fixture detached before recovery returned it to its initial pose')
        detach_pub.publish(Empty())
        report['detach_published'] = True
        detach_deadline = time.monotonic() + min(20.0, args.wall_timeout_s)
        while time.monotonic() < detach_deadline:
            spin_step(require_attached=False)
            if state['attachment'][-1] == 'detached':
                break
            time.sleep(.03)
        if not state['attachment'] or state['attachment'][-1] != 'detached':
            raise TimeoutError('fixture detach was not acknowledged')
        report['attachment_states'] = list(state['attachment'])

        remove = Entity()
        remove.name = fixture_name
        remove.type = Entity.MODEL
        requested, response = gz.request('/world/'+policy['world']+'/remove',
                                         remove, Entity, Boolean, 3000)
        remove_ack = bool(requested and response.data)
        names = _gz_model_names()
        report['fixture_removal_confirmation'] = {
            'remove_service_acknowledged': remove_ack,
            'scene_model_absent': fixture_name not in names,
            'scene_model_names': sorted(names),
        }
        if fixture_name in names:
            raise RuntimeError('fixture model remains in the Gazebo scene after detach')

        # Confirm the aircraft remains on its support and PX4 remains disarmed
        # before the project container is allowed to stop.
        final_deadline = time.monotonic() + 2.0
        while time.monotonic() < final_deadline:
            spin_step(require_attached=False)
            time.sleep(.03)
        report['attachment_states'] = list(state['attachment'])
        report['final_sim_clock_ns'] = state['clock']
        report['outcome'] = 'fixture_returned_detached_and_removed'
    except Exception as exc:
        report['error'] = str(exc)
        if state['attachment']:
            report['attachment_states'] = list(state['attachment'])
        if len(state['joints']) == len(AXES):
            report['last_joint_state'] = {axis: list(state['joints'][axis]) for axis in AXES}
        raise
    finally:
        report_path = run_dir/'n05-recovery.json'
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
        ros.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
