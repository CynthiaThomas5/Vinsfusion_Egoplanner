"""Offline process lifetime proof using kernel birth identity, never invented clock stamps."""
CORE_ROLES={'px4','vins_node','ego_planner_node','traj_server','navigation_supervisor','px4_bridge',
            'mapping_input_adapter','localization_adapter','parameter_bridge','MicroXRCEAgent','gazebo_server'}


def assess_lifecycle(primary,rows,supplement,supplement_rows,start_ns,end_ns,run_id):
    missing=[];proof={}
    if primary.get('run_id')!=run_id or set(primary.get('expected_roles',[]))!=CORE_ROLES:
        missing.append('primary_identity_or_role_inventory')
    if primary.get('safe_terminal_observed') is not True:missing.append('primary_terminal_closeout_missing')
    clock_rows=[r for r in rows if isinstance(r.get('sim_ns'),int)]
    direct=bool(clock_rows and min(r['sim_ns'] for r in clock_rows)<=start_ns
                and max(r['sim_ns'] for r in clock_rows)>=end_ns)
    if direct:
        selected=[r for r in clock_rows if start_ns<=r['sim_ns']<=end_ns]
        for role in sorted(CORE_ROLES):
            sets=[set(r['roles'].get(role,[])) for r in selected]
            stable=set.intersection(*sets) if sets else set();proof[role]=sorted(stable)
            if not stable:missing.append('process_missing_or_restarted:'+role)
        method='direct_source_window'
    else:
        method='kernel_birth_before_runner_and_alive_after_source_end'
        runners=supplement.get('runner_identities_observed_while_alive') or []
        if supplement.get('run_id')!=run_id or len(runners)!=1:missing.append('live_runner_birth_identity_missing')
        after=[r for r in supplement_rows if isinstance(r.get('sim_ns'),int) and r['sim_ns']>=end_ns]
        if not after:missing.append('post_window_clock_snapshot_missing')
        runner_tick=int(runners[0].split(':')[1]) if len(runners)==1 else -1
        for role in sorted(CORE_ROLES):
            sets=[set(r.get('roles',{}).get(role,[])) for r in rows+after]
            stable=set.intersection(*sets) if sets else set()
            # Identical kernel start tick pre-dating the task runner, and alive
            # after the independently observed source end, entails lifetime
            # coverage; no wall-to-sim interpolation or session stitching.
            stable={identity for identity in stable if int(identity.split(':')[1])<runner_tick}
            proof[role]=sorted(stable)
            if not stable:missing.append('kernel_lifetime_not_proven:'+role)
    return {'status':'INSUFFICIENT' if missing else 'PASS','method':method,'stable_process_identities':proof,
            'missing':missing,'raw_clock_values_rewritten':False,'runtime_control_effect':False}
