# #109 N06.2.1 wall-layout live EGO certificate

**Scope:** N06.2.1, run `n06-20261023-wall-r34`, actual `wall_box_column` Gazebo + D435i + VINS + plan_env/EGO. One planner-only goal; no bridge, `traj_server`, PX4, controller, control publisher, or flight.

## Result

r34 completed the same strict gate as r33 in the second layout. Each of three fresh snapshots had a unique camera pose at its fused-depth source stamp. For all snapshots, the actual-start body sphere, 24-query continuous sweep to the `(0,+0.6,0)m` candidate, and terminal hold were raw free with zero unknown or occupied voxels.

The live map kept one epoch/map/frame identity. At probe time, source/fusion/odometry ages were 0.099/0.100/0.165 s, below the 0.4 s limit. The live body query was free, all 24 continuous-sweep queries passed, and the terminal hold was free. EGO logged `queries=45 wall_ms=0.396 reason=free`, then published one B-spline. No planner fault, late curve, forbidden graph node, or control topic was observed.

The sensor rig ran from simulation time 4.962 to 97.967 s in 9,300 truth samples. It reached x=−2.407446 m and returned to x=−0.011718 m. All 3,199 localization statuses and 7,521 depth-health statuses were valid; all 699 recorded MapStatus samples were ready under the same identity.

| Snapshot | Source stamp | Source / fusion age | Body free voxels | Sweep queries | Hold free voxels |
| --- | ---: | ---: | ---: | ---: | ---: |
| 01 | 107.152 s | 0.113 / 0.042 s | 2,199 | 24 | 4,882 |
| 02 | 115.567 s | 0.139 / 0.042 s | 2,198 | 24 | 4,886 |
| 03 | 122.299 s | 0.138 / 0.039 s | 2,198 | 24 | 4,888 |

Each source stamp matched exactly one archived camera pose. The online body and hold queries returned 2,191 and 4,907 free voxels respectively, with zero unknown and occupied voxels.

## Verification and artifacts

- `bash tools/run_n04_map_layout.sh n06-20261023-wall-r34 wall_box_column 97 motion_n06 config/components/simulation/n06_x_visibility_recorded_slow.json` — exit 0; all run artifacts produced; container and project processes absent after cleanup.
- The same patch/binary set passed `bash tools/project.sh build` (17 packages) and `bash tools/project.sh test` (251 tests plus navigation-adapter integration) in #108; r34 changes only the simulation motion/recording profile.
- [Machine evidence](n06-second-layout-live-ego-certificate-20261023-109.json)
- [Run directory](../../artifacts/runs/n06-20261023-wall-r34/): [input manifest](../../artifacts/runs/n06-20261023-wall-r34/run-inputs.json), [motion truth](../../artifacts/runs/n06-20261023-wall-r34/motion.json), [mapping inputs](../../artifacts/runs/n06-20261023-wall-r34/inputs/mapping-inputs.json), [probe and planner result](../../artifacts/runs/n06-20261023-wall-r34/n06-live-layout-probe.json), [full-curve certificate log](../../artifacts/runs/n06-20261023-wall-r34/mapping-stack.log).
- Run-input manifest SHA-256: `e175212d2f9afa0cd3e16ddd296ddd2b3f0c11369267e14700acf51bc0f0aafc`; probe SHA-256: `8a76947b0e446be61ff76ea8f907b62587a9ba0461c4a90260cb8b3074ee93ec`.

## Limits and continuation

r33 corridor and r34 wall now provide two actual-layout planner-only full-curve certificates with matching snapshots and live raw body/sweep/hold gates. The curves were not executed. Terminal/emergency-hold transition, replanning/handoff, new-obstacle response, late-curve rejection, wrong identity, stale map, query failure, and resource-bound rejection remain to be demonstrated. N06/S4 stay `in_progress`; the next subtask is N06.2.2.
