# #108 N06.10 completed-fusion sphere gate

**Scope:** N06.10, run `n06-20261023-corridor-r33`, actual `corridor_box_column` Gazebo + D435i + VINS + plan_env/EGO. One planner-only goal; no bridge, `traj_server`, PX4, control publisher, or flight.

## Result

The query patch and coverage correction both worked. The read-only sphere service now evaluates the last completed occupancy fusion while preserving epoch/map/frame identity, source and occupancy age, depth-pose health, and raw voxel classification. The r33 run produced three fresh snapshots with unique camera poses at each fused-depth source stamp. In all three snapshots, the body sphere, ten-query continuous sweep, and terminal hold were known free.

The online body sphere, all ten sweep queries, and terminal hold also returned raw free with the same epoch/map/frame. The planner emitted one B-spline, and its internal full-curve certificate logged `queries=22 wall_ms=0.219 reason=free`. No planner fault or curve-after-fault was observed. The ROS graph had no forbidden control node or topic.

The sensor rig covered simulation time 4.984–117.026 s in 11,204 truth samples. Its minimum X was −2.601080 m and it ended at −0.810278 m with an estimated terminal X speed of −0.00024 m/s. All 3,199 recorded localization statuses and 7,872 depth-health statuses were valid. The 695 recorded map statuses remained ready under one identity.

| Snapshot | Source stamp | Source / fusion age | Body free voxels | Sweep queries | Hold free voxels |
| --- | ---: | ---: | ---: | ---: | ---: |
| 01 | 125.302 s | 0.117 / 0.049 s | 2,193 | 10 | 4,913 |
| 02 | 132.298 s | 0.113 / 0.048 s | 2,198 | 10 | 4,915 |
| 03 | 139.525 s | 0.150 / 0.051 s | 2,203 | 10 | 4,916 |

All three poses matched exactly once in the recorded camera-pose stream. Unknown and occupied counts were zero in each body and hold query.

## Verification and artifacts

- `bash tools/project.sh build` — PASS, 17 packages. `plan_env` emitted existing ROS message `ConstPtr` deprecation warnings; no build failures.
- `bash tools/project.sh test` — PASS, 251 tests plus navigation-adapter integration.
- `python3 tools/fetch_dependencies.py --source ego_planner --target /tmp/ego-planner-n06-r33-20261023` — PASS; reconstructed `grid_map.cpp` hash matches the lock and built vendor file.
- `bash tools/run_n04_map_layout.sh n06-20261023-corridor-r33 corridor_box_column 96 motion_n06 config/components/simulation/n06_x_holdpoint_recorded_slow.json` — exit 0; run artifacts saved and project container/process cleanup confirmed.
- [Machine evidence](n06-completed-fusion-sphere-gate-20261023-108.json)
- [Run directory](../../artifacts/runs/n06-20261023-corridor-r33/): [input manifest](../../artifacts/runs/n06-20261023-corridor-r33/run-inputs.json), [motion truth](../../artifacts/runs/n06-20261023-corridor-r33/motion.json), [mapping inputs](../../artifacts/runs/n06-20261023-corridor-r33/inputs/mapping-inputs.json), [probe and planner result](../../artifacts/runs/n06-20261023-corridor-r33/n06-live-layout-probe.json), [full-curve certificate log](../../artifacts/runs/n06-20261023-corridor-r33/mapping-stack.log).
- Run-input manifest SHA-256: `36542f9aa9646b787c7f0312250dab1934a1eaab9acd80c0061690d31e0df150`; probe SHA-256: `29133cd658d751d0c12375411cdbad0bf95678ebb66f67cebf2ff2326ae482ef`.

## Limits and continuation

This proves one corridor-layout planner-only curve and its current raw occupancy certificate. It does not complete N06's two-layout, terminal/emergency hold, replanning/handoff, or fault-rejection exits; the generated curve was not executed. The sphere service does not report the exact pending-depth flag at request time, so r32's pending-gate explanation remains an evidence-supported diagnosis rather than a directly captured flag.

N06/S4 remain `in_progress`, with `next_goal=N06`. Continue with N06.2: repeat the fully gated planner-only integration in the second actual layout, then close the remaining N06 curve, hold, handoff, identity/freshness, resource, and failure-refusal exits.
