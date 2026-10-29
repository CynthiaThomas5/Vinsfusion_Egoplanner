"""Read-only offline evaluation input; never publishes ROS, Gazebo or control data."""
import json
import hashlib
import math
import os
import gc
from pathlib import Path
import sys
import threading
import time

from gz.msgs10.odometry_pb2 import Odometry
from gz.transport13 import Node

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from observer_window import (observation_end_metadata, safe_session_terminal_observed,
                             should_continue_observing,
                             install_observer_stop_handlers,
                             restore_observer_stop_handlers)
from truth_observer import odometry_sample, kinematics_sample


run = Path(sys.argv[1]).resolve()
rows = []
lock = threading.Lock()
node = Node()
start = time.monotonic()
stop_request, previous_signal_handlers = install_observer_stop_handlers()
kinematics_enabled = os.environ.get('D435I_N10_KINEMATICS') == '1'
kinematics_path = run / 'debug-truth-kinematics.jsonl'
kinematics_stream = None
kinematics_state = {'record_count': 0, 'error_count': 0, 'error_examples': [],
                    'subscribe_ok': False}


def kinematics_error(reason):
    with lock:
        kinematics_state['error_count'] += 1
        if len(kinematics_state['error_examples']) < 10:
            kinematics_state['error_examples'].append(reason)


def receive_kinematics(message):
    now = time.monotonic()
    try:
        row = kinematics_sample(message, now - start, now)
        text = json.dumps(row, separators=(',', ':'), allow_nan=False) + '\n'
        with lock:
            if kinematics_stream is not None:
                kinematics_stream.write(text)
                kinematics_state['record_count'] += 1
    except (OSError, ValueError, TypeError) as exc:
        kinematics_error(f'{type(exc).__name__}:{exc}')


if kinematics_enabled:
    try:
        kinematics_stream = kinematics_path.open('x', buffering=65536)
        kinematics_state['subscribe_ok'] = bool(node.subscribe(
            Odometry, '/debug_truth/model_kinematics', receive_kinematics))
        if not kinematics_state['subscribe_ok']:
            kinematics_error('kinematics_subscribe_failed')
    except OSError as exc:
        kinematics_error(f'ledger_open:{type(exc).__name__}:{exc}')


def receive(message):
    wall_now = time.monotonic()
    row = odometry_sample(message, wall_now - start, wall_now)
    with lock:
        rows.append(row)


if not node.subscribe(Odometry, '/debug_truth/base_odometry', receive):
    restore_observer_stop_handlers(previous_signal_handlers)
    raise RuntimeError('failed to subscribe to debug truth odometry')
flight_record = run / 'flight.json'
while (not stop_request.requested
       and should_continue_observing(time.monotonic() - start,
                                     safe_session_terminal_observed(run))):
    time.sleep(0.2)
elapsed = time.monotonic() - start
end = observation_end_metadata(
    elapsed, safe_session_terminal_observed(run),
    flight_record_exists=flight_record.is_file(), run_dir=run,
    stop_signal=stop_request.signal_name)
# Detach the Gazebo transport callbacks and destroy their Node explicitly while
# the Python interpreter and GIL are still live. Let queued callbacks drain
# before dropping the pybind11 object; otherwise its callback tuple can be
# decref'd from a transport thread during interpreter shutdown.
for topic in list(node.subscribed_topics()):
    node.unsubscribe(topic)
if node.subscribed_topics():
    raise RuntimeError('Gazebo truth subscriptions remained after unsubscribe')
time.sleep(0.05)
node = None
gc.collect()
if kinematics_enabled:
    with lock:
        if kinematics_stream is not None:
            kinematics_stream.close()
            kinematics_stream = None
        kinematics_report = {
            'schema': 'uav-kinematics-observation/v1',
            'classification': 'read-only instantaneous physics evidence; no control effect',
            'enabled': True,
            **kinematics_state,
            'metadata_validated': (kinematics_state['record_count'] > 0
                                   and kinematics_state['error_count'] == 0
                                   and kinematics_state['subscribe_ok']),
            'record_file': kinematics_path.name,
            'record_sha256': (hashlib.sha256(kinematics_path.read_bytes()).hexdigest()
                              if kinematics_path.is_file() else None),
            **end,
        }
        (run / 'debug-truth-kinematics-observation.json').write_text(
            json.dumps(kinematics_report, indent=2, allow_nan=False) + '\n')
with lock:
    stamps = [int(row['stamp_ns']) for row in rows]
    gaps = [(right - left) / 1e9 for left, right in zip(stamps, stamps[1:])]
    ordered_gaps = sorted(gaps)
    cadence = {
        'sample_count': len(rows),
        'source_stamp_monotonic': all(right > left for left, right in zip(stamps, stamps[1:])),
        'source_gap_max_sim_s': max(gaps) if gaps else None,
        'source_gap_p99_sim_s': ordered_gaps[min(len(ordered_gaps) - 1,
                                                  math.ceil(0.99 * len(ordered_gaps)) - 1)]
            if ordered_gaps else None,
        'source_gap_median_sim_s': ordered_gaps[len(ordered_gaps) // 2]
            if ordered_gaps else None,
        'expected_odometry_publisher_hz': 250,
        'expected_world_physics_step_s': 0.004,
        'classification': 'Observed samples only; interval coverage must be checked offline; no interpolation is counted as a received sample.',
    }
    report = {'scope': __doc__, 'samples': rows, 'cadence': cadence,
              'truth_payload_semantics': {
                  'pose_reference': 'gazebo_model_origin',
                  'robot_base_frame_is_message_label_only': True,
                  'twist_frame': 'body',
                  'twist_estimator': 'OdometryPublisher rolling mean; not exact instantaneous physics state'},
              **end}
    (run / 'debug-truth-evaluation.json').write_text(
        json.dumps(report, indent=2, allow_nan=False) + '\n')
restore_observer_stop_handlers(previous_signal_handlers)
