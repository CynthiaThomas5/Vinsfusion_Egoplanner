# N10.3/#375 — runtime and tool freeze alignment

## Scope

Prepare the unchanged `unit_cylinder_0` dynamic-obstacle diagnostic after the #374 source audit. No flight was started during preparation.

## Changes

- Recomputed the runtime manifest from source, configuration, simulation assets, runtime tools, installed ROS packages and PX4: `b4707af345d1cd082dfb1cae3a24f24103134eedfce306205785b44342582ea7` across 665 files.
- Updated the run-local freeze, protocol and prelaunch identity report to this fingerprint and to the #375-local tool paths/hashes; confirmed planner settings are bound to `n10_horizon5_speed080_calibration.json` (0.8 m/s, 0.25 m/s², 5 m horizon, official_ego).
- Recorded #374 health-gate audit and the #372/#373 no-flight failures; no acceptance threshold changed.

## Verification

`python3 tools/runtime_manifest.py /tmp/n10-375-runtime-contract-check.json` produced the same manifest as the prepared candidate. Protocol, prelaunch, freeze and run-local tool hashes cross-check. `python3 tools/project_status.py` and `git diff --check` are pending final prelaunch checks.

## Next

Launch #375 with explicit `D435I_PLANNER_CONFIG`, verify loaded planner profile and runtime/service/graph/contact readiness before sending a goal, then preserve the full result and safe-stop evidence. N10 remains `in_progress`.
