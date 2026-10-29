# N10.3 #415 result and safe-closeout hold

Linked dialogue summary: `collaboration/dialogues/2026-10-28-415-n10-compact-voxel-trace-result.md`.

## Result

The single-goal action directly failed with EGO `planner_full_curve_depth_odom_timeout`. Compact trace encoding reduced observed bytes/update from 319.14 to 66.37 (79.2%) at the exact #414 ROI; the covered 200-fusion interval matched all 341 touched voxels with zero trace-to-snapshot class mismatches. This is a trace-volume and source-consistency result only; it does not explain the task failure or establish clearance.

Independent closeout remains unsafe: bridge `LANDING`, PX4 armed in native `DESCEND` failsafe, EV position/yaw false, land detector false, and `safe-to-stop.json=false`. The Gazebo pose is near the ground but is not a terminal-state substitute. The one-time emergency-disarm authorization was consumed at #391, so none was repeated. The SITL container and PX4/bridge stack remain running.

## Observer shutdown finding

The run driver attempted SIGINT on background observers; Python truth and contact recorders inherited SIGINT-ignore and kept waiting for a safe terminal. After the action had aborted, only those two verified read-only processes were ended with SIGTERM. This produced missing truth/contact finals and left clearance/tracking/acceptance `INSUFFICIENT`. Fix the run-local observer shutdown path before another calibrated flight. No controller process was signaled.

## Verification/evidence

The live run used the pre-run 17-package ROS build and 24 focused tests recorded in `progress/evidence/n10-integrated-calibration-build-20261028-415.json`. Offline compact trace evaluation passed. The action, PX4/bridge readback and explicit unsafe closeout are in `progress/evidence/n10-integrated-calibration-result-20261028-415.json`.

## Next

Keep monitoring the existing SITL until a native landed/disarmed/control-disabled/zero-control terminal is independently confirmed or the user provides a new emergency-disarm authorization. Do not run N10.4+ clean-build or mutate runtime code while this active stack is unresolved. N10 remains `in_progress`.
