# #351 N10.3 horizon-5 speed-0.8 calibration protocol

Status: **frozen before SITL**. This is an evidence-based, single-variable follow-up to #350.

## Hypothesis and sole changed factor

The #350 launch confirmed `planning_horizon=5.0 m`. EGO then generated rebound candidates that route around the central cylinder. Its final-spline check rejected three refinements under `max_vel=0.25 m/s/axis`: the largest proposed axis velocity was 0.747555 m/s, while all logged axis accelerations remained below the configured 0.25 m/s²/axis. No candidate was executed. This test raises only the EGO planner's velocity-model input to 0.8 m/s/axis, rounding above that observed rejected-candidate value, to test whether EGO can produce a feasible curve.

This `max_velocity_m_s` field is an EGO trajectory-planning parameter. The additional project runtime speed cancellation and cancel-stop numerical admission caps remain removed; EGO reference and PX4 measured speed remain observation-only. This protocol does not introduce a runtime speed guard or change any acceptance threshold.

## Frozen settings and task

- Planner: `config/components/mapping/n10_horizon5_speed080_calibration.json`; `max_velocity_m_s=0.8` per axis, horizon 5.0 m, max acceleration 0.25 m/s² per axis.
- Sole variable vs #350: EGO planner max velocity 0.25→0.8 m/s per axis.
- Spawn, inflation, target, +16.0 m ENU / +0.10 m / +0.20 rad, 3 s dwell, 600 simulation-second ACTIVE observation, official_ego collision policy and other runtime checks stay unchanged.
- PX4 control remains owned only by `uav_px4_bridge`. No online truth; contact and truth are read-only evaluation inputs.
- Candidate arrival, tracking, localization, map-age, contact and stop metrics remain descriptive until N10.4 creates the shared evaluator. Failed or incomplete runs remain negative/inconclusive.

## Input identity

- Run ID: `n10-20261026-351-horizon5-speed080-open-speed-16m`.
- Source HEAD: `fd90f3b73e48101ad35c5a0ed9372865392eca7c`; dirty/untracked inputs are represented by the runtime contract.
- Image: `d435i-vins:dev`, `sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8`.
- Prelaunch runtime contract: 657 files, SHA-256 `f39082d77188f3d7682275adaf5a6e6328eb5437d7594b239fc9decc66013ea0`; full map is in [the prelaunch manifest](n10-horizon5-speed080-16m-runtime-contract-prelaunch-20261026-351.json).
- Planner config SHA-256: `0f92519ded6f367387998f01e19a27e270b94c7571e12fbe5b80f82b8ed7473e`.
- The #350 failed sample and all prior outcomes remain unchanged.

See the complete [#351 protocol JSON](n10-horizon5-speed080-open-speed-16m-protocol-20261026-351.json).

## Outcome

Pending. This protocol and runtime identity were frozen before starting PX4 SITL. Run outputs will be stored under `artifacts/runs/n10-20261026-351-horizon5-speed080-open-speed-16m/`.
