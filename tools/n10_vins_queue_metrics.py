"""Reduce read-only VINS estimator queue telemetry without applying a gate."""

QUEUE_FIELDS = {
    'acc': ('acc_current_before_feature_dequeue', 'acc_high_water'),
    'gyr': ('gyr_current_before_feature_dequeue', 'gyr_high_water'),
    'feature': ('feature_current_before_feature_dequeue', 'feature_high_water'),
}


def _valid_count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def summarize_queue_samples(samples):
    """Summarize VINS high-water samples; missing or malformed data is explicit."""
    samples = list(samples)
    valid = []
    errors = []
    for index, row in enumerate(samples):
        metrics = row.get('queue_metrics') if isinstance(row, dict) else None
        if not isinstance(metrics, dict):
            errors.append(f'sample_{index}_missing_queue_metrics')
            continue
        if metrics.get('scope') != 'estimator_process_lifetime':
            errors.append(f'sample_{index}_unexpected_scope')
            continue
        counts = {}
        malformed = False
        for queue_name, (current_field, high_field) in QUEUE_FIELDS.items():
            current = metrics.get(current_field)
            high = metrics.get(high_field)
            if not _valid_count(current) or not _valid_count(high):
                errors.append(f'sample_{index}_{queue_name}_count_invalid')
                malformed = True
                break
            counts[queue_name] = {'current': current, 'high_water': high}
        if not malformed:
            valid.append((row, counts))

    by_epoch = {}
    for row, counts in valid:
        epoch = str(row.get('epoch') or 'unknown')
        by_epoch.setdefault(epoch, []).append((row, counts))

    epoch_reports = {}
    aggregate = {
        name: {'max_reported_high_water': None,
               'max_current_before_feature_dequeue': None}
        for name in QUEUE_FIELDS
    }
    for epoch, rows in by_epoch.items():
        queues = {}
        for queue_name in QUEUE_FIELDS:
            peaks = [counts[queue_name]['high_water'] for _, counts in rows]
            currents = [counts[queue_name]['current'] for _, counts in rows]
            monotonic = all(a <= b for a, b in zip(peaks, peaks[1:]))
            queues[queue_name] = {
                'max_reported_high_water': max(peaks),
                'max_current_before_feature_dequeue': max(currents),
                'high_water_nondecreasing': monotonic,
            }
            current_peak = aggregate[queue_name]['max_reported_high_water']
            aggregate[queue_name]['max_reported_high_water'] = (
                max(peaks) if current_peak is None else max(current_peak, max(peaks)))
            current_peak = aggregate[queue_name]['max_current_before_feature_dequeue']
            aggregate[queue_name]['max_current_before_feature_dequeue'] = (
                max(currents) if current_peak is None else max(current_peak, max(currents)))
            if not monotonic:
                errors.append(f'epoch_{epoch}_{queue_name}_high_water_decreased')
        stamps = [row.get('source_stamp_ns') for row, _ in rows
                  if _valid_count(row.get('source_stamp_ns'))]
        epoch_reports[epoch] = {
            'sample_count': len(rows),
            'source_stamp_ns_range': ([min(stamps), max(stamps)] if stamps else None),
            'queues': queues,
        }

    complete = bool(valid) and not errors and len(valid) == len(samples)
    return {
        'status': 'OBSERVED' if complete else 'INSUFFICIENT',
        'sample_count': len(samples),
        'valid_sample_count': len(valid),
        'process_lifetime_high_water_is_observation_only': True,
        'queue_capacity_or_runtime_limit_inferred': False,
        'aggregate_queues': aggregate,
        'epochs': epoch_reports,
        'errors': errors,
        'qualification': (
            'High-water values describe reported estimator process-lifetime maxima. '
            'They do not establish a queue capacity or impose a runtime decision.'),
    }
