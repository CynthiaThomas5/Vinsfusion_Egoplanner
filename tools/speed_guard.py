"""Small, ROS-independent vector-speed guard shared by runtime and unit checks."""

import math


def speed_limit_event(velocity, limit_m_s, *, source, timestamp=None,
                      tolerance_m_s=1e-6):
    """Return a structured violation event, or None when the sample is in bounds.

    Invalid values fail closed because a speed guard cannot certify them.
    """
    try:
        values = tuple(float(value) for value in velocity)
        limit = float(limit_m_s)
        tolerance = float(tolerance_m_s)
    except (TypeError, ValueError, OverflowError):
        values, limit, tolerance = (), float('nan'), float('nan')

    valid = (len(values) == 3 and all(math.isfinite(value) for value in values)
             and math.isfinite(limit) and limit > 0.0
             and math.isfinite(tolerance) and tolerance >= 0.0)
    speed = math.sqrt(sum(value * value for value in values)) if valid else None
    if valid and speed <= limit + tolerance:
        return None
    return {
        'source': str(source),
        'velocity_m_s': (list(values) if len(values) == 3
                         and all(math.isfinite(value) for value in values) else None),
        'vector_speed_m_s': speed,
        'limit_m_s': limit if math.isfinite(limit) else None,
        'tolerance_m_s': tolerance if math.isfinite(tolerance) else None,
        'timestamp': timestamp,
        'reason': ('vector_speed_exceeded' if valid
                   else 'invalid_speed_guard_sample'),
    }
