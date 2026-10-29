# N10.3 #415 result (failure and safety closeout pending)

## Result

The action was submitted, then aborted by native EGO with `planner_full_curve_depth_odom_timeout`. The task is a direct **FAIL**; its position endpoint does not satisfy the target and no independent arrival pass is claimed. No acceptance threshold was changed.

The only changed experiment variable from #414 was voxel-trace serialization. With the same ROI and flight settings, #415 recorded `183,573` compact v2 updates in `12,182,889` bytes; #414 recorded `179,724` verbose v1 updates in `57,357,550` bytes. The observed serialized bytes per update fell from `319.14` to `66.37` (79.2%). The compact decoder matched all 200 covered fusion events in its evaluated interval, and 341 touched voxels matched the source-covered after snapshot with zero class mismatches. This proves the trace is smaller and internally source-consistent for that interval; it does not identify the cause of either flight failure.

## PX4/bridge end state

The last independent readback shows bridge `LANDING` (`planner_fault:full_curve_depth_odom_timeout`), PX4 armed in failsafe `DESCEND`, EV position/yaw fusion false, and `land_detected=false`. `safe-to-stop.json` is **false**. A Gazebo truth pose near the ground is retained as observation only and does not satisfy the independent PX4/bridge terminal contract. The SITL container and control stack remain running.

The earlier one-time emergency-disarm authorization was consumed at #391. No second emergency disarm was used.

## Evidence limits

The run-local driver attempted to stop its background observers with SIGINT, but the read-only truth and contact recorders inherited SIGINT-ignore and did not exit. After the action had already aborted, those two recorder processes were stopped with SIGTERM so the driver could reach its independent PX4 readback. Their final report files are missing; full-body interval clearance, tracking-clearance relation, and overall acceptance remain `INSUFFICIENT`. No control process was signaled.

The map-source watermark is covered by 220 ms and the v2 per-voxel trace evaluator passes for 200 matched fusions. `n10-acceptance-evaluation.json` was not produced; no full N10 acceptance pass is implied.

## Next step

Keep this SITL running until it reaches an independently verified landed/disarmed/control-disabled/zero-control state or the user provides a new emergency-disarm authorization. Then fix the read-only recorder shutdown behavior before a retry, preserve the #415 failure, and continue the remaining N10 calibration, clean rebuild, rebuilt-runtime regression, and freeze.

Machine-readable result: `n10-integrated-calibration-result-20261028-415.json`.
