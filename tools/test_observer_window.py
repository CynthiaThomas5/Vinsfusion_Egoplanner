import json
import os
import signal
from pathlib import Path
import selectors
import subprocess
import sys
import tempfile
import unittest

from tools.observer_window import (
    DEFAULT_MAX_OBSERVATION_WALL_S,
    observation_end_metadata,
    install_observer_stop_handlers,
    restore_observer_stop_handlers,
    safe_session_terminal_observed,
    should_continue_observing,
)


class ObserverWindowTests(unittest.TestCase):
    def test_flight_record_alone_does_not_end_observation(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            (run / 'flight.json').write_text(json.dumps({
                'result': 'FAIL', 'landed_and_disarmed': False,
                'latest_bridge_status': {
                    'phase': 'LANDING', 'landed': False, 'armed': True,
                },
            }))
            self.assertFalse(safe_session_terminal_observed(run))
            self.assertTrue(should_continue_observing(20.0, False))
            report = observation_end_metadata(
                20.0, False, flight_record_exists=True)
            self.assertTrue(report['terminal_flight_record_observed'])
            self.assertFalse(report['safe_session_terminal_observed'])

    def test_native_safe_to_stop_requires_landed_disarmed_and_zero_controls(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            (run / 'safe-to-stop.json').write_text(json.dumps({
                'safe_to_stop_project_container': True,
                'bridge': {'phase': 'LANDED', 'armed': False, 'landed': True},
                'control_samples_zero': True,
            }))
            self.assertTrue(safe_session_terminal_observed(run))
            self.assertFalse(should_continue_observing(20.0, True))

    def test_emergency_closeout_is_safe_observer_boundary_but_separate_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            (run / 'emergency-disarm-safe-terminal.json').write_text(json.dumps({
                'classification': 'authorized emergency-disarm closeout; not native landing',
                'bridge_phase': 'LANDED', 'bridge_armed': False,
                'bridge_landed': True, 'bridge_control_enabled': False,
                'px4_arming_state': 1, 'px4_land_detected': True,
                'control_samples_zero_during_readback': True,
            }))
            self.assertTrue(safe_session_terminal_observed(run))

    def test_successful_flight_record_is_accepted_only_with_terminal_state(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            (run / 'flight.json').write_text(json.dumps({
                'result': 'PASS', 'landed_and_disarmed': True,
                'latest_bridge_status': {
                    'phase': 'LANDED', 'landed': True, 'armed': False,
                },
            }))
            self.assertTrue(safe_session_terminal_observed(run))

    def test_timeout_is_bounded_and_reported_as_incomplete(self):
        self.assertFalse(should_continue_observing(
            DEFAULT_MAX_OBSERVATION_WALL_S, False))
        report = observation_end_metadata(DEFAULT_MAX_OBSERVATION_WALL_S, False)
        self.assertFalse(report['safe_session_terminal_observed'])
        self.assertEqual(report['observation_stop_reason'], 'wall_timeout')

    def test_signal_stop_is_reported_as_incomplete_and_overrides_inherited_ignore(self):
        old_int = signal.getsignal(signal.SIGINT)
        old_term = signal.getsignal(signal.SIGTERM)
        try:
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            stop, previous = install_observer_stop_handlers()
            self.assertIsNot(signal.getsignal(signal.SIGINT), signal.SIG_IGN)
            installed_handler = signal.getsignal(signal.SIGINT)
            installed_handler(signal.SIGINT, None)
            self.assertTrue(stop.requested)
            self.assertEqual(stop.signal_name, 'SIGINT')
            report = observation_end_metadata(
                3.0, False, flight_record_exists=True,
                stop_signal=stop.signal_name)
            self.assertEqual(report['observation_stop_reason'], 'signal_requested')
            self.assertFalse(report['safe_session_terminal_observed'])
            self.assertTrue(report['terminal_flight_record_observed'])
            restore_observer_stop_handlers(previous)
        finally:
            signal.signal(signal.SIGINT, old_int)
            signal.signal(signal.SIGTERM, old_term)

    def test_safe_terminal_takes_precedence_over_stop_signal(self):
        report = observation_end_metadata(
            3.0, True, stop_signal='SIGTERM')
        self.assertEqual(report['observation_stop_reason'], 'safe_session_terminal')
        self.assertTrue(report['safe_session_terminal_observed'])
        self.assertEqual(report['observer_stop_signal'], 'SIGTERM')

    def test_child_overrides_inherited_sigint_ignore_and_writes_incomplete_report(self):
        with tempfile.TemporaryDirectory() as temp:
            report_path = Path(temp) / 'observer-end.json'
            child_code = '''
import json, pathlib, sys, time
from tools.observer_window import install_observer_stop_handlers, observation_end_metadata
stop, previous = install_observer_stop_handlers()
print("ready", flush=True)
deadline = time.monotonic() + 5.0
while not stop.requested and time.monotonic() < deadline:
    time.sleep(0.01)
pathlib.Path(sys.argv[1]).write_text(json.dumps(
    observation_end_metadata(1.0, False, stop_signal=stop.signal_name)))
'''
            process = subprocess.Popen(
                [sys.executable, '-c', child_code, str(report_path)],
                cwd=str(Path.cwd()), stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True,
                preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_IGN),
            )
            selector = selectors.DefaultSelector()
            selector.register(process.stdout, selectors.EVENT_READ)
            try:
                self.assertTrue(selector.select(timeout=5.0))
                self.assertEqual(process.stdout.readline().strip(), 'ready')
                os.kill(process.pid, signal.SIGINT)
                self.assertEqual(process.wait(timeout=5.0), 0)
                report = json.loads(report_path.read_text())
                self.assertEqual(report['observer_stop_signal'], 'SIGINT')
                self.assertEqual(report['observation_stop_reason'], 'signal_requested')
                self.assertFalse(report['safe_session_terminal_observed'])
            finally:
                selector.close()
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=2.0)
                process.stdout.close()
                process.stderr.close()

    def test_rejects_invalid_timeout(self):
        with self.assertRaises(ValueError):
            should_continue_observing(0.0, False, 0.0)


if __name__ == '__main__':
    unittest.main()
