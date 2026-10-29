# #356 N10.3 observer completion repair

## Scope and cause

#355 demonstrated target arrival and the 600 simulated-second ACTIVE hold with the run-scoped localization quality/freshness bypass. Its truth, alignment, bridge and Gazebo contact observers stopped at a fixed 380 wall-second limit, while the full run lasted about 885 wall seconds. Contact landing and a complete PRESTREAM-to-LANDED raw-VIO interval were therefore absent. The flight itself ended safely, but the evidence bundle was incomplete.

## Changes

- Added a shared observer stop condition: stop when the terminal flight.json appears, with a 1500 wall-second upper bound.
- Updated truth, alignment, planner, bridge and contact observers to emit terminal-record completion metadata.
- Updated the #356 run driver to require all five terminal-observer records before treating the run evidence as complete.
- Frozen #356 to the same 0.8 m/s/axis planner, 0.25 m/s²/axis acceleration, 5 m horizon, 16 m route, 3 s arrival dwell, 600 simulated-second ACTIVE hold and run-scoped diagnostic localization bypass. Health thresholds, route and flight dynamics are unchanged.

## Verification

- bash tools/project.sh test: 413 unit tests passed; navigation adapter and official navigation policy ROS integration probes passed.
- Python AST parse passed for all seven changed/test Python files; Bash syntax passed for the #356 driver and project/simulation launch scripts; git diff --check passed.
- Runtime contract: 659 files, SHA-256 c8a1ee4f5d91d3db7454a9d4608e6ad7e8e09fced7c4c4e2782547760c702e23.
- Protocol and prelaunch contract: ../evidence/n10-upstream-spline-speed080-health-bypass-open-speed-16m-protocol-20261026-356.md.

## SITL result

Preflight, official takeoff admission, contact readiness and all frozen runtime/profile identity checks passed. All five observers recorded the terminal flight marker. EGO aborted after about 2.60 m with planner_full_curve_planning_failed; logs show repeated colliding candidate splines and a final planning_failed state, while maximum normalized cost was 0.644, below the unchanged 1.0 policy. This was an EGO inflated-occupancy planning failure, not a localization health-gate refusal. The 16 m arrival, 3-second dwell, 600-second hold and braking measurement were not reached.

Contact evaluation passed with zero prohibited contacts and a landing contact observed. Complete raw-VIO metrics were generated. Tracking error p95 was 0.528 m, above the current 0.15 m candidate value; this is diagnostic and does not freeze a threshold. Independent 6-second PX4/bridge readback confirmed LANDED, disarmed, control disabled and zero control samples; the project container exited 0.

The run driver initially omitted staging its frozen calibration analyzer into the run directory. I staged the exact prepared analyzer after stop and ran the offline analysis; the resulting report and hashes are preserved. Exact EGO collision voxels were not captured, so physical obstacle versus map false occupancy remains unresolved. See [#356 result](../evidence/n10-upstream-spline-speed080-health-bypass-16m-20261026-356.md).

N10.3 remains incomplete. The next bounded diagnostic is one independent cold start with the same flight settings and completed observers, plus explicit analyzer staging. If the same planning failure recurs, stop repeating the route and collect map/collision diagnostics before another flight.
