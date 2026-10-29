# Change record #353 — N10.3 upstream spline-flow protocol

- Frozen a single-variable PX4 SITL regression after removing active patch 0044.
- Kept the #352 1.2 m/s/axis planner velocity, 0.25 m/s²/axis acceleration, 5 m horizon, 16 m goal, 600 s ACTIVE hold, observation-only speed policy and all task thresholds.
- Fresh EGO source replay passed (32 active patches); `bash tools/project.sh build ros` passed (17 packages); `bash tools/project.sh test` passed (407 unit tests and two ROS integration probes).
- Prelaunch manifest: `progress/evidence/n10-upstream-spline-speed120-16m-runtime-contract-prelaunch-20261026-353.json` (658 files, SHA-256 `304c2f8551172d95813fbdeb62f2c7aa68f57cfbf467c90bce71dee18db58591`).
- Frozen protocol: `progress/evidence/n10-upstream-spline-speed120-open-speed-16m-protocol-20261026-353.md`. The SITL run has not started yet.
