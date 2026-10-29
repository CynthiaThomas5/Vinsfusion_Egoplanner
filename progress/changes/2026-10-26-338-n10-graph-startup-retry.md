# #338 N10.3 graph discovery launch failure and bounded readiness fix

The horizon=2 calibration launch passed preflight and takeoff admission but did not start its flight runner. The immediate `ros2 topic info /navigation/ego_goal` returned `Unknown topic`; a later read-only query found exactly one supervisor publisher and one EGO planner subscriber. This was a ROS graph discovery race before arming, not a planner result. Bridge readback was DISABLED/landed/disarmed and PX4 arming_state 1; the project container was stopped.

Changed `tools/n09_runtime.sh` to retry graph discovery for up to 10 seconds and require the expected single publisher/subscriber before observers and flight. Verified shell syntax and `git diff --check`; the next full SITL run will exercise this gate.

Evidence: [#338 startup report](../evidence/n10-calibration-startup-20261026-338.md).
