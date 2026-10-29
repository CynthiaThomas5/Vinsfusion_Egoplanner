# #107 N06 r32 corridor wall-clear holdpoint

## Scope

Continue the user-authorized Goal completion mode for N06, with no stop between internal subtasks. Keep all existing worktree changes. No PX4, bridge, controller, setpoint, flight, unknown-space changes, N05 budget changes or N06 threshold changes.

## Findings

- r32 changed only the retreat endpoint from −3.2m to −2.6m. Truth reached x=−2.600431m, avoided the confirmed x=−3.0m back wall, and ended at x=−0.803939m. All recorded localization and depth-health samples were valid.
- Snapshot-01 and -02 were exact source-pose matched and their raw body, continuous sweep, and terminal hold checks were all free. Snapshot-03 was fresh and same identity, but its source stamp 154.342s exceeded recorder coverage, last camera pose 150.151s, by 4.191s.
- Live MapStatus was ready/fresh. `QueryOccupancySphere` returned `no_fresh_fused_depth` for body/sweep/hold. The last recorder MapStatus showed 2 pending depth pairs. Source code uses `queryReadiness(..., true)` for this sphere endpoint, but `certifyCurve` explicitly uses `queryReadiness(..., false)` to read the last completed fusion with age checks. Pending input is the likely cause; request-time pending state was not recorded.
- The source-match/live gate rejected the goal. No goal was published, no curve/fault was observed, the graph had no control consumer, and the runner cleaned up naturally.

## Decision

Proceed with N06.10: add a narrow EGO vendor patch after 0041 so the read-only sphere endpoint uses last-completed-fusion readiness like `certifyCurve`, preserving identity, freshness, pose and raw occupancy rejection. Extend only recorder wall time to 160s to cover the measured 4.191s source-pose gap. Then repeat the same motion and target. N06/S4 remain `in_progress`; `next_goal=N06`.

## Artifacts

- [#107 report](../../progress/evidence/n06-corridor-wallclear-holdpoint-20261023-107.md)
- [r32 run](../../artifacts/runs/n06-20261023-corridor-r32/)
