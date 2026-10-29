# #350 N10.3 horizon-5 open-speed calibration protocol

Status: **frozen before SITL**. This is a one-variable follow-up to the failed #349 calibration sample.

## Hypothesis and sole changed factor

#349 became active with speed guards disabled, then EGO failed full-curve planning after repeatedly reporting that the terminal point of the local trajectory was inside an obstacle. The recorded final terminal point was about 0.563 m from the axis of the 0.3 m-radius, 10 m-tall cylinder at world X≈-4 m on the straight +X route. This protocol tests whether restoring the repository's default 5 m local planning horizon moves the EGO local target beyond the obstacle and permits an obstacle-around trajectory.

The sole changed factor from #349 is `planning_horizon_m: 1.0 → 5.0`. The max velocity (0.25 m/s per axis), max acceleration (0.25 m/s² per axis), inflation, spawn, +16.0 m ENU / +0.10 m / +0.20 rad goal, 3 s dwell, 600 simulated-second ACTIVE hold, and all other freshness/identity/collision/contact/watchdog/bridge rules remain fixed. EGO-reference and PX4 speed remain observation-only. No speed sample can cancel or reject the mission.

## Frozen task and interpretation

- Planner: `config/components/mapping/n10_horizon5_speed025_calibration.json`; horizon 5.0 m, max velocity 0.25 m/s/axis and max acceleration 0.25 m/s²/axis.
- Spawn: `config/components/simulation/n10_long_range_spawn_minus8.json`.
- Goal: `config/components/navigation/n10_long_range_vio_calibration_goal.json`; single 16 m leg, independent truth position/yaw dwell, then 600 simulation seconds ACTIVE.
- PX4 execution remains owned only by `uav_px4_bridge`; official_ego collision policy; contacts and truth are read-only evaluation inputs. No online truth.
- Profile candidate metrics remain descriptive until N10.4 supplies the shared executable evaluator. Any incomplete mission or evidence window remains failed/inconclusive and cannot count as qualification.
- This is N10 calibration, not an N11–N16 formal trial. It changes no threshold and does not re-enable a project speed guard.

## Input identity

- Run ID: `n10-20261026-350-horizon5-open-speed-16m`.
- Source HEAD: `fd90f3b73e48101ad35c5a0ed9372865392eca7c`; the dirty/untracked worktree is represented by the runtime contract.
- Image: `d435i-vins:dev`, `sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8`.
- Prelaunch contract: 656 files, SHA-256 `57a94ad15861ad36ad95f9cbab31143e9b6449d37624bb10cf79f5b7be26364c`; full file map is in [the prelaunch manifest](n10-horizon5-open-speed-16m-runtime-contract-prelaunch-20261026-350.json).
- Planner file SHA-256: `1b46ef1330bbe43f97dd5299db7ed4a46b69886bed4c2455c1901bc89a4f5e32`.
- #349 remains a failed calibration sample; it is not overwritten by this test.

The exact task and all hashed runtime inputs are recorded in [`n10-horizon5-open-speed-16m-protocol-20261026-350.json`](n10-horizon5-open-speed-16m-protocol-20261026-350.json).

## Outcome

Pending. The protocol and input identity were frozen before starting PX4 SITL. Raw outputs will be kept under `artifacts/runs/n10-20261026-350-horizon5-open-speed-16m/`.
