#!/usr/bin/env python3
"""Exercise the ROS action adapter with synthetic localization and EGO peers."""

import threading
import time
import uuid
import math
import tempfile
import json
from pathlib import Path

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.task import Future
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rosgraph_msgs.msg import Clock
from uav_interfaces.action import NavigateToPose
from uav_interfaces.msg import LocalizationStatus, MapStatus, NavigationCommand, TrajectoryCancel

from uav_navigation.node import NavigationNode, NavigationExecutor
from uav_interfaces.srv import QueryOccupancySphere


def wait_for(predicate, description, timeout_s=5.0):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise RuntimeError(f'timed out waiting for {description}')


def wait_future(future, description, timeout_s=5.0):
    wait_for(future.done, description, timeout_s)
    return future.result()


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--project-root', required=True)
    args = parser.parse_args()

    rclpy.init()
    # Preserve the historical known-free regression as an explicitly selected policy.
    test_root = tempfile.TemporaryDirectory(prefix='navigation-known-free-')
    fixture_root = Path(test_root.name)
    for relative in ['config/components/navigation/task_supervisor.json',
                     'config/components/mapping/ego_planner.json']:
        source = Path(args.project_root)/relative
        target = fixture_root/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        config = json.loads(source.read_text())
        if relative.endswith('task_supervisor.json'):
            config['collision_policy'] = 'known_free'
        target.write_text(json.dumps(config))
    root_parameter = rclpy.parameter.Parameter(
        'project_root', rclpy.parameter.Parameter.Type.STRING, str(fixture_root))
    simulated_time_parameter = rclpy.parameter.Parameter(
        'use_sim_time', rclpy.parameter.Parameter.Type.BOOL, True)
    navigation = NavigationNode(
        parameter_overrides=[root_parameter, simulated_time_parameter])
    peer = Node('navigation_adapter_probe')
    executor = NavigationExecutor()
    executor.add_node(navigation)
    executor.add_node(peer)

    epoch = uuid.uuid4().hex
    goals = []
    cancels = []
    status_qos = QoSProfile(
        depth=1,
        reliability=ReliabilityPolicy.RELIABLE,
        durability=DurabilityPolicy.TRANSIENT_LOCAL,
    )
    status_pub = peer.create_publisher(
        LocalizationStatus, '/localization/status', status_qos)
    fault_pub = peer.create_publisher(TrajectoryCancel, '/navigation/planner_fault', 10)
    map_pub = peer.create_publisher(MapStatus, '/mapping/status', status_qos)
    map_id = uuid.uuid4().hex
    query_mode = {'reason': 'free', 'delay': 0.0, 'transient_remaining': 0, 'requests': 0}

    def publish_map():
        msg = MapStatus()
        msg.epoch = epoch
        msg.map_id = map_id
        msg.reset_acknowledged = True
        msg.input_ready = True
        map_pub.publish(msg)

    map_timer = peer.create_timer(0.02, publish_map)

    async def query_target(request, response):
        # Synthetic service, isolated from SITL; never writes the production grid.
        reason, delay = query_mode['reason'], query_mode['delay']
        query_mode['requests'] += 1
        if query_mode['transient_remaining']:
            reason = 'no_fresh_fused_depth'
            query_mode['transient_remaining'] -= 1
        if delay:
            future = Future(executor=executor)
            threading.Timer(delay, lambda: future.set_result(True)).start()
            await future
        response.accepted = reason != 'no_fresh_fused_depth'
        response.free = reason == 'free'
        response.reason = reason
        response.epoch = request.expected_epoch
        response.map_id = request.expected_map_id
        response.header.frame_id = request.frame_id
        response.header.stamp = navigation.get_clock().now().to_msg()
        response.last_depth_source_stamp = response.header.stamp
        response.last_fusion_stamp = response.header.stamp
        response.center = request.center
        response.radius_m = request.radius_m
        response.free_count = 10
        if reason == 'wrong_identity':
            response.free = True
            response.reason = 'free'
            response.map_id = 'wrong'
        if reason == 'stale':
            response.free = True
            response.reason = 'free'
            response.last_fusion_stamp.sec -= 1
        return response

    query_server = peer.create_service(
        QueryOccupancySphere, '/mapping/query_occupancy_sphere', query_target)
    odom_pub = peer.create_publisher(Odometry, '/localization/optimized_imu_odom', 10)
    clock_pub = peer.create_publisher(Clock, '/clock', 10)
    peer.create_subscription(
        NavigationCommand, '/navigation/ego_goal', goals.append, 10)
    peer.create_subscription(
        TrajectoryCancel, '/navigation/trajectory_cancel', cancels.append, 10)
    action_client = ActionClient(peer, NavigateToPose, '/navigation/navigate_to_pose')

    spin_thread = threading.Thread(target=executor.spin, daemon=True)
    spin_thread.start()
    try:
        wait_for(lambda: action_client.wait_for_server(timeout_sec=0.0),
                 'navigation action server')
        wait_for(lambda: navigation._ego_goal_pub.get_subscription_count() == 1,
                 'fake EGO goal subscriber')
        wait_for(lambda: navigation._trajectory_cancel_pub.get_subscription_count() == 1,
                 'fake EGO cancellation subscriber')

        status = LocalizationStatus()
        status.epoch = epoch
        status.state = LocalizationStatus.DEGRADED
        status.valid = False
        status.reason = 'health_state_is_observational'
        odom = Odometry()
        odom.header.frame_id = f'odom_{epoch}'
        odom.pose.pose.orientation.w = 1.0
        clock = Clock()
        for tick in range(10):
            status_pub.publish(status)
            odom_pub.publish(odom)
            clock.clock.sec = tick
            clock_pub.publish(clock)
            time.sleep(0.02)
        wait_for(lambda: navigation.core.localization_ready
                 and navigation._latest_pose_epoch == epoch,
                 'initial navigation state before blocked-log check')

        wait_for(lambda: navigation._map_ready(time.monotonic())
                 and navigation._map_query.service_is_ready(), 'synthetic map and query service')

        def make_goal(x, frame_epoch=None, *, y=0.0, z=0.0, yaw=0.0,
                      timeout_s=5.0):
            request = NavigateToPose.Goal()
            request.target = PoseStamped()
            request.target.header.frame_id = f'odom_{frame_epoch or epoch}'
            request.target.pose.position.x = x
            request.target.pose.position.y = y
            request.target.pose.position.z = z
            request.target.pose.orientation.z = math.sin(yaw / 2.0)
            request.target.pose.orientation.w = math.cos(yaw / 2.0)
            request.position_tolerance_m = 0.1
            request.yaw_tolerance_rad = 0.1
            request.dwell_s = 0.0
            request.timeout_s = timeout_s
            return request

        def set_odometry(x=0.0, y=0.0, z=0.0, yaw=0.0, frame_epoch=None):
            odom.header.frame_id = f'odom_{frame_epoch or epoch}'
            odom.pose.pose.position.x = x
            odom.pose.pose.position.y = y
            odom.pose.pose.position.z = z
            odom.pose.pose.orientation.z = math.sin(yaw / 2.0)
            odom.pose.pose.orientation.w = math.cos(yaw / 2.0)
            odom_pub.publish(odom)

        keep_inputs = threading.Event()

        def refresh_inputs():
            while not keep_inputs.wait(0.03):
                status_pub.publish(status)
                odom_pub.publish(odom)

        input_thread = threading.Thread(target=refresh_inputs, daemon=True)
        input_thread.start()
        try:
            for reason in ('unknown', 'occupied', 'outside_map', 'wrong_identity'):
                query_mode['reason'] = reason
                handle = wait_future(action_client.send_goal_async(make_goal(5.0)),
                                     'query rejection response')
                if not handle.accepted:
                    raise RuntimeError('query admission should run after protocol acceptance')
                result = wait_future(handle.get_result_async(), 'map query rejection result')
                if result.status != GoalStatus.STATUS_ABORTED or result.result.outcome != 'rejected':
                    raise RuntimeError(f'query {reason} did not reject: {result}')
                if goals or cancels:
                    raise RuntimeError('rejected map query emitted an EGO goal or trajectory cancel')
            # Source and fusion timestamps are observational in this project.
            # A correctly classified, same-identity query remains admissible
            # when those reported stamps are old.
            query_mode['reason'] = 'stale'
            aged_handle = wait_future(
                action_client.send_goal_async(make_goal(5.0)),
                'age-independent map query response')
            if not aged_handle.accepted:
                raise RuntimeError('aged map timestamps rejected protocol acceptance')
            aged_result_future = aged_handle.get_result_async()
            wait_for(lambda: len(goals) == 1, 'age-independent EGO command')
            aged_result = wait_future(aged_handle.cancel_goal_async(),
                                      'age-independent query cancel response')
            aged_result = wait_future(aged_result_future,
                                      'age-independent query cancellation result')
            if (aged_result.status != GoalStatus.STATUS_CANCELED
                    or aged_result.result.reason != 'caller_cancel'
                    or len(cancels) != 1):
                raise RuntimeError('aged map query did not forward and cancel as expected')
            # Start the independent refusal/timeout phase with empty command
            # observations so those cases still prove they emit no control work.
            goals.clear()
            cancels.clear()
            query_mode.update(reason='no_fresh_fused_depth', delay=0.)
            requests_before_wait = query_mode['requests']
            handle = wait_future(action_client.send_goal_async(make_goal(5.0)), 'fusion wait response')
            result = wait_future(handle.get_result_async(), 'bounded fusion wait result')
            if result.result.reason != 'map_query_timeout' or goals:
                raise RuntimeError('persistent pending fusion did not fail within the wall deadline')
            wait_requests = query_mode['requests'] - requests_before_wait
            if wait_requests > 6:
                raise RuntimeError(f'stale fusion response caused {wait_requests} repeated queries')
            query_mode.update(reason='free', delay=.15)
            handle = wait_future(action_client.send_goal_async(make_goal(5.0)), 'map reset response')
            wait_for(lambda: navigation._pending_admission is not None, 'pending map reset query')
            map_id = uuid.uuid4().hex
            publish_map()
            result = wait_future(handle.get_result_async(), 'map reset admission result')
            if result.result.reason != 'map_context_changed_or_stale' or goals:
                raise RuntimeError('map reset during admission did not discard the certificate')
            peer.destroy_service(query_server)
            wait_for(lambda: not navigation._map_query.service_is_ready(), 'query service removal')
            handle = wait_future(action_client.send_goal_async(make_goal(5.0)), 'unavailable service response')
            if handle.accepted or goals:
                raise RuntimeError('missing query service did not reject protocol acceptance')
            query_server = peer.create_service(
                QueryOccupancySphere, '/mapping/query_occupancy_sphere', query_target)
            wait_for(navigation._map_query.service_is_ready, 'query service recovery')
            query_mode.update(reason='free', delay=.6)
            handle = wait_future(action_client.send_goal_async(make_goal(5.0)), 'timeout response')
            result = wait_future(handle.get_result_async(), 'timeout result')
            if result.result.reason != 'map_query_timeout' or goals:
                raise RuntimeError('query timeout did not fail closed')
            time.sleep(.4)
            if goals:
                raise RuntimeError('late query response forwarded a goal')
            handle = wait_future(action_client.send_goal_async(make_goal(5.0)), 'pending cancel response')
            wait_for(lambda: navigation._pending_admission is not None, 'pending query before concurrent request')
            busy = wait_future(action_client.send_goal_async(make_goal(6.0)), 'concurrent admission response')
            busy_result = wait_future(busy.get_result_async(), 'concurrent admission result')
            if busy_result.result.reason != 'map_query_busy' or goals:
                raise RuntimeError('concurrent admission did not fail closed')
            # Foxy/Nano can spend the 0.25s deadline serving the busy request.
            # Check that timeout separately, then cancel a newly pending query.
            expired = wait_future(handle.get_result_async(), 'busy-phase query timeout')
            if expired.result.reason != 'map_query_timeout' or goals or cancels:
                raise RuntimeError('busy-phase query did not time out without forwarding')
            handle = wait_future(action_client.send_goal_async(make_goal(5.0)), 'fresh pending cancel response')
            wait_for(lambda: navigation._pending_admission is not None, 'fresh pending query')
            wait_future(handle.cancel_goal_async(), 'pending query cancel acknowledgement')
            result = wait_future(handle.get_result_async(), 'pending query cancel result')
            if result.status != GoalStatus.STATUS_CANCELED or goals or cancels:
                raise RuntimeError('cancel while querying forwarded or cleared an unrelated trajectory')
            time.sleep(.65)
            query_mode.update(reason='free', delay=0.)
        finally:
            keep_inputs.set()
            input_thread.join(timeout=1.)
        print('PASS: target query rejects unknown/occupied/outside/identity/timeout, ignores reported source age for a valid same-identity result, and prevents late reply/pending-cancel forwarding')

        info_entered = threading.Event()
        release_info = threading.Event()
        original_get_logger = navigation.get_logger
        original_logger = original_get_logger()

        class BlockingAcceptedGoalLogger:
            def info(self, message):
                if message.startswith('accepted goal '):
                    info_entered.set()
                    release_info.wait(timeout=3.0)
                else:
                    original_logger.info(message)

            def __getattr__(self, name):
                return getattr(original_logger, name)

        navigation.get_logger = lambda: BlockingAcceptedGoalLogger()
        query_mode['transient_remaining'] = 1
        first_query_count = query_mode['requests']
        first_goal_future = action_client.send_goal_async(make_goal(5.0))
        try:
            wait_for(info_entered.is_set, 'accepted-goal info entry')
            if not navigation._lock.acquire(timeout=0.5):
                raise RuntimeError('accepted-goal info held the navigation state lock')
            navigation._lock.release()
        finally:
            release_info.set()
            navigation.get_logger = original_get_logger
        first_handle = wait_future(first_goal_future, 'first goal response')
        if not first_handle.accepted:
            raise RuntimeError('same-epoch goal was rejected by the localization health-state gate')
        first_result_future = first_handle.get_result_async()
        wait_for(lambda: len(goals) >= 1, 'first EGO goal command')
        if query_mode['requests'] - first_query_count < 2:
            raise RuntimeError('transient pending fusion was not rechecked before forwarding')
        expected_id = uuid.UUID(bytes=bytes(first_handle.goal_id.uuid)).hex
        if (goals[-1].goal_id != expected_id or goals[-1].epoch != epoch
                or goals[-1].map_id != map_id):
            raise RuntimeError('EGO command did not preserve the action goal UUID and epoch')

        wait_future(first_handle.cancel_goal_async(), 'cancel acknowledgement')
        canceled = wait_future(first_result_future, 'canceled action result')
        if canceled.status != GoalStatus.STATUS_CANCELED:
            raise RuntimeError(f'expected canceled result, got status {canceled.status}')
        wait_for(lambda: len(cancels) >= 1, 'EGO trajectory cancellation')
        if cancels[-1].goal_id != expected_id or cancels[-1].epoch != epoch:
            raise RuntimeError('explicit cancellation lost its goal UUID or epoch')
        if cancels[-1].mode != TrajectoryCancel.MODE_STOP_HOLD:
            raise RuntimeError('caller cancellation did not request EGO stop/hold')

        status_pub.publish(status)
        odom_pub.publish(odom)
        reset_handle = wait_future(action_client.send_goal_async(make_goal(5.2)), 'active map reset goal')
        reset_future = reset_handle.get_result_async()
        wait_for(lambda: len(goals) >= 2, 'active map reset EGO command')
        map_id = uuid.uuid4().hex
        publish_map()
        reset_result = wait_future(reset_future, 'active map reset abort')
        if reset_result.result.reason != 'map_identity_changed':
            raise RuntimeError('map identity change did not abort the active goal')
        wait_for(lambda: len(cancels) >= 2, 'active map reset cancellation')
        if cancels[-1].goal_id != goals[-1].goal_id:
            raise RuntimeError('map reset canceled a different goal')
        if cancels[-1].mode != TrajectoryCancel.MODE_ABORT:
            raise RuntimeError('map identity fault did not retain fail-safe abort mode')

        status_pub.publish(status)
        odom_pub.publish(odom)
        fault_handle = wait_future(action_client.send_goal_async(make_goal(5.4)), 'planner fault test goal')
        fault_future = fault_handle.get_result_async()
        wait_for(lambda: len(goals) >= 3, 'planner fault test EGO command')
        fault = TrajectoryCancel()
        fault.goal_id = 'wrong-goal'
        fault.epoch = epoch
        fault.reason = 'full_curve_unknown'
        fault_pub.publish(fault)
        time.sleep(.03)
        if fault_future.done():
            raise RuntimeError('unrelated planner fault aborted the active goal')
        fault.goal_id = goals[-1].goal_id
        fault_pub.publish(fault)
        fault_result = wait_future(fault_future, 'planner fault action abort')
        if fault_result.result.reason != 'planner_full_curve_unknown':
            raise RuntimeError('full-curve rejection did not reach the action result')
        wait_for(lambda: len(cancels) >= 3, 'planner fault trajectory cancel')
        if cancels[-1].goal_id != fault.goal_id:
            raise RuntimeError('planner fault cleared an unrelated trajectory')

        status_pub.publish(status)
        odom_pub.publish(odom)
        bridge_fault_handle = wait_future(
            action_client.send_goal_async(make_goal(5.45)),
            'bridge safety-landing fault goal')
        bridge_fault_future = bridge_fault_handle.get_result_async()
        wait_for(lambda: len(goals) >= 4, 'bridge safety-landing EGO command')
        bridge_fault = TrajectoryCancel()
        bridge_fault.goal_id = goals[-1].goal_id
        bridge_fault.epoch = 'stale-epoch'
        bridge_fault.mode = TrajectoryCancel.MODE_ABORT
        bridge_fault.reason = 'bridge_px4_local_position_invalid'
        fault_pub.publish(bridge_fault)
        time.sleep(.03)
        if bridge_fault_future.done():
            raise RuntimeError('bridge fault from a stale epoch aborted the active action')
        bridge_fault.epoch = epoch
        fault_pub.publish(bridge_fault)
        bridge_fault_result = wait_future(
            bridge_fault_future, 'bridge safety-landing action abort')
        if (bridge_fault_result.status != GoalStatus.STATUS_ABORTED
                or bridge_fault_result.result.reason != 'bridge_px4_local_position_invalid'):
            raise RuntimeError(
                'bridge safety landing did not terminate the exact navigation action: '
                f'status={bridge_fault_result.status} '
                f'outcome={bridge_fault_result.result.outcome!r} '
                f'reason={bridge_fault_result.result.reason!r}')
        wait_for(lambda: len(cancels) >= 4, 'bridge fault trajectory abort')
        if (cancels[-1].goal_id != bridge_fault.goal_id
                or cancels[-1].epoch != bridge_fault.epoch
                or cancels[-1].mode != TrajectoryCancel.MODE_ABORT):
            raise RuntimeError('bridge safety landing did not abort the matching EGO trajectory')

        status_pub.publish(status)
        odom_pub.publish(odom)
        hold_handle = wait_future(action_client.send_goal_async(make_goal(0.0)), 'completed hold goal')
        hold_future = hold_handle.get_result_async()
        wait_for(lambda: len(goals) >= 5, 'completed hold EGO command')
        odom_pub.publish(odom)
        hold_result = wait_future(hold_future, 'completed hold action result')
        if hold_result.status != GoalStatus.STATUS_SUCCEEDED:
            raise RuntimeError('stationary synthetic arrival did not complete')
        fault.goal_id = goals[-1].goal_id
        fault_pub.publish(fault)
        wait_for(lambda: len(cancels) >= 5, 'planner fault clears completed-action hold')
        if cancels[-1].goal_id != fault.goal_id:
            raise RuntimeError('completed hold safety fault did not clear its trajectory')

        # Replacing a live target is a new EGO plan from measured state. It must
        # cancel the old action without sending the bridge a trajectory ABORT.
        set_odometry()
        replaced_handle = wait_future(
            action_client.send_goal_async(make_goal(5.0)), 'replaceable goal response')
        if not replaced_handle.accepted:
            raise RuntimeError('first goal for replacement test was rejected')
        replaced_result_future = replaced_handle.get_result_async()
        wait_for(lambda: len(goals) >= 6, 'replaceable EGO command')
        replaced_id = uuid.UUID(bytes=bytes(replaced_handle.goal_id.uuid)).hex
        cancel_count_before_replace = len(cancels)

        replacement_yaw = 0.3
        replacement_handle = wait_future(
            action_client.send_goal_async(make_goal(
                0.0, z=0.25, yaw=replacement_yaw)), 'replacement goal response')
        if not replacement_handle.accepted:
            raise RuntimeError('valid active-goal replacement was rejected')
        replacement_result_future = replacement_handle.get_result_async()
        wait_for(lambda: len(goals) >= 7, 'replacement EGO command')
        replaced_result = wait_future(replaced_result_future, 'replaced action terminal result')
        if (replaced_result.status != GoalStatus.STATUS_ABORTED
                or replaced_result.result.outcome != 'aborted'
                or replaced_result.result.reason != 'goal_replaced'):
            raise RuntimeError('replaced action did not report its server-initiated goal_replaced terminal result')
        replacement_id = uuid.UUID(bytes=bytes(replacement_handle.goal_id.uuid)).hex
        if goals[-1].goal_id != replacement_id or goals[-1].goal_id == replaced_id:
            raise RuntimeError('replacement command did not carry the new goal identity')
        if len(cancels) != cancel_count_before_replace:
            raise RuntimeError('goal replacement emitted a faulting trajectory cancellation')

        # A late planner fault tagged with the retired identity must not end the
        # new task, even though both goals share the same epoch and map.
        fault.goal_id = replaced_id
        fault.epoch = epoch
        fault_pub.publish(fault)
        time.sleep(0.05)
        if replacement_result_future.done():
            raise RuntimeError('late old-goal fault affected the replacement action')
        if (navigation.core.active_goal is None
                or navigation.core.active_goal.goal_id != replacement_id):
            raise RuntimeError('replacement task lost ownership after a stale old-goal fault')

        # Arrival requires 3D position and the requested yaw, not just XY.
        set_odometry(z=0.25, yaw=replacement_yaw)
        replacement_result = wait_future(
            replacement_result_future, '3D plus yaw replacement result')
        if (replacement_result.status != GoalStatus.STATUS_SUCCEEDED
                or replacement_result.result.reason != 'position_yaw_tolerance_held'
                or abs(replacement_result.result.final_pose.pose.position.z - 0.25) > 1e-6):
            raise RuntimeError('3D/yaw replacement target did not complete at its requested pose')

        stale_epoch = epoch
        epoch = uuid.uuid4().hex
        status.epoch = epoch
        odom.header.frame_id = f'odom_{epoch}'
        for tick in range(10, 13):
            status_pub.publish(status)
            odom_pub.publish(odom)
            clock.clock.sec = tick
            clock_pub.publish(clock)
            time.sleep(0.02)
        wait_for(lambda: navigation.core.epoch == epoch
                 and navigation._latest_pose_epoch == epoch
                 and navigation._map_ready(time.monotonic()),
                 'new localization epoch')
        stale_handle = wait_future(
            action_client.send_goal_async(make_goal(5.5, stale_epoch)),
            'stale-epoch goal response')
        if stale_handle.accepted:
            raise RuntimeError('goal in the previous VINS epoch was accepted')

        second_handle = wait_future(
            action_client.send_goal_async(make_goal(6.0)), 'second goal response')
        if not second_handle.accepted:
            raise RuntimeError('same-epoch goal was rejected after the clock-reset recovery')
        second_result_future = second_handle.get_result_async()
        wait_for(lambda: len(goals) >= 8, 'second EGO goal command')
        clock.clock.sec = 11
        clock.clock.nanosec = 999_999_999
        clock_pub.publish(clock)
        aborted = wait_future(second_result_future, 'clock-regression abort')
        if aborted.status != GoalStatus.STATUS_ABORTED:
            raise RuntimeError(f'expected aborted result after clock rollback, got {aborted.status}')
        if aborted.result.reason != 'clock_regression':
            raise RuntimeError(f'unexpected rollback reason: {aborted.result.reason}')
        wait_for(lambda: len(cancels) >= 6, 'rollback trajectory cancellation')
        if cancels[-1].goal_id != goals[-1].goal_id or cancels[-1].epoch != epoch:
            raise RuntimeError('clock rollback cancellation did not target the active epoch goal')

        epoch = uuid.uuid4().hex
        status.epoch = epoch
        odom.header.frame_id = f'odom_{epoch}'
        for tick in range(12, 15):
            status_pub.publish(status)
            odom_pub.publish(odom)
            clock.clock.sec = tick
            clock_pub.publish(clock)
            time.sleep(0.02)
        wait_for(lambda: navigation.core.epoch == epoch
                 and navigation.core.localization_ready
                 and navigation._map_ready(time.monotonic()),
                 'recovered epoch before shutdown test')

        publish_map()
        stale_handle = wait_future(
            action_client.send_goal_async(make_goal(6.5)),
            'localization age-independent goal response')
        if not stale_handle.accepted:
            raise RuntimeError('TRACKING goal was rejected before receipt-age test')
        stale_result_future = stale_handle.get_result_async()
        wait_for(lambda: len(goals) >= 9, 'receipt-age-independent EGO goal command')
        with navigation._lock:
            navigation._last_localization_received = time.monotonic() - 20.0
            navigation._latest_pose_received = time.monotonic() - 20.0
            navigation._map_received = time.monotonic()
        navigation._on_timer()
        if navigation.core.active_goal is None:
            raise RuntimeError('localization/odometry receipt age still aborted the active action')
        caller_cancel = wait_future(stale_handle.cancel_goal_async(), 'receipt-age test cancel request')
        canceled = wait_future(stale_result_future, 'receipt-age test action result')
        if (not caller_cancel.goals_canceling or canceled.status != GoalStatus.STATUS_CANCELED
                or canceled.result.reason != 'caller_cancel'):
            raise RuntimeError('receipt-age test goal did not remain active until caller cancellation')
        wait_for(lambda: len(cancels) >= 7, 'receipt-age test trajectory cancellation')

        timeout_refresh_stop = threading.Event()

        def keep_timeout_inputs_fresh():
            while not timeout_refresh_stop.wait(0.03):
                status_pub.publish(status)
                odom_pub.publish(odom)

        timeout_refresh_thread = threading.Thread(
            target=keep_timeout_inputs_fresh, daemon=True)
        timeout_refresh_thread.start()
        try:
            timeout_handle = wait_future(
                action_client.send_goal_async(make_goal(3.0, timeout_s=0.25)),
                'accepted goal-timeout response')
            if not timeout_handle.accepted:
                raise RuntimeError('same-epoch goal-timeout request was rejected')
            timeout_future = timeout_handle.get_result_async()
            wait_for(lambda: len(goals) >= 10, 'goal-timeout EGO command')
            timeout_result = wait_future(timeout_future, 'bounded active-goal timeout', 2.0)
        finally:
            timeout_refresh_stop.set()
            timeout_refresh_thread.join(timeout=1.0)
        if (timeout_result.status != GoalStatus.STATUS_ABORTED
                or timeout_result.result.reason != 'goal_timeout'):
            raise RuntimeError(
                'active navigation timeout returned an unexpected terminal result: '
                f'status={timeout_result.status} outcome={timeout_result.result.outcome!r} '
                f'reason={timeout_result.result.reason!r}')
        if len(cancels) < 8 or cancels[-1].mode != TrajectoryCancel.MODE_ABORT:
            raise RuntimeError('goal timeout did not fail closed through trajectory abort')

        shutdown_handle = wait_future(
            action_client.send_goal_async(make_goal(7.0)),
            'shutdown-path goal response')
        if not shutdown_handle.accepted:
            raise RuntimeError('same-epoch shutdown-path goal was rejected')
        shutdown_result_future = shutdown_handle.get_result_async()
        wait_for(lambda: len(goals) >= 11, 'shutdown-path EGO goal command')

        # Reproduce the high-rate simulation clock while an action waits for motion.
        load_stamp_ns = clock.clock.sec * 1_000_000_000 + clock.clock.nanosec
        load_start = time.monotonic()
        next_input = load_start
        max_pose_age = 0.0
        while time.monotonic() - load_start < 3.0:
            now = time.monotonic()
            stamp_ns = load_stamp_ns + int((now - load_start) * 1e9)
            clock.clock.sec, clock.clock.nanosec = divmod(stamp_ns, 1_000_000_000)
            clock_pub.publish(clock)
            if now >= next_input:
                status_pub.publish(status)
                odom_pub.publish(odom)
                next_input = now + 0.05
            with navigation._lock:
                pose_age = now - navigation._latest_pose_received
            max_pose_age = max(max_pose_age, pose_age)
            if shutdown_result_future.done():
                raise RuntimeError('active action ended during fresh-input clock-load test')
            time.sleep(0.004)
        print(f'250 Hz clock / active action: maximum pose receipt age {max_pose_age:.3f}s')
        navigation.request_shutdown()
        shutdown_result = wait_future(
            shutdown_result_future, 'graceful navigation shutdown result')
        if (shutdown_result.status != GoalStatus.STATUS_ABORTED
                or shutdown_result.result.reason != 'navigation_node_shutdown'):
            raise RuntimeError('shutdown did not abort the active action with its shutdown reason')
        wait_for(lambda: len(cancels) >= 8, 'shutdown trajectory cancellation')
        if cancels[-1].goal_id != goals[-1].goal_id or cancels[-1].epoch != epoch:
            raise RuntimeError('shutdown cancellation did not target the active goal and epoch')
        if not navigation.wait_for_action_callbacks(timeout_sec=1.0):
            raise RuntimeError('shutdown action callback did not finish before executor teardown')

        print('PASS: action routing with degraded localization status, caller cancel, active-goal replacement, stale old-goal fault isolation, 3D/yaw arrival, unknown map refusal, map identity enforcement, project source-age and localization-health gates removed, bounded active-goal timeout, stale epoch rejection, clock regression, and shutdown abort')
    finally:
        executor.shutdown()
        spin_thread.join(timeout=2.0)
        action_client.destroy()
        peer.destroy_node()
        navigation.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
