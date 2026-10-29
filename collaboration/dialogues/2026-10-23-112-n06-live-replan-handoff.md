# #112 N06.2.3 actual-layout handoff

- **User constraint:** Continue Goal completion mode for N06 and preserve the existing acceptance criteria. Keep PX4/control execution and flight out of scope for this subtask.
- **Task:** Exercise a second, independently map-gated goal while the first EGO curve is active; verify actual FSM replan and a new certified curve.
- **Implementation:** Add optional handoff offsets to the live-layout probe and runner. Require archived and live raw body/sweep/hold predicates, stable map identity and freshness before replacement. Keep the 0.4 s odometry limit; wait briefly for a fresh sample rather than bypassing it.
- **Run result:** r35 refused to publish on 0.566 s sampled odometry age. r36 passed after explicit fresh-odometry gating: three snapshots and both targets were known-free, first curve had trajectory ID 1, the planner logged `EXEC_TRAJ -> REPLAN_TRAJ -> EXEC_TRAJ`, and the second goal produced trajectory ID 2 with `reason=free`.
- **Limits:** Planner-only curves were not executed. The exact r35 sample timing cause is not established. Emergency-hold and remaining combined refusal cases are still open.
- **Next:** N06.2.4 identity/freshness/query/resource refusal matrix and emergency-hold evidence.
