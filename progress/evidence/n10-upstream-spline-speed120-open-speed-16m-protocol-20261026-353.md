# N10.3 #353 upstream spline-flow calibration protocol

Status: **frozen before SITL**. This is a one-variable follow-up to #352. It tests whether restoring upstream EGO final-curve handling changes the result while the planner settings and task stay fixed.

## Hypothesis and sole changed factor

#352 aborted with `planner_full_curve_planning_failed` after 0.072 simulation seconds. EGO’s read-only diagnostics showed candidate derivative control-point bounds up to 1.3 m/s/axis and 1.2 m/s²/axis. The project-added 0044 loop kept rechecking/refining and rejected candidates whose normalized ratio remained about 1.32–1.35. Those values are candidate bounds, not measured flight speed.

Remove active patch 0044 and restore upstream’s single feasibility check followed by one time-reallocation/refine attempt. Keep the 0050 output diagnostic-only. If the upstream refinement itself fails, retain that failure. This changes no goal, acceptance threshold, map/collision rule, state/freshness gate, or PX4 control ownership.

## Frozen settings and task

- Planner profile: `config/components/mapping/n10_horizon5_speed120_calibration.json`; `max_velocity_m_s=1.2` and `max_acceleration_m_s2=0.25` per axis; planning horizon `5.0 m`; inflation and timeouts unchanged from #352.
- Sole changed factor: EGO planner source flow with 0044 excluded from the active source patch list.
- Same single D435i, `official_ego` policy, spawn, +16.0 m ENU / +0.10 m / +0.20 rad goal, 3 s dwell and 600 simulation-second ACTIVE observation.
- Extra runtime/cancel-stop speed caps remain removed. Speed telemetry remains observation-only.
- PX4 control remains owned by `uav_px4_bridge`; no online truth. Truth and contact records are read-only evaluation inputs.
- Do not count a curve as accepted solely because the upstream planner returns one. Arrival, dwell, tracking, freshness, hold, contacts and landed/disarmed state remain separately evaluated.

## Frozen run and input identity

- Run ID: `n10-20261026-353-upstream-spline-speed120-open-speed-16m`.
- Source HEAD: `fd90f3b73e48101ad35c5a0ed9372865392eca7c`; working-tree content is captured by the runtime contract.
- Image: `d435i-vins:dev`, `sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8`.
- Runtime contract: 658 files, SHA-256 `304c2f8551172d95813fbdeb62f2c7aa68f57cfbf467c90bce71dee18db58591`; full input map is in [the prelaunch manifest](n10-upstream-spline-speed120-16m-runtime-contract-prelaunch-20261026-353.json).
- Planner profile SHA-256: `1f628fcaec9fcdfbf5989a83d7c5a7bd322899e5af550fa975be4026a90e0481`.
- Fresh EGO source replay passed with 32 active patches. ROS build passed for all 17 packages; `project.sh test` passed 407 unit tests and both navigation ROS integration probes.

## Run procedure

Start a fresh project SITL using:

```bash
D435I_PLANNER_CONFIG=config/components/mapping/n10_horizon5_speed120_calibration.json \
D435I_SPAWN_CONFIG=config/components/simulation/n10_long_range_spawn_minus8.json \
bash tools/project.sh sim n10-20261026-353-upstream-spline-speed120-open-speed-16m
```

After stack readiness, capture the same read-only truth, alignment, planner, bridge, contact and localization-source observations used in #352. Run `tools/run_vio_ego_flight.py` with goal config `config/components/navigation/n10_long_range_vio_calibration_goal.json`, output `artifacts/runs/n10-20261026-353-upstream-spline-speed120-open-speed-16m/flight.json`, flight timeout 360 s and landing timeout 45 s. Keep the existing 600 s active hold and wall/clock watchdogs from the goal profile. Stop the project container only after independent PX4/bridge readback confirms landed, disarmed and control disabled.

See the [machine-readable protocol](n10-upstream-spline-speed120-open-speed-16m-protocol-20261026-353.json) for hashed inputs and exact criteria. Raw data will be under `artifacts/runs/n10-20261026-353-upstream-spline-speed120-open-speed-16m`.
