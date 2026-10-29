# PX4 alignment-gate change build and regression (#369)

- Source change: removed the project-local 0.15 m translation / 0.15 rad yaw alignment discrepancy landing cutoff. Both computed errors remain available as diagnostics. Configuration no longer contains `alignment_max_drift_m` or `alignment_max_yaw_error_rad`.
- Focused command: `PYTHONPYCACHEPREFIX=/tmp/n10-pycache python3 -m py_compile src/own/uav_px4_bridge/uav_px4_bridge/px4_bridge_node.py tools/test_px4_bridge_fault_landing.py` — PASS.
- Project regression: `bash tools/project.sh test` — PASS, 415 unit tests, navigation adapter ROS integration, and official EGO navigation policy ROS integration.
- ROS build: `bash tools/project.sh build ros` — PASS, 17 packages including `uav_px4_bridge`.
- Runtime identity: `5c3cbe4d4621e7c520d323e80911a2fc0ce09ae040c22adbf313c2fc21e45c01` (665 files).
- Installed bridge executable SHA-256: `6b12e131f2776fbfe4a52a27eb3f194b7b77030d914e323e1e1f0362e0fc7606`.
- Installed bridge module SHA-256: `bad90f0eea2f6e6336f555add1d7431e9aa1d8d65b1b4746e4bbad1af5926e9f`.
- Structural check: `python3 tools/project_status.py` — PASS; `git diff --check` — PASS.
- Scope: SITL behavior is not yet verified; #369 remains a diagnostic run and N10 remains in progress.
