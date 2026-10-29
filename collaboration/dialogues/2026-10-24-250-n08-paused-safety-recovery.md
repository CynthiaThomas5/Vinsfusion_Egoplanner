# #250 N08 diagnostic paused and safety recovery

## Scope

The read-only timestamp diagnostic was started to distinguish a raw VINS future timestamp from delayed `/clock` delivery. No thresholds, planner behavior, or PX4 control were changed.

## Pause and result

The user paused N08 during support scan stage 3/16. The partial timeline ended before the scan’s N05 gate and does not determine the time-skew source. The first SIGINT left the support attached because ROS shutdown preempted the scanner cleanup. The project container stayed running while a smooth fixture return/detach/removal was completed. Fresh PX4/bridge readback confirmed DISARMED, landed, bridge disabled, zero control messages; the fixture was absent and the container exited 0.

## Resume point

N08 remains incomplete and paused. Review #250’s partial timeline and #249’s lockout snapshot before deciding whether another signal-safe diagnostic is needed. Preserve the current 20 ms guard and all N05/N08 gates; do not repeat N07.
