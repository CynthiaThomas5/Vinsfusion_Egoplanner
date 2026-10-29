"""Small, pure helpers for N10 caller-cancel speed calibration."""
import math


def cancel_trigger(command, local, *, goal_id, epoch, ready_flag, speed_window_m_s):
    """Return a measured trigger row or None until a matching moving command exists."""
    lower, upper = map(float, speed_window_m_s)
    if not (math.isfinite(lower) and math.isfinite(upper) and 0.0 < lower < upper):
        raise ValueError('cancel_speed_window_must_be_finite_positive_increasing')
    if not isinstance(command, dict) or not isinstance(local, dict):
        return None
    if (command.get('goal_id') != goal_id or command.get('epoch') != epoch
            or command.get('flag') != ready_flag):
        return None
    if local.get('xy_valid') is not True or local.get('z_valid') is not True:
        return None
    try:
        actual_v = tuple(float(local[k]) for k in ('vx', 'vy', 'vz'))
        reference_v = tuple(float(x) for x in command['velocity_enu_m_s'])
        reference_a = tuple(float(x) for x in command['acceleration_enu_m_s2'])
        sim_ns = int(local['sim_time_ns'])
        sample_us = int(local['timestamp_sample_us'])
    except (KeyError, TypeError, ValueError, OverflowError):
        return None
    values = (*actual_v, *reference_v, *reference_a)
    if (len(reference_v) != 3 or len(reference_a) != 3
            or not all(math.isfinite(x) for x in values) or sim_ns <= 0 or sample_us <= 0):
        return None
    actual_horizontal = math.hypot(actual_v[0], actual_v[1])
    reference_speed = math.sqrt(sum(x*x for x in reference_v))
    if not (lower <= actual_horizontal <= upper and reference_speed > 0.0):
        return None
    return {
        'request_sim_ns': sim_ns,
        'px4_sample_us': sample_us,
        'px4_horizontal_speed_m_s': actual_horizontal,
        'px4_vertical_speed_m_s': actual_v[2],
        'ego_reference_speed_m_s': reference_speed,
        'ego_reference_velocity_enu_m_s': list(reference_v),
        'ego_reference_acceleration_enu_m_s2': list(reference_a),
        'ego_reference_trajectory_id': command.get('trajectory_id'),
        'ego_reference_source_stamp_ns': command.get('source_stamp_ns'),
        'position_local_ned_m': [float(local[k]) for k in ('x', 'y', 'z')],
    }


class StopWindowTracker:
    """Find a continuous PX4 stop band using sample source times, without sorting."""

    def __init__(self, *, trigger_sim_ns, horizontal_max_m_s=0.03,
                 vertical_abs_max_m_s=0.05, dwell_sim_s=1.0,
                 max_sample_gap_sim_s=0.20):
        self.trigger_sim_ns = int(trigger_sim_ns)
        self.horizontal_max_m_s = float(horizontal_max_m_s)
        self.vertical_abs_max_m_s = float(vertical_abs_max_m_s)
        self.dwell_ns = int(float(dwell_sim_s) * 1e9)
        self.max_gap_ns = int(float(max_sample_gap_sim_s) * 1e9)
        if (self.trigger_sim_ns <= 0 or self.dwell_ns <= 0 or self.max_gap_ns <= 0
                or not all(math.isfinite(x) and x > 0 for x in (
                    self.horizontal_max_m_s, self.vertical_abs_max_m_s,
                    float(dwell_sim_s), float(max_sample_gap_sim_s)))):
            raise ValueError('invalid_stop_window_definition')
        self.last_sample_us = None
        self.last_sim_ns = None
        self.window_start_sim_ns = None
        self.last_stop_sim_ns = None
        self.samples = []
        self.max_stop_gap_ns = 0

    def observe(self, row):
        try:
            sample_us = int(row['timestamp_sample_us'])
            sim_ns = int(row['sim_time_ns'])
            vx, vy, vz = (float(row[k]) for k in ('vx', 'vy', 'vz'))
        except (KeyError, TypeError, ValueError, OverflowError):
            return None
        if (sim_ns < self.trigger_sim_ns or sample_us <= 0
                or not all(math.isfinite(x) for x in (vx, vy, vz))):
            return None
        if self.last_sample_us is not None:
            if sample_us < self.last_sample_us or sim_ns < self.last_sim_ns:
                raise ValueError('px4_stop_sample_time_regressed')
            if sample_us == self.last_sample_us or sim_ns == self.last_sim_ns:
                return None
        self.last_sample_us = sample_us
        self.last_sim_ns = sim_ns
        horizontal = math.hypot(vx, vy)
        state_valid = row.get('xy_valid') is True and row.get('z_valid') is True
        if (state_valid and horizontal <= self.horizontal_max_m_s
                and abs(vz) <= self.vertical_abs_max_m_s):
            if self.window_start_sim_ns is None:
                self.window_start_sim_ns = sim_ns
                self.last_stop_sim_ns = sim_ns
                self.max_stop_gap_ns = 0
                self.samples = []
            else:
                gap = sim_ns - self.last_stop_sim_ns
                if gap > self.max_gap_ns:
                    self.window_start_sim_ns = sim_ns
                    self.samples = []
                    self.max_stop_gap_ns = 0
                else:
                    self.max_stop_gap_ns = max(self.max_stop_gap_ns, gap)
                self.last_stop_sim_ns = sim_ns
            self.samples.append({
                'sim_time_ns': sim_ns,
                'timestamp_sample_us': sample_us,
                'horizontal_speed_m_s': horizontal,
                'absolute_vertical_speed_m_s': abs(vz),
                'position_ned_m': [float(row[k]) for k in ('x', 'y', 'z')],
            })
            if sim_ns - self.window_start_sim_ns >= self.dwell_ns:
                return {
                    'start_sim_ns': self.window_start_sim_ns,
                    'confirmed_sim_ns': sim_ns,
                    'dwell_sim_s': (sim_ns - self.window_start_sim_ns) / 1e9,
                    'sample_count': len(self.samples),
                    'max_sample_gap_sim_s': self.max_stop_gap_ns / 1e9,
                    'samples': list(self.samples),
                }
        else:
            self.window_start_sim_ns = None
            self.last_stop_sim_ns = None
            self.samples.clear()
        return None
