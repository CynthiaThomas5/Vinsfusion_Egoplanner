#!/usr/bin/env python3
"""Unarmed whole-airframe physical-support experiment; no navigation or PX4 writes."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import signal
import subprocess
import time

import xml.etree.ElementTree as ET

AXES = ('x', 'z', 'yaw', 'pitch')
PROFILE_CHOICES = (
    'smoke', 'coverage', 'n06_extended_reach', 'n06_extended_reach_slow_x',
    'n06_extended_reach_slow_x_pitch60',
    'n06_extended_reach_slow_x_pitch60_single_yaw',
    'n06_extended_reach_slow_x_pitch45_yaw0',
    'n06_full_airframe_retreat_240',
    'n06_full_airframe_retreat_240_translation_only',
    'n06_full_airframe_retreat_240_segmented_actual_return',
    'n06_full_airframe_retreat_240_oblique_site_view',
    'n06_full_airframe_retreat_240_oblique_separated_return',
    'n06_full_airframe_retreat_240_oblique_early_view',
    'n08_far_small_pitch_view',
    'n08_far_overhead_neutral_view',
    'n08_overhead_free_sector_view',
    'n08_overhead_free_sector_with_negative_side_view',
    'n08_overhead_free_sector_with_negative_side_recovery',
    'n08_overhead_free_sector_negative_side_short_dwell',
    'n08_overhead_free_sector_negative_y_side_view',
    'n08_overhead_free_sector_negative_y_rear_view',
    'n08_overhead_free_sector_negative_y_rear_short_hold',
    'n08_overhead_free_sector_negative_y_rear_short_hold_slow_descent',
    'n08_overhead_free_sector_negative_y_rear_short_hold_slow_return_slow_descent',
    'n08_overhead_free_sector_negative_y_rear_short_hold_slow_return_pitch_down_descent',
    'n08_overhead_free_sector_negative_y_rear_short_hold_slow_return_segmented_neutral_descent',
    'n08_overhead_free_sector_negative_y_rear_short_hold_low_rear_view',
    'n08_overhead_free_sector_negative_y_rear_short_hold_low_rear_view_separated_pitch',
    'n08_overhead_free_sector_negative_y_rear_short_hold_low_rear_view_neutral_yaw_pitch_only_rear',
    'n08_overhead_free_sector_negative_y_rear_short_hold_low_rear_view_midheight_yaw_pitch_only_rear',
    'n08_overhead_free_sector_view_decoupled_return',
    'n08_overhead_free_sector_view_decoupled_slow_vertical_return',
    'n08_overhead_free_sector_view_decoupled_slow_vertical_return_negative_side',
    'n08_overhead_free_sector_negative_side_slow_descent',
    'n08_overhead_free_sector_view_steeper',
    'n08_overhead_negative_side_view',
    'n08_overhead_rear_facing_view',
    'n08_overhead_rear_down_view',
    'n08_overhead_rear_down_slow_yaw_return',
    'n08_terminal_horizontal_views',
    'n08_terminal_horizontal_views_via_neutral',
    'n08_overhead_rear_one_side_view',
    'n08_overhead_positive_side_view',
    'n07_default_spawn_translation_only',
    'n07_default_spawn_bidirectional_translation_only',
    'n07_spawn_minus65_retreat_150_translation_only',
    'n07_spawn_minus65_retreat_180_translation_only',
    'n07_spawn_minus65_retreat_180_yaw015rad_view',
    'n07_spawn_minus65_retreat_180_yaw015rad_return_view',
    'n07_spawn_minus65_retreat_180_pitch045_view',
    'n07_spawn_minus65_retreat_180_pitch045_return_view',
    'drift', 'loop_revisit',
)


def _localization_gate_diagnostic(loc, expected_epoch, receipt_wall_s,
                                  now_wall_s, tracking_state, sim_time_ns):
    """Describe localization presence/state/epoch without a receipt-age gate."""
    age = now_wall_s-receipt_wall_s if loc is not None else None
    source_stamp = getattr(loc, 'source_stamp', None) if loc is not None else None
    source_stamp_ns = None
    if source_stamp is not None:
        source_stamp_ns = int(source_stamp.sec)*1_000_000_000+int(source_stamp.nanosec)
    observed_state = int(loc.state) if loc is not None else None
    valid = bool(loc.valid) if loc is not None else None
    observed_epoch = str(loc.epoch) if loc is not None else None
    failures = []
    if loc is None:
        failures.append('missing')
    else:
        if not valid:
            failures.append('invalid')
        if observed_state != int(tracking_state):
            failures.append('not_tracking')
        if observed_epoch != expected_epoch:
            failures.append('epoch_mismatch')
    return {
        'failed': bool(failures),
        'failures': failures,
        'valid': valid,
        'state': observed_state,
        'tracking_state': int(tracking_state),
        'reason': str(loc.reason) if loc is not None else None,
        'observed_epoch': observed_epoch,
        'expected_epoch': expected_epoch,
        'receipt_age_wall_s': age,
        'receipt_age_gate_enforced': False,
        'source_stamp_ns': source_stamp_ns,
        'sim_time_ns': int(sim_time_ns),
    }


def _gz_model_names(timeout_s=10.0):
    """Return the live Gazebo model names, or raise if the query is inconclusive."""
    completed = subprocess.run(['gz', 'model', '--list'], capture_output=True,
                               text=True, timeout=timeout_s, check=False)
    if completed.returncode != 0:
        raise RuntimeError('Gazebo model-list query failed: '+completed.stderr[-500:])
    return set(re.findall(r'^\s*-\s+([^\s]+)\s*$', completed.stdout, re.MULTILINE))


def _confirm_fixture_removed(model_name, remove_acknowledged, timeout_s=8.0):
    deadline = time.monotonic()+timeout_s
    names = set()
    while True:
        names = _gz_model_names(timeout_s=max(1.0, min(10.0, deadline-time.monotonic())))
        if model_name not in names:
            return {
                'remove_service_acknowledged': bool(remove_acknowledged),
                'scene_model_absent': True,
                'method': 'gz model --list after detach/removal request',
                'scene_model_names': sorted(names),
            }
        if time.monotonic() >= deadline:
            return {
                'remove_service_acknowledged': bool(remove_acknowledged),
                'scene_model_absent': False,
                'method': 'gz model --list after detach/removal request',
                'scene_model_names': sorted(names),
            }
        time.sleep(.25)


def fixture_pose_returned(joint_states, position_tolerance=.015,
                          velocity_tolerance=.03):
    """Check the fixture's initial physical pose, treating yaw modulo 2*pi."""
    for axis, (position, velocity) in joint_states.items():
        error = math.remainder(position, 2.0*math.pi) if axis == 'yaw' else position
        if abs(error) > position_tolerance or abs(velocity) > velocity_tolerance:
            return False
    return True


def validate_profile(policy, model_path, profile="smoke"):
    model = ET.parse(model_path).getroot().find('model')
    limits = [tuple(float(model.findtext(f"joint[@name='{axis}']/axis/limit/{bound}"))
                    for bound in ('lower', 'upper')) for axis in AXES]
    legs = policy[profile+'_profile']
    if not isinstance(legs, list) or not legs:
        raise ValueError('a bounded scan profile is required')
    for leg in legs:
        if ('start_from_actual' in leg
                and not isinstance(leg['start_from_actual'], bool)):
            raise ValueError('start_from_actual must be boolean')
        duration = leg['duration_sim_s']
        target = leg['target']
        if (isinstance(duration, bool) or not isinstance(duration, (int, float))
                or not math.isfinite(duration) or duration <= 0):
            raise ValueError('scan duration must be positive and finite')
        if not isinstance(target, list) or len(target) != len(AXES):
            raise ValueError('scan target must contain x,z,yaw,pitch')
        for value, (lower, upper) in zip(target, limits):
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or not lower <= value <= upper):
                raise ValueError('scan target outside physical joint bounds')
    if profile in ('drift', 'loop_revisit'):
        protocol = policy[profile+'_measurement']
        references = [leg for leg in legs if leg.get('label') == 'reference']
        returns = [leg for leg in legs if leg.get('label') == 'return']
        if len(references) != 1 or len(returns) != protocol['required_returns']:
            raise ValueError('drift profile requires one reference and all returns')
        if [leg.get('cycle') for leg in returns] != list(range(1, protocol['required_returns']+1)):
            raise ValueError('return cycles must be consecutive')
        if sum(leg['duration_sim_s'] for leg in legs) < protocol['minimum_duration_sim_s']:
            raise ValueError('drift profile is shorter than the measurement interval')
        for index, leg in enumerate(legs):
            if leg.get('label') in ('reference', 'return'):
                if (index == 0 or legs[index-1]['target'] != leg['target']
                        or leg['target'] != references[0]['target']
                        or leg['duration_sim_s'] <= protocol['stationary_tail_sim_s']):
                    raise ValueError('reference/return measurement must end with a stationary hold at the same pose')


def _layout_model(obj, model_name, offset_xy, spawn_yaw):
    """Build a static Gazebo model from the selected N04 layout object."""
    x, y, z, roll, pitch, yaw = obj['pose_xyz_rpy_m_rad']
    c, s = math.cos(spawn_yaw), math.sin(spawn_yaw)
    pose = [offset_xy[0] + c*x - s*y, offset_xy[1] + s*x + c*y,
            z, roll, pitch, yaw + spawn_yaw]
    geometry = ET.Element('geometry')
    if obj['shape'] == 'box':
        box = ET.SubElement(geometry, 'box')
        ET.SubElement(box, 'size').text = ' '.join(map(str, obj['size_m']))
    elif obj['shape'] == 'cylinder':
        cylinder = ET.SubElement(geometry, 'cylinder')
        ET.SubElement(cylinder, 'radius').text = str(obj['radius_m'])
        ET.SubElement(cylinder, 'length').text = str(obj['length_m'])
    else:
        raise ValueError(f"unsupported N05 layout shape: {obj['shape']}")
    sdf = ET.Element('sdf', version='1.9')
    model = ET.SubElement(sdf, 'model', name=model_name)
    ET.SubElement(model, 'static').text = 'true'
    ET.SubElement(model, 'pose').text = ' '.join(map(str, pose))
    link = ET.SubElement(model, 'link', name='body')
    collision = ET.SubElement(link, 'collision', name='collision')
    collision.append(ET.fromstring(ET.tostring(geometry)))
    visual = ET.SubElement(link, 'visual', name='visual')
    visual.append(ET.fromstring(ET.tostring(geometry)))
    material = ET.SubElement(visual, 'material')
    rgba = ' '.join(map(str, obj.get('rgba', [0.5, 0.5, 0.5, 1.0])))
    ET.SubElement(material, 'ambient').text = rgba
    ET.SubElement(material, 'diffuse').text = rgba
    return ET.ElementTree(sdf)


def main():
    import gz.transport13 as transport
    from gz.msgs10.boolean_pb2 import Boolean
    from gz.msgs10.double_pb2 import Double
    from gz.msgs10.empty_pb2 import Empty
    from gz.msgs10.entity_factory_pb2 import EntityFactory
    from gz.msgs10.entity_pb2 import Entity
    from gz.msgs10.model_pb2 import Model
    from gz.msgs10.stringmsg_pb2 import StringMsg
    import rclpy
    from rclpy.signals import SignalHandlerOptions
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data, QoSProfile, ReliabilityPolicy, DurabilityPolicy
    from px4_msgs.msg import VehicleStatus, VehicleLandDetected
    from uav_interfaces.msg import LocalizationStatus, MapStatus
    from std_msgs.msg import String
    from nav_msgs.msg import Odometry
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--profile', choices=PROFILE_CHOICES, default='smoke')
    parser.add_argument('--n05-layout', choices=(
        'wall_box_column', 'corridor_box_column', 'n08_overhead_calibration'))
    parser.add_argument('--hold-for-live-check', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    args.run = args.run.resolve()
    trace_path = args.run/'fixture-trace.jsonl'
    if trace_path.exists():
        raise FileExistsError(trace_path)
    if args.hold_for_live_check and not args.n05_layout:
        raise ValueError('--hold-for-live-check requires --n05-layout')
    ready_marker = args.run/'n05-prescan-ready.json'
    release_marker = args.run/'n05-release-fixture'
    if ready_marker.exists() or release_marker.exists():
        raise FileExistsError('N05 support-scan markers already exist')
    policy = json.loads((root/'config/components/simulation/preflight_scan.json').read_text())
    validate_profile(policy, root/'simulation/models/preflight_scan_fixture/model.sdf', args.profile)
    bridge = json.loads((root/'config/components/px4_bridge/debug_truth.json').read_text())
    runtime = json.loads((root/'config/runtime.json').read_text())
    spawn = [float(v) for v in runtime['spawn_pose'].split(',')]
    # Keep the ROS context alive until the fixture has returned and detached.
    # rclpy's default SIGINT handler shuts it down before our finally block.
    cancel_requested = False
    def request_cancel(_signum, _frame):
        nonlocal cancel_requested
        cancel_requested = True
    signal.signal(signal.SIGINT, request_cancel)
    signal.signal(signal.SIGTERM, request_cancel)
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    ros = Node('unarmed_physical_scan_probe', parameter_overrides=[
        rclpy.parameter.Parameter('use_sim_time', value=True)])
    gz = transport.Node()
    latest = {}
    initial_map_id = ''
    joint_states = {}
    attachment = []
    vehicle_states = []
    landed_states = []
    qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                     durability=DurabilityPolicy.TRANSIENT_LOCAL)

    def vehicle(msg):
        latest['vehicle'] = (msg.arming_state,time.monotonic())
        vehicle_states.append(msg.arming_state)

    def land_detected(msg):
        latest['landed'] = (bool(msg.landed),time.monotonic())
        landed_states.append(bool(msg.landed))

    def joints(msg):
        for joint in msg.joint:
            if joint.name in ('x','z','yaw','pitch'):
                joint_states[joint.name] = (joint.axis1.position, joint.axis1.velocity)

    ros.create_subscription(VehicleStatus, bridge['vehicle_status_topic'],vehicle,qos_profile_sensor_data)
    ros.create_subscription(VehicleLandDetected, bridge['vehicle_land_detected_topic'],
                            land_detected,qos_profile_sensor_data)
    ros.create_subscription(LocalizationStatus, '/localization/status',lambda m:latest.update(loc=m,loc_received=time.monotonic()),qos)
    ros.create_subscription(MapStatus, '/mapping/status',lambda m:latest.update(map=m),qos)
    gz.subscribe(Model, policy['joint_state_topic'], joints)
    gz.subscribe(StringMsg, policy['attachment_status_topic'],lambda m:attachment.append(m.data))
    publishers = {axis:gz.advertise('/preflight_scan/'+axis,Double) for axis in ('x','z','yaw','pitch')}
    detach = gz.advertise('/preflight_scan/detach',Empty)
    deadline = time.monotonic()+policy.get(args.profile+'_max_wall_s',600.)
    targets = [0.,0.,0.,0.]
    initial_epoch = ''
    previous_ns = 0
    outcome = 'failed'
    error = ''
    stages = []
    layout_manifest=None
    started_wall = time.monotonic()
    trace = trace_path.open('w')
    telemetry = (args.run/'fixture-vins.jsonl').open('w')
    odometry = (args.run/'fixture-odometry.jsonl').open('w')
    safety_cleanup={'attempted':False,'verified_detached':False,'error':''}
    fixture_removed=False
    fixture_spawned=False
    fixture_removal_confirmation={'scene_model_absent':False,
                                  'remove_service_acknowledged':False}

    def step(require_health=True):
        nonlocal previous_ns
        if require_health and (cancel_requested or (args.run/'n05-cancel-scan').exists()):
            raise RuntimeError('operator_cancelled_support_scan')
        rclpy.spin_once(ros,timeout_sec=.02)
        if time.monotonic()>deadline:
            raise TimeoutError('fixture diagnostic wall deadline')
        stamp = ros.get_clock().now().nanoseconds
        if stamp < previous_ns:
            raise RuntimeError('clock regression during physical scan')
        previous_ns = stamp
        state,received = latest.get('vehicle',(None,0.))
        if (state != VehicleStatus.ARMING_STATE_DISARMED
                or time.monotonic()-received > bridge['px4_status_max_receipt_age_wall_s']):
            raise RuntimeError('fresh DISARMED status is required for every fixture command')
        loc = latest.get('loc')
        loc_diagnostic = _localization_gate_diagnostic(
            loc, initial_epoch, latest.get('loc_received',0), time.monotonic(),
            LocalizationStatus.TRACKING, stamp)
        if require_health and loc_diagnostic['failed']:
            raise RuntimeError('localization changed or became invalid during physical scan: '
                               +json.dumps(loc_diagnostic,sort_keys=True))
        if require_health and (latest.get('map') is None
                               or not latest['map'].input_ready
                               or latest['map'].epoch != initial_epoch
                               or latest['map'].map_id != initial_map_id):
            raise RuntimeError('map readiness or identity changed during physical scan')
        return stamp/1e9

    try:
        ready_deadline=time.monotonic()+60.
        while time.monotonic()<ready_deadline:
            rclpy.spin_once(ros,timeout_sec=.02)
            loc=latest.get('loc');state,receipt=latest.get('vehicle',(None,0.))
            map_status=latest.get('map')
            if (loc is not None and loc.valid and loc.state==LocalizationStatus.TRACKING
                    and state==VehicleStatus.ARMING_STATE_DISARMED
                    and map_status is not None and map_status.input_ready
                    and map_status.reset_acknowledged and map_status.epoch==loc.epoch
                    and map_status.map_id.startswith(loc.epoch+'-')
                    and time.monotonic()-receipt<bridge['px4_status_max_receipt_age_wall_s']):
                initial_epoch=loc.epoch
                initial_map_id=map_status.map_id
                def on_telemetry(msg):
                    telemetry.write(msg.data+'\n')
                def on_odom(msg,kind):
                    q=msg.pose.pose.orientation;p=msg.pose.pose.position;t=msg.header.stamp
                    twist=msg.twist.twist
                    odometry.write(json.dumps({'kind':kind,'source_ns':t.sec*10**9+t.nanosec,
                                               'receive_sim_ns':ros.get_clock().now().nanoseconds,
                                               'receive_monotonic_ns':time.monotonic_ns(),
                                               'frame':msg.header.frame_id,'child_frame':msg.child_frame_id,
                                               'xyz':[p.x,p.y,p.z],
                                               'q_xyzw':[q.x,q.y,q.z,q.w],
                                               'velocity_xyz':[twist.linear.x,twist.linear.y,twist.linear.z],
                                               'angular_velocity_xyz':[twist.angular.x,twist.angular.y,twist.angular.z]})+'\n')
                ros.create_subscription(String,f'/vins_raw/s_{initial_epoch}/estimator_telemetry',on_telemetry,10)
                ros.create_subscription(Odometry,f'/vins_raw/s_{initial_epoch}/odometry',
                                        lambda m:on_odom(m,'raw'),qos_profile_sensor_data)
                ros.create_subscription(Odometry,'/localization/optimized_imu_odom',
                                        lambda m:on_odom(m,'optimized'),qos_profile_sensor_data)
                break
        else:
            raise RuntimeError('no healthy/disarmed initial state')
        spawned_layout_models=[]
        if args.n05_layout:
            if args.n05_layout == 'n08_overhead_calibration':
                layout_config_path=root/'config/components/simulation/n08_overhead_calibration.json'
            else:
                layout_config_path=root/'config/components/simulation/n04_geometry_layouts.json'
            layout_cfg=json.loads(layout_config_path.read_text())
            layout_sources=[layout_config_path]
            if 'layouts' in layout_cfg:
                layouts={layout['id']:layout for layout in layout_cfg['layouts']}
                selected=layouts[args.n05_layout]
            else:
                if layout_cfg.get('layout_id') != args.n05_layout:
                    raise ValueError('N08 layout config id does not match selected layout')
                selected=dict(layout_cfg)
                base_layout_id=selected.get('base_layout_id')
                if base_layout_id:
                    base_config_path=root/'config/components/simulation/n04_geometry_layouts.json'
                    base_cfg=json.loads(base_config_path.read_text())
                    base_layouts={layout['id']:layout for layout in base_cfg['layouts']}
                    if base_layout_id not in base_layouts:
                        raise ValueError(f'unknown N08 base layout: {base_layout_id}')
                    selected['objects']=base_layouts[base_layout_id]['objects']+selected['objects']
                    layout_sources.append(base_config_path)
            if len({obj['name'] for obj in selected['objects']})!=len(selected['objects']):
                raise ValueError('N05 scene has duplicate layout object names')
            layout_dir=args.run/'n05-generated-layout'
            layout_dir.mkdir(parents=True,exist_ok=True)
            # Preserve room around the full airframe support scan. The selected
            # layout is shifted 1.5 m away from the initial IMU pose; the scan
            # records the exact generated SDF and offset for offline comparison.
            offset=(spawn[0]+1.5,spawn[1])
            for index,obj in enumerate(selected['objects']):
                model_name=f'n05_{args.n05_layout}_{index}'
                sdf_path=layout_dir/(model_name+'.sdf')
                _layout_model(obj,model_name,offset,spawn[5]).write(
                    sdf_path,encoding='utf-8',xml_declaration=True)
                request=EntityFactory();request.sdf_filename=str(sdf_path)
                request.name=model_name;request.allow_renaming=False
                created,response=gz.request('/world/'+policy['world']+'/create',
                                            request,EntityFactory,Boolean,3000)
                if not created or not response.data:
                    raise RuntimeError(f'N05 layout insertion rejected: {model_name}')
                spawned_layout_models.append(model_name)
            layout_manifest={
                'layout_id':args.n05_layout,
                'source_config':str(layout_config_path.relative_to(root)),
                'source_config_sha256':hashlib.sha256(layout_config_path.read_bytes()).hexdigest(),
                'source_configs':[{
                    'path':str(path.relative_to(root)),
                    'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                } for path in layout_sources],
                'base_layout_id':selected.get('base_layout_id'),
                'world_offset_xy_m':list(offset),'spawn_yaw_rad':spawn[5],
                'spawned_models':spawned_layout_models,
                'objects':selected['objects'],'online_truth_input':False,
            }
            (args.run/'n05-layout-scene.json').write_text(
                json.dumps(layout_manifest,indent=2)+'\n')
        request=EntityFactory()
        request.sdf_filename=str(root/'simulation/models/preflight_scan_fixture/model.sdf')
        request.name=policy['fixture_model']
        request.allow_renaming=False
        request.pose.position.x,request.pose.position.y=spawn[:2]
        request.pose.orientation.z=math.sin(spawn[5]/2)
        request.pose.orientation.w=math.cos(spawn[5]/2)
        success,response=gz.request('/world/'+policy['world']+'/create',request,EntityFactory,Boolean,3000)
        if not success or not response.data:
            raise RuntimeError('fixture insertion rejected')
        fixture_spawned=True
        while not attachment or len(joint_states)<4:
            step()
        if attachment[-1]!='attached':
            raise RuntimeError('fixture is not attached: '+str(attachment))
        for leg_index, leg in enumerate(policy[args.profile+'_profile']):
            begin=step()
            start=([joint_states[axis][0] for axis in AXES]
                   if leg.get('start_from_actual') else list(targets))
            duration=leg['duration_sim_s']
            while True:
                now=step()
                fraction=min(1.,max(0.,(now-begin)/duration))
                blend=.5-.5*math.cos(math.pi*fraction)
                targets=[a+(b-a)*blend for a,b in zip(start,leg['target'])]
                for axis,value in zip(('x','z','yaw','pitch'),targets):
                    msg=Double();msg.data=value;publishers[axis].publish(msg)
                trace.write(json.dumps({'sim_s':now,'target':targets,'joints':dict(joint_states),
                                       'leg_index':leg_index,'label':leg.get('label'), 'cycle':leg.get('cycle'),
                                       'epoch':initial_epoch,'attachment':attachment[-1],
                                       'localization':{'state':latest['loc'].state,'valid':latest['loc'].valid,
                                                       'reason':latest['loc'].reason,'normalized_cost':latest['loc'].normalized_cost}})+'\n')
                if fraction>=1:
                    break
                time.sleep(.03)
            stages.append({'leg_index':leg_index,'label':leg.get('label'),'cycle':leg.get('cycle'),
                           'begin_sim_s':begin,'end_sim_s':now,'target':leg['target']})
        if args.hold_for_live_check:
            if not attachment or attachment[-1] != 'attached':
                raise RuntimeError('support detached before the N05 online check')
            ready_marker.write_text(json.dumps({
                'schema':'n05-prescan-ready/v1','layout_id':args.n05_layout,
                'epoch':initial_epoch,'map_id':initial_map_id,
                'profile':args.profile,'completed_stages':len(stages),
                'attachment':'attached','vehicle_arming_state':latest['vehicle'][0],
                'pose_check_window':'fixture returned to initial physical pose; yaw equivalent modulo 2*pi',
                'truth_input_used':False,'control_or_goal_published':False,
            },indent=2)+'\n')
            while not release_marker.exists():
                step()
                if attachment[-1] != 'attached':
                    raise RuntimeError('support attachment changed during the online check')
                time.sleep(.05)
        if not fixture_pose_returned(joint_states):
            raise RuntimeError('fixture not returned to the floor before detach')
        detach.publish(Empty())
        while attachment[-1]!='detached':
            step()
        remove=Entity();remove.name=policy['fixture_model'];remove.type=Entity.MODEL
        removed,answer=gz.request('/world/'+policy['world']+'/remove',remove,Entity,Boolean,3000)
        remove_acknowledged=bool(removed and answer.data)
        fixture_removal_confirmation=_confirm_fixture_removed(
            policy['fixture_model'],remove_acknowledged)
        if not fixture_removal_confirmation['scene_model_absent']:
            raise RuntimeError('detached fixture model remains in the Gazebo scene')
        fixture_removed=True
        finish=step()+2.
        while step()<finish:
            pass
        outcome='unarmed_support_'+args.profile+'_completed'
    except Exception as exc:
        error=str(exc)
        raise
    finally:
        if attachment and attachment[-1] == 'attached':
            safety_cleanup['attempted']=True
            try:
                # On an interrupted scan, return the still-disarmed aircraft to
                # the fixture's initial support position before detaching it.
                deadline=max(deadline,time.monotonic()+120.)
                start=[joint_states[axis][0] for axis in ('x','z','yaw','pitch')]
                begin=ros.get_clock().now().nanoseconds/1e9
                duration=5.0
                while True:
                    now=step(require_health=False)
                    fraction=min(1.,max(0.,(now-begin)/duration))
                    blend=.5-.5*math.cos(math.pi*fraction)
                    targets=[value*(1.-blend) for value in start]
                    for axis,value in zip(('x','z','yaw','pitch'),targets):
                        msg=Double();msg.data=value;publishers[axis].publish(msg)
                    if fraction>=1. and all(abs(joint_states[axis][0])<=.02
                                            and abs(joint_states[axis][1])<=.04
                                            for axis in ('x','z','yaw','pitch')):
                        break
                    time.sleep(.03)
                detach.publish(Empty())
                detach_deadline=time.monotonic()+15.
                while attachment[-1] != 'detached' and time.monotonic()<detach_deadline:
                    step(require_health=False)
                    time.sleep(.03)
                if attachment[-1] != 'detached':
                    raise RuntimeError('recovery detach was not acknowledged')
                remove=Entity();remove.name=policy['fixture_model'];remove.type=Entity.MODEL
                removed,answer=gz.request('/world/'+policy['world']+'/remove',
                                          remove,Entity,Boolean,3000)
                remove_acknowledged=bool(removed and answer.data)
                fixture_removal_confirmation=_confirm_fixture_removed(
                    policy['fixture_model'],remove_acknowledged)
                if not fixture_removal_confirmation['scene_model_absent']:
                    raise RuntimeError('recovery fixture model remains in the Gazebo scene')
                fixture_removed=True
                safety_cleanup['verified_detached']=True
            except Exception as cleanup_exc:  # preserve the still-running project for monitoring
                safety_cleanup['error']=str(cleanup_exc)
        if fixture_removed and attachment and attachment[-1]=='detached':
            try:
                # Let PX4's land detector observe the returned, detached vehicle
                # before the project runner decides whether it may stop SITL.
                finish=ros.get_clock().now().nanoseconds/1e9+1.0
                while ros.get_clock().now().nanoseconds/1e9<finish:
                    step(require_health=False)
                    time.sleep(.03)
                landed,received=latest.get('landed',(None,0.))
                safety_cleanup['final_land_detector_landed']=landed
                safety_cleanup['final_land_detector_receipt_age_wall_s']=(
                    None if not received else time.monotonic()-received)
                safety_cleanup['verified_landed']=bool(
                    landed is True and time.monotonic()-received
                    <= bridge['px4_status_max_receipt_age_wall_s'])
                if not safety_cleanup['verified_landed']:
                    safety_cleanup['land_detector_error']=(
                        'final PX4 land detector did not confirm a fresh landed state')
            except Exception as land_exc:
                safety_cleanup['land_detector_error']=str(land_exc)
        trace.close()
        telemetry.close()
        odometry.close()
        (args.run/'fixture-stages.json').write_text(json.dumps(stages,indent=2)+'\n')
        report={'scope':'unarmed whole-airframe physical-support experiment only; not free flight or localization accuracy approval',
                'outcome':outcome,'error':error,'epoch':initial_epoch,'profile':args.profile,
                'wall_duration_s':time.monotonic()-started_wall,'completed_stages':len(stages),
                'n05_layout':layout_manifest,
                'n05_live_check_requested':bool(args.hold_for_live_check),
                'n05_live_check_completed':release_marker.exists(),
                'safety_cleanup':safety_cleanup,
                'last_localization':None if 'loc' not in latest else {'state':latest['loc'].state, 'valid':latest['loc'].valid,'reason':latest['loc'].reason,'normalized_cost':latest['loc'].normalized_cost},
                'vehicle_states':sorted(set(vehicle_states)),'vehicle_status_samples':len(vehicle_states),
                'vehicle_land_detected_samples':len(landed_states),
                'vehicle_land_detected_values':sorted(set(landed_states)),
                'final_landed':(None if 'landed' not in latest else latest['landed'][0]),
                'final_landed_receipt_age_wall_s':(
                    None if 'landed' not in latest else time.monotonic()-latest['landed'][1]),
                'attachment_states':attachment,'final_joint_states':dict(joint_states),
                'fixture_spawned':fixture_spawned,
                'fixture_removed':fixture_removed,
                'fixture_removal_confirmation':fixture_removal_confirmation,
                'fixture_may_remain_attached':bool(fixture_spawned and
                                                   (not attachment or attachment[-1]!='detached')),
                'publishers':'Gazebo fixture joints/detach only; no ROS control or goal publisher'}
        (args.run/'fixture-result.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report))
        ros.destroy_node()
        rclpy.shutdown()


if __name__=='__main__':
    main()
