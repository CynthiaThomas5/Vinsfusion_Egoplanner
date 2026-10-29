# #249 N08 negative-only current-map diagnostic and safe handoff

## Work

- Reused the existing `n08_overhead_negative_side_view` profile without changing config, planner, health guards, or thresholds.
- N05 after-scan and post-release gates accepted the same epoch/map. The subsequent current-area readiness check failed closed at `localization_not_tracking`.
- Archived the exact `propagated_from_future` lockout snapshot, independent final PX4/bridge readback, and container stop result. No goal/control/XY was issued.

## Verification

- 40.01 s read-only preflight passed; optimized odometry max receipt gap was 86.5 ms, with zero samples over the configured guard.
- Current-area gate failed because propagated odometry stamp 536.304 s was 152 ms ahead of the adapter's latest received `/clock` stamp 536.152 s, beyond the 20 ms health tolerance. This confirms a localization timestamp-ordering refusal; PX4 HRT/ROS was not the mission failure.
- Independent 5 s safety readback: DISARMED, landed, bridge DISABLED, control samples zero. `bash tools/project.sh stop n08-20261024-249-negative-only-current-map` returned 0; container exited 0.
- N05 current-map acquisition passed, but no unknown-volume audit/compute-only certificate/XY/braking evidence was produced.

## Next

#250 will use the existing read-only N08 source timeline from before the support scan through the current-area gate to distinguish a raw propagated timestamp lead from delayed `/clock` delivery to the localization adapter. No health or map thresholds are changed.
