"""Pure contact-event classification used by the read-only N09 evaluator."""


def evaluate_contacts(report, manifest, bridge_phases, goal_stamp_ns):
    expected = set(manifest.get('sensor_topics', []))
    advertised = set(report.get('advertised_topics', []))
    reported = set(report.get('expected_topics', []))
    sensors_ready = (report.get('ready') is True and bool(expected)
                     and expected == advertised == reported)
    phases = sorted(bridge_phases, key=lambda row: int(row.get('stamp_ns', 0)))
    ground_events = []
    prohibited = []
    for event in report.get('events', []):
        stamp = int(event.get('stamp_ns', 0))
        phase_rows = [row for row in phases if int(row.get('stamp_ns', 0)) <= stamp]
        phase = phase_rows[-1].get('phase') if phase_rows else None
        for pair in event.get('pairs', []):
            names = (str(pair.get('collision1', '')), str(pair.get('collision2', '')))
            is_ground = any('ground_plane' in name for name in names)
            detail = {'stamp_ns': stamp, 'phase': phase, 'pair': pair,
                      'vehicle_sensor_topic': event.get('topic')}
            if is_ground:
                ground_events.append(detail)
                if stamp >= int(goal_stamp_ns) and phase not in {'LANDING', 'LANDED'}:
                    prohibited.append(detail)
            else:
                prohibited.append(detail)
    landing_ground_observed = any(
        row['phase'] in {'LANDING', 'LANDED'} for row in ground_events)
    passed = sensors_ready and not prohibited and landing_ground_observed
    return {
        'passed': passed,
        'sensor_topics_ready': sensors_ready,
        'ground_contact_event_count': len(ground_events),
        'prohibited_contact_event_count': len(prohibited),
        'landing_ground_contact_observed': landing_ground_observed,
        'first_prohibited_contact': prohibited[0] if prohibited else None,
    }
