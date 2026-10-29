"""Read-only simultaneous position/yaw dwell analysis for N10 runs."""
from __future__ import annotations

import math


def wrapped_angle_error_rad(actual: float, target: float) -> float:
    """Return the absolute shortest angular distance in radians."""
    if not math.isfinite(actual) or not math.isfinite(target):
        raise ValueError('yaw values must be finite')
    return abs((actual - target + math.pi) % (2.0 * math.pi) - math.pi)


def longest_contiguous_window(rows, max_sim_gap_s=0.04, max_wall_gap_s=0.12):
    """Find the longest joint-good window without sorting or repairing stamps."""
    if not (math.isfinite(max_sim_gap_s) and max_sim_gap_s > 0.0
            and math.isfinite(max_wall_gap_s) and max_wall_gap_s > 0.0):
        raise ValueError('gap limits must be finite and positive')

    best = []
    current = []
    previous = None

    def keep_longer(candidate, existing):
        if not candidate:
            return existing
        candidate_duration = candidate[-1]['sim_s'] - candidate[0]['sim_s']
        existing_duration = (existing[-1]['sim_s'] - existing[0]['sim_s']
                             if existing else -1.0)
        return candidate if candidate_duration > existing_duration else existing

    for row in rows:
        sim_s = float(row['sim_s'])
        wall_s = float(row['wall_s'])
        if not (math.isfinite(sim_s) and math.isfinite(wall_s)):
            raise ValueError('window timestamps must be finite')
        if previous is not None:
            sim_gap = sim_s - previous['sim_s']
            wall_gap = wall_s - previous['wall_s']
            if sim_gap <= 0.0 or wall_gap <= 0.0:
                raise ValueError('window timestamps must increase without repair')
            if sim_gap > max_sim_gap_s or wall_gap > max_wall_gap_s:
                best = keep_longer(current, best)
                current = []

        if row['within_tolerance']:
            current.append(row)
        elif current:
            best = keep_longer(current, best)
            current = []
        previous = {'sim_s': sim_s, 'wall_s': wall_s}

    best = keep_longer(current, best)
    if not best:
        return {
            'sample_count': 0,
            'sim_duration_s': 0.0,
            'wall_duration_s': 0.0,
            'start_sim_s': None,
            'end_sim_s': None,
            'max_position_error_m': None,
            'max_yaw_error_deg': None,
        }
    return {
        'sample_count': len(best),
        'sim_duration_s': best[-1]['sim_s'] - best[0]['sim_s'],
        'wall_duration_s': best[-1]['wall_s'] - best[0]['wall_s'],
        'start_sim_s': best[0]['sim_s'],
        'end_sim_s': best[-1]['sim_s'],
        'max_position_error_m': max(row['position_error_m'] for row in best),
        'max_yaw_error_deg': max(row['yaw_error_deg'] for row in best),
    }
