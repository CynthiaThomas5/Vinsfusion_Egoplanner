"""ROS action adapter for the epoch-aware navigation task core."""

import copy
import json
import math
from pathlib import Path
import signal
import threading
import time
import uuid

from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
import rclpy
from rclpy.action import ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.clock import Clock as RclpyClock, ClockType, JumpThreshold
from rclpy.duration import Duration
from rclpy.executors import ExternalShutdownException, MultiThreadedExecutor
from rclpy._rclpy_pybind11 import RCLError
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rclpy.signals import SignalHandlerOptions
from uav_interfaces.action import NavigateToPose
from uav_interfaces.msg import LocalizationStatus, NavigationCommand, TrajectoryCancel

from .task_state import NavigationGoal, Outcome, TaskEvent, TaskSupervisor


def yaw_from_quaternion(q):
    norm = math.sqrt(q.x*q.x + q.y*q.y + q.z*q.z + q.w*q.w)
    if not math.isfinite(norm) or norm < 1e-9:
        raise ValueError('target quaternion must be finite and nonzero')
    x, y, z, w = q.x/norm, q.y/norm, q.z/norm, q.w/norm
    sin_yaw = 2.0 * (w*z + x*y)
    cos_yaw = 1.0 - 2.0 * (y*y + z*z)
    return math.atan2(sin_yaw, cos_yaw)


def yaw_from_odometry(q):
    return yaw_from_quaternion(q)


def epoch_from_frame(frame_id):
    if not frame_id.startswith('odom_'):
        return ''
    epoch = frame_id[len('odom_'):]
    if len(epoch) != 32 or any(c not in '0123456789abcdef' for c in epoch):
        return ''
    return epoch


class NavigationNode(Node):
    def __init__(self, **node_kwargs):
        super().__init__('uav_navigation', **node_kwargs)
        self.declare_parameter('project_root', '')
        project_root = self.get_parameter('project_root').get_parameter_value().string_value
        if not project_root:
            raise RuntimeError('project_root is required to read the canonical task supervisor config')
        config_path = Path(project_root) / 'config/components/navigation/task_supervisor.json'
        self.config = json.loads(config_path.read_text())
        if self.config.get('schema') != 1:
            raise RuntimeError(f'unsupported navigation supervisor config schema: {config_path}')
        self.max_localization_age_s = float(self.config['max_localization_receipt_age_s'])
        self.max_odometry_age_s = float(self.config['max_odometry_receipt_age_s'])
        if min(self.max_localization_age_s, self.max_odometry_age_s) <= 0:
            raise RuntimeError('navigation freshness guards must be positive')

        self.core = TaskSupervisor()
        self._lock = threading.RLock()
        self._action_callback_condition = threading.Condition(self._lock)
        self._executing_goal_ids = set()
        self._stopping = False
        self._goal_epochs = {}
        self._terminal_events = {}
        self._latest_pose = None
        self._latest_pose_epoch = ''
        self._latest_pose_received = None
        self._last_localization_received = None
        self._last_timer_callback = None
        self._last_status_epoch = ''
        self._last_status_valid = False
        self._last_status_reason = 'waiting_for_localization'
        self._callbacks = ReentrantCallbackGroup()

        status_qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
        )
        self._status_sub = self.create_subscription(
            LocalizationStatus, self.config['localization_status_topic'],
            self._on_localization, status_qos, callback_group=self._callbacks)
        self._odom_sub = self.create_subscription(
            Odometry, self.config['odometry_topic'], self._on_odometry, 10,
            callback_group=self._callbacks)
        self._clock_jump_handle = self.get_clock().create_jump_callback(
            JumpThreshold(min_forward=None, min_backward=Duration(nanoseconds=-1),
                          on_clock_change=False),
            post_callback=self._on_clock_jump)
        self._ego_goal_pub = self.create_publisher(
            NavigationCommand, self.config['ego_goal_topic'], 10)
        self._trajectory_cancel_pub = self.create_publisher(
            TrajectoryCancel, self.config['trajectory_cancel_topic'], 10)
        self._action_server = ActionServer(
            self,
            NavigateToPose,
            self.config['navigation_goal_action'],
            execute_callback=self._execute_goal,
            goal_callback=self._goal_request,
            cancel_callback=self._cancel_request,
            callback_group=self._callbacks,
        )
        self._timer = self.create_timer(
            0.05, self._on_timer, callback_group=self._callbacks,
            clock=RclpyClock(clock_type=ClockType.STEADY_TIME))

    def _goal_request(self, request):
        now = time.monotonic()

        def reject(reason):
            self.get_logger().warning(f'navigation goal rejected: {reason}')
            return GoalResponse.REJECT

        rejection_reason = None
        try:
            with self._lock:
                expected_frame = f'odom_{self.core.epoch}' if self.core.epoch else ''
                if self._stopping:
                    rejection_reason = 'navigation node is stopping'
                elif not self.core.localization_ready or not expected_frame:
                    rejection_reason = 'localization is not ready'
                elif self._last_status_epoch != self.core.epoch:
                    rejection_reason = 'localization status epoch does not match current epoch'
                elif not self._last_status_valid:
                    rejection_reason = f'localization status is invalid: {self._last_status_reason}'
                elif self._last_localization_received is None:
                    rejection_reason = 'no localization status has been received'
                elif now - self._last_localization_received > self.max_localization_age_s:
                    localization_age = now - self._last_localization_received
                    rejection_reason = (
                        f'localization status is stale ({localization_age:.3f}s > '
                        f'{self.max_localization_age_s:.3f}s)')
                elif self._latest_pose is None:
                    rejection_reason = 'no optimized odometry has been received'
                elif self._latest_pose_epoch != self.core.epoch:
                    rejection_reason = 'optimized odometry epoch does not match current epoch'
                elif self._latest_pose_received is None:
                    rejection_reason = 'optimized odometry receipt time is unavailable'
                elif now - self._latest_pose_received > self.max_odometry_age_s:
                    odometry_age = now - self._latest_pose_received
                    rejection_reason = (
                        f'optimized odometry is stale ({odometry_age:.3f}s > '
                        f'{self.max_odometry_age_s:.3f}s)')
                elif self._ego_goal_pub.get_subscription_count() < 1:
                    rejection_reason = 'EGO goal subscriber is unavailable'
                elif self._trajectory_cancel_pub.get_subscription_count() < 1:
                    rejection_reason = 'trajectory cancellation subscriber is unavailable'
                elif request.target.header.frame_id != expected_frame:
                    rejection_reason = (
                        f'target frame {request.target.header.frame_id!r} does not match '
                        f'current frame {expected_frame!r}')
            if rejection_reason is not None:
                return reject(rejection_reason)
            pose = request.target.pose
            NavigationGoal(
                'validation', expected_frame[len('odom_'):],
                (pose.position.x, pose.position.y, pose.position.z),
                yaw_from_quaternion(pose.orientation),
                request.position_tolerance_m, request.yaw_tolerance_rad,
                request.dwell_s, request.timeout_s,
            )
        except (ValueError, TypeError, OverflowError) as exc:
            return reject(f'invalid goal: {exc}')
        return GoalResponse.ACCEPT

    def _cancel_request(self, _goal_handle):
        return CancelResponse.ACCEPT

    @staticmethod
    def _action_goal_id(goal_handle):
        return uuid.UUID(bytes=bytes(goal_handle.goal_id.uuid)).hex

    def _execute_goal(self, goal_handle):
        goal_id = self._action_goal_id(goal_handle)
        with self._action_callback_condition:
            self._executing_goal_ids.add(goal_id)
        try:
            return self._execute_goal_impl(goal_handle, goal_id)
        finally:
            with self._action_callback_condition:
                self._executing_goal_ids.discard(goal_id)
                self._action_callback_condition.notify_all()

    def _execute_goal_impl(self, goal_handle, goal_id):
        request = goal_handle.request
        pose = request.target.pose
        with self._lock:
            now = time.monotonic()
            epoch = epoch_from_frame(request.target.header.frame_id)
            context_valid = bool(
                not self._stopping and epoch and epoch == self.core.epoch
                and self.core.localization_ready
                and self._last_status_epoch == epoch and self._last_status_valid
                and self._last_localization_received is not None
                and now - self._last_localization_received <= self.max_localization_age_s
                and self._latest_pose is not None and self._latest_pose_epoch == epoch
                and self._latest_pose_received is not None
                and now - self._latest_pose_received <= self.max_odometry_age_s
                and self._ego_goal_pub.get_subscription_count() > 0
                and self._trajectory_cancel_pub.get_subscription_count() > 0)
            if not context_valid:
                events = (TaskEvent(Outcome.REJECTED, goal_id,
                                    'goal_context_changed_or_stale'),)
            else:
                try:
                    goal = NavigationGoal(
                        goal_id, epoch,
                        (pose.position.x, pose.position.y, pose.position.z),
                        yaw_from_quaternion(pose.orientation),
                        request.position_tolerance_m, request.yaw_tolerance_rad,
                        request.dwell_s, request.timeout_s,
                    )
                    events = self.core.submit(goal, now)
                except (ValueError, TypeError, OverflowError) as exc:
                    events = (TaskEvent(Outcome.REJECTED, goal_id, str(exc)),)
            self._goal_epochs[goal_id] = epoch
            self._process_events(events)
            accepted = any(event.outcome == Outcome.ACCEPTED for event in events)
            if accepted:
                command = NavigationCommand()
                command.goal_id = goal_id
                command.epoch = epoch
                command.target = copy.deepcopy(request.target)
                command.target.header.stamp = self.get_clock().now().to_msg()
                self._ego_goal_pub.publish(command)

        if accepted:
            self.get_logger().info(f'accepted goal {goal_id} in epoch {epoch}')

        if not accepted:
            terminal = self._pop_terminal(goal_id)
            result = self._result(terminal or TaskEvent(Outcome.REJECTED, goal_id,
                                                        'localization_not_ready'))
            goal_handle.abort()
            self._forget_goal(goal_id)
            return result

        while rclpy.ok() and not self._stopping:
            terminal = self._pop_terminal(goal_id)
            if terminal is not None:
                result = self._result(terminal)
                if terminal.outcome == Outcome.SUCCEEDED:
                    goal_handle.succeed()
                elif terminal.outcome == Outcome.CANCELED:
                    goal_handle.canceled()
                else:
                    goal_handle.abort()
                self._forget_goal(goal_id)
                return result

            if goal_handle.is_cancel_requested:
                with self._lock:
                    events = self.core.cancel(goal_id, 'caller_cancel')
                    self._process_events(events)
                terminal = self._pop_terminal(goal_id) or TaskEvent(
                    Outcome.CANCELED, goal_id, 'caller_cancel', True)
                result = self._result(terminal)
                if terminal.outcome == Outcome.CANCELED:
                    goal_handle.canceled()
                elif terminal.outcome == Outcome.SUCCEEDED:
                    goal_handle.succeed()
                else:
                    goal_handle.abort()
                self._forget_goal(goal_id)
                return result

            feedback = self._feedback(goal_id, goal)
            if feedback is not None:
                goal_handle.publish_feedback(feedback)
            time.sleep(0.05)

        with self._lock:
            event = self.core.cancel(goal_id, 'navigation_node_shutdown')
            self._process_events(event)
        terminal = self._pop_terminal(goal_id) or TaskEvent(
            Outcome.ABORTED, goal_id, 'navigation_node_shutdown', True)
        result = self._result(terminal)
        if terminal.outcome == Outcome.CANCELED:
            goal_handle.canceled()
        elif terminal.outcome == Outcome.SUCCEEDED:
            goal_handle.succeed()
        else:
            goal_handle.abort()
        self._forget_goal(goal_id)
        return result

    def request_shutdown(self):
        """Stop active navigation before the ROS context and action server close."""
        with self._lock:
            if self._stopping:
                return
            self._stopping = True
            if not rclpy.ok() or self.core.active_goal is None:
                return
            events = self.core.abort(
                self.core.active_goal.goal_id, 'navigation_node_shutdown')
            self._process_events(events)

    def wait_for_action_callbacks(self, timeout_sec=5.0):
        deadline = time.monotonic() + timeout_sec
        with self._action_callback_condition:
            while self._executing_goal_ids:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._action_callback_condition.wait(remaining)
        return True

    def _on_localization(self, msg):
        now = time.monotonic()
        status_warning = None
        with self._lock:
            if self._last_localization_received is not None:
                status_gap = now - self._last_localization_received
                if status_gap > self.max_localization_age_s:
                    status_warning = (
                        f'localization status callback resumed after {status_gap:.3f}s '
                        f'(guard {self.max_localization_age_s:.3f}s); '
                        f'new_status_valid={bool(msg.valid and msg.state == LocalizationStatus.TRACKING)} '
                        f'new_status_reason={msg.reason!r}')
            self._last_localization_received = now
            self._last_status_epoch = msg.epoch
            self._last_status_valid = bool(msg.valid and msg.state == LocalizationStatus.TRACKING)
            self._last_status_reason = msg.reason
            events = self.core.update_localization(
                msg.epoch, msg.state == LocalizationStatus.TRACKING,
                bool(msg.valid), msg.reason)
            self._process_events(events)
        if status_warning is not None:
            self.get_logger().warning(status_warning)

    def _on_odometry(self, msg):
        now = time.monotonic()
        epoch = epoch_from_frame(msg.header.frame_id)
        if not epoch:
            with self._lock:
                events = self.core.update_pose('', (0.0, 0.0, 0.0), 0.0,
                                               now, fresh=False)
                self._process_events(events)
            return
        pose = copy.deepcopy(msg.pose.pose)
        try:
            yaw = yaw_from_odometry(pose.orientation)
        except ValueError:
            yaw = float('nan')
        position = (pose.position.x, pose.position.y, pose.position.z)
        odometry_warning = None
        with self._lock:
            if self._latest_pose_received is not None:
                odometry_gap = now - self._latest_pose_received
                if odometry_gap > self.max_odometry_age_s:
                    odometry_warning = (
                        f'optimized odometry callback resumed after {odometry_gap:.3f}s '
                        f'(guard {self.max_odometry_age_s:.3f}s); '
                        f'new_epoch={epoch!r}')
            self._latest_pose = pose
            self._latest_pose_epoch = epoch
            self._latest_pose_received = now
            events = self.core.update_pose(epoch, position, yaw, now, fresh=True)
            self._process_events(events)
        if odometry_warning is not None:
            self.get_logger().warning(odometry_warning)

    def _on_clock_jump(self, time_jump):
        if time_jump.delta.nanoseconds >= 0:
            return
        stamp_ns = self.get_clock().now().nanoseconds
        previous_stamp_ns = stamp_ns - time_jump.delta.nanoseconds
        with self._lock:
            self.core.last_clock_ns = previous_stamp_ns
            events = self.core.update_clock(stamp_ns)
            self._process_events(events)
        self.get_logger().warning(
            f'ROS clock regression: {previous_stamp_ns} -> {stamp_ns} ns')

    def _on_timer(self):
        now = time.monotonic()
        warnings = []
        with self._lock:
            if self._last_timer_callback is not None:
                timer_gap = now - self._last_timer_callback
                if timer_gap > self.max_localization_age_s:
                    warnings.append(
                        f'navigation timer callback resumed after {timer_gap:.3f}s '
                        f'(freshness guard {self.max_localization_age_s:.3f}s)')
            self._last_timer_callback = now
            status_age = (now - self._last_localization_received
                          if self._last_localization_received is not None else None)
            if (status_age is not None and status_age > self.max_localization_age_s
                    and self.core.localization_ready):
                odometry_age = (now - self._latest_pose_received
                                if self._latest_pose_received is not None else None)
                warnings.append(
                    f'localization status became stale: receipt_age={status_age:.3f}s '
                    f'(guard {self.max_localization_age_s:.3f}s), '
                    f'last_status_valid={self._last_status_valid}, '
                    f'last_status_reason={self._last_status_reason!r}, '
                    f'epoch={self.core.epoch!r}, '
                    f'optimized_odometry_receipt_age={odometry_age}')
                events = self.core.update_localization(
                    self.core.epoch or '', False, False, 'status_stale')
                self._process_events(events)
            if (self.core.active_goal is not None and self._latest_pose_received is not None
                    and now - self._latest_pose_received > self.max_odometry_age_s):
                events = self.core.update_pose(
                    self._latest_pose_epoch, (0.0, 0.0, 0.0), 0.0, now, fresh=False)
                self._process_events(events)
            events = self.core.tick(now)
            self._process_events(events)
        for warning in warnings:
            self.get_logger().warning(warning)

    def _process_events(self, events):
        for event in events:
            if event.outcome in (Outcome.CANCELED, Outcome.ABORTED) and event.clear_trajectory:
                cancel = TrajectoryCancel()
                cancel.goal_id = event.goal_id
                cancel.epoch = self._goal_epochs.get(event.goal_id, self.core.epoch or '')
                cancel.mode = TrajectoryCancel.MODE_ABORT
                cancel.reason = event.reason
                self._trajectory_cancel_pub.publish(cancel)
            if event.outcome in (Outcome.SUCCEEDED, Outcome.CANCELED,
                                 Outcome.ABORTED, Outcome.REJECTED):
                self._terminal_events.setdefault(event.goal_id, []).append(event)

    def _pop_terminal(self, goal_id):
        with self._lock:
            events = self._terminal_events.get(goal_id)
            if not events:
                return None
            event = events.pop(0)
            if not events:
                self._terminal_events.pop(goal_id, None)
            return event

    def _feedback(self, goal_id, goal):
        with self._lock:
            if (self._latest_pose is None or self._latest_pose_epoch != goal.epoch
                    or self._latest_pose_received is None
                    or time.monotonic() - self._latest_pose_received > self.max_odometry_age_s):
                return None
            pose = self._latest_pose
            current_yaw = yaw_from_odometry(pose.orientation)
            distance = math.sqrt(
                (pose.position.x-goal.position[0])**2
                + (pose.position.y-goal.position[1])**2
                + (pose.position.z-goal.position[2])**2)
            yaw_error = abs(math.atan2(math.sin(current_yaw-goal.yaw),
                                      math.cos(current_yaw-goal.yaw)))
            feedback = NavigateToPose.Feedback()
            feedback.current_pose.header.frame_id = f'odom_{goal.epoch}'
            feedback.current_pose.header.stamp = self.get_clock().now().to_msg()
            feedback.current_pose.pose = copy.deepcopy(pose)
            feedback.position_error_m = distance
            feedback.yaw_error_rad = yaw_error
            return feedback

    def _result(self, event):
        result = NavigateToPose.Result()
        result.success = event.outcome == Outcome.SUCCEEDED
        result.outcome = event.outcome.value
        result.reason = event.reason
        with self._lock:
            expected_epoch = self._goal_epochs.get(event.goal_id, '')
            if (self._latest_pose is not None
                    and self._latest_pose_epoch == expected_epoch):
                result.final_pose.header.frame_id = f'odom_{self._latest_pose_epoch}'
                result.final_pose.header.stamp = self.get_clock().now().to_msg()
                result.final_pose.pose = copy.deepcopy(self._latest_pose)
        return result

    def _forget_goal(self, goal_id):
        with self._lock:
            self._goal_epochs.pop(goal_id, None)
            self._terminal_events.pop(goal_id, None)


def main(args=None):
    shutdown_requested = threading.Event()

    def request_shutdown(_signum, _frame):
        shutdown_requested.set()

    signal.signal(signal.SIGINT, request_shutdown)
    rclpy.init(args=args, signal_handler_options=SignalHandlerOptions.NO)
    node = NavigationNode()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)

    def finish_shutdown():
        shutdown_requested.wait()
        node.request_shutdown()
        if not node.wait_for_action_callbacks(timeout_sec=5.0):
            node.get_logger().error('action callback did not finish within 5 seconds during shutdown')
        # Keep the executor and action server alive briefly so the aborted result can be served.
        time.sleep(1.0)
        if not executor.shutdown(timeout_sec=5.0):
            node.get_logger().error('executor did not stop within 5 seconds')

    shutdown_thread = threading.Thread(
        target=finish_shutdown, name='navigation_shutdown', daemon=True)
    shutdown_thread.start()
    try:
        executor.spin()
    except ExternalShutdownException:
        shutdown_requested.set()
    except KeyboardInterrupt:
        shutdown_requested.set()
    except RCLError:
        if rclpy.ok():
            raise
    finally:
        shutdown_requested.set()
        shutdown_thread.join(timeout=12.0)
        if shutdown_thread.is_alive():
            node.request_shutdown()
            executor.shutdown(timeout_sec=5.0)
            shutdown_thread.join(timeout=1.0)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
