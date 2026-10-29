"""Small, runtime-neutral state core for epoch-bound navigation tasks."""

from dataclasses import dataclass
from enum import Enum
import math
from typing import Optional, Tuple


class TaskState(str, Enum):
    WAIT_LOCALIZATION = 'wait_localization'
    READY = 'ready'
    ACTIVE = 'active'


class Outcome(str, Enum):
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'
    CANCELED = 'canceled'
    ABORTED = 'aborted'
    SUCCEEDED = 'succeeded'


@dataclass(frozen=True)
class NavigationGoal:
    goal_id: str
    epoch: str
    position: Tuple[float, float, float]
    yaw: float
    position_tolerance_m: float
    yaw_tolerance_rad: float
    dwell_s: float
    timeout_s: float

    def __post_init__(self):
        if not self.goal_id or not self.epoch:
            raise ValueError('goal_id and epoch are required')
        if len(self.position) != 3 or not all(math.isfinite(v) for v in self.position):
            raise ValueError('position must contain three finite values')
        if not math.isfinite(self.yaw):
            raise ValueError('yaw must be finite')
        if not math.isfinite(self.position_tolerance_m) or self.position_tolerance_m <= 0:
            raise ValueError('position tolerance must be finite and positive')
        if not math.isfinite(self.yaw_tolerance_rad) or not 0 < self.yaw_tolerance_rad <= math.pi:
            raise ValueError('yaw tolerance must be in (0, pi]')
        if not math.isfinite(self.dwell_s) or self.dwell_s < 0:
            raise ValueError('dwell time must be finite and nonnegative')
        if not math.isfinite(self.timeout_s) or self.timeout_s <= 0:
            raise ValueError('timeout must be finite and positive')


@dataclass(frozen=True)
class TaskEvent:
    outcome: Outcome
    goal_id: str
    reason: str
    clear_trajectory: bool = False


class TaskSupervisor:
    """Track one active goal and fail closed on epoch and clock faults.

    `now_s` values are caller-provided monotonic wall time. ROS clock stamps are
    tracked separately so a backwards jump can invalidate the current session.
    This class emits policy events; a ROS adapter must deliver them to EGO and
    the control bridge before the runtime can be considered integrated.
    """

    def __init__(self):
        self.epoch: Optional[str] = None
        self.localization_ready = False
        self.localization_reason = 'waiting_for_localization'
        self.clock_locked = False
        self.last_clock_ns: Optional[int] = None
        self.active_goal: Optional[NavigationGoal] = None
        self.active_trajectory_id: Optional[int] = None
        self.deadline_s: Optional[float] = None
        self.reached_since_s: Optional[float] = None

    @property
    def state(self) -> TaskState:
        if self.active_goal is not None:
            return TaskState.ACTIVE
        if self.localization_ready and not self.clock_locked:
            return TaskState.READY
        return TaskState.WAIT_LOCALIZATION

    def update_localization(self, epoch: str, tracking: bool, valid: bool,
                            reason: str) -> Tuple[TaskEvent, ...]:
        events = []
        first_epoch = bool(epoch and self.epoch is None)
        changed_epoch = bool(epoch and self.epoch and epoch != self.epoch)
        if changed_epoch:
            event = self._finish(Outcome.ABORTED, 'epoch_changed', clear=True)
            if event:
                events.append(event)
        if first_epoch or changed_epoch:
            self.clock_locked = False
            self.last_clock_ns = None
        if epoch:
            self.epoch = epoch
        self.localization_reason = reason or 'localization_unavailable'
        # TRACKING/valid are diagnostics; they do not gate goals. Keep the
        # VINS epoch and clock lock as session-integrity checks.
        self.localization_ready = bool(epoch and not self.clock_locked)
        if not self.localization_ready:
            event = self._finish(Outcome.ABORTED,
                                 'localization_' + self.localization_reason,
                                 clear=True)
            if event:
                events.append(event)
        return tuple(events)

    def update_clock(self, stamp_ns: int) -> Tuple[TaskEvent, ...]:
        if stamp_ns < 0:
            raise ValueError('clock stamp must be nonnegative')
        regressed = self.last_clock_ns is not None and stamp_ns < self.last_clock_ns
        self.last_clock_ns = stamp_ns
        if not regressed:
            return ()
        self.clock_locked = True
        self.localization_ready = False
        event = self._finish(Outcome.ABORTED, 'clock_regression', clear=True)
        return (event,) if event else ()

    def submit(self, goal: NavigationGoal, now_s: float) -> Tuple[TaskEvent, ...]:
        if not math.isfinite(now_s) or now_s < 0:
            raise ValueError('monotonic time must be finite and nonnegative')
        if not self.localization_ready or self.clock_locked:
            return (TaskEvent(Outcome.REJECTED, goal.goal_id,
                              'localization_not_ready', clear_trajectory=False),)
        if goal.epoch != self.epoch:
            return (TaskEvent(Outcome.REJECTED, goal.goal_id,
                              'goal_epoch_mismatch', clear_trajectory=False),)
        events = []
        if self.active_goal is not None:
            # This is a server-initiated terminal result, not an action cancel
            # request from the client. ROS actions require it to use ABORTED.
            replaced = self._finish(Outcome.ABORTED, 'goal_replaced', clear=True)
            if replaced:
                events.append(replaced)
        self.active_goal = goal
        self.active_trajectory_id = None
        self.deadline_s = now_s + goal.timeout_s
        self.reached_since_s = None
        events.append(TaskEvent(Outcome.ACCEPTED, goal.goal_id, 'accepted'))
        return tuple(events)

    def cancel(self, goal_id: str, reason: str = 'canceled') -> Tuple[TaskEvent, ...]:
        if self.active_goal is None:
            return ()
        if goal_id and goal_id != self.active_goal.goal_id:
            return (TaskEvent(Outcome.REJECTED, goal_id, 'goal_id_mismatch'),)
        event = self._finish(Outcome.CANCELED, reason, clear=True)
        return (event,) if event else ()

    def abort(self, goal_id: str, reason: str = 'aborted') -> Tuple[TaskEvent, ...]:
        if self.active_goal is None:
            return ()
        if goal_id and goal_id != self.active_goal.goal_id:
            return (TaskEvent(Outcome.REJECTED, goal_id, 'goal_id_mismatch'),)
        event = self._finish(Outcome.ABORTED, reason, clear=True)
        return (event,) if event else ()

    def attach_trajectory(self, goal_id: str, epoch: str,
                          trajectory_id: int) -> Tuple[TaskEvent, ...]:
        if (self.active_goal is None or goal_id != self.active_goal.goal_id
                or epoch != self.active_goal.epoch):
            return (TaskEvent(Outcome.REJECTED, goal_id, 'stale_trajectory', clear_trajectory=True),)
        if trajectory_id < 0:
            raise ValueError('trajectory id must be nonnegative')
        self.active_trajectory_id = trajectory_id
        return ()

    def update_pose(self, epoch: str, position: Tuple[float, float, float], yaw: float,
                    now_s: float, fresh: bool = True) -> Tuple[TaskEvent, ...]:
        if self.active_goal is None:
            return ()
        if not self.localization_ready or epoch != self.active_goal.epoch:
            event = self._finish(Outcome.ABORTED, 'pose_epoch_mismatch', clear=True)
            return (event,) if event else ()
        if not fresh:
            event = self._finish(Outcome.ABORTED, 'pose_stale', clear=True)
            return (event,) if event else ()
        if (len(position) != 3 or not all(math.isfinite(v) for v in position)
                or not math.isfinite(yaw) or not math.isfinite(now_s)):
            event = self._finish(Outcome.ABORTED, 'invalid_pose', clear=True)
            return (event,) if event else ()
        timeout_event = self.tick(now_s)
        if timeout_event:
            return timeout_event
        goal = self.active_goal
        distance = math.sqrt(sum((a-b)**2 for a, b in zip(position, goal.position)))
        yaw_error = abs(math.atan2(math.sin(yaw-goal.yaw), math.cos(yaw-goal.yaw)))
        if distance <= goal.position_tolerance_m and yaw_error <= goal.yaw_tolerance_rad:
            if self.reached_since_s is None:
                self.reached_since_s = now_s
            if now_s - self.reached_since_s >= goal.dwell_s:
                event = self._finish(Outcome.SUCCEEDED, 'position_yaw_tolerance_held')
                return (event,) if event else ()
        else:
            self.reached_since_s = None
        return ()

    def tick(self, now_s: float) -> Tuple[TaskEvent, ...]:
        if not math.isfinite(now_s) or now_s < 0:
            raise ValueError('monotonic time must be finite and nonnegative')
        if self.active_goal is None or self.deadline_s is None or now_s < self.deadline_s:
            return ()
        event = self._finish(Outcome.ABORTED, 'goal_timeout', clear=True)
        return (event,) if event else ()

    def _finish(self, outcome: Outcome, reason: str,
                clear: bool = False) -> Optional[TaskEvent]:
        if self.active_goal is None:
            return None
        goal_id = self.active_goal.goal_id
        event = TaskEvent(outcome, goal_id, reason, clear)
        self.active_goal = None
        self.active_trajectory_id = None
        self.deadline_s = None
        self.reached_since_s = None
        return event
