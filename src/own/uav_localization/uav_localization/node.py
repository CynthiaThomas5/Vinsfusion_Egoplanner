"""Adapt a fresh, immutable VINS session. No truth inputs, PX4 messages or control."""
from collections import deque
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re
import time

import rclpy
from rclpy.clock import Clock as ROSClock, ClockType
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import (qos_profile_sensor_data, QoSProfile, DurabilityPolicy,
                       ReliabilityPolicy)
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image, Imu
from std_msgs.msg import String
from rosgraph_msgs.msg import Clock
from uav_interfaces.msg import LocalizationStatus
from uav_sim.geometry import load_session_rig
from .image_metadata import image_metadata
from .health import (Health, PublisherEndpointNotReady, body_velocity,
                     interpolate_angular_velocity,
                     publisher_endpoint_identity,
                     publisher_endpoint_identity_changed, quaternion_diagnostic)


def stamp_ns(header):
    return header.stamp.sec*1000000000+header.stamp.nanosec


class Localization(Node):
    def __init__(self):
        super().__init__('localization_adapter')
        root = Path(self.declare_parameter('project_root','').value).resolve()
        path = Path(self.declare_parameter('session_manifest','').value).resolve()
        self.session = json.loads(path.read_text())
        self.epoch = self.session['epoch']
        if not re.fullmatch('[0-9a-f]{32}', self.epoch) or self.session['namespace'] != '/vins_raw/s_'+self.epoch:
            raise ValueError('Invalid session identity')
        for name,digest in self.session['files_sha256'].items():
            if Path(name).name != name or hashlib.sha256((path.parent/name).read_bytes()).hexdigest() != digest:
                raise ValueError('Session configuration hash mismatch')
        self.rig = load_session_rig(root, self.session)
        self.hardware_mode = self.rig.get('source_kind') == 'hardware_json'
        use_sim_time = bool(self.get_parameter('use_sim_time').value)
        if self.hardware_mode and use_sim_time:
            raise ValueError('Hardware localization requires use_sim_time=False')
        settings_relative = self.session.get(
            'settings_config', 'config/components/localization/vins_sim.json')
        settings_path = Path(settings_relative)
        if settings_path.is_absolute() or '..' in settings_path.parts:
            raise ValueError('Session settings path must be project-relative')
        settings_path = root/settings_path
        if root not in settings_path.parents:
            raise ValueError('Session settings path must stay inside the project root')
        settings = settings_path
        if hashlib.sha256(settings.read_bytes()).hexdigest() != self.session['settings_sha256']:
            raise ValueError('Session settings differ from project settings')
        self.settings = json.loads(settings.read_text())
        text = (path.parent/'vins.yaml').read_text()
        if not all(re.search(r'^'+key+r': '+str(value)+r'$',text,re.M) for key,value in [('imu',1),('num_of_cam',2),('estimate_extrinsic',0)]):
            raise ValueError('Adapter requires fixed-extrinsic stereo + IMU VINS')
        if self.hardware_mode:
            policy_relative = self.session.get('health_config')
            if (not isinstance(policy_relative, str) or Path(policy_relative).is_absolute()
                    or '..' in Path(policy_relative).parts
                    or not self.session.get('health_sha256')):
                raise ValueError('Hardware session must bind a relative freshness policy and hash')
            policy_path = root/policy_relative
            if root not in policy_path.parents or hashlib.sha256(policy_path.read_bytes()).hexdigest() != self.session['health_sha256']:
                raise ValueError('Hardware freshness policy differs from the generated session')
        else:
            policy_path = root/'config/components/localization/health.json'
        policy = json.loads(policy_path.read_text())
        self.require_solver_usable = bool(policy.get('solver_usable_required', self.hardware_mode))
        self.health = Health(policy,time.monotonic())
        # Consuming an epoch twice would silently reconnect two sessions.
        with (path.parent/'.localization-used').open('x') as marker:
            marker.write(self.epoch+'\n')
        self.raw_world = f'vins_{self.epoch}_world'
        self.raw_body = f'vins_{self.epoch}_imu'
        self.world = f'odom_{self.epoch}'
        self.body = f'd435i_imu_{self.epoch}'
        self.pending = {}
        self.published = {'optimized':None,'propagated':None}
        self.counts = {'optimized':0,'propagated':0}
        self.future_observation_logged = False
        self.health_lockout_logged = False
        self.post_lock_telemetry_logged = False
        self.last_age_log_wall = 0.0
        self.latest_optimized_pose = None
        self.gids = {}
        self.vins_node = None
        self.imu = deque(maxlen=1000)
        optimized_qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)
        self.output = {
            'optimized': self.create_publisher(
                Odometry, '/localization/optimized_imu_odom', optimized_qos),
            'propagated': self.create_publisher(
                Odometry, '/localization/imu_odom', qos_profile_sensor_data),
        }
        self.status_pub = self.create_publisher(LocalizationStatus,'/localization/status',QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
        ns = self.session['namespace']
        self.topics = {'optimized':ns+'/odometry','propagated':ns+'/imu_propagate','telemetry':ns+'/estimator_telemetry'}
        imu_topic = self.settings.get('imu_topic')
        image_topics = [self.settings.get('image0_topic'), self.settings.get('image1_topic')]
        if (not isinstance(imu_topic, str) or not imu_topic.startswith('/')
                or any(not isinstance(topic, str) or not topic.startswith('/')
                       for topic in image_topics)):
            raise ValueError('Session settings must provide absolute IMU and stereo image topics')
        self.subscriptions_owned = []
        if not self.hardware_mode:
            self.subscriptions_owned.append(self.create_subscription(
                Clock,'/clock',self.on_clock,qos_profile_sensor_data))
        self.subscriptions_owned.extend([
            self.create_subscription(Imu,imu_topic,self.on_imu,qos_profile_sensor_data),
            self.create_subscription(String,self.topics['telemetry'],self.on_telemetry,qos_profile_sensor_data),
        ])
        for kind,topic in zip(('left','right'),image_topics):
            self.subscriptions_owned.append(self.create_subscription(
                Image, topic,
                (lambda msg,k=kind:self.on_serialized_image(k,msg)) if self.hardware_mode
                else (lambda msg,k=kind:self.on_image(k,msg)),
                qos_profile_sensor_data, raw=self.hardware_mode))
        # Explicit two-argument callbacks retain DDS publisher identity.
        def optimized(msg):self.on_raw('optimized',msg)
        def propagated(msg):self.on_raw('propagated',msg)
        self.subscriptions_owned.extend([self.create_subscription(Odometry,self.topics['optimized'],optimized,qos_profile_sensor_data),
                                         self.create_subscription(Odometry,self.topics['propagated'],propagated,qos_profile_sensor_data)])
        self.timer = self.create_timer(self.health.status_period_wall_s,self.on_timer,clock=ROSClock(clock_type=ClockType.STEADY_TIME))
        self.status()

    def fault(self,reason):
        self.health.fail(reason)
        self.pending.clear()
        self.status()

    def bind(self,kind):
        if self.health.locked:
            return False
        # Foxy discards per-message publisher info; the 20 Hz status timer
        # revalidates cached hardware endpoints without a DDS graph scan per IMU-rate odometry.
        if self.hardware_mode and kind in self.gids:
            return True
        try:
            gid, node_name, node_namespace = publisher_endpoint_identity(
                self.get_publishers_info_by_topic(self.topics[kind]))
        except PublisherEndpointNotReady:
            return False
        except ValueError:
            self.fault(kind+'_missing_or_ambiguous_publisher')
            return False
        node = (node_name, node_namespace)
        if self.vins_node is not None and self.vins_node != node:
            self.get_logger().error(
                f"VINS publisher node identity changed on {kind}: "
                f"expected {self.vins_node}, got {node}, gid={gid}")
            self.fault('vins_node_identity_mismatch')
            return False
        self.vins_node = node
        if kind in self.gids and self.gids[kind] != gid:
            self.fault(kind+'_publisher_changed')
            return False
        self.gids[kind] = gid
        return not self.health.locked

    def on_clock(self,msg):
        self.health.clock(msg.clock.sec*1000000000+msg.clock.nanosec,time.monotonic())
        if self.health.locked:
            self.pending.clear()

    def advance_hardware_clock(self):
        if self.hardware_mode:
            self.health.clock(int(self.get_clock().now().nanoseconds),time.monotonic())
            if self.health.locked:
                self.pending.clear()
            return not self.health.locked
        return not self.health.locked

    def on_serialized_image(self,kind,serialized):
        try:
            msg = image_metadata(serialized)
        except (ValueError, TypeError, IndexError):
            return self.fault(kind+'_invalid_serialized_image')
        self.on_image(kind,msg)

    def on_image(self,kind,msg):
        if not self.advance_hardware_clock():return
        name = 'infra1' if kind=='left' else 'infra2'
        camera = self.rig['cameras'][name]
        if (msg.header.frame_id!=camera.get('image_frame',camera['frame'])
            or msg.encoding!='mono8' or msg.width!=camera['width']
            or msg.height!=camera['height'] or msg.step<msg.width or len(msg.data)<msg.height*msg.step):
            return self.fault(kind+'_invalid_image')
        self.health.sample(kind,stamp_ns(msg.header),time.monotonic())
        self.drain()

    def on_imu(self,msg):
        if not self.advance_hardware_clock():return
        a,g = msg.linear_acceleration,msg.angular_velocity
        if msg.header.frame_id!=self.rig['imu']['frame'] or not all(math.isfinite(v) for v in [a.x,a.y,a.z,g.x,g.y,g.z]):
            return self.fault('invalid_imu')
        stamp = stamp_ns(msg.header)
        if self.health.sample('imu',stamp,time.monotonic()):
            self.imu.append((stamp,[g.x,g.y,g.z]))
        self.drain()

    def on_telemetry(self,msg):
        if not self.advance_hardware_clock():return
        if self.health.locked:
            if not self.post_lock_telemetry_logged:
                self.post_lock_telemetry_logged = True
                try:
                    data = json.loads(msg.data)
                    source_stamp = data.get('stamp_ns') if isinstance(data,dict) else None
                except (ValueError,TypeError):
                    source_stamp = None
                wall = time.monotonic()
                clock_ns = self.health.clock_ns
                self.get_logger().warning('telemetry_after_health_lockout '+json.dumps({
                    'reason': self.health.reason,
                    'source_stamp_ns': source_stamp,
                    'clock_stamp_ns': clock_ns,
                    'source_age_ns': (clock_ns-source_stamp
                                      if type(clock_ns) is int and type(source_stamp) is int
                                      else None),
                    'receipt_monotonic_s': wall,
                },sort_keys=True))
            return
        if not self.bind('telemetry'):return
        try:
            metrics = json.loads(msg.data)
            if not isinstance(metrics,dict):raise ValueError('Expected object')
        except (ValueError,TypeError):
            return self.fault('malformed_telemetry')
        self.health.telemetry(metrics,time.monotonic())
        self.drain()

    def on_raw(self,kind,msg):
        if not self.advance_hardware_clock():return
        if not self.bind(kind):return
        p,q,v = msg.pose.pose.position,msg.pose.pose.orientation,msg.twist.twist.linear
        if (msg.header.frame_id!=self.raw_world or (kind=='optimized' and msg.child_frame_id!=self.raw_body)
            or (kind=='propagated' and msg.child_frame_id not in ['',self.raw_body])
            or not all(math.isfinite(x) for x in [p.x,p.y,p.z,q.x,q.y,q.z,q.w,v.x,v.y,v.z])):
            return self.fault(kind+'_invalid_odometry')
        try:
            body_velocity([q.x,q.y,q.z,q.w],[v.x,v.y,v.z])
        except ValueError:
            record = quaternion_diagnostic([q.x,q.y,q.z,q.w])
            record.update({
                'kind': kind, 'epoch': self.epoch,
                'source_stamp_ns': stamp_ns(msg.header),
                'clock_stamp_ns': self.health.clock_ns,
                'frame_id': msg.header.frame_id,
                'child_frame_id': msg.child_frame_id,
                'position': [p.x,p.y,p.z],
                'velocity': [v.x,v.y,v.z],
                'last_published_source_ns': dict(self.published),
                'last_imu_sample': self.imu[-1] if self.imu else None,
            })
            self.get_logger().error('odometry_integrity_fault '+json.dumps(
                record, sort_keys=True, allow_nan=False))
            return self.fault(kind+'_invalid_quaternion')
        if self.health.sample(kind,stamp_ns(msg.header),time.monotonic()):
            self.pending[kind] = msg
        self.drain()

    def angular_velocity(self,stamp):
        return interpolate_angular_velocity(self.imu,stamp)

    def drain(self):
        wall = time.monotonic()
        if not self.advance_hardware_clock():
            return
        if self.health.locked:
            self.pending.clear()
            return
        self.health.paired(wall,require_solver_usable=self.require_solver_usable)
        if self.hardware_mode:
            self.health.enforce_freshness(self.health.clock_ns,time.monotonic())
        if not self.health.tick(wall):
            if self.health.locked:
                self.pending.clear()
            return
        for kind,msg in list(self.pending.items()):
            stamp = stamp_ns(msg.header)
            if self.published[kind] is not None and stamp<=self.published[kind]:continue
            if kind=='optimized' and stamp!=self.health.last_pair:continue
            omega = self.angular_velocity(stamp)
            if omega is None:continue
            # The hardware callback owns this deserialized object exclusively.
            # Published stamps prevent a second conversion of the pending sample.
            result = msg if self.hardware_mode else deepcopy(msg)
            q,v = msg.pose.pose.orientation,msg.twist.twist.linear
            velocity = body_velocity([q.x,q.y,q.z,q.w],[v.x,v.y,v.z])
            result.header.frame_id,result.child_frame_id = self.world,self.body
            result.twist.twist.linear.x,result.twist.twist.linear.y,result.twist.twist.linear.z = velocity
            result.twist.twist.angular.x,result.twist.twist.angular.y,result.twist.twist.angular.z = omega
            self.output[kind].publish(result)
            self.published[kind] = stamp
            self.counts[kind] += 1
            if kind == 'optimized':
                position = result.pose.pose.position
                orientation = result.pose.pose.orientation
                self.latest_optimized_pose = {
                    'stamp_ns': stamp,
                    'frame_id': result.header.frame_id,
                    'child_frame_id': result.child_frame_id,
                    'position_m': [position.x, position.y, position.z],
                    'orientation_xyzw': [orientation.x, orientation.y,
                                         orientation.z, orientation.w],
                }

    def on_timer(self):
        if not self.advance_hardware_clock():
            self.pending.clear()
        if self.health.state=='TRACKING' or (self.hardware_mode and not self.health.locked):
            for kind,topic in self.topics.items():
                # Each stream binds its DDS identity when its first message
                # arrives. VINS may advertise a publisher after another
                # stream has already moved the adapter into TRACKING.
                if kind not in self.gids:
                    continue
                publishers = self.get_publishers_info_by_topic(topic)
                try:
                    gid,node_name,node_namespace = publisher_endpoint_identity(publishers)
                except PublisherEndpointNotReady:
                    continue
                except ValueError:
                    self.fault(kind+'_publisher_missing_or_ambiguous')
                    break
                if publisher_endpoint_identity_changed(
                        self.gids.get(kind),self.vins_node,gid,node_name,node_namespace):
                    self.fault(kind+'_publisher_missing_or_changed')
                    break
        if self.hardware_mode and not self.health.locked:
            self.health.enforce_freshness(self.health.clock_ns,time.monotonic())
        self.drain()
        if self.health.locked:self.pending.clear()
        self.status()
        if self.hardware_mode:
            wall = time.monotonic()
            if wall-self.last_age_log_wall >= 1.0:
                self.last_age_log_wall = wall
                self.get_logger().info('localization_age_observation '+json.dumps(
                    {
                        'wall_epoch_s': time.time(),
                        'freshness_mode': self.health.freshness['mode'],
                        'epoch': self.epoch,
                        'status': {
                            'state': self.health.state,
                            'valid': self.health.state == 'TRACKING' and not self.health.locked,
                            'reason': self.health.reason,
                            'accepted_optimized': self.counts['optimized'],
                            'accepted_propagated': self.counts['propagated'],
                        },
                        'pose_observation': self.latest_optimized_pose,
                        'ages': self.health.age_metrics(self.health.clock_ns,wall),
                        'streams': self.health.stream_summary(),
                    },sort_keys=True))

    def status(self):
        if self.health.locked and not self.health_lockout_logged:
            snapshot = self.health.diagnostic_snapshot()
            snapshot['epoch'] = self.epoch
            snapshot['captured_wall_s'] = time.monotonic()
            self.health_lockout_logged = True
            self.get_logger().error('localization_integrity_fault_snapshot '+json.dumps(snapshot,sort_keys=True))
        msg = LocalizationStatus()
        now = self.health.clock_ns or 0
        msg.header.stamp.sec,msg.header.stamp.nanosec = divmod(now,1000000000)
        msg.header.frame_id = self.world
        msg.epoch,msg.body_frame = self.epoch,self.body
        msg.state = getattr(LocalizationStatus,self.health.state)
        msg.valid = self.health.state=='TRACKING' and not self.health.locked
        msg.reason = self.health.reason
        source = self.published['propagated'] or 0
        msg.source_stamp.sec,msg.source_stamp.nanosec = divmod(source,1000000000)
        msg.covariance_valid = False  # Upstream publishes no estimated covariance.
        msg.normalized_cost = self.health.normalized_cost
        msg.good_pairs = self.health.good_pairs
        msg.accepted_optimized,msg.accepted_propagated = self.counts['optimized'],self.counts['propagated']
        self.status_pub.publish(msg)


def main():
    rclpy.init()
    node = None
    try:
        node = Localization()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except ExternalShutdownException:
        pass
    except Exception:
        if rclpy.ok():
            raise
    finally:
        if node is not None:node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
