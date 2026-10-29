# N06.2.1 r34 second-layout certificate

## Scope

- Continue the resumed Goal-completion task in N06.
- Verify the second real layout with the r33 source-matched snapshot and live raw body/sweep/hold gate.
- Keep PX4, bridge, controller, `traj_server`, and flight out of scope; preserve N05 and N06 acceptance thresholds.

## Decision

#104/r29 already produced a wall-layout EGO curve, but its live body query failed closed and its input recording ended before the later snapshot source stamps. Reuse the r29 sensor motion and lateral target; extend the input recorder to 160 wall seconds and require the same strict certificate gate used in r33.

## Result

r34 produced three unique source-time camera-pose matches, all raw-free snapshot and live body/sweep/terminal-hold predicates, and one 45-query `reason=free` planner-only curve. No fault or control path was observed. Combined with r33, two actual layouts now have positive planner-only curve certificates.

## Next

Continue N06.2.2 with terminal/emergency hold, replanning handoff, and the identity/freshness/query/resource refusal matrix. N06 remains in progress.
