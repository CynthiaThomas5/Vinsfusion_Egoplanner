# #357 N10.3 independent cold-start replication

## Purpose

#355 completed the goal and 600-second hold but its observers ended at 380 seconds. #356 captured complete contact and raw-VIO evidence but EGO aborted after repeated candidate collisions with the upstream inflated occupancy layer at about 2.60 m. Normalized cost stayed below 1.0. One same-configuration independent cold start tests whether that planner failure repeats.

## Frozen scope

No flight dynamics, map policy, route, goal, health threshold or observer behavior change. Keep the run-scoped quality/freshness bypass for diagnosis only. If the planner failure repeats, stop route retries and capture map/collision evidence in a no-flight diagnostic.

The driver now copies the frozen calibration analyzer into the run directory and checks its SHA-256 before preflight, correcting the #356 staging omission.

## Verification and SITL result

- Runtime contract: 659 files, SHA-256 matched the frozen #357 protocol.
- Bash syntax passed for the frozen driver. No compiled project source changed.
- Preflight, official takeoff admission, contact observer readiness and analyzer SHA check passed.
- The 16 m action succeeded; independent 3D error 0.044 m, continuous dwell 3.160 s, 600 simulated-second ACTIVE hold passed. Five observers recorded terminal flight.json; contact evaluation passed with zero prohibited events.
- Health bypass was observed; normalized cost peaked at 2.615 against unchanged 1.0. This remains diagnostic and does not qualify health.
- Raw VIO: 667.888 simulated seconds / 24.544 m paired path; position p95 0.497 m, yaw p95 8.692 degrees. Tracking error p95 0.521 m, max 1.099 m. Map source/occupancy ages peaked at 0.164/0.100 s.
- Independent 6-second terminal readback passed; project container exited 0.
- See [#357 result](../evidence/n10-upstream-spline-speed080-health-bypass-16m-20261026-357.md).
- Protocol: ../evidence/n10-upstream-spline-speed080-health-bypass-open-speed-16m-protocol-20261026-357.md

N10.3 remains incomplete: there is no justified final tracking threshold, no high-speed braking result at the measured 0.636 m/s PX4 peak, and health qualification is not supported by a run with the gate enabled. #356 planning failure did not repeat; its exact collision voxels remain unknown.
