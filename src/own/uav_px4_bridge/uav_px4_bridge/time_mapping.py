"""Map ROS simulation stamps into PX4's XRCE-DDS timestamp domain."""

from collections import deque
from dataclasses import dataclass
import math


class TimeMappingError(ValueError):
    pass


def fallback_agent_timestamp_us(agent_time_ns, timesync_fresh):
    """Use current Agent/system time after clock mapping fails, if synced."""
    if not timesync_fresh:
        return 0
    timestamp_us = int(agent_time_ns) // 1000
    if timestamp_us <= 0:
        raise TimeMappingError('timestamps_must_be_positive')
    return timestamp_us


def px4_clock_age_sim_s(ros_clock_ns, agent_timestamp_us, estimated_offset_us):
    """Recover a PX4 HRT stamp from XRCE's Agent clock and compare with /clock."""
    ros_clock_ns = int(ros_clock_ns)
    px4_sample_us = int(agent_timestamp_us) + int(estimated_offset_us)
    if ros_clock_ns <= 0 or px4_sample_us <= 0:
        raise TimeMappingError('px4_timestamp_invalid')
    return (ros_clock_ns // 1000 - px4_sample_us) / 1e6


def px4_timesync_age_sim_s(ros_clock_ns, timesync_timestamp_us, estimated_offset_us):
    """Recover PX4 HRT from shifted TimesyncStatus and compare it with /clock."""
    try:
        return px4_clock_age_sim_s(
            ros_clock_ns, timesync_timestamp_us, estimated_offset_us)
    except TimeMappingError as exc:
        raise TimeMappingError('px4_timesync_stale') from exc


def px4_ros_source_gap_sim_s(ros_stamp_ns, px4_agent_stamp_us,
                             estimated_offset_us, px4_ros_clock_offset_us=0):
    """Compare a ROS source stamp with a PX4 telemetry stamp in PX4 sim time."""
    ros_stamp_ns = int(ros_stamp_ns)
    px4_stamp_us = int(px4_agent_stamp_us) + int(estimated_offset_us)
    ros_px4_stamp_us = ros_stamp_ns // 1000 + int(px4_ros_clock_offset_us)
    if ros_px4_stamp_us <= 0 or px4_stamp_us <= 0:
        raise TimeMappingError('px4_timestamp_invalid')
    return abs(ros_px4_stamp_us - px4_stamp_us) / 1e6


@dataclass(frozen=True)
class PX4Time:
    """Outgoing timestamp fields in the Agent clock expected by PX4 XRCE-DDS."""
    now_us: int
    sample_us: int
    sample_age_wall_s: float


def retain_hardware_sync(previous, previous_receipt, incoming, receipt_ns, system_ns, config):
    """Reject a noisy measurement without renewing the last accepted sample."""
    age = (system_ns-int(incoming.timestamp)*1000)/1e9
    if incoming.source_protocol != 2 or age < -config['max_future_s']:
        return None, None
    if age > config['timesync_max_age_s']:
        return previous, previous_receipt
    if not 0 <= incoming.round_trip_time <= config['timesync_max_rtt_us']:
        return previous, previous_receipt
    if previous is not None and incoming.timestamp < previous.timestamp:
        return None, None
    return incoming, receipt_ns


class SystemClockMapper:
    """Hardware stamps already use the Agent's system epoch; never add offset.

    Monotonic/system disagreement latches a fault instead of silently joining
    clock epochs. Timesync's offset is only used to validate recovered HRT.
    """

    def __init__(self, max_source_age_s, max_future_s, max_clock_step_s, enforce_source_age=True):
        self.enforce_source_age = enforce_source_age
        self.max_source_age_s = float(max_source_age_s)
        self.max_future_s = float(max_future_s)
        self.max_clock_step_s = float(max_clock_step_s)
        if any(not math.isfinite(x) or x <= 0 for x in (
                self.max_source_age_s, self.max_future_s, self.max_clock_step_s)):
            raise ValueError('Hardware clock budgets must be finite and positive')
        self.previous = None
        self.reason = ''

    def observe(self, system_ns, monotonic_ns):
        if self.reason:
            raise TimeMappingError(self.reason)
        if system_ns <= 0 or monotonic_ns <= 0:
            raise TimeMappingError('timestamps_must_be_positive')
        if self.previous is not None:
            old_system, old_mono = self.previous
            if (system_ns < old_system or monotonic_ns < old_mono
                    or abs((system_ns-old_system)-(monotonic_ns-old_mono))
                    > self.max_clock_step_s * 1e9):
                self.reason = 'hardware_system_clock_changed'
                raise TimeMappingError(self.reason)
        self.previous = (int(system_ns), int(monotonic_ns))

    def to_px4(self, source_ns, system_ns, monotonic_ns, timesync,
               timesync_receipt_ns, max_timesync_age_s, max_rtt_us):
        self.observe(system_ns, monotonic_ns)
        if timesync is None or timesync_receipt_ns is None:
            raise TimeMappingError('px4_timesync_stale')
        ages = ((monotonic_ns-timesync_receipt_ns)/1e9,
                (system_ns-timesync.timestamp*1000)/1e9)
        if (timesync.source_protocol != 2 or any(
                not -self.max_future_s <= age <= max_timesync_age_s for age in ages)):
            raise TimeMappingError('px4_timesync_stale')
        if not 0 <= timesync.round_trip_time <= max_rtt_us:
            raise TimeMappingError('px4_timesync_rtt_high')
        age = (system_ns-int(source_ns))/1e9
        if source_ns <= 0 or age < -self.max_future_s or (self.enforce_source_age and age > self.max_source_age_s):
            raise TimeMappingError('hardware_source_stamp_stale_or_future')
        if int(source_ns)//1000 + int(timesync.estimated_offset) <= 0:
            raise TimeMappingError('mapped_px4_time_invalid')
        return PX4Time(system_ns//1000, int(source_ns)//1000, max(0., age))


class RosClockMapper:
    """Fit /clock to monotonic time for freshness checks and map lockstep stamps.

    ROS simulation time is PX4 HRT in Gazebo lockstep. Outgoing timestamps are
    inverse-mapped through the latest PX4-to-Agent offset because PX4's XRCE
    deserializer converts them back into its local clock. Rollbacks, poor
    fits, and future timestamps fail closed; receipt age remains observable.
    """

    def __init__(self, min_samples, max_samples, max_future_s,
                 min_rate, max_rate, lockstep=False):
        if min_samples < 3 or max_samples < min_samples:
            raise ValueError('clock sample limits are inconsistent')
        self.min_samples = int(min_samples)
        self.max_future_s = float(max_future_s)
        self.min_rate = float(min_rate)
        self.max_rate = float(max_rate)
        self.lockstep = bool(lockstep)
        self.samples = deque(maxlen=int(max_samples))
        self.last_ros_ns = None
        self.locked = False
        self.reason = ''

    def add_clock(self, ros_ns, monotonic_ns):
        ros_ns, monotonic_ns = int(ros_ns), int(monotonic_ns)
        if ros_ns <= 0 or monotonic_ns <= 0:
            raise TimeMappingError('clock samples must be positive')
        if self.locked:
            raise TimeMappingError(self.reason)
        if self.last_ros_ns is not None and ros_ns < self.last_ros_ns:
            self.locked = True
            self.reason = 'ros_clock_regression'
            self.samples.clear()
            raise TimeMappingError(self.reason)
        if self.last_ros_ns == ros_ns and self.samples:
            self.samples[-1] = (ros_ns, monotonic_ns)
        else:
            self.samples.append((ros_ns, monotonic_ns))
        self.last_ros_ns = ros_ns

    def current_lockstep_px4_time_us(self, monotonic_ns):
        """Return current /clock directly when it is PX4 HRT in lockstep."""
        monotonic_ns = int(monotonic_ns)
        if not self.lockstep:
            raise TimeMappingError('px4_clock_requires_lockstep_without_timestamp_sync')
        if self.locked:
            raise TimeMappingError(self.reason)
        if len(self.samples) < self.min_samples:
            raise TimeMappingError('clock_mapping_not_converged')
        ros_ns, latest_monotonic_ns = self.samples[-1]
        if monotonic_ns < latest_monotonic_ns:
            raise TimeMappingError('clock_receipt_in_future')
        return ros_ns // 1000

    def _fit(self):
        if self.locked:
            raise TimeMappingError(self.reason)
        if len(self.samples) < self.min_samples:
            raise TimeMappingError('clock_mapping_not_converged')
        x0, y0 = self.samples[0]
        dx = [float(x - x0) for x, _ in self.samples]
        dy = [float(y - y0) for _, y in self.samples]
        mean_x = sum(dx) / len(dx)
        mean_y = sum(dy) / len(dy)
        variance_x = sum((x - mean_x) ** 2 for x in dx)
        if variance_x <= 0.0:
            raise TimeMappingError('clock_mapping_no_span')
        slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(dx, dy)) / variance_x
        if not math.isfinite(slope) or not self.min_rate <= slope <= self.max_rate:
            raise TimeMappingError('clock_mapping_rate_out_of_bounds')
        residuals = [y - (mean_y + slope * (x - mean_x))
                     for x, y in zip(dx, dy)]
        residual_ns = max(abs(value) for value in residuals)
        return x0, y0, slope, residual_ns

    def ros_time_at_monotonic(self, monotonic_ns, max_fit_residual_s):
        """Estimate current simulation time at a monotonic receipt instant."""
        monotonic_ns = int(monotonic_ns)
        if not self.samples:
            raise TimeMappingError('clock_mapping_not_converged')
        latest_ros_ns, latest_mono_ns = self.samples[-1]
        if monotonic_ns < latest_mono_ns:
            raise TimeMappingError('clock_receipt_in_future')
        if self.lockstep:
            # In Gazebo lockstep /clock is PX4 HRT. Do not extrapolate it
            # through wall time: the simulator can pause briefly while the
            # clock callback is still within its configured freshness window.
            self._fit()  # Keep sample-count and simulation-rate validation.
            return latest_ros_ns
        x0, y0, slope, residual_ns = self._fit()
        if residual_ns / 1e9 > float(max_fit_residual_s):
            raise TimeMappingError('clock_mapping_residual_high')
        ros_ns = int(round(x0 + (monotonic_ns - y0) / slope))
        return max(ros_ns, latest_ros_ns)

    def to_px4(self, source_ros_ns, receipt_monotonic_ns, receipt_system_ns,
               estimated_offset_us, timesync_rtt_us, timesync_receipt_monotonic_ns,
               max_timesync_age_s, max_timesync_rtt_us, max_fit_residual_s,
               timesync_age_s=None, px4_ros_clock_offset_us=0,
               max_timesync_future_s=None, timestamp_sync_enabled=True):
        source_ros_ns = int(source_ros_ns)
        receipt_monotonic_ns = int(receipt_monotonic_ns)
        receipt_system_ns = int(receipt_system_ns)
        timesync_receipt_monotonic_ns = int(timesync_receipt_monotonic_ns)
        if self.locked:
            raise TimeMappingError(self.reason)
        if not self.samples:
            raise TimeMappingError('clock_mapping_not_converged')
        latest_ros_ns, latest_clock_mono_ns = self.samples[-1]
        if receipt_monotonic_ns < latest_clock_mono_ns:
            raise TimeMappingError('clock_receipt_in_future')
        if type(timestamp_sync_enabled) is not bool:
            raise TimeMappingError('timestamp_sync_enabled must be boolean')
        if timestamp_sync_enabled:
            if timesync_receipt_monotonic_ns <= 0:
                raise TimeMappingError('px4_timesync_stale')
            if timesync_age_s is None:
                timesync_age_s = (receipt_monotonic_ns - timesync_receipt_monotonic_ns) / 1e9
            timesync_age_s = float(timesync_age_s)
            if max_timesync_future_s is None:
                max_timesync_future_s = self.max_future_s
            max_timesync_future_s = float(max_timesync_future_s)
            if (not math.isfinite(timesync_age_s)
                    or not math.isfinite(max_timesync_future_s)
                    or max_timesync_future_s < 0.0
                    or timesync_age_s < -max_timesync_future_s):
                raise TimeMappingError('px4_timesync_stale')
            if timesync_age_s > max_timesync_age_s:
                raise TimeMappingError('px4_timesync_stale')
            if int(timesync_rtt_us) < 0 or int(timesync_rtt_us) > max_timesync_rtt_us:
                raise TimeMappingError('px4_timesync_rtt_high')
        elif not self.lockstep:
            raise TimeMappingError('px4_clock_requires_lockstep_without_timestamp_sync')
        if source_ros_ns <= 0 or receipt_system_ns <= 0:
            raise TimeMappingError('timestamps_must_be_positive')

        x0, y0, slope, residual_ns = self._fit()
        if not self.lockstep and residual_ns / 1e9 > max_fit_residual_s:
            raise TimeMappingError('clock_mapping_residual_high')
        if source_ros_ns > latest_ros_ns:
            raise TimeMappingError('source_stamp_outside_clock_history')
        if (self.lockstep and self.samples[0][0] <= source_ros_ns <= latest_ros_ns):
            sample_mono_ns = self._monotonic_at_ros_time(source_ros_ns)
        else:
            # Older lockstep samples remain mappable after the bounded clock
            # history rolls over; the timestamp still carries its original
            # PX4 simulation time and is not rejected for age.
            sample_mono_ns = int(round(y0 + slope * (source_ros_ns - x0)))
        age_ns = receipt_monotonic_ns - sample_mono_ns
        if age_ns < -self.max_future_s * 1e9:
            raise TimeMappingError('source_stamp_in_future')
        if age_ns < 0:
            age_ns = 0

        offset_us = int(estimated_offset_us) if timestamp_sync_enabled else 0
        # With UXRCE_DDS_SYNCT enabled, inverse-map the source stamp into the
        # Agent clock expected by PX4. With Gazebo lockstep and timestamp sync
        # disabled, /clock is PX4 HRT directly for both current and sample time.
        if timestamp_sync_enabled:
            now_us = receipt_system_ns // 1000
        else:
            now_us = self.ros_time_at_monotonic(
                receipt_monotonic_ns, max_fit_residual_s) // 1000
        px4_sample_us = source_ros_ns // 1000 + int(px4_ros_clock_offset_us)
        sample_us = px4_sample_us - offset_us
        if sample_us <= 0 or now_us <= 0 or sample_us > now_us + self.max_future_s * 1e6:
            raise TimeMappingError('mapped_px4_time_invalid')
        return PX4Time(now_us=now_us, sample_us=sample_us,
                       sample_age_wall_s=age_ns / 1e9)

    def _monotonic_at_ros_time(self, ros_ns):
        """Interpolate the observed lockstep clock history at a source stamp."""
        samples = tuple(self.samples)
        ros_ns = int(ros_ns)
        for (left_ros_ns, left_mono_ns), (right_ros_ns, right_mono_ns) in zip(
                samples, samples[1:]):
            if left_ros_ns <= ros_ns <= right_ros_ns:
                ros_span = right_ros_ns - left_ros_ns
                if ros_span <= 0:
                    raise TimeMappingError('clock_mapping_no_span')
                rate = (right_mono_ns - left_mono_ns) / ros_span
                # DDS may deliver queued clock samples in a burst. _fit()
                # already checks the window rate; retain actual receipt times
                # for age interpolation without treating callback jitter as RTF.
                if not math.isfinite(rate) or rate <= 0.0:
                    raise TimeMappingError('clock_receipt_not_increasing')
                return int(round(left_mono_ns + rate * (ros_ns - left_ros_ns)))
        if samples and ros_ns == samples[-1][0]:
            return samples[-1][1]
        raise TimeMappingError('source_stamp_outside_clock_history')
