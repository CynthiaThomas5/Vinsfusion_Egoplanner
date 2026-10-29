# #106 N06 r31 corridor holdpoint attempt: back-wall collision

**Scope:** N06.8, `corridor_box_column`, run `n06-20261023-corridor-r31`. Sensor fixture only; no PX4, bridge, controller, `traj_server`, setpoint or flight.

## Result

The phase-duration helper and r31 profile ran to completion, but the intended endpoint and map qualification were not reached. Fixture truth started at x=0, reached a minimum x=−2.987523 m at simulation time 53.590 s, then ended at x=+2.011171 m with residual forward speed about 0.0444 m/s. The configured rest-to-rest endpoint was x=−0.8 m.

This is explained by a physical collision in the generated corridor scene. Its back wall is centered at x=−3.05 m with 0.10 m thickness, so its near face is x=−3.00 m. The D435i housing collision extends 0.0125 m along X; the sensor fixture therefore contacts the wall at center x≈−2.9875 m, matching measured truth. That impact changed the return velocity and invalidated the planned endpoint. The profile’s −3.2 m excursion was geometrically incompatible with this scene.

Localization later reported `normalized_cost_exceeded` at 149.755 s; the last captured optimized odometry and camera pose were stamped 101.674 s. MapStatus had `input_ready=false`, reason `map_reset_acknowledged`, and no current depth source stamp. Snapshot-01 timed out after 120 s waiting for a ready map. The runner stopped before creating snapshots or launching the gated probe. **No EGO goal was sent.** No source-matched snapshot certificate, live sweep certificate, curve, or graph report exists for r31.

The run therefore does not support the N06.8 positive-entry hypothesis. It does confirm the back-wall collision point and that a no-go readiness failure prevents goal publication.

## Implementation and verification

- Added explicit per-phase durations to the sensor-motion profile path; preserved the legacy uniform-phase behavior. The r31 profile numerically integrates to x≈−0.8 m at rest with peak commanded speed 0.12 m/s.
- Added a gated probe path that requires three fresh, identity-matched snapshots with exact fused-source camera poses, and raw-free body, continuous sweep and terminal hold. It then repeats those three predicates against the live map and freshness before it can publish. The r31 run failed before this gate was entered.
- Extended the N06 recorder to remain active through all three snapshots and added regression cases for profile integration, invalid phase counts and raw-unknown sphere/sweep rejection.
- `bash tools/project.sh test`: **PASS**, 251 unit tests plus navigation-adapter integration checks.
- Python in-memory compilation of the modified tools, `bash -n` for both runner scripts, and JSON parsing of the r31 profile: **PASS**.
- Run command: `bash tools/run_n04_map_layout.sh n06-20261023-corridor-r31 corridor_box_column 94 motion_n06 config/components/simulation/n06_x_holdpoint_slow.json`.
- Snapshot-01 failure: `MapStatus did not become ready within 120.0s: MapStatus is not ready: map_reset_acknowledged`.
- Container and project processes were absent after the runner stopped. Artifacts: [`r31 run directory`](../../artifacts/runs/n06-20261023-corridor-r31/).

Run manifest SHA-256: `d57e4dd8ab662be66d9d69aceb074b66934ed108a83621ed382fa7cbd8f87e47`; motion truth SHA-256: `295131d8a088d658e0c1d96b5de9cbf6a9b87b27b15a71a3c18cdf2c980f38cc`; recorded mapping inputs SHA-256: `cd593385bdd7614294aba6da2c2d762c21ce2f4514b09597e5dc02ca51e86deb`.

## Next action

N06.9 / r32 keeps the same map endpoint (x≈−0.8 m), goal offset, acceleration and sensors, but shortens the retreat endpoint to x≈−2.6 m. This leaves about 0.4 m between the fixture reference point and the wall face, while the hold sphere’s far X extent remains within 0.82 m of the forward-facing camera. This changes only the observation excursion endpoint. It must still pass health, three source-matched snapshots, raw body/sweep/hold and live gates before any planner-only goal is sent.

N06 and S4 remain `in_progress`; `next_goal` remains N06. The original two-layout, full-curve, hold, handoff and fault-rejection exits remain open.
