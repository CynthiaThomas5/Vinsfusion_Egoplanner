# #107 N06 r32 corridor wall-clear holdpoint

**Scope:** N06.9, `corridor_box_column`, run `n06-20261023-corridor-r32`. Sensor fixture and planner-only diagnostics; no PX4, bridge, controller, `traj_server`, setpoint or flight.

## Result

The revised motion avoided the back wall and reached its intended rest point: truth ranged from x=0 to x=−2.600431 m and ended at x=−0.803939 m. All 2,998 localization-status samples were valid, all 7,336 depth-health samples were valid, and the last recorded MapStatus remained ready under one epoch/map identity.

The first two snapshots had exact, unique camera poses at their fused-depth source stamps and were fresh (source/fusion ages 0.201/0.047 s and 0.153/0.047 s). For both, the raw body sphere, ten-sample continuous sweep, and terminal hold for `(0,+0.25,0)m` were all free. Snapshot-03 was also fresh (0.118/0.048 s), but its source stamp 154.342 s was 4.191 s later than the last recorded camera pose at 150.151 s. The three-snapshot source-match gate therefore failed closed.

The live map status was ready and fresh at the probe (`source_age=0.110 s`, `fusion_age=0.017 s`), but `/mapping/query_occupancy_sphere` returned `no_fresh_fused_depth` for the body and the first sweep query. The last recorded MapStatus had two pending depth pairs while the completed map remained fresh. Source inspection shows that this sphere endpoint requires no pending pair, while the full-curve certifier explicitly reads the last completed fusion with the same age and pose gates. Pending input is therefore a supported explanation for the refusal, but the exact pending flag at probe request time was not recorded.

The goal gate did not publish an EGO target. The probe graph contained no forbidden control node or topic. No curve or planner fault was generated for this candidate.

## Verification and artifacts

- Run command: `bash tools/run_n04_map_layout.sh n06-20261023-corridor-r32 corridor_box_column 95 motion_n06 config/components/simulation/n06_x_holdpoint_wallclear_slow.json` — runner exited 0 and reported capture complete.
- `tools/project.sh test` remained green from #106 (251 tests and navigation-adapter integration); r32 added runtime verification of the snapshot/live fail-closed gate.
- Container and matching project processes were absent after natural cleanup.
- [r32 run directory](../../artifacts/runs/n06-20261023-corridor-r32/), including motion truth, 4,428 depth/camera-pose pairs, 2,214 optimized odometry samples, three snapshot archives and the gated probe.
- Run-manifest SHA-256: `4df9230bd461b72d2b068a5f042d4125242e3cbabc6215e1742b42d67ade7b6`; motion truth: `7cd5995dbeeab5921344162a54791cdcce652d76644a676d800171b7cfa63df4`; mapping inputs: `c9edbbcd91f34b1ee107177021576701d8b846861c6f34f52622c55abfd58cd4`; probe report: `fdbbe42af8b862846a43548e20446cb4d0105c6dc1bcd9414762bf37e3b608c5`.

## Next action

N06.10 aligns the public raw-sphere endpoint with the existing full-curve checker’s last-completed-fusion semantics. It will still require matching identity, valid depth pose, current source and occupancy ages, and raw-free voxels; unknown/occupied/outside/query errors remain reject conditions. Extend only the recorder window enough to include the demonstrated 4.191 s snapshot-03 source-pose gap, then rerun the same profile and target. A target can publish only if all three archived and live raw predicates pass.

N06 and S4 remain `in_progress`; `next_goal` remains N06. Original two-layout curve, hold, handoff and fault-matrix exits remain open.
