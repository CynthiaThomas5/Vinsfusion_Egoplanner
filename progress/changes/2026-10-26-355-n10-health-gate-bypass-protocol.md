# #355 N10 localization health-gate bypass diagnostic

## Scope

N10.3 diagnostic follow-up to #354. A run-scoped `D435I_DIAGNOSTIC_BYPASS_HEALTH_GATES=1` allows the existing 0.8 m/s-per-axis EGO profile and 16 m route to continue past project localization quality/freshness policy gates while retaining truthful status and telemetry. Default behavior remains unchanged. The normalized-cost threshold in `config/components/localization/health.json` remains 1.0.

## Changes

- Localization policy bypass is explicit, boolean-validated, disabled by default and enabled only through the SITL environment variable.
- Bypassed gate reasons accumulate in status diagnostics; `LocalizationStatus.health_gate_bypassed` exposes the mode, and flight history records the flag and reason summary.
- Structural telemetry, clock/timestamp monotonicity and identity checks remain hard failures. Collision/map checks and PX4/bridge state protections remain active.
- Added focused health-state coverage for bypass behavior and retained structural failures.
- Prepared a frozen #355 run driver and analyzer outside `artifacts/runs/`; the analyzer reports whether the bypass was observed and preserves raw cost observations.

## Verification

- `python3 -B -m unittest tools.test_localization_health`: 16 tests passed.
- `bash tools/project.sh build ros`: 17 packages built successfully; only upstream deprecation/unused-parameter warnings.
- `bash tools/project.sh test`: 409 tests and both ROS integration probes passed.
- `bash -n tools/project.sh` and Python AST parsing: passed.
- Frozen runtime contract: 658 files, SHA-256 `8e05456f4e2bcfddf2a2a41799aa7e3368ef15dfa9d3e627220244c981f71011`.

## SITL result

The #355 flight action passed, independent true 3D arrival reached 0.030 m minimum error with 3.250 s continuous dwell, and the configured 600 simulated-second ACTIVE hold completed. The run-scoped bypass was observed; normalized cost peaked at 1.766 while the configured threshold remained 1.0. PX4 local-position speed peaked at 0.613 m/s.

The overall evidence run remains incomplete: truth, alignment, bridge and contact observers stopped at their 380 wall-second cap, well before the roughly 885-second task finished. Contact evaluation has zero prohibited events but did not observe landing contact, so it is incomplete rather than a zero-contact pass. Raw odometry evaluation lacked a full PRESTREAM-to-LANDED interval; the N10 calibration report was consequently not produced. An independent 6-second readback confirmed LANDED, landed=true, armed=false, control_enabled=false, vehicle_remained_disarmed=true and control_samples_zero=true; the project container was then stopped.

Result and limitations: [#355 report](../evidence/n10-upstream-spline-speed080-health-bypass-16m-20261026-355.md). N10 remains in progress; #356 fixes observer termination and repeats the same flight profile.
