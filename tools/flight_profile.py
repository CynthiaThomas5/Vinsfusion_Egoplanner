"""Bounded mission profiles: all offsets share the initial airborne odom pose."""
import math


def navigation_duration_requirement(config):
    value = config.get('continuous_navigation_min_sim_s', 0.0)
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value < 0):
        raise ValueError('Finite nonnegative continuous navigation duration required')
    return float(value)


def navigation_elapsed_sim_s(start_ns, end_ns):
    if (not isinstance(start_ns, int) or not isinstance(end_ns, int)
            or end_ns < start_ns):
        raise ValueError('Invalid continuous navigation source-time interval')
    return (end_ns - start_ns) / 1e9


def legs(config):
    if config.get('enabled', True) is not True:
        raise ValueError('Mission profile disabled: '+str(config.get('disabled_reason', 'pending safety review')))
    rows = config.get('goals', [dict(target_offset_enu_m=config.get('target_offset_enu_m'),
                                     yaw_offset_rad=config.get('yaw_offset_rad', 0.0))])
    maximum = 24 if navigation_duration_requirement(config) > 0 else 3
    if not isinstance(rows, list) or not 1 <= len(rows) <= maximum:
        raise ValueError(f'Mission needs one to {maximum} goals')
    result = []
    for row in rows:
        offset = row.get('target_offset_enu_m')
        yaw = row.get('yaw_offset_rad', 0.0)
        if (not isinstance(offset, list) or len(offset) != 3
                or any(isinstance(v, bool) or not isinstance(v, (float, int))
                       or not math.isfinite(v) for v in offset + [yaw])):
            raise ValueError('Finite ENU offset and yaw required')
        result.append({**config, 'target_offset_enu_m': offset, 'yaw_offset_rad': yaw})
    return result


def attempts(flight):
    """Include an unfinished current goal, without reusing an earlier end stamp."""
    rows = list(flight.get('legs') or [])
    if flight.get('goal_id') and not any(p['goal_id'] == flight['goal_id'] for p in rows):
        current = dict(flight)
        if not current.get('action_success'):
            current.pop('goal_completed_source_ns', None)
        rows.append(current)
    return rows or [flight]
