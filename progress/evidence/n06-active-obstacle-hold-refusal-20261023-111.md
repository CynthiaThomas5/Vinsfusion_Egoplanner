# #111 N06.2.2 active-curve and completed-hold refusal

**Scope:** isolated actual EGO/plan_env component with synthetic depth in ROS domain 98. No Gazebo, VINS, world truth, PX4, bridge, controller, `traj_server`, or flight.

## Result

Both current-source probes passed. Raw occupancy queries distinguished free (792 voxels), occupied (4), unknown (792), and outside-map (rejected). A goal carrying the wrong map identity was rejected as `full_curve_map_id_mismatch` with zero occupancy queries and no curve.

In the active-curve case, the test changed the depth surface while EGO held one certified curve. The changed observation made the remaining sweep unknown; EGO emitted `full_curve_unknown`, then refused a subsequent goal with `full_curve_planning_failed`. No curve appeared after the fault. The current injection therefore proves fail-closed handling of active map loss; it did not classify this changed surface as occupied. The prior #093 active-obstacle probe directly recorded `full_curve_occupied` and remains the occupied-path evidence.

In the after-completion case, the curve first completed and the map then placed an occupied voxel inside the terminal hold neighborhood. EGO emitted `full_curve_terminal_hold_occupied`, rejected the next goal for the same reason, and published no late curve. The hold certificate used 61 queries and 0.450 ms.

The #108 regression still supplies current-source sphere/sweep resource-bound tests and the navigation-adapter identity, stale, timeout, late-reply, and pending-cancel checks. #111 adds the EGO planner's current-source wrong-map, active-map-loss, and completed-hold fault behavior.

## Verification and artifacts

- The first container bootstrap stopped before starting a probe because ROS setup references an unset shell variable under `set -u`. Retried without nounset; both probes then passed.
- `tools/probe_ego_safety.py` active case — PASS; one certified curve, faults `full_curve_map_id_mismatch`, `full_curve_unknown`, `full_curve_planning_failed`, zero curves after fault.
- `tools/probe_ego_safety.py --after-completion` — PASS; fault `full_curve_terminal_hold_occupied`, zero curves after fault.
- [Machine evidence](n06-active-obstacle-hold-refusal-20261023-111.json)
- [Run directory](../../artifacts/runs/n06-20261023-safety-111/): [active-map-loss result](../../artifacts/runs/n06-20261023-safety-111/active-obstacle/result.json), [completed-hold result](../../artifacts/runs/n06-20261023-safety-111/completed-hold/result.json), and corresponding planner logs.
- Existing direct occupied-path evidence: [#093 report](n06-full-curve-layout-review-20261023.md), [#093 run result](../../artifacts/runs/flight-safety-20261023-093-component/result.json).

## Limits and continuation

This is component fault evidence, not an additional real-layout run. The current active case faulted on unknown before an occupied curve sample; #093 supplies the direct occupied case. Actual-layout replanning/handoff, emergency-stop behavior, and remaining combined-runtime identity/freshness/query/resource refusals remain open. N06/S4 stay `in_progress`; next is N06.2.3.
