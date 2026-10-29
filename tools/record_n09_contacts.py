#!/usr/bin/env python3
"""Read-only Gazebo contact observer for the N09 PX4 SITL mission."""
import json
from pathlib import Path
import sys
import threading
import time

from gz.msgs10.contacts_pb2 import Contacts
from gz.transport13 import Node
from observer_window import (observation_end_metadata, safe_session_terminal_observed,
                             should_continue_observing,
                             install_observer_stop_handlers,
                             restore_observer_stop_handlers)

run = Path(sys.argv[1]).resolve()
stop_request, previous_signal_handlers = install_observer_stop_handlers()
manifest = json.loads((run / 'n09-contact-models/n09-contact-model-manifest.json').read_text())
expected = list(manifest['sensor_topics'])
node = Node()
lock = threading.Lock()
events = []
counts = {topic: 0 for topic in expected}
start = time.monotonic()


def stamp_ns(stamp):
    return int(stamp.sec) * 1_000_000_000 + int(stamp.nsec)


def callback_for(topic):
    def receive(message):
        header_stamp = stamp_ns(message.header.stamp)
        pairs = []
        for contact in message.contact:
            pairs.append({
                'collision1': str(contact.collision1.name),
                'collision2': str(contact.collision2.name),
                'depth_m': [float(value) for value in contact.depth],
                'contact_point_count': len(contact.position),
            })
        with lock:
            counts[topic] += 1
            events.append({'topic': topic, 'stamp_ns': header_stamp,
                           'wall_elapsed_s': time.monotonic() - start,
                           'pairs': pairs})
    return receive


for topic in expected:
    node.subscribe(Contacts, topic, callback_for(topic))

ready_path = run / 'n09-contact-observer-ready.json'
deadline = time.monotonic() + 20.0
advertised = []
while time.monotonic() < deadline:
    if stop_request.requested:
        break
    advertised = sorted(set(node.topic_list()).intersection(expected))
    if set(advertised) == set(expected):
        ready_path.write_text(json.dumps({
            'ready': True, 'expected_topics': expected,
            'advertised_topics': advertised,
            'topic_info': {topic: str(node.topic_info(topic)) for topic in expected},
            'read_only': True,
        }, indent=2) + '\n')
        break
    if (run / 'flight.json').exists():
        break
    time.sleep(0.1)
if stop_request.requested:
    end = observation_end_metadata(
        time.monotonic() - start, safe_session_terminal_observed(run),
        flight_record_exists=(run / 'flight.json').is_file(), run_dir=run,
        stop_signal=stop_request.signal_name)
    ready_path.write_text(json.dumps({
        'ready': False, 'expected_topics': expected,
        'advertised_topics': advertised,
        'reason': 'observer_stop_signal_during_readiness',
        'read_only': True,
    }, indent=2) + '\n')
    for topic in expected:
        node.unsubscribe(topic)
    with lock:
        report = {
            'schema': 'n09-contact-observation/v1',
            'ready': False, 'expected_topics': expected,
            'advertised_topics': advertised,
            'counts_by_topic': counts.copy(), 'total_contact_messages': sum(counts.values()),
            'events': list(events), 'read_only': True,
            'source': 'Gazebo Contact system messages from each vehicle collision link.',
            **end,
        }
    (run / 'n09-contact-observation.json').write_text(json.dumps(report, indent=2) + '\n')
    restore_observer_stop_handlers(previous_signal_handlers)
    raise SystemExit(0)

if not ready_path.exists():
    for topic in expected:
        node.unsubscribe(topic)
    ready_path.write_text(json.dumps({
        'ready': False, 'expected_topics': expected,
        'advertised_topics': advertised,
        'reason': 'contact_sensor_topics_not_all_advertised_before_flight',
        'read_only': True,
    }, indent=2) + '\n')
    (run / 'n09-contact-observation.json').write_text(json.dumps({
        'schema': 'n09-contact-observation/v1', 'ready': False,
        'events': [], 'counts_by_topic': counts,
    }, indent=2) + '\n')
    restore_observer_stop_handlers(previous_signal_handlers)
    raise SystemExit(1)

flight_record = run / 'flight.json'
while (not stop_request.requested
       and should_continue_observing(time.monotonic() - start,
                                     safe_session_terminal_observed(run))):
    time.sleep(0.05)

end = observation_end_metadata(
    time.monotonic() - start, safe_session_terminal_observed(run),
    flight_record_exists=flight_record.is_file(), run_dir=run,
    stop_signal=stop_request.signal_name)
for topic in expected:
    node.unsubscribe(topic)
with lock:
    report = {
        'schema': 'n09-contact-observation/v1',
        'ready': True,
        'expected_topics': expected,
        'advertised_topics': advertised,
        'counts_by_topic': counts.copy(),
        'total_contact_messages': sum(counts.values()),
        'events': list(events),
        'read_only': True,
        'source': 'Gazebo Contact system messages from each vehicle collision link.',
        **end,
    }
(run / 'n09-contact-observation.json').write_text(json.dumps(report, indent=2) + '\n')
restore_observer_stop_handlers(previous_signal_handlers)
