# #106 N06 r31 wall-clearance diagnosis

## Scope and constraints

The user resumed Goal completion mode for N06. Continue the N06 work without stopping between internal subtasks. Preserve existing worktree changes. Keep N06/S4 in progress and `next_goal=N06`; no PX4, bridge, controller, setpoint, flight, map unknown changes, budget changes or acceptance-threshold changes.

## Result

r31 used a single-axis sensor fixture profile planned to retreat to x≈−3.2 m and rest at x≈−0.8 m. The phase-duration helper predicted the intended ideal motion, but fixture truth hit the generated back wall: minimum x=−2.987523 m, then drifted forward to x=+2.011171 m with residual speed ≈0.0444 m/s. The wall occupies x=[−3.10,−3.00] m; the D435i housing half-length is 0.0125 m, predicting fixture-center contact at −2.9875 m. This matches observed truth.

VINS later reported `normalized_cost_exceeded` at sim time149.755 s. `MapStatus.input_ready` became false with reason `map_reset_acknowledged`; snapshot-01 hit its 120 s readiness timeout. No snapshot or gated probe was produced, and no EGO goal was sent. After the runner stopped, no matching project container/process remained.

## Decisions

- Keep the explicit-duration helper and the exact source-time archived/live raw body/sweep/hold gate; unit and navigation integration tests passed.
- N06.8 did not establish its intended map-entry evidence. Continue with N06.9 / r32 by changing only the retreat endpoint from −3.2 m to −2.6 m. The same x≈−0.8 m map endpoint and `(0,+0.25,0)m` planner-only goal remain, and every gate remains fail-closed.
- N06/S4 stay `in_progress`; N07 is not started.

## Artifacts

- [#106 report](../../progress/evidence/n06-corridor-wall-clearance-20261023-106.md)
- [r31 run](../../artifacts/runs/n06-20261023-corridor-r31/)
