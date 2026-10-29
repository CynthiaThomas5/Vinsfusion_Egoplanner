# 2026-10-26 #357 N10.3 independent cold-start replication

## Task

One independently started repeat of the #356 16 m route to determine whether its EGO planning failure repeats. Keep the same 0.8 m/s/axis planner, 0.25 m/s²/axis acceleration, 5 m horizon, goal, health threshold, run-scoped diagnostic bypass and completed observers.

## Decision

If the EGO planner fails again against inflated occupancy before target, stop repeating flights and switch to read-only map/collision diagnosis. Do not remove the collision policy or raise health limits. Stage and SHA-check the offline analyzer before any flight action.

## Current state

Protocol and 659-file runtime contract are frozen. The #357 SITL container has not started yet.

## Result

#357 completed the target and 600-second ACTIVE hold. Independent arrival was 0.044 m minimum 3D error with 3.160 s continuous dwell; contact evaluation passed with zero prohibited contacts; all observers reached terminal flight.json; PX4/bridge readback passed and the project container was stopped.

The run-scoped bypass was observed while normalized cost reached 2.615, above the unchanged 1.0 threshold. Full raw VIO and tracking were measured: position p95 0.497 m, yaw p95 8.692 degrees, EGO-reference tracking p95 0.521 m. Map source/occupancy age maxima were 0.164/0.100 s. This is not formal health qualification; 0.15 m tracking and 0.4 s age remain unsupported candidates. No high-speed braking measurement or minimum-clearance measurement was made. #356's planner failure did not repeat. See the [#357 report](../../progress/evidence/n10-upstream-spline-speed080-health-bypass-16m-20261026-357.md).
