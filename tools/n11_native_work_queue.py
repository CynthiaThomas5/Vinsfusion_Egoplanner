"""Validate native pending-work telemetry; all results are offline only."""

def evaluate_native_work(rows, limits, required_start_ns=None, required_end_ns=None):
    missing=[];violations=[];observed=[];stamps=[];sequences=[]
    fields=('sequence','waiting_features','pending_feature_span_ns','interval_endpoint_ns',
            'latest_imu_before_ns','oldest_imu_after_ns','remaining_imu_after_interval')
    for index,row in enumerate(rows):
        q=row.get('queue_metrics') if isinstance(row,dict) else None
        q=q if isinstance(q,dict) else {}
        w=q.get('work');w=w if isinstance(w,dict) else {}
        stamp=row.get('source_stamp_ns') if isinstance(row,dict) else None
        if w.get('schema')!='vins-native-pending-work/v1' or not isinstance(stamp,int) or isinstance(stamp,bool) or stamp<0:
            missing.append(f'{index}:native_schema_or_source_missing');continue
        if any(not isinstance(w.get(k),int) or isinstance(w.get(k),bool) or w[k]<0 for k in fields):
            missing.append(f'{index}:invalid_native_field');continue
        stamps.append(stamp);sequences.append(w['sequence'])
        if q.get('feature_current_before_feature_dequeue')!=w['waiting_features']+1:
            missing.append(f'{index}:waiting_count_inconsistent')
        if w['waiting_features']==0 and w['pending_feature_span_ns']!=0:
            missing.append(f'{index}:source_span_inconsistent')
        if limits.get('native_remaining_imu_must_not_precede_interval') is not True:
            missing.append('invalid_native_interval_policy')
        if w['oldest_imu_after_ns']<w['interval_endpoint_ns']:
            violations.append(f'{index}:stale_post_consumption_imu')
        if w['latest_imu_before_ns']<w['oldest_imu_after_ns'] or w['remaining_imu_after_interval']<1:
            missing.append(f'{index}:native_imu_order_inconsistent')
        lag=(w['latest_imu_before_ns']-w['interval_endpoint_ns'])/1e9
        span=w['pending_feature_span_ns']/1e9
        if lag<0:missing.append(f'{index}:negative_native_lag')
        if lag>limits['native_work_lag_budget_s']:violations.append(f'{index}:source_lag_budget')
        if span>limits['native_feature_source_span_max_s']:violations.append(f'{index}:pending_source_horizon')
        if w['waiting_features']>limits['native_waiting_features_max']:violations.append(f'{index}:pending_work_count')
        observed.append((lag,span,w['waiting_features']))
    if not rows or len(observed)!=len(rows):missing.append('native_work_coverage_incomplete')
    if sequences and any(b!=a+1 for a,b in zip(sequences,sequences[1:])):missing.append('native_telemetry_sequence_gap')
    if stamps and any(b<=a for a,b in zip(stamps,stamps[1:])):missing.append('native_source_not_monotonic')
    maximum_gap=max(((b-a)/1e9 for a,b in zip(stamps,stamps[1:])),default=None)
    if maximum_gap is None or maximum_gap>limits['native_telemetry_source_gap_max_s']:missing.append('native_source_coverage_gap')
    if required_start_ns is not None and (not stamps or stamps[0]>required_start_ns):missing.append('native_record_starts_after_flight')
    if required_end_ns is not None and (not stamps or stamps[-1]<required_end_ns):missing.append('native_record_ends_before_landing')
    return {'schema':'n11-native-work-result/v1','status':'FAIL' if violations else 'INSUFFICIENT' if missing else 'PASS',
            'sample_count':len(rows),'maximum_native_lag_s':max((v[0] for v in observed),default=None),
            'maximum_pending_source_span_s':max((v[1] for v in observed),default=None),
            'maximum_waiting_features':max((v[2] for v in observed),default=None),'maximum_telemetry_source_gap_s':maximum_gap,
            'violations':violations,'missing_or_inconsistent':missing,'runtime_effect':False,
            'raw_buffer_ols_is_diagnostic_only':True}
