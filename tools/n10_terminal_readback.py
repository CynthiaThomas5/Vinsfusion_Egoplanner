"""Pure offline classification of fault-exit terminal readbacks."""


def emergency_closeout_used(record):
    if not isinstance(record, dict):
        return False
    classification = str(record.get('classification') or '').lower()
    return ('emergency-disarm' in classification
            or record.get('command_count_requested', 0) > 0)


def summarize_terminal_readback(readback, emergency_record=None):
    """Separate a native terminal from a user-authorized emergency closeout."""
    readback = readback if isinstance(readback, dict) else {}
    latest = readback.get('latest') or {}
    bridge = latest.get('bridge') or {}
    px4 = latest.get('px4_status') or {}
    land = latest.get('land_detected') or {}

    fields = {
        'bridge_phase_landed': bridge.get('phase') == 'LANDED',
        'bridge_landed': bridge.get('landed') is True,
        'bridge_disarmed': bridge.get('armed') is False,
        'bridge_control_disabled': bridge.get('control_enabled') is False,
        'px4_disarmed': px4.get('arming_state') == 1,
        'px4_land_detected': land.get('landed') is True,
        'zero_control_after_terminal': (
            readback.get('zero_control_after_terminal') is True),
        'no_old_epoch_goal_or_trajectory': (
            readback.get('no_old_epoch_goal_or_trajectory') is True),
    }
    required_fields = {
        'bridge_phase_landed': 'latest.bridge.phase',
        'bridge_landed': 'latest.bridge.landed',
        'bridge_disarmed': 'latest.bridge.armed',
        'bridge_control_disabled': 'latest.bridge.control_enabled',
        'px4_disarmed': 'latest.px4_status.arming_state',
        'px4_land_detected': 'latest.land_detected.landed',
        'zero_control_after_terminal': 'zero_control_after_terminal',
        'no_old_epoch_goal_or_trajectory': 'no_old_epoch_goal_or_trajectory',
    }
    present = {
        'bridge_phase_landed': isinstance(bridge.get('phase'), str),
        'bridge_landed': type(bridge.get('landed')) is bool,
        'bridge_disarmed': type(bridge.get('armed')) is bool,
        'bridge_control_disabled': type(bridge.get('control_enabled')) is bool,
        'px4_disarmed': type(px4.get('arming_state')) is int,
        'px4_land_detected': type(land.get('landed')) is bool,
        'zero_control_after_terminal': type(
            readback.get('zero_control_after_terminal')) is bool,
        'no_old_epoch_goal_or_trajectory': type(
            readback.get('no_old_epoch_goal_or_trajectory')) is bool,
    }
    missing = [required_fields[key] for key, has_value in present.items()
               if not has_value]
    emergency_used = emergency_closeout_used(emergency_record)
    state_failures = [key for key in fields
                      if present[key] and key not in (
                          'zero_control_after_terminal',
                          'no_old_epoch_goal_or_trajectory')
                      and not fields[key]]
    post_terminal_failures = [key for key in (
        'zero_control_after_terminal', 'no_old_epoch_goal_or_trajectory')
        if present[key] and not fields[key]]
    native_terminal = (not missing and not state_failures
                       and not post_terminal_failures and not emergency_used)
    return {
        'native_terminal_evidence_complete': native_terminal,
        'emergency_closeout_used': emergency_used,
        'missing_evidence': missing,
        'observed_state_failures': state_failures,
        'post_terminal_failures': post_terminal_failures,
        'checks': fields,
        'stable_terminal_window_wall_s': readback.get(
            'stable_terminal_window_wall_s'),
        'terminal_state_violation_count': readback.get(
            'terminal_state_violation_count'),
    }
