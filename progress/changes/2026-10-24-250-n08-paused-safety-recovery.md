# #250 N08 diagnostic paused and support safely recovered

## Result

- Started the existing negative-only profile with the read-only localization source timeline enabled. The user paused the N08 Goal after 3 of 16 support stages, before the prescan-ready marker. The partial timeline stopped with `support_scan_failed_before_prescan`; it does not resolve the #249 timestamp hypothesis.
- The support scan’s SIGINT handling shut down its ROS context before its internal cleanup. The container was kept running. A bounded smooth support-return recovery detached and removed the fixture; Gazebo model-list confirmation showed the fixture absent.
- Fresh independent PX4/bridge readback confirmed DISARMED, landed, bridge DISABLED, and zero control samples. `tools/project.sh stop` exited 0; container exited 0.
- No map gate, mission, compute-only certificate, XY, or braking measurement was run. N08 remains `in_progress`; Goal status is paused by user.

## Resume condition

On user resume, review this partial timeline and #249 health snapshot first. Continue only with a signal-safe, evidence-directed source-timing diagnostic if still needed; preserve all existing gates and do not retest N07.
