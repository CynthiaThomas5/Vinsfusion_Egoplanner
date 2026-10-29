# N10.3/#376 — explicit spawn identity preflight

## Scope

Prepare a rerun of the frozen #371 cylinder/dynamic-box diagnostic after #375 exposed a missing spawn override. No #376 container or goal has started.

## Changes

- Bind `D435I_PLANNER_CONFIG=config/components/mapping/n10_horizon5_speed080_calibration.json` and `D435I_SPAWN_CONFIG=config/components/simulation/n10_long_range_spawn_minus8.json` in the protocol.
- Add run-local pre-goal checks for the exact loaded planner path and effective spawn source, source hash, and six pose values. Persist these in the run manifest. These are version/configuration identity checks, not localization or health threshold gates.
- Freeze runtime `b4707af345d1cd082dfb1cae3a24f24103134eedfce306205785b44342582ea7`, protocol, patch, installed binaries, and all five run-local tool hashes.

## Verification

Prepared hashes and required settings are cross-checked in the prelaunch JSON. `bash -n`, Python bytecode compilation, runtime-manifest equality, planner/spawn/tool hash cross-checks, `python3 tools/project_status.py`, and `git diff --check` passed. The first driver invocation then stopped before goal because top-level `planner_config_path` was missing; independent PX4/bridge readback confirmed the vehicle remained landed/disarmed/control-disabled with zero controls. Added the missing field, bound the prelaunch SHA in the run-local freeze, and preserved the no-flight failure record. The same stack is retained for a no-variable-change preflight retry. No ROS package build/test was needed: only run-local diagnostic scripts and evidence files changed.

## Next

Start #376 with both explicit environment variables. Driver must confirm the loaded planner profile and -8 m spawn before flight submission. N10 remains `in_progress`.
