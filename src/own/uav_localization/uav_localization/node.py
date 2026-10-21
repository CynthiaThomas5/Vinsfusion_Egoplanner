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
from uav_sim.geometry import calibration
from .health import (Health, PublisherEndpointNotReady, body_velocity,
                     publisher_endpoint_identity)


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
        settings = root/'config/components/localization/vins_sim.json'
        if hashlib.sha256(settings.read_bytes()).hexdigest() != self.session['settings_sha256']:
            raise ValueError('Session settings differ from project settings')
        text = (path.parent/'vins.yaml').read_text()
        if not all(re.search(r'^'+key+r': '+str(value)+r'$',text,re.M) for key,value in [('imu',1),('num_of_cam',2),('estimate_extrinsic',0)]):
            raise ValueError('Adapter requires fixed-extrinsic stereo + IMU VINS')
        self.rig = calibration(root/'simulation/models/d435i/model.sdf')
        if self.rig['model_sha256'] != self.session['model_sha256']:
            raise ValueError('Session model hash mismatch')
        policy = json.loads((root/'config/components/localization/health.json').read_text())
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
        self.subscriptions_owned = [self.create_subscription(Clock,'/clock',self.on_clock,qos_profile_sensor_data),
                                    self.create_subscription(Imu,'/sensors/d435i/imu',self.on_imu,qos_profile_sensor_data),
                                    self.create_subscription(String,self.topics['telemetry'],self.on_telemetry,qos_profile_sensor_data)]
        for kind,topic in [('left','infra1/image_rect'),('right','infra2/image_rect')]:
            self.subscriptions_owned.append(self.create_subscription(Image,'/sensors/d435i/'+topic,lambda msg,k=kind:self.on_image(k,msg),qos_profile_sensor_data))
        # Explicit two-argument callbacks retain DDS publisher identity.
        def optimized(msg):self.on_raw('optimized',msg)
        def propagated(msg):self.on_raw('propagated',msg)
        self.subscriptions_owned.extend([self.create_subscription(Odometry,self.topics['optimized'],optimized,qos_profile_sensor_data),
                                         self.create_subscription(Odometry,self.topics['propagated'],propagated,qos_profile_sensor_data)])
        self.timer = self.create_timer(policy['status_period_wall_s'],self.on_timer,clock=ROSClock(clock_type=ClockType.STEADY_TIME))
        self.status()

    def fault(self,reason):
        self.health.fail(reason)
        self.pending.clear()
        self.status()

    def bind(self,kind):
        if self.health.locked:
            return False
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

    def on_image(self,kind,msg):
        name = 'infra1' if kind=='left' else 'infra2'
        camera = self.rig['cameras'][name]
        if (msg.header.frame_id!=camera['frame'] or msg.encoding!='mono8' or msg.width!=camera['width']
            or msg.height!=camera['height'] or msg.step<msg.width or len(msg.data)<msg.height*msg.step):
            return self.fault(kind+'_invalid_image')
        self.health.sample(kind,stamp_ns(msg.header),time.monotonic())
        self.drain()

    def on_imu(self,msg):
        a,g = msg.linear_acceleration,msg.angular_velocity
        if msg.header.frame_id!=self.rig['imu']['frame'] or not all(math.isfinite(v) for v in [a.x,a.y,a.z,g.x,g.y,g.z]):
            return self.fault('invalid_imu')
        stamp = stamp_ns(msg.header)
        if self.health.sample('imu',stamp,time.monotonic()):
            self.imu.append((stamp,[g.x,g.y,g.z]))
        self.drain()

    def on_telemetry(self,msg):
        if not self.bind('telemetry'):return
        try:
            metrics = json.loads(msg.data)
            if not isinstance(metrics,dict):raise ValueError('Expected object')
        except (ValueError,TypeError):
            return self.fault('malformed_telemetry')
        self.health.telemetry(metrics,time.monotonic())
        self.drain()

    def on_raw(self,kind,msg):
        if not self.bind(kind):return
        p,q,v = msg.pose.pose.position,msg.pose.pose.orientation,msg.twist.twist.linear
        if (msg.header.frame_id!=self.raw_world or (kind=='optimized' and msg.child_frame_id!=self.raw_body)
            or (kind=='propagated' and msg.child_frame_id not in ['',self.raw_body])
            or not all(math.isfinite(x) for x in [p.x,p.y,p.z,q.x,q.y,q.z,q.w,v.x,v.y,v.z])):
            return self.fault(kind+'_invalid_odometry')
        try:
            body_velocity([q.x,q.y,q.z,q.w],[v.x,v.y,v.z])
        except ValueError:
            return self.fault(kind+'_invalid_quaternion')
        if self.health.sample(kind,stamp_ns(msg.header),time.monotonic()):
            self.pending[kind] = msg
        self.drain()

    def angular_velocity(self,stamp):
        previous = None
        for current in self.imu:
            if abs(current[0]-stamp)<=1000:return current[1]
            if current[0]>=stamp:
                if previous is None:return None
                weight = (stamp-previous[0])/(current[0]-previous[0])
                return [a+weight*(b-a) for a,b in zip(previous[1],current[1])]
            previous = current
        return None

    def drain(self):
        wall = time.monotonic()
        self.health.paired(wall)
        if not self.health.tick(wall):return
        for kind,msg in list(self.pending.items()):
            stamp = stamp_ns(msg.header)
            if self.published[kind] is not None and stamp<=self.published[kind]:continue
            if kind=='optimized' and stamp!=self.health.last_pair:continue
            omega = self.angular_velocity(stamp)
            if omega is None:continue
            result = deepcopy(msg)
            q,v = msg.pose.pose.orientation,msg.twist.twist.linear
            velocity = body_velocity([q.x,q.y,q.z,q.w],[v.x,v.y,v.z])
            result.header.frame_id,result.child_frame_id = self.world,self.body
            result.twist.twist.linear.x,result.twist.twist.linear.y,result.twist.twist.linear.z = velocity
            result.twist.twist.angular.x,result.twist.twist.angular.y,result.twist.twist.angular.z = omega
            self.output[kind].publish(result)
            self.published[kind] = stamp
            self.counts[kind] += 1

    def on_timer(self):
        if self.health.state=='TRACKING':
            for kind,topic in self.topics.items():
                publishers = self.get_publishers_info_by_topic(topic)
                try:
                    gid,node_name,node_namespace = publisher_endpoint_identity(publishers)
                except PublisherEndpointNotReady:
                    continue
                except ValueError:
                    self.fault(kind+'_publisher_missing_or_ambiguous')
                    break
                if (gid!=self.gids.get(kind) or (node_name,node_namespace)!=self.vins_node):
                    self.fault(kind+'_publisher_missing_or_changed')
                    break
        self.health.tick(time.monotonic())
        if self.health.locked:self.pending.clear()
        self.status()

    def status(self):
        if (not self.future_observation_logged and self.health.reason.endswith('_from_future')
                and self.health.future_observation is not None):
            observation = dict(self.health.future_observation)
            observation['epoch'] = self.epoch
            self.get_logger().error('health_future_observation '+json.dumps(observation,sort_keys=True))
            self.future_observation_logged = True
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
