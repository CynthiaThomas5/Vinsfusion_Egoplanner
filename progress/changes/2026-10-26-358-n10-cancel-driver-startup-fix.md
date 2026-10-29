# #358 N10 cancellation driver startup failure and fix

## Changed

The new N10 cancellation driver failed before preflight because `set -u` made the ROS Jazzy setup script exit on its optional unset `AMENT_TRACE_SETUP_FILES` variable. Removed nounset from `tools/run_n10_cancel_calibration.sh`; `errexit` and `pipefail` remain. No flight code, task parameter, collision behavior, health policy, or test window changed.

## Verification and result

The failed invocation stopped at ROS environment sourcing. An independent three-second PX4/bridge readback found DISABLED, landed, disarmed, control disabled and zero control samples. The run container then exited with code 0. No goal, enable request, arm or flight occurred; no measurement is counted.

The next fresh run is #359 under the already frozen 0.50–0.56 m/s trigger protocol. Evidence: [#358 setup failure](../evidence/n10-high-speed-cancel-stop-startup-failure-20261026-358.md).
