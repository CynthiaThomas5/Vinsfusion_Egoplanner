# N10.3 #353 upstream spline-flow result

**Outcome: failed calibration sample; not qualification.** Removing the active project-added 0044 patch allowed the EGO route to emit and execute a spline. The run then aborted on the project-owned localization health guard; the guard value was not changed.

## Code and pre-run verification

- 0044-final-spline-dynamics-check.patch is absent from the active patch list. EGO now uses the upstream single feasibility check and one time-reallocation/refinement attempt. Patch 0050 only adds diagnostics.
- Fresh dependency replay passed with 32 active EGO patches.
- bash tools/project.sh build ros passed for 17 packages.
- bash tools/project.sh test passed 407 unit tests and both navigation ROS integration probes.
- The prelaunch runtime contract contained 658 files and SHA-256 304c2f8551172d95813fbdeb62f2c7aa68f57cfbf467c90bce71dee18db58591.
- Effective parameters were max velocity 1.2 m/s/axis, max acceleration 0.25 m/s²/axis, and planning horizon 5.0 m.

## SITL result

The official EGO collision policy, preflight, and takeoff admission passed. The planner observer recorded 26 B-spline messages, one goal, and one cancel. Its custom final-spline rejection message occurred zero times. The PX4 bridge recorded 1,071 READY trajectory commands and the aircraft moved 5.19 m forward in world X, along 7.20 m of observed path.

Observed vector speed peaks were 0.835 m/s from EGO position-command references and 0.859 m/s from PX4 local-position telemetry. Speed monitoring was observation-only; no extra speed guard was enabled.

The run stopped after 9.4 simulated seconds because localization health changed to normalized_cost_exceeded. At source time 299.544 s, normalized cost was 1.007707962 against the project-configured provisional value 1.0; VINS reported a usable solve, 180 input features, 136 stereo features and 65 long tracks. The diagnostic cost groups reconcile with the total within 4.6e-13. This is the immediate lockout trigger, not a demonstrated root cause for the residual increase. The project health threshold remains unchanged.

One fixed preflight alignment compared READY command positions with the truth IMU point. The measured error was median 0.771 m, p95 0.942 m, maximum 0.946 m; the runner's candidate 0.15 m figure is not an enforced limit or a final acceptance value. Raw VIO before enable and through the sampled pre-enable interval had RMSE 0.024 m, p95 0.051 m, and maximum 0.060 m.

The true minimum 3D goal error was 11.247 m, with zero continuous dwell. There was no 3 s arrival, 600 s ACTIVE hold, or controlled braking measurement. Contact evaluation found zero prohibited contacts. Independent 6 s PX4/bridge readback confirmed landed, disarmed, bridge control disabled, and zero control samples; only the project container was then stopped.

## Decision and next trial

Keep #353 as a failed calibration sample. Do not change the provisional localization health threshold from this single run. #354 will use the same route and source with only the EGO per-axis max_velocity_m_s changed from 1.2 to 0.8; acceleration, horizon, task, health thresholds and all other gates stay fixed. This measures whether actual speed, tracking error, and the VINS cost event change after 0044 removal. If the same health event occurs, the result will not be treated as proof that velocity is unrelated because prior runs used different routes.

Detailed measurements: [calibration evaluation](../../artifacts/runs/n10-20261026-353-upstream-spline-speed120-open-speed-16m/n10-calibration-evaluation.json), [arrival evaluation](../../artifacts/runs/n10-20261026-353-upstream-spline-speed120-open-speed-16m/arrival-evaluation.json), [PX4/bridge readback](../../artifacts/runs/n10-20261026-353-upstream-spline-speed120-open-speed-16m/postflight-px4-bridge-readback.json). Machine-readable summary: [result JSON](n10-upstream-spline-speed120-open-speed-16m-20261026-353.json).
