"""Bounded mission profiles: all offsets share the initial airborne odom pose."""
import math


def legs(config):
    if config.get('enabled', True) is not True:
        raise ValueError('Mission profile disabled: '+str(config.get('disabled_reason', 'pending safety review')))
    rows = config.get('goals', [dict(target_offset_enu_m=config.get('target_offset_enu_m'),
                                     yaw_offset_rad=config.get('yaw_offset_rad', 0.0))])
    if not isinstance(rows, list) or not 1 <= len(rows) <= 3:
        raise ValueError('Mission needs one to three goals')
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
