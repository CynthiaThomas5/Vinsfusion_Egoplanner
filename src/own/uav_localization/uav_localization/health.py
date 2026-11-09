"""Localization stream/session integrity checks, without project quality gates."""
import math


class PublisherEndpointNotReady(ValueError):
    """The DDS endpoint exists, but its ROS node identity is not resolved yet."""


class Health:
    def __init__(self, policy, started_wall):
        self.status_period_wall_s = float(policy['status_period_wall_s'])
        if not math.isfinite(self.status_period_wall_s) or self.status_period_wall_s <= 0:
            raise ValueError('status_period_wall_s must be finite and positive')
        freshness = policy.get('freshness', {'mode': 'observe', 'streams': {}})
        if freshness.get('mode') not in ('observe', 'gate') or not isinstance(freshness.get('streams'), dict):
            raise ValueError('freshness requires mode observe/gate and a streams object')
        self.freshness = freshness
        self.startup_fresh_window_s = float(policy.get('startup_fresh_window_s', 0.0))
        if not math.isfinite(self.startup_fresh_window_s) or self.startup_fresh_window_s < 0:
            raise ValueError('startup_fresh_window_s must be finite and non-negative')
        self.startup_fresh_since_wall = None
        if freshness['mode'] == 'gate':
            if not freshness['streams']:
                raise ValueError('freshness gate requires measured stream budgets')
            for name, budget in freshness['streams'].items():
                for key in ('source_age_budget_s', 'receipt_age_budget_s'):
                    value = budget.get(key)
                    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
                        raise ValueError(f'{name} {key} must be finite and positive')
        for budget in freshness['streams'].values():
            future = budget.get('future_source_tolerance_s', 0.0)
            if type(future) not in (int, float) or not math.isfinite(future) or future < 0:
                raise ValueError('future_source_tolerance_s must be finite and non-negative')
        self.clock_ns = None
        self.samples = {}
        self.stream_stats = {}
        self.metrics = None
        self.good_pairs = 0
        self.last_pair = None
        self.state = 'INITIALIZING'
        self.reason = 'waiting_for_inputs'
        self.locked = False
        self.normalized_cost = 0.0
        self.last_age_metrics = {}

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
        stats = self.stream_stats.setdefault(name, {
            'count': 0, 'first_source_stamp_ns': stamp_ns,
            'last_source_stamp_ns': stamp_ns, 'first_receipt_wall_s': wall,
            'last_receipt_wall_s': wall, 'max_source_interval_s': 0.0,
            'max_receipt_interval_s': 0.0, 'max_source_age_s': None,
        })
        previous = self.samples.get(name)
        if previous is not None:
            stats['max_source_interval_s'] = max(
                stats['max_source_interval_s'], (stamp_ns - previous[0]) * 1e-9)
            stats['max_receipt_interval_s'] = max(
                stats['max_receipt_interval_s'], wall - previous[1])
        if self.clock_ns is not None:
            age = (self.clock_ns - stamp_ns) * 1e-9
            if age >= 0:
                stats['max_source_age_s'] = max(stats['max_source_age_s'] or 0.0, age)
        stats['count'] += 1
        stats['last_source_stamp_ns'] = stamp_ns
        stats['last_receipt_wall_s'] = wall
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
            'stream_stats': self.stream_summary(),
            'clock_ns': self.clock_ns,
            'last_pair_ns': self.last_pair,
            'age_metrics': dict(self.last_age_metrics),
        }

    def paired(self, wall, require_solver_usable=False):
        if (not self.locked and self.state != 'TRACKING'
                and self.freshness['mode'] == 'gate' and self.startup_fresh_window_s > 0):
            ages = self.age_metrics(self.clock_ns, wall) if self.clock_ns is not None else {}
            if any(name not in ages
                   or ages[name]['source_age_s'] < -budget.get('future_source_tolerance_s', 0.0)
                   or (budget.get('enforce_source_age', True) and ages[name]['source_age_s'] > budget['source_age_budget_s'])
                   or ages[name]['receipt_age_s'] > budget['receipt_age_budget_s']
                   for name, budget in self.freshness['streams'].items()):
                self.startup_fresh_since_wall = None
        if self.locked or self.metrics is None or 'optimized' not in self.samples:
            return False
        stamp = self.samples['optimized'][0]
        # Pairing binds the estimator telemetry to its optimized pose; the
        # one-microsecond tolerance is timestamp correlation, not a quality gate.
        if abs(stamp - self.samples['telemetry'][0]) > 1000:
            return False
        if stamp == self.last_pair and self.state == 'TRACKING':
            return False
        if stamp != self.last_pair:
            self.last_pair = stamp
            self.good_pairs += 1
        if require_solver_usable and not all(self.metrics[key] for key in
                                             ('initialized', 'state_finite', 'solve_current', 'solver_usable')):
            self.state = 'INITIALIZING'
            self.startup_fresh_since_wall = None
            self.reason = 'waiting_for_usable_vins_solution'
            return False
        missing = [name for name in self.freshness['streams'] if name not in self.samples]
        if missing:
            self.state = 'INITIALIZING'
            self.reason = 'waiting_for_freshness_inputs'
            return False
        if self.freshness['mode'] == 'gate':
            if self.clock_ns is None:
                self.state = 'INITIALIZING'
                self.reason = 'waiting_for_freshness_inputs'
                return False
            ages = self.age_metrics(self.clock_ns, wall)
            for name, budget in self.freshness['streams'].items():
                current = ages[name]
                if current['source_age_s'] < -budget.get('future_source_tolerance_s', 0.0):
                    return self.fail(name + '_future_source_stamp')
                if ((budget.get('enforce_source_age', True) and current['source_age_s'] > budget['source_age_budget_s'])
                        or current['receipt_age_s'] > budget['receipt_age_budget_s']):
                    if self.state == 'TRACKING':
                        # Keep the tracking state until enforce_freshness locks;
                        # a new stale pair must not demote it back to startup.
                        return False
                    self.state = 'INITIALIZING'
                    self.startup_fresh_since_wall = None
                    self.reason = 'waiting_for_freshness_inputs'
                    return False
            if self.state != 'TRACKING' and self.startup_fresh_window_s > 0:
                if self.startup_fresh_since_wall is None:
                    self.startup_fresh_since_wall = wall
                if wall - self.startup_fresh_since_wall < self.startup_fresh_window_s:
                    self.reason = 'waiting_for_stable_freshness'
                    return False
        self.state = 'TRACKING'
        self.reason = 'paired_telemetry_and_optimized_odometry'
        return True

    def age_metrics(self, source_now_ns, receipt_now_s):
        ages = {}
        for name, sample in self.samples.items():
            ages[name] = {
                'source_age_s': (source_now_ns - sample[0]) * 1e-9,
                'receipt_age_s': receipt_now_s - sample[1],
            }
        self.last_age_metrics = ages
        return ages

    def stream_summary(self):
        summary = {}
        for name, stats in self.stream_stats.items():
            source_elapsed = (stats['last_source_stamp_ns'] - stats['first_source_stamp_ns']) * 1e-9
            receipt_elapsed = stats['last_receipt_wall_s'] - stats['first_receipt_wall_s']
            count = stats['count']
            summary[name] = dict(stats)
            summary[name]['mean_source_period_s'] = (
                source_elapsed / (count - 1) if count > 1 and source_elapsed > 0 else None)
            summary[name]['mean_receipt_period_s'] = (
                receipt_elapsed / (count - 1) if count > 1 and receipt_elapsed > 0 else None)
            summary[name]['source_frequency_hz'] = (
                (count - 1) / source_elapsed if count > 1 and source_elapsed > 0 else None)
            summary[name]['receipt_frequency_hz'] = (
                (count - 1) / receipt_elapsed if count > 1 and receipt_elapsed > 0 else None)
        return summary

    def enforce_freshness(self, source_now_ns, receipt_now_s):
        if self.locked or self.freshness['mode'] != 'gate' or self.state != 'TRACKING':
            return not self.locked
        ages = self.age_metrics(source_now_ns, receipt_now_s)
        for name, budget in self.freshness['streams'].items():
            current = ages.get(name)
            if current is None:
                return True  # Startup is not an age fault; paired() holds admission until all streams arrive.
            source_age = current['source_age_s']
            receipt_age = current['receipt_age_s']
            if source_age < -budget.get('future_source_tolerance_s', 0.0):
                return self.fail(name + '_future_source_stamp')
            if budget.get('enforce_source_age', True) and source_age > budget['source_age_budget_s']:
                return self.fail(name + '_source_stale')
            if receipt_age > budget['receipt_age_budget_s']:
                return self.fail(name + '_receipt_stale')
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


def interpolate_angular_velocity(samples, stamp):
    """Interpolate the nearest bracketing IMU gyro pair, scanning newest first."""
    following = None
    for current in reversed(samples):
        if abs(current[0] - stamp) <= 1000:
            return current[1]
        if current[0] < stamp:
            if following is None:
                return None
            weight = (stamp - current[0]) / (following[0] - current[0])
            return [a + weight * (b - a) for a, b in zip(current[1], following[1])]
        following = current
    return None


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
