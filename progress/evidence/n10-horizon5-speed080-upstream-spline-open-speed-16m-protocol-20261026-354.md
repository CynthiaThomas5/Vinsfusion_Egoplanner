# N10.3 #354 upstream spline, speed-0.8 protocol

Status: **frozen before SITL**. This is a one-variable follow-up to #353 after removing the project-added 0044 final-curve rejection.

## Hypothesis and sole changed factor

#353 emitted and executed EGO splines with max_velocity 1.2 m/s/axis. PX4's measured vector-speed peak was 0.859 m/s, and fixed preflight-aligned command-to-truth-IMU tracking error had p95 0.942 m. The run later aborted on the unchanged project localization health guard. Compare the same route with the earlier 0.8 m/s/axis planner value to measure how the planner parameter relates to actual vector speed, command tracking, and VINS cost response.

The only changed factor from #353 is EGO max_velocity_m_s: 1.2 to 0.8 m/s per axis. This planner setting is not a total vehicle speed cap. EGO and PX4 speed remain observation-only, and the user-authorized removal of added runtime speed guards remains in effect.

## Frozen settings and task

- Planner profile: config/components/mapping/n10_horizon5_speed080_calibration.json; max velocity 0.8 m/s/axis, max acceleration 0.25 m/s²/axis, planning horizon 5.0 m.
- Same EGO source flow with patch 0044 excluded and diagnostic-only patch 0050.
- Same single D435i, official_ego collision policy, spawn, +16.0 m ENU / +0.10 m / +0.20 rad goal, 3 s arrival dwell, and 600 simulated-second ACTIVE observation.
- All localization health/freshness, map identity, collision, watchdog, bridge and contact rules remain unchanged. The configured normalized-cost value 1.0 remains provisional and is not modified.
- PX4 control remains owned by uav_px4_bridge; truth is used only for offline evaluation.
- Report EGO command and PX4 local-position vector speeds from full histories; where axes are reported, identify their frame. Do not equate per-axis planner parameters with a total vector-speed limit.
- If the action aborts, preserve the failure and evaluate any available speed/tracking/cost data. No spline emission alone counts as arrival or qualification.

## Input identity

- Run ID: n10-20261026-354-upstream-spline-speed080-open-speed-16m.
- Runtime contract: 658 files, SHA-256 304c2f8551172d95813fbdeb62f2c7aa68f57cfbf467c90bce71dee18db58591.
- Planner profile SHA-256: 0f92519ded6f367387998f01e19a27e270b94c7571e12fbe5b80f82b8ed7473e.
- The profile is the existing 0.8 m/s/axis candidate. Source, installed binary, environment and all other runtime inputs match #353.
- The same calibration analyzer is frozen; the run driver and analyzer hashes are in the machine-readable protocol.

## Run procedure

Start SITL with:

~~~bash
D435I_PLANNER_CONFIG=config/components/mapping/n10_horizon5_speed080_calibration.json D435I_SPAWN_CONFIG=config/components/simulation/n10_long_range_spawn_minus8.json bash tools/project.sh sim n10-20261026-354-upstream-spline-speed080-open-speed-16m
~~~

After stack readiness, execute the frozen run driver inside that project container:

~~~bash
docker exec d435i-n10-20261026-354-upstream-spline-speed080-open-speed-16m   bash /workspace/artifacts/runs/n10-20261026-354-upstream-spline-speed080-open-speed-16m/n10-runtime-driver.sh
~~~

The driver verifies runtime and loaded planner settings, captures read-only truth/alignment/planner/bridge/contact/localization observations, runs the same PX4 task, performs arrival/contact/odometry analysis, and obtains independent terminal readback. Stop only this project container after landed/disarmed/control-disabled and zero-control evidence is present.

See the [machine-readable protocol](n10-horizon5-speed080-upstream-spline-open-speed-16m-protocol-20261026-354.json). Raw output is under artifacts/runs/n10-20261026-354-upstream-spline-speed080-open-speed-16m/.
