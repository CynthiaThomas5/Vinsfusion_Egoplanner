"""Fail-closed P3 Offboard supervision, independent of ROS message types."""
from dataclasses import dataclass
import math

from .trajectory import validate_px4_runtime_profile


READINESS_REQUIREMENTS = (
    ('px4_time_domain_valid', 'px4_time_domain_invalid'),
    ('local_position_valid', 'px4_local_position_invalid'),
    ('ev_position_fused', 'ev_position_not_fused'),
    ('ev_yaw_fused', 'ev_yaw_not_fused'),
    ('alignment_valid', 'px4_frame_unaligned'),
    ('preflight_passed', 'px4_preflight_failed'),
)


def readiness_failure(snapshot, profile, frame_contract, require_preflight=True):
    """Check PX4-native state and input identity; receipt ages are observational."""
    validate_px4_runtime_profile(profile, frame_contract)
    for name, reason in READINESS_REQUIREMENTS:
        if name == 'preflight_passed' and not require_preflight:
            continue
        if type(snapshot.get(name)) is not bool:
            return 'missing_' + name
        if not snapshot[name]:
            return reason
    for name in ('gnss_position_aiding', 'gnss_velocity_aiding',
                 'gnss_height_aiding', 'gnss_yaw_aiding'):
        if type(snapshot.get(name)) is not bool:
            return 'missing_' + name
        if snapshot[name]:
            return 'gnss_aiding_active'
    return ''


def matching_planner_abort_reason(mode, abort_mode, active_goal_id, active_epoch,
                                  fault_goal_id, fault_epoch, reason, airborne):
    """Return a planner abort reason only for the current airborne task."""
    if not airborne or mode != abort_mode:
        return ''
    if (not active_goal_id or not active_epoch
            or fault_goal_id != active_goal_id or fault_epoch != active_epoch):
        return ''
    detail = str(reason).strip()
    return 'planner_fault:' + (detail or 'unspecified')


@dataclass(frozen=True)
class ControlOutput:
    phase: str
    publish_offboard: bool = False
    setpoint_kind: str = ''
    command: str = ''
    reason: str = ''


class OffboardSupervisor:
    """One-shot service-gated state machine for a P3 SITL flight session."""

    DISABLED = 'DISABLED'
    PRESTREAM = 'PRESTREAM'
    REQUEST_OFFBOARD = 'REQUEST_OFFBOARD'
    REQUEST_ARM = 'REQUEST_ARM'
    TAKEOFF = 'TAKEOFF'
    ACTIVE = 'ACTIVE'
    LANDING = 'LANDING'
    LANDED = 'LANDED'
    LOCKED = 'LOCKED'

    def __init__(self, profile, frame_contract, prestream_wall_s,
                 takeoff_altitude_m, position_tolerance_m,
                 velocity_tolerance_m_s, takeoff_dwell_wall_s,
                 command_retry_wall_s, command_retry_limit):
        validate_px4_runtime_profile(profile, frame_contract)
        numeric = (prestream_wall_s, takeoff_altitude_m, position_tolerance_m,
                   velocity_tolerance_m_s, takeoff_dwell_wall_s,
                   command_retry_wall_s)
        if not all(math.isfinite(float(v)) and float(v) > 0.0 for v in numeric):
            raise ValueError('Offboard timing and takeoff limits must be positive and finite')
        if type(command_retry_limit) is not int or command_retry_limit < 1:
            raise ValueError('command_retry_limit must be a positive integer')
        self.profile = profile
        self.frame_contract = frame_contract
        self.prestream_wall_s = float(prestream_wall_s)
        self.takeoff_altitude_m = float(takeoff_altitude_m)
        self.position_tolerance_m = float(position_tolerance_m)
        self.velocity_tolerance_m_s = float(velocity_tolerance_m_s)
        self.takeoff_dwell_wall_s = float(takeoff_dwell_wall_s)
        self.command_retry_wall_s = float(command_retry_wall_s)
        self.command_retry_limit = command_retry_limit
        self.phase = self.DISABLED
        self.reason = 'service_enable_required'
        self.started_wall = None
        self.takeoff_origin = None
        self.takeoff_target = None
        self.takeoff_yaw = None
        self.takeoff_dwell_since = None
        self.last_command_wall = None
        self.command_attempts = 0
        self.active_trajectory_seen = False
        self.landing_reason = ''
        self.land_command_attempts = 0
        self.last_land_command_wall = None

    def enable(self, snapshot, wall_now):
        if self.phase != self.DISABLED:
            return False, 'controller_not_disabled'
        # PX4's current AUTO_LOITER state can require global position even when
        # the requested Offboard mode needs only local EV position. Start the
        # disarmed prestream, then require PX4 preflight approval before arming.
        reason = readiness_failure(snapshot, self.profile, self.frame_contract,
                                   require_preflight=False)
        if reason:
            self.reason = reason
            return False, reason
        if type(snapshot.get('landed')) is not bool or not snapshot['landed']:
            self.reason = 'vehicle_not_landed'
            return False, self.reason
        if type(snapshot.get('armed')) is not bool or snapshot['armed']:
            self.reason = 'vehicle_already_armed'
            return False, self.reason
        position = tuple(float(v) for v in snapshot.get('position_ned', ()))
        yaw = float(snapshot.get('heading_ned', math.nan))
        if len(position) != 3 or not all(math.isfinite(v) for v in position) or not math.isfinite(yaw):
            self.reason = 'invalid_px4_hold_pose'
            return False, self.reason
        self.started_wall = float(wall_now)
        self.takeoff_origin = position
        self.takeoff_target = (position[0], position[1],
                               position[2] - self.takeoff_altitude_m)
        self.takeoff_yaw = yaw
        self.phase = self.PRESTREAM
        self.reason = 'prestreaming_offboard_setpoints'
        self.command_attempts = 0
        self.last_command_wall = None
        return True, self.reason

    def disable(self, snapshot, wall_now=0.0):
        if self.phase in (self.PRESTREAM, self.REQUEST_OFFBOARD, self.REQUEST_ARM):
            self.phase = self.DISABLED
            self.reason = 'operator_disabled_before_takeoff'
            return ControlOutput(self.phase, reason=self.reason)
        if self.phase in (self.TAKEOFF, self.ACTIVE):
            return self._begin_landing('operator_disable', snapshot, wall_now)
        return ControlOutput(self.phase, reason=self.reason)

    def _begin_landing(self, reason, snapshot, wall_now):
        self.phase = self.LANDING
        self.landing_reason = reason
        self.reason = reason
        self.land_command_attempts = 0
        self.last_land_command_wall = None
        command = self._landing_command(snapshot, wall_now)
        return ControlOutput(self.phase, command=command, reason=self.reason)

    def _landing_command(self, snapshot, wall_now):
        """Retry an unconfirmed PX4 LAND request, then keep monitoring native state."""
        # DESCEND is a native failsafe mode, not confirmation of NAV_LAND.
        # A previously accepted command does not confirm the current mode.
        descend = snapshot.get('px4_descend_active') is True
        if (not descend and (snapshot.get('px4_landing_active') is True
                or snapshot.get('land_command_accepted') is True)):
            self.reason = self.landing_reason
            return ''
        if self.land_command_attempts >= self.command_retry_limit:
            self.reason = self.landing_reason + (
                '_native_descend_requires_operator' if descend
                else '_land_command_unconfirmed')
            return ''
        if (self.last_land_command_wall is not None
                and wall_now - self.last_land_command_wall < self.command_retry_wall_s):
            return ''
        self.land_command_attempts += 1
        self.last_land_command_wall = wall_now
        return 'land'

    def _control_output(self, setpoint_kind='hold', command=''):
        return ControlOutput(self.phase, publish_offboard=True,
                             setpoint_kind=setpoint_kind, command=command,
                             reason=self.reason)

    def _retry_due(self, wall_now):
        if self.last_command_wall is None:
            return True
        return wall_now - self.last_command_wall >= self.command_retry_wall_s

    def _request_command(self, name, wall_now):
        if not self._retry_due(wall_now):
            return ''
        if self.command_attempts >= self.command_retry_limit:
            self.phase = self.LOCKED
            self.reason = name + '_command_timeout'
            return ''
        self.command_attempts += 1
        self.last_command_wall = wall_now
        return name

    def _reset_command_retry(self):
        self.command_attempts = 0
        self.last_command_wall = None

    def step(self, snapshot, wall_now):
        wall_now = float(wall_now)
        if self.phase in (self.DISABLED, self.LANDED, self.LOCKED):
            return ControlOutput(self.phase, reason=self.reason)

        if self.phase != self.LANDING:
            require_preflight = self.phase not in (self.PRESTREAM,
                                                   self.REQUEST_OFFBOARD)
            reason = readiness_failure(snapshot, self.profile, self.frame_contract,
                                       require_preflight=require_preflight)
            if reason:
                if snapshot.get('armed') or self.phase in (self.TAKEOFF, self.ACTIVE):
                    return self._begin_landing(reason, snapshot, wall_now)
                self.phase = self.DISABLED
                self.reason = reason
                return ControlOutput(self.phase, reason=reason)

        if self.phase == self.PRESTREAM:
            if wall_now - self.started_wall >= self.prestream_wall_s:
                self.phase = self.REQUEST_OFFBOARD
                self.reason = 'requesting_offboard'
                self._reset_command_retry()
                command = self._request_command('offboard', wall_now)
                return self._control_output(command=command)
            return self._control_output()

        if self.phase == self.REQUEST_OFFBOARD:
            if snapshot.get('nav_offboard') is True:
                if snapshot.get('preflight_passed') is not True:
                    deadline_s = (self.prestream_wall_s
                                  + self.command_retry_wall_s * self.command_retry_limit)
                    if wall_now - self.started_wall >= deadline_s:
                        self.phase = self.LOCKED
                        self.reason = 'offboard_preflight_timeout'
                        return ControlOutput(self.phase, reason=self.reason)
                    self.reason = 'waiting_for_px4_preflight'
                    return self._control_output()
                self.phase = self.REQUEST_ARM
                self.reason = 'requesting_arm'
                self._reset_command_retry()
                if snapshot.get('armed') is True:
                    self.phase = self.TAKEOFF
                    self.reason = 'takeoff_setpoint_active'
                    return self._control_output('takeoff')
                return self._control_output(command=self._request_command('arm', wall_now))
            command = self._request_command('offboard', wall_now)
            if self.phase == self.LOCKED:
                return ControlOutput(self.phase, reason=self.reason)
            return self._control_output(command=command)

        if self.phase == self.REQUEST_ARM:
            if snapshot.get('nav_offboard') is not True:
                return self._begin_landing(
                    'offboard_mode_lost_before_arm', snapshot, wall_now)
            if snapshot.get('armed') is True:
                self.phase = self.TAKEOFF
                self.reason = 'takeoff_setpoint_active'
                self._reset_command_retry()
                return self._control_output('takeoff')
            command = self._request_command('arm', wall_now)
            if self.phase == self.LOCKED:
                return ControlOutput(self.phase, reason=self.reason)
            return self._control_output(command=command)

        if self.phase == self.TAKEOFF:
            if snapshot.get('trajectory_fault') is True:
                return self._begin_landing(
                    snapshot.get('trajectory_reason') or 'trajectory_invalid',
                    snapshot, wall_now)
            if snapshot.get('nav_offboard') is not True or snapshot.get('armed') is not True:
                return self._begin_landing(
                    'offboard_or_armed_state_lost', snapshot, wall_now)
            position = tuple(float(v) for v in snapshot.get('position_ned', ()))
            velocity = tuple(float(v) for v in snapshot.get('velocity_ned', ()))
            if len(position) != 3 or len(velocity) != 3 or not all(
                    math.isfinite(v) for v in (*position, *velocity)):
                return self._begin_landing(
                    'invalid_takeoff_feedback', snapshot, wall_now)
            distance = math.sqrt(sum((a - b) ** 2
                                     for a, b in zip(position, self.takeoff_target)))
            speed = math.sqrt(sum(v * v for v in velocity))
            if (distance <= self.position_tolerance_m
                    and speed <= self.velocity_tolerance_m_s):
                if self.takeoff_dwell_since is None:
                    self.takeoff_dwell_since = wall_now
                elif wall_now - self.takeoff_dwell_since >= self.takeoff_dwell_wall_s:
                    self.phase = self.ACTIVE
                    self.reason = 'takeoff_complete_waiting_for_trajectory'
                    if snapshot.get('trajectory_fault') is True:
                        return self._begin_landing(
                            snapshot.get('trajectory_reason') or 'trajectory_invalid',
                            snapshot, wall_now)
                    if snapshot.get('trajectory_ready') is True:
                        self.active_trajectory_seen = True
                        return self._control_output('trajectory')
                    return self._control_output('hold')
            else:
                self.takeoff_dwell_since = None
            return self._control_output('takeoff')

        if self.phase == self.ACTIVE:
            if snapshot.get('nav_offboard') is not True or snapshot.get('armed') is not True:
                return self._begin_landing(
                    'offboard_or_armed_state_lost', snapshot, wall_now)
            if snapshot.get('trajectory_fault') is True:
                return self._begin_landing(
                    snapshot.get('trajectory_reason') or 'trajectory_invalid',
                    snapshot, wall_now)
            if snapshot.get('trajectory_ready') is True:
                self.active_trajectory_seen = True
                return self._control_output('trajectory')
            if self.active_trajectory_seen:
                return self._begin_landing('active_trajectory_lost', snapshot, wall_now)
            return self._control_output('hold')

        if self.phase == self.LANDING:
            if snapshot.get('landed') is True and snapshot.get('armed') is False:
                self.phase = self.LANDED
                self.reason = 'landed_and_disarmed'
                return ControlOutput(self.phase, reason=self.reason)
            command = self._landing_command(snapshot, wall_now)
            return ControlOutput(self.phase, command=command, reason=self.reason)

        return ControlOutput(self.phase, reason=self.reason)
