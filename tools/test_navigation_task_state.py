#!/usr/bin/env python3
"""Unit checks for epoch-bound goal, arrival, timeout, and invalidation policy."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/own/uav_navigation'))
from uav_navigation.task_state import NavigationGoal, Outcome, TaskState, TaskSupervisor


def goal(goal_id='g1', epoch='epoch-a', timeout=10.0, dwell=1.0):
    return NavigationGoal(goal_id, epoch, (1.0, 2.0, 3.0), 0.5,
                          0.2, 0.1, dwell, timeout)


class TaskStateTests(unittest.TestCase):
    def ready(self, supervisor=None, epoch='epoch-a'):
        supervisor = supervisor or TaskSupervisor()
        self.assertEqual(supervisor.update_localization(epoch, True, True, 'tracking'), ())
        self.assertEqual(supervisor.state, TaskState.READY)
        return supervisor

    def test_rejects_goal_until_epoch_exists_but_ignores_localization_health_state(self):
        supervisor = TaskSupervisor()
        rejected = supervisor.submit(goal(), 1.0)[0]
        self.assertEqual((rejected.outcome, rejected.reason),
                         (Outcome.REJECTED, 'localization_not_ready'))
        supervisor.update_localization('epoch-a', False, False, 'degraded')
        self.assertEqual(supervisor.state, TaskState.READY)
        accepted = supervisor.submit(goal(), 2.0)[0]
        self.assertEqual(accepted.outcome, Outcome.ACCEPTED)
        rejected = supervisor.submit(goal(epoch='epoch-b'), 2.0)[0]
        self.assertEqual(rejected.reason, 'goal_epoch_mismatch')

    def test_epoch_change_aborts_goal_and_clears_trajectory(self):
        supervisor = self.ready()
        supervisor.submit(goal(), 1.0)
        supervisor.attach_trajectory('g1', 'epoch-a', 7)
        events = supervisor.update_localization('epoch-b', False, False, 'initializing')
        self.assertEqual([(e.outcome, e.reason, e.clear_trajectory) for e in events],
                         [(Outcome.ABORTED, 'epoch_changed', True)])
        self.assertIsNone(supervisor.active_goal)
        self.assertEqual(supervisor.state, TaskState.READY)

    def test_invalid_localization_state_is_observational_for_active_goal(self):
        supervisor = self.ready()
        supervisor.submit(goal(), 1.0)
        events = supervisor.update_localization('epoch-a', False, False, 'clock_regression')
        self.assertEqual(events, ())
        self.assertEqual(supervisor.active_goal.goal_id, 'g1')
        self.assertEqual(supervisor.state, TaskState.ACTIVE)

    def test_clock_backstep_locks_goal_admission_until_new_epoch(self):
        supervisor = self.ready()
        supervisor.update_clock(100)
        supervisor.submit(goal(), 1.0)
        supervisor.update_clock(99)
        self.assertIsNone(supervisor.active_goal)
        self.assertEqual(supervisor.state, TaskState.WAIT_LOCALIZATION)
        rejected = supervisor.submit(goal('g2'), 2.0)[0]
        self.assertEqual(rejected.reason, 'localization_not_ready')
        supervisor.update_localization('epoch-b', True, True, 'tracking')
        self.assertEqual(supervisor.submit(goal('g3', 'epoch-b'), 3.0)[0].outcome,
                         Outcome.ACCEPTED)

    def test_cancel_and_replacement_clear_the_previous_trajectory_first(self):
        supervisor = self.ready()
        supervisor.submit(goal(), 1.0)
        supervisor.attach_trajectory('g1', 'epoch-a', 4)
        events = supervisor.submit(goal('g2'), 2.0)
        self.assertEqual([(e.outcome, e.goal_id, e.reason, e.clear_trajectory) for e in events], [
            (Outcome.ABORTED, 'g1', 'goal_replaced', True),
            (Outcome.ACCEPTED, 'g2', 'accepted', False),
        ])
        canceled = supervisor.cancel('g2', 'caller_cancel')
        self.assertEqual((canceled[0].outcome, canceled[0].clear_trajectory),
                         (Outcome.CANCELED, True))

    def test_shutdown_aborts_and_clears_the_active_trajectory(self):
        supervisor = self.ready()
        supervisor.submit(goal(), 1.0)
        supervisor.attach_trajectory('g1', 'epoch-a', 9)
        stopped = supervisor.abort('g1', 'navigation_node_shutdown')[0]
        self.assertEqual(
            (stopped.outcome, stopped.reason, stopped.clear_trajectory),
            (Outcome.ABORTED, 'navigation_node_shutdown', True))
        self.assertIsNone(supervisor.active_goal)

    def test_arrival_requires_position_yaw_and_continuous_dwell(self):
        supervisor = self.ready()
        supervisor.submit(goal(), 1.0)
        self.assertEqual(supervisor.update_pose('epoch-a', (1.0, 2.0, 3.0), 0.8, 2.0), ())
        self.assertEqual(supervisor.update_pose('epoch-a', (1.0, 2.0, 3.0), 0.5, 2.5), ())
        self.assertEqual(supervisor.update_pose('epoch-a', (1.0, 2.0, 3.0), 0.5, 3.49), ())
        events = supervisor.update_pose('epoch-a', (1.0, 2.0, 3.0), 0.5, 3.5)
        self.assertEqual((events[0].outcome, events[0].reason),
                         (Outcome.SUCCEEDED, 'position_yaw_tolerance_held'))

    def test_yaw_tolerance_wraps_across_pi_boundary(self):
        supervisor = self.ready()
        wrapped_goal = NavigationGoal('wrapped', 'epoch-a', (0.0, 0.0, 0.0),
                                      -3.12, 0.1, 0.1, 0.0, 2.0)
        supervisor.submit(wrapped_goal, 1.0)
        events = supervisor.update_pose('epoch-a', (0.0, 0.0, 0.0), 3.12, 1.1)
        self.assertEqual(events[0].outcome, Outcome.SUCCEEDED)

    def test_timeout_and_stale_pose_abort_and_clear(self):
        supervisor = self.ready()
        supervisor.submit(goal(timeout=2.0), 1.0)
        self.assertEqual(supervisor.tick(2.99), ())
        timed_out = supervisor.tick(3.0)[0]
        self.assertEqual((timed_out.outcome, timed_out.reason, timed_out.clear_trajectory),
                         (Outcome.ABORTED, 'goal_timeout', True))
        supervisor.submit(goal('g2'), 4.0)
        stale = supervisor.update_pose('epoch-a', (1.0, 2.0, 3.0), 0.5, 4.1, fresh=False)[0]
        self.assertEqual((stale.reason, stale.clear_trajectory), ('pose_stale', True))

    def test_rejects_old_trajectory_metadata(self):
        supervisor = self.ready()
        supervisor.submit(goal(), 1.0)
        event = supervisor.attach_trajectory('old-goal', 'epoch-old', 1)[0]
        self.assertEqual((event.outcome, event.reason, event.clear_trajectory),
                         (Outcome.REJECTED, 'stale_trajectory', True))


if __name__ == '__main__':
    unittest.main()
