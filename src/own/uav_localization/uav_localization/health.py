"""Localization stream/session integrity checks, without project quality gates."""
import math


class PublisherEndpointNotReady(ValueError):
    """The DDS endpoint exists, but its ROS node identity is not resolved yet."""


class Health:
    def __init__(self, policy, started_wall):
        self.status_period_wall_s = float(policy['status_period_wall_s'])
        if not math.isfinite(self.status_period_wall_s) or self.status_period_wall_s <= 0:
            raise ValueError('status_period_wall_s must be finite and positive')
        self.clock_ns = None
        self.samples = {}
        self.metrics = None
        self.good_pairs = 0
        self.last_pair = None
        self.state = 'INITIALIZING'
        self.reason = 'waiting_for_inputs'
        self.locked = False
        self.normalized_cost = 0.0

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
        self.clock_ns = stamp_ns
        return not self.locked

    def sample(self, name, stamp_ns, wall):
        if self.locked:
            return False
        if type(stamp_ns) is not int or stamp_ns < 0:
            return self.fail(name + '_invalid_stamp')
        if name in self.samples and stamp_ns <= self.samples[name][0]:
            return self.fail(name + '_stamp_not_increasing')
        self.samples[name] = (stamp_ns, wall, self.clock_ns)
        return True

    def telemetry(self, metrics, wall):
        if not isinstance(metrics, dict):
            return self.fail('malformed_telemetry')
        numeric = ['stamp_ns', 'input_features', 'stereo_features', 'long_tracks',
                   'residual_components', 'final_cost', 'accel_bias_norm',
                   'gyro_bias_norm', 'solve_seconds']
        flags = ['initialized', 'state_finite', 'solve_current', 'solver_usable']
        if (metrics.get('schema') != 1
                or any(type(metrics.get(key)) is not bool for key in flags)
                or any(type(metrics.get(key)) not in (int, float)
                       or not math.isfinite(metrics[key]) for key in numeric)):
            return self.fail('malformed_telemetry')
        if (metrics['stamp_ns'] != int(metrics['stamp_ns'])
                or metrics['residual_components'] < 0 or metrics['final_cost'] < 0):
            return self.fail('invalid_telemetry_values')
        if not self.sample('telemetry', int(metrics['stamp_ns']), wall):
            return False
        self.metrics = metrics
        self.normalized_cost = (math.sqrt(2 * metrics['final_cost'] / metrics['residual_components'])
                                if metrics['residual_components'] > 0 else 0.0)
        if not math.isfinite(self.normalized_cost):
            return self.fail('invalid_normalized_cost')
        return True

    def diagnostic_snapshot(self):
        """Return current source measurements for an integrity-fault report."""
        metrics = dict(self.metrics) if self.metrics is not None else None
        derived_cost = None
        if metrics is not None and metrics['residual_components'] > 0:
            derived_cost = math.sqrt(2 * metrics['final_cost'] / metrics['residual_components'])
        samples = {
            name: {'source_stamp_ns': sample[0], 'receipt_wall_s': sample[1],
                   'clock_at_receipt_ns': sample[2]}
            for name, sample in self.samples.items()
        }
        return {
            'state': self.state,
            'locked': self.locked,
            'reason': self.reason,
            'normalized_cost': self.normalized_cost,
            'normalized_cost_recomputed_from_metrics': derived_cost,
            'metrics': metrics,
            'samples': samples,
            'clock_ns': self.clock_ns,
            'last_pair_ns': self.last_pair,
        }

    def paired(self, wall):
        if self.locked or self.metrics is None or 'optimized' not in self.samples:
            return False
        stamp = self.samples['optimized'][0]
        # Pairing binds the estimator telemetry to its optimized pose; the
        # one-microsecond tolerance is timestamp correlation, not a quality gate.
        if abs(stamp - self.samples['telemetry'][0]) > 1000 or stamp == self.last_pair:
            return False
        self.last_pair = stamp
        self.good_pairs += 1
        self.state = 'TRACKING'
        self.reason = 'paired_telemetry_and_optimized_odometry'
        return True

    def tick(self, wall):
        if self.locked:
            self.state = 'LOCKED'
            return False
        return self.state == 'TRACKING'


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


def publisher_endpoint_identity_changed(expected_gid, expected_node, gid, node_name, node_namespace):
    """Detect identity changes only after this stream's first message bound it."""
    if expected_gid is None:
        return False
    return gid != expected_gid or (node_name, node_namespace) != expected_node


def quaternion_diagnostic(quaternion):
    """Preserve rejected raw components without normalizing or accepting them."""
    values = tuple(float(v) for v in quaternion)
    norm = math.hypot(*values)
    return {
        'quaternion_xyzw': [v if math.isfinite(v) else repr(v) for v in values],
        'quaternion_norm': norm if math.isfinite(norm) else None,
        'quaternion_norm_finite': math.isfinite(norm),
    }
