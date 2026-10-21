"""Fail-closed session health. Pure Python so time and fault behavior can be tested."""
import math


class PublisherEndpointNotReady(ValueError):
    """The DDS endpoint exists, but its ROS node identity is not resolved yet."""


class Health:
    def __init__(self, policy, started_wall):
        self.policy = policy
        for group in ['max_source_age_s', 'max_receipt_age_s']:
            if set(policy[group]) != {'left','right','imu','telemetry','optimized','propagated'}:
                raise ValueError('Health policy must cover all six streams')
            if not all(math.isfinite(v) and v>0 for v in policy[group].values()):
                raise ValueError('Invalid freshness limits')
        for key,value in policy.items():
            if key != 'qualification' and not isinstance(value,dict) and (not math.isfinite(value) or value<=0):
                raise ValueError('Invalid health limit: '+key)
        self.started_wall = started_wall
        self.active_since_wall = None
        self.clock_ns = None
        self.clock_wall = started_wall
        self.clock_origin_ns = None
        self.clock_origin_wall = None
        self.clock_rate = 1.0
        self.samples = {}
        self.metrics = None
        self.good_pairs = 0
        self.last_pair = None
        self.state = 'INITIALIZING'
        self.reason = 'waiting_for_inputs'
        self.locked = False
        self.normalized_cost = 0.0
        self.future_observation = None

    def fail(self, reason):
        if not self.locked:
            self.locked = True
            self.state = 'LOST'
            self.reason = reason
        return False

    def clock(self, stamp_ns, wall):
        if type(stamp_ns) is not int or stamp_ns < 0:
            return self.fail('invalid_clock_stamp')
        if self.clock_ns is not None and stamp_ns < self.clock_ns:
            return self.fail('clock_regression')
        if self.active_since_wall is None:
            self.active_since_wall = wall
        if self.clock_ns is None:
            self.clock_origin_ns = stamp_ns
            self.clock_origin_wall = wall
        if self.clock_ns != stamp_ns:
            self.clock_wall = wall
            elapsed_wall = wall-self.clock_origin_wall
            if elapsed_wall > 0:
                measured_rate = (stamp_ns-self.clock_origin_ns)*1e-9/elapsed_wall
                if math.isfinite(measured_rate) and measured_rate > 0:
                    self.clock_rate = measured_rate
        self.clock_ns = stamp_ns
        return not self.locked

    def sample(self, name, stamp_ns, wall):
        if self.locked:
            return False
        if name in self.samples and stamp_ns <= self.samples[name][0]:
            return self.fail(name+'_stamp_not_increasing')
        if stamp_ns < 0:
            return self.fail(name+'_invalid_stamp')
        self.samples[name] = (stamp_ns, wall, self.clock_ns)
        return True

    def telemetry(self, metrics, wall):
        if not isinstance(metrics, dict):
            return self.fail('malformed_telemetry')
        numeric = ['stamp_ns','input_features','stereo_features','long_tracks','residual_components',
                   'final_cost','accel_bias_norm','gyro_bias_norm','solve_seconds']
        flags = ['initialized','state_finite','solve_current','solver_usable']
        if (metrics.get('schema') != 1 or any(type(metrics.get(k)) is not bool for k in flags)
            or any(type(metrics.get(k)) not in [int,float] or not math.isfinite(metrics[k]) for k in numeric)):
            return self.fail('malformed_telemetry')
        if metrics['stamp_ns'] != int(metrics['stamp_ns']) or metrics['residual_components'] < 0 or metrics['final_cost'] < 0:
            return self.fail('invalid_telemetry_values')
        if not self.sample('telemetry', int(metrics['stamp_ns']), wall):
            return False
        self.metrics = metrics
        if metrics['residual_components'] > 0:
            self.normalized_cost = math.sqrt(2*metrics['final_cost']/metrics['residual_components'])
            if not math.isfinite(self.normalized_cost):
                return self.fail('invalid_normalized_cost')
        return True

    def freshness(self, wall):
        if self.clock_ns is None:
            return 'waiting_for_clock'
        if wall-self.clock_wall > self.policy['clock_stall_wall_s']:
            return 'clock_stalled'
        future_tolerance_ns = int(round(self.policy['future_tolerance_s'] * 1e9))
        for name,limit in self.policy['max_source_age_s'].items():
            if name not in self.samples:
                return 'waiting_for_'+name
            stamp,_,receipt_clock_ns = self.samples[name]
            age_ns = self.clock_ns - stamp
            if age_ns < -future_tolerance_ns:
                self.future_observation = {
                    'stream': name,
                    'source_stamp_ns': stamp,
                    'clock_stamp_ns': self.clock_ns,
                    'source_age_ns': age_ns,
                    'future_tolerance_ns': future_tolerance_ns,
                    'receipt_clock_ns': receipt_clock_ns,
                    'evaluated_wall_s': wall,
                }
                return name+'_from_future'
            # Receipt freshness is measured in observed simulation time. Do
            # not extrapolate /clock through a short lockstep pause: while the
            # simulator is not advancing, no source can become stale in sim
            # time. The steady-clock watchdog above bounds that pause.
            receipt_age_in_clock_ns = (max(0, self.clock_ns-receipt_clock_ns)
                                       if receipt_clock_ns is not None else 0)
            source_limit_ns = int(round(limit * 1e9))
            receipt_limit_ns = int(round(self.policy['max_receipt_age_s'][name] * 1e9))
            if age_ns > source_limit_ns or receipt_age_in_clock_ns > receipt_limit_ns:
                return name+'_stale'
        return ''

    def quality(self):
        m,p = self.metrics,self.policy
        if m is None or not m['initialized']:
            return 'vins_initializing'
        if not all(m[k] for k in ['state_finite','solve_current','solver_usable']):
            return 'solver_invalid'
        if m['residual_components']<=0:
            return 'no_residuals'
        for key,limit in [('input_features','min_features'),('stereo_features','min_stereo_features'),('long_tracks','min_long_tracks')]:
            if m[key] < p[limit]:
                return key+'_insufficient'
        for key,limit in [('accel_bias_norm','max_accel_bias_m_s2'),('gyro_bias_norm','max_gyro_bias_rad_s'),('solve_seconds','max_solve_s')]:
            if m[key] < 0 or m[key] > p[limit]:
                return key+'_exceeded'
        if self.normalized_cost > p['max_normalized_cost']:
            return 'normalized_cost_exceeded'
        return ''

    def paired(self, wall):
        if self.locked or self.metrics is None or 'optimized' not in self.samples:
            return False
        stamp = self.samples['optimized'][0]
        if abs(stamp-self.samples['telemetry'][0]) > 1000 or stamp == self.last_pair:
            return False
        reason = self.freshness(wall) or self.quality()
        if reason:
            self.good_pairs = 0
            if self.state == 'TRACKING':
                return self.fail(reason)
            self.state = 'INITIALIZING' if reason.startswith('waiting') or reason == 'vins_initializing' else 'DEGRADED'
            self.reason = reason
            return False
        self.last_pair = stamp
        self.good_pairs += 1
        if self.good_pairs >= self.policy['good_pairs_required']:
            self.state,self.reason = 'TRACKING','fresh_inputs_and_usable_solver'
        return self.state == 'TRACKING'

    def tick(self, wall):
        if self.locked:
            self.state = 'LOCKED'
            return False
        reason = self.freshness(wall) or self.quality()
        if self.state == 'TRACKING' and reason:
            return self.fail(reason)
        if (self.state != 'TRACKING' and self.active_since_wall is not None
                and wall-self.active_since_wall > self.policy['initialization_wall_s']):
            return self.fail('initialization_timeout')
        return self.state == 'TRACKING' and not reason


def body_velocity(quaternion, velocity):
    x,y,z,w = quaternion
    norm = math.sqrt(sum(v*v for v in quaternion))
    if not math.isfinite(norm) or abs(norm-1)>0.01:
        raise ValueError('Invalid pose quaternion')
    x,y,z,w = (v/norm for v in quaternion)
    r = [[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],
         [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],
         [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]]
    return [sum(r[j][i]*velocity[j] for j in range(3)) for i in range(3)]


def publisher_endpoint_identity(publishers):
    """Use discovered endpoint metadata; Jazzy callback MessageInfo omits GID."""
    if len(publishers) != 1:
        raise ValueError('Expected exactly one DDS publisher')
    endpoint = publishers[0]
    try:
        value = bytes(endpoint.endpoint_gid)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError('Missing or invalid DDS endpoint GID') from exc
    if not value:
        raise ValueError('Missing DDS endpoint GID')
    if endpoint.node_name in ('_NODE_NAME_UNKNOWN_', '_NODE_NAMESPACE_UNKNOWN_') or endpoint.node_namespace in (
            '_NODE_NAME_UNKNOWN_', '_NODE_NAMESPACE_UNKNOWN_'):
        raise PublisherEndpointNotReady('DDS publisher node identity is not resolved yet')
    if not endpoint.node_name or not endpoint.node_namespace:
        raise ValueError('Missing DDS endpoint node identity')
    return value.hex(), endpoint.node_name, endpoint.node_namespace
