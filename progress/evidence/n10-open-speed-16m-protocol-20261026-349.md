# #349 N10.3 open-speed 16 m calibration protocol

Status: **frozen before SITL**. This is the first calibration run using the #348 build after the user authorized removing the project's extra numerical speed guards. #347 remains a failed historical run and is not recast as a pass.

## Hypothesis and one changed factor

Compared with #347, the single changed factor is the project's extra speed-guard policy: EGO reference speed and measured PX4 speed are observation-only, and cancel-stop no longer rejects finite speeds using the former 0.10 m/s total / 0.01 m/s vertical limits. The candidate planner profile, acceleration, horizon, spawn, target and remaining freshness / identity / collision / bridge rules stay fixed. EGO's own 0.25 m/s-per-axis trajectory dynamics constraint remains an input to planning, not a measured flight-speed cap.

The run tests whether the current official-EGO single-D435i path can complete the original +16.0 m ENU, +0.10 m height, +0.20 rad yaw single goal, then hold ACTIVE for 600 simulation seconds, while recording reference speed, PX4 speed, tracking, VIO error, mapping freshness, contact and final PX4 state. Speed samples cannot cancel the mission.

## Frozen task and interpretation

- Planner: `config/components/mapping/n10_horizon1_speed025_calibration.json`; max velocity 0.25 m/s per axis, max acceleration 0.25 m/s² per axis, horizon 1.0 m.
- Spawn: `config/components/simulation/n10_long_range_spawn_minus8.json`.
- Goal: `config/components/navigation/n10_long_range_vio_calibration_goal.json`; 16 m single leg, 3 simulation-second dwell, 360 simulation-second native timeout, 1500 s goal wall watchdog, then 600 simulation-second ACTIVE hold with 2400 s wall watchdog and 15 s clock-stall timeout.
- Mode: PX4 execute through the single `uav_px4_bridge`; official_ego collision policy; contact instrumentation is read-only; no online truth.
- The profile's 0.15 m / 7.5 deg / 0.15 m tracking / 0.4 s map-age / receipt-gap values are calibration candidates only. Current runner does not evaluate them as runtime guards; N10.3 will report measurable distributions and N10.4 must give the final acceptance configuration an executable evaluator.
- Mission-level success requires the native single-goal action, independent fixed-SE(3) truth confirmation within 0.30 m and 15 deg for at least 3 simulation seconds, complete 600 simulation-second ACTIVE hold, valid source / PX4 observations, no prohibited or unobserved contact, and final landed/disarmed with bridge control disabled. Any failed or incomplete sample stays negative/inconclusive and is not counted as qualification.
- This is a calibration run, not an N11–N16 formal trial or a claim that removed guards have been replaced by new safety limits. Existing localization, freshness, map, collision, timeout and bridge state-machine behavior remains in force.

## Input identity

- Run ID: `n10-20261026-349-open-speed-16m`.
- Source HEAD: `fd90f3b73e48101ad35c5a0ed9372865392eca7c`; dirty/untracked worktree is represented by the runtime-contract fingerprint, not by HEAD alone.
- Container image: `d435i-vins:dev`, `sha256:099ab9afecd28b7354f6d649b3384b1db30c7c67c973e9b93b03f87aca7ad6f8`.
- Prelaunch runtime-contract snapshot: 655 input files, SHA-256 `9fc811d5b318e392d62d0254ab55c7524a13494ca9c78a23f13c9853ce99d7ac`; it covers current own source, config, simulation, runtime tools, installed runtime programs/libraries, dependency manifest and PX4 binary.
- PX4 binary SHA-256: `8a82871c0bde6474759569bcfe2c5ad464d25d2c0993e36ae9d965be45c101d0`.
- EGO node SHA-256: `f5feaa5eec8122af837bb72b2e97627ebd5f2c0e62242e1853c0b8e0568f0d29`.
- EGO cancel-stop source SHA-256: `9228431f4222923b0e1e559ec39bd16c9901215263e9b19e441457be1ee0d9e2`; patch 0052 SHA-256: `2479c81ce35a80a7b3101fe70a8ea65b6831a31d892561e155f8174308a1dd68`.
- Full per-file input hashes and the fixed task settings are in [`n10-open-speed-16m-protocol-20261026-349.json`](n10-open-speed-16m-protocol-20261026-349.json).

## Outcome

Pending. The protocol is frozen before starting the mission. Raw run outputs will be kept under `artifacts/runs/n10-20261026-349-open-speed-16m/`; the report will distinguish action/flight, independent truth, timing, contact and PX4 terminal-state results.
