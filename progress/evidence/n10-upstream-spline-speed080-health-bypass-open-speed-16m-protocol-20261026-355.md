# N10.3 #355 localization health-gate bypass diagnostic protocol

**Status: frozen before SITL.** The target is a diagnostic PX4 run on the same route and EGO profile as #354, with a run-scoped bypass for project localization quality/freshness policy gates.

## Hypothesis and single variable

#354 reached a minimum true goal error of 0.061 m and progressed 15.972 m, then aborted when normalized cost reached 1.08530 against the unchanged provisional 1.0 policy. This run tests whether that project policy gate alone prevents the vehicle from completing the same 16 m task. The only behavioral variable is `D435I_DIAGNOSTIC_BYPASS_HEALTH_GATES=1`; the localization thresholds remain unchanged and the default remains off.

## Frozen task and settings

- EGO profile: `config/components/mapping/n10_horizon5_speed080_calibration.json`; max velocity 0.8 m/s per axis, max acceleration 0.25 m/s² per axis, horizon 5 m.
- Same single D435i, `official_ego` collision policy, spawn, +16.0 m ENU / +0.10 m / +0.20 rad goal, 3 s arrival dwell, and 600 simulated-second ACTIVE observation as #354.
- Same upstream EGO feasibility and refinement behavior; no project-added final whole-curve rejection and no extra runtime speed guard.
- Localization health policy file and `max_normalized_cost=1.0` stay unchanged. The diagnostic override bypasses localization adapter quality/freshness gates and its initialization timeout; actual normalized cost, features, residuals, timing and bypass reasons remain recorded.
- Malformed telemetry, invalid values, non-increasing timestamps, clock regression, publisher/epoch identity errors, collision/map checks, and PX4/bridge state and control safeguards remain enforced. Downstream receipt freshness remains a flight safety check.
- PX4 setpoints remain owned by `uav_px4_bridge`; online truth is not used for control. Contact sensors are read-only.

## Measurements and interpretation

Record effective planner settings, spline/action outcomes, full EGO/PX4 vector-speed histories, fixed preflight-aligned command-to-truth-IMU tracking, raw VIO error, localization gate reasons and raw quality values, independent 3D arrival and dwell, map/source timing, contacts, any 600 s hold, braking only if actually reached, and independent landed/disarmed/control-disabled readback.

A bypassed flight is diagnostic evidence only. It cannot establish localization-health qualification or pass N10. A task abort, incomplete dwell/hold, missing measurement, collision, or unsafe terminal state remains a failed/incomplete sample and is retained.

## Input identity and procedure

- Runtime contract: 658 files, SHA-256 `8e05456f4e2bcfddf2a2a41799aa7e3368ef15dfa9d3e627220244c981f71011`.
- Planner profile SHA-256: `0f92519ded6f367387998f01e19a27e270b94c7571e12fbe5b80f82b8ed7473e`.
- Goal profile SHA-256: `23617388b441e093bbf45f83d19c64fdf69bd77a6ed6c82b2f6d0e6cc1a30aa0`.
- Health policy SHA-256: `54c5a7b83d858f44ca6a8957a1aa96b8b3f25168f11b2fcff016c538d4e348c6`.
- Frozen runner SHA-256: `e447c3901bf4178cd56f128d5089c337cedf78497030df4c8e7edc1f60485eee`.
- Frozen analyzer SHA-256: `f94812ecdc16006513f987952398f8240fb1beab36d452cbee54628864017ba8`.

Start command:

~~~bash
D435I_DIAGNOSTIC_BYPASS_HEALTH_GATES=1 D435I_PLANNER_CONFIG=config/components/mapping/n10_horizon5_speed080_calibration.json D435I_SPAWN_CONFIG=config/components/simulation/n10_long_range_spawn_minus8.json bash tools/project.sh sim n10-20261026-355-upstream-spline-speed080-health-bypass-16m
~~~

Once the stack is ready, copy the frozen runner/analyzer from `artifacts/n10-prepared/n10-20261026-355-upstream-spline-speed080-health-bypass-16m/` into the run directory and execute the runner inside that container. Obtain the independent six-second PX4/bridge readback; stop only this project container after it confirms landed, disarmed, bridge control disabled and zero control samples.

Machine-readable protocol: [JSON](n10-upstream-spline-speed080-health-bypass-open-speed-16m-protocol-20261026-355.json). Frozen runtime manifest: [prelaunch contract](n10-upstream-spline-speed080-health-bypass-16m-runtime-contract-prelaunch-20261026-355.json).
