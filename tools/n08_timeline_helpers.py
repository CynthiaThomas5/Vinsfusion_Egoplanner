"""Small pure helpers used by the N08 read-only timing observer."""
import json
import math


BRIDGE_TIMING_FIELDS = (
    'phase', 'reason', 'px4_time_domain_valid', 'px4_timestamp_error',
    'px4_time_reference_us', 'px4_ros_clock_gap_sim_s',
    'odometry_time_error', 'timesync_age_sim_s',
    'clock_receipt_age_wall_s', 'clock_progress_age_wall_s',
    'alignment_pair_gap_sim_s', 'alignment_pair_validated_gap_sim_s',
    'alignment_pair_validated_age_wall_s', 'wall_age_s',
    'px4_telemetry_freshness',
)


def clock_sample_due(previous_clock_ns, current_clock_ns,
                     now_monotonic_ns, last_record_monotonic_ns,
                     interval_ns):
    """Sample clocks periodically, but always preserve a clock regression."""
    regression = (previous_clock_ns is not None
                  and current_clock_ns < previous_clock_ns)
    due = (last_record_monotonic_ns is None or regression
           or now_monotonic_ns - last_record_monotonic_ns >= interval_ns)
    return bool(due), bool(regression)


def stream_sample_due(now_monotonic_ns, last_record_monotonic_ns,
                      interval_ns, transition_changed=False,
                      source_regression=False):
    """Decimate high-rate sources while retaining state changes and regressions."""
    due = (last_record_monotonic_ns is None
           or now_monotonic_ns - last_record_monotonic_ns >= interval_ns
           or transition_changed or source_regression)
    return bool(due)


def health_metric_summary(metrics, cost_limit=None):
    """Keep health totals and compact residual-group details for timeline samples."""
    if not isinstance(metrics, dict):
        raise ValueError('telemetry metrics must be an object')
    if (cost_limit is not None
            and (not math.isfinite(cost_limit) or cost_limit <= 0)):
        raise ValueError('cost limit must be positive and finite')
    keys = ('stamp_ns', 'initialized', 'solve_current', 'solver_usable',
            'state_finite', 'termination_type', 'solve_seconds',
            'residual_components', 'iterations', 'input_features',
            'stereo_features', 'continued_tracks', 'long_tracks',
            'final_cost')
    record = {key: metrics.get(key) for key in keys}
    final_cost = metrics.get('final_cost')
    residuals = metrics.get('residual_components')
    normalized = None
    if (type(final_cost) in (int, float) and math.isfinite(final_cost)
            and final_cost >= 0 and type(residuals) in (int, float)
            and math.isfinite(residuals) and residuals > 0):
        normalized = math.sqrt(2 * final_cost / residuals)
    record['normalized_cost'] = normalized
    record['cost_limit'] = cost_limit
    record['cost_limit_exceeded'] = (
        None if normalized is None or cost_limit is None else normalized > cost_limit)

    components = metrics.get('cost_components')
    if not isinstance(components, dict):
        record['cost_components'] = None
        return record
    groups = {}
    for name in ('visual', 'imu', 'marginalization'):
        group = components.get(name)
        if not isinstance(group, dict):
            groups[name] = None
            continue
        groups[name] = {
            'cost': group.get('cost'),
            'residual_components': group.get('residual_components'),
        }
    prior = components.get('prior_details')
    prior_summary = None
    if isinstance(prior, dict):
        prior_keys = (
            'available', 'evaluation_ok', 'spectrum_ok',
            'next_marginalization_branch', 'information_rank',
            'retained_dimension', 'information_min_positive',
            'information_max', 'current_squared_norm',
            'r0_squared_norm', 'Jdx_squared_norm',
            'twice_r0_dot_Jdx')
        prior_summary = {key: prior.get(key) for key in prior_keys}
    record['cost_components'] = {
        'evaluation_ok': components.get('evaluation_ok'),
        'evaluation_seconds': components.get('evaluation_seconds'),
        'grouped_cost_sum': components.get('grouped_cost_sum'),
        'grouped_residual_components': components.get(
            'grouped_residual_components'),
        'grouped_cost_error': components.get('grouped_cost_error'),
        'groups': groups,
        'prior': prior_summary,
    }
    return record


def bridge_timing_fields(serialized):
    """Return only time/alignment fields from the bridge detail JSON."""
    try:
        value = json.loads(serialized)
    except (TypeError, ValueError) as exc:
        return {'parse_error': str(exc)}
    if not isinstance(value, dict):
        return {'parse_error': 'bridge detail is not a JSON object'}
    return {key: value.get(key) for key in BRIDGE_TIMING_FIELDS}
