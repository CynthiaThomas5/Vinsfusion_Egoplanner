# #343 N10.3 spawn geometry diagnostic

## Scope

Continue Goal completion mode for N10.3. #342 loaded the 0.31 m/s/axis EGO candidate but stopped before publishing a READY trajectory because its first local target was refused as inside an inflated obstacle. The exact rejected point was not instrumented; the cylinder overlap is a geometry-supported inference.

This run changes only the run-specific PX4/Gazebo spawn x from −6.5 m to −8.0 m. The 16 m goal, planner profile, official collision policy, 0.12 m/s runtime guard and all acceptance thresholds remain fixed. No global runtime pose or collision gate is changed.

## Artifacts and pre-run verification

- Added `config/components/simulation/n10_long_range_spawn_minus8.json`.
- Added `tools/resolve_sim_spawn.py` and four unit tests. `tools/project.sh sim` validates a project-relative spawn profile; `tools/sim_runtime.sh` resolves it before PX4 launch and records its source path, SHA-256 and effective pose in the run directory. Without an override, the prior `config/runtime.json` pose remains the default.
- The first wrapper call was correctly rejected before container creation because I had put the test log in the run directory, which `project.sh sim` refuses to reuse. After moving that log to a separate preflight archive, the container started but exited 2 before PX4 launch: `sim_runtime.sh` had changed into the PX4 build directory and invoked the resolver by a workspace-relative path. No PX4 process, spawn pose record, flight record or unlock occurred. Raw container log: `artifacts/runs/n10-20261026-343-speed031-start8/container-startup.log` (SHA-256 `3ac97fa3f7cf9ae15449ab7476506c2731f63a0fa3483c8896ebfa1481605c6f`).
- Fixed the resolver call to use `/workspace/tools/resolve_sim_spawn.py` and added a regression assertion for the absolute path. The latest `bash tools/project.sh test` passed: 405 unit tests, navigation-adapter integration and official-policy ROS probe. Full output SHA-256: `9e183c3e0043a5c9b17b198a1f9291562aa21cdafbd997d08f2568e5cd4a3f4b`, archived at `artifacts/runs/n10-20261026-343-preflight/project-test-r01.log`.
- `git diff --check` passed. No project-labeled container is active; unrelated containers were left untouched.

Frozen protocol and all relevant input hashes: [#343 protocol](../evidence/n10-speed031-start8-protocol-20261026-343.md) and [JSON](../evidence/n10-speed031-start8-protocol-20261026-343.json).

## Result

The corrected fresh run `n10-20261026-343-speed031-start8-r01` completed safely but failed the 16 m planner exit. At spawn x=−8.0 m the prior terminal-obstacle error disappeared. EGO made 10 replan attempts/40 feasibility checks; final max x control-point derivative was 0.326505 m/s against a 0.3255 m/s gate at configured 0.31 m/s, while acceleration passed. It published no READY curve and had no horizontal route motion. The 0.12 m/s guard did not trip because it received no EGO reference samples; three PX4 samples only covered takeoff/landing (max 0.07470 m/s).

Independent arrival failed with 0 s dwell. Raw VIO covers 28.332 sim-s/1.8306 m only. Contact evaluation and live refusal passed; direct postflight readback confirmed PX4 disarmed/landed and bridge LANDED/control disabled. The project run was stopped successfully after that readback; unrelated containers were untouched.

Result report: [#343](../evidence/n10-speed031-start8-20261026-343.md) and [JSON](../evidence/n10-speed031-start8-20261026-343.json). N10.3 remains open. Next evidence-driven trial is #344: keep spawn x=−8.0 m and the 0.12 m/s guard fixed, change only planner max velocity from 0.31 to 0.32 m/s so the measured spline falls below the existing 5% feasibility envelope, then inspect whether READY reference speed trips the unchanged guard.

Dialogue summary: [#343](../../collaboration/dialogues/2026-10-26-343-n10-spawn-geometry.md).
