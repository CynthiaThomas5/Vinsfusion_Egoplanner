# #352 N10.3 horizon-5 speed-1.2 calibration protocol

Status: **frozen before SITL**. This isolates EGO's planner velocity parameter, using the actual candidate curve data from #351.

#351 loaded `max_vel=0.8 m/s/axis`, `max_acc=0.25 m/s²/axis` and horizon 5 m. The planner produced candidate summaries with maximum proposed axis velocity 1.04976 m/s and maximum proposed axis acceleration 0.78 m/s², then rejected the curves. Neither maximum is an achieved PX4 flight value.

## Sole changed factor

Change only EGO planner `max_velocity_m_s` from 0.8 to 1.2 m/s per axis, rounding upward from the #351 rejected candidate peak. Keep acceleration 0.25 m/s²/axis, horizon 5 m, inflation, spawn, 16 m ENU / +0.10 m / +0.20 rad goal, dwell, 600 simulation-second ACTIVE hold, official_ego policy, all identity/freshness/contact/watchdog/bridge rules and user-authorized speed-guard removal unchanged.

The planner velocity field controls EGO's curve feasibility/dynamics model; it does not add a PX4/runtime speed cancellation guard. EGO/PX4 speed remains observation-only. If the candidate still fails due acceleration feasibility, preserve that result and isolate the acceleration parameter in a separate experiment. No acceptance threshold changes.

## Input identity

- Run ID: `n10-20261026-352-horizon5-speed120-open-speed-16m`.
- Source HEAD: `fd90f3b73e48101ad35c5a0ed9372865392eca7c`; dirty worktree is represented by the contract.
- Image: `d435i-vins:dev`, `sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8`.
- Runtime contract: 658 files, SHA-256 `e7f46274e9cc72ea757038a0d8f4beaadf4fa9f64cc18aa13ad8274f6dde35b4`; complete file map is in [the prelaunch manifest](n10-horizon5-speed120-16m-runtime-contract-prelaunch-20261026-352.json).
- Planner profile SHA-256: `1f628fcaec9fcdfbf5989a83d7c5a7bd322899e5af550fa975be4026a90e0481`.

See [protocol JSON](n10-horizon5-speed120-open-speed-16m-protocol-20261026-352.json) for exact settings and all hashed inputs.

## Outcome

Pending. Protocol and input identity were frozen before SITL. Raw outputs will be under `artifacts/runs/n10-20261026-352-horizon5-speed120-open-speed-16m/`.
