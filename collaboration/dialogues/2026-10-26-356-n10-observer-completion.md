# 2026-10-26 #356 N10.3 observer completion

## Task and constraints

Continue the authorized N10 Goal-completion scope. #355 reached and held its single 16 m target but its 380-second observer cap ended before landing and complete raw-VIO capture. Keep the 0.8 m/s/axis planner, 16 m/3D/yaw route, 3-second dwell, 600 simulated-second hold, and run-scoped localization quality/freshness bypass unchanged. No real hardware.

## Decision

Change only the read-only observer lifecycle: wait for flight.json terminal record, allow up to 1500 wall seconds, and record whether the terminal marker was observed. The run driver must reject an incomplete observer set. Preserve the health threshold and all structural, time, map/collision, bridge and PX4 control checks.

## Current state

413 unit tests plus the two ROS integration probes passed. The new 659-file runtime contract and #356 protocol are frozen. SITL has not started yet; after start, independently confirm landed/disarmed/control-disabled/zero commands before stopping the project container.

## Run result and follow-up

All five observers completed. The vehicle advanced about 2.60 m, then EGO aborted after repeated candidate collisions against its upstream inflated occupancy layer. Maximum normalized cost was 0.644, below the unchanged 1.0 threshold, so localization health was not the blocker. Contact evaluation passed with zero prohibited contacts and landing contact observed; raw pre-enable position error p95 was 0.0216 m; EGO-to-truth tracking error p95 was 0.528 m. Independent terminal readback passed and the project container was stopped.

The flight did not reach the target, dwell or 600-second hold. Exact collision voxels were not recorded. A postflight analyzer-staging omission was corrected offline; for the next independent cold start, stage and hash-check the analyzer before flight. If the same planner failure repeats, switch to map/collision diagnosis instead of repeating unchanged flights. See the [#356 result](../../progress/evidence/n10-upstream-spline-speed080-health-bypass-16m-20261026-356.md).
