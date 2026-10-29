"""Shared stop condition for observers that must cover safe session closeout."""

import json
from pathlib import Path
import signal

try:
    from n10_run_identity import read_run_identity
except ModuleNotFoundError:  # imported as tools.observer_window by unit tests
    from tools.n10_run_identity import read_run_identity

DEFAULT_MAX_OBSERVATION_WALL_S = 2400.0


class ObserverStopRequest:
    """Record an external stop request without treating it as a safe terminal."""

    def __init__(self):
        self.requested = False
        self.signal_name = None

    def __call__(self, signum, _frame):
        self.signal_name = signal.Signals(signum).name
        self.requested = True


def install_observer_stop_handlers():
    """Override inherited SIGINT/SIGTERM ignores for orderly read-only cleanup.

    A caller may restore the returned handlers after its observation window. The
    signal handler only records the request; subscription cleanup and report
    writing stay in the main loop.
    """
    stop_request = ObserverStopRequest()
    previous = {}
    for signum in (signal.SIGINT, signal.SIGTERM):
        previous[signum] = signal.getsignal(signum)
        signal.signal(signum, stop_request)
    return stop_request, previous


def restore_observer_stop_handlers(previous):
    for signum, handler in previous.items():
        signal.signal(signum, handler)


def should_continue_observing(
    elapsed_wall_s: float,
    safe_session_terminal_observed: bool,
    max_wall_s: float = DEFAULT_MAX_OBSERVATION_WALL_S,
) -> bool:
    """Continue until a verified safe closeout, not merely a task result file."""
    if max_wall_s <= 0:
        raise ValueError("max_wall_s must be positive")
    return elapsed_wall_s < max_wall_s and not safe_session_terminal_observed


def safe_session_terminal_observed(run_dir: Path) -> bool:
    """Recognize native safe-to-stop or explicitly recorded emergency closeout."""
    run_dir = Path(run_dir)
    safe_path = run_dir / "safe-to-stop.json"
    if safe_path.is_file():
        try:
            report = json.loads(safe_path.read_text())
        except (OSError, ValueError):
            report = {}
        bridge = report.get("bridge") or {}
        if (report.get("safe_to_stop_project_container") is True
                and bridge.get("armed") is False
                and bridge.get("landed") is True
                and bridge.get("phase") in ("LANDED", "DISABLED")
                and report.get("control_samples_zero") is True):
            return True

    emergency_path = run_dir / "emergency-disarm-safe-terminal.json"
    if emergency_path.is_file():
        try:
            report = json.loads(emergency_path.read_text())
        except (OSError, ValueError):
            report = {}
        if (report.get("classification", "").startswith(
                "authorized emergency-disarm closeout")
                and report.get("bridge_phase") == "LANDED"
                and report.get("bridge_armed") is False
                and report.get("bridge_landed") is True
                and report.get("bridge_control_enabled") is False
                and report.get("px4_arming_state") == 1
                and report.get("px4_land_detected") is True
                and report.get("control_samples_zero_during_readback") is True):
            return True

    # The flight runner writes this result only after its own terminal wait.
    # A failed result can exist while the bridge is still LANDING, so require
    # all bridge fields before treating it as a safe observer boundary.
    flight_path = run_dir / "flight.json"
    if flight_path.is_file():
        try:
            report = json.loads(flight_path.read_text())
        except (OSError, ValueError):
            report = {}
        bridge = report.get("latest_bridge_status") or {}
        return (report.get("landed_and_disarmed") is True
                and bridge.get("phase") == "LANDED"
                and bridge.get("landed") is True
                and bridge.get("armed") is False)
    return False


def observation_end_metadata(
    elapsed_wall_s: float,
    safe_terminal_observed: bool,
    max_wall_s: float = DEFAULT_MAX_OBSERVATION_WALL_S,
    flight_record_exists: bool = False,
    run_dir: Path | None = None,
    stop_signal: str | None = None,
) -> dict[str, object]:
    """Report safe closeout separately from presence of a task result record."""
    safe = bool(safe_terminal_observed)
    stop_reason = ("safe_session_terminal" if safe else
                   "signal_requested" if stop_signal else "wall_timeout")
    result = {
        "terminal_flight_record_observed": bool(flight_record_exists),
        "safe_session_terminal_observed": safe,
        "observation_stop_reason": stop_reason,
        "observer_stop_signal": stop_signal,
        "max_observation_wall_s": max_wall_s,
        "observation_elapsed_wall_s": elapsed_wall_s,
    }
    if run_dir is not None:
        result["run_identity"] = read_run_identity(run_dir)
    return result
