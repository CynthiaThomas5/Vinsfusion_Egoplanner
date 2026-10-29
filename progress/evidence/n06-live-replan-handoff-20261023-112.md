# #112 N06.2.3 actual-layout two-goal replan handoff

**Scope:** Planner-only EGO handoff in the `wall_box_column` actual Gazebo + D435i + VINS + plan_env layout. No PX4, bridge, controller, `traj_server`, navigation supervisor, setpoint topic, or trajectory execution.

## Result

The first r35 run did not publish a goal. Snapshot and raw body/sweep/hold gates passed, but the sampled optimized-odometry age was 0.566 s against the unchanged 0.4 s limit. Source/fusion ages were 0.137/0.005 s; the probe failed closed. The mapping log continued to show VINS outputs later in that run, so this is retained as an initial stale-sample refusal; the exact cause of that sample timing is not established.

The probe now waits up to 2 wall seconds for a same-epoch odometry sample within the existing 0.4 s limit. In fresh-epoch r36, the initial and handoff gates passed. At first-goal admission, source/fusion/odometry ages were 0.132/0.019/0.099 s. Before the replacement goal they were 0.091/0.002 s for source/fusion.

All three r36 archived snapshots shared one epoch, map ID and frame; each source stamp matched one unique camera pose. For the first `+0.6 m y` goal, all archived body, 24-query continuous sweep and terminal hold predicates were free. The `+0.9 m y` replacement goal independently passed all three archived body, 36-query continuous sweep and terminal hold predicates. Both live body/sweep/hold certificates passed under the same map identity.

EGO published the first goal as trajectory ID 1 and certified its full curve with 45 queries in 0.572 ms (`reason=free`). The second goal arrived while the FSM was active: the captured planner log records `EXEC_TRAJ -> REPLAN_TRAJ -> EXEC_TRAJ`; its new goal ID produced trajectory ID 2. Its full-curve certificate used 57 queries in 0.506 ms (`reason=free`). There were no planner faults, the epoch/map identity stayed stable, and the observed graph had no control nodes or forbidden control topics. Neither curve was executed.

## Verification and artifacts

- `bash tools/project.sh test` — pass: 251 unit tests plus navigation-adapter integration, including identity/stale/timeout, late reply, cancel and resource bounds.
- `bash tools/run_n04_map_layout.sh n06-20261023-wall-r36 wall_box_column 100 motion_n06 config/components/simulation/n06_x_visibility_handoff_recorded_slow.json` — exit 0; container cleaned up.
- r36 live report: [probe JSON](../../artifacts/runs/n06-20261023-wall-r36/n06-live-layout-probe.json), SHA-256 `6fc66f34b78c3dd273611492a96325bea6d90170f03d7baef8efed491020113e`.
- Planner and FSM transitions: [mapping stack log](../../artifacts/runs/n06-20261023-wall-r36/mapping-stack.log), SHA-256 `6524412f6dd86b1037124140f11d40cc48e6e7f53f6ae6e1a525e0cb02a4f578`.
- Inputs, motion, snapshots and run manifest are under `artifacts/runs/n06-20261023-wall-r36/`; manifest SHA-256 `6b4207c617d1b5d4745c48985e94648250c1614e0a849ca745aee4015cf8accd`.
- Machine summary: [#112 JSON](n06-live-replan-handoff-20261023-112.json).

## Limits and continuation

This proves a planner-level replacement/replan and map-certified B-spline publication; it does not prove trajectory execution, braking, emergency-stop motion, or flight. N06 remains `in_progress`. Continue with N06.2.4 to close the remaining combined identity/freshness/query/resource and emergency-hold refusal evidence, then re-evaluate all original N06 exits.
