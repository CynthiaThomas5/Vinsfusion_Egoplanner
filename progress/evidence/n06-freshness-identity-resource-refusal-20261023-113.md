# #113 N06.2.4 identity, freshness and bounded-query refusal matrix

**Scope:** Current EGO/plan_env component with synthetic depth in isolated ROS domain 102; no Gazebo, VINS, PX4, bridge, controller, `traj_server`, world truth or flight.

## Results

The three component scenarios passed. A wrong-epoch goal was rejected by the EGO callback with no curve or fault. A wrong-map goal reached the curve gate, which returned `map_id_mismatch` with zero occupancy queries. Raw sphere queries distinguished free, occupied, unknown, outside-map and invalid-radius results.

The active-map mutation failed closed with `full_curve_unknown`; the completed-hold mutation failed with `full_curve_terminal_hold_occupied`. After depth input stopped while clock and odometry continued, the active curve failed closed with `full_curve_occupancy_update_stale`; a subsequent blocked goal received `full_curve_depth_pose_gate_closed`. All three cases published zero late curves.

Current-source tests also exercised `query_too_large` and `sweep_too_large` bounds. Navigation-adapter integration rejected wrong identity, stale status, unavailable query service, query timeout, concurrent busy admission, late replies, and cancellation while a query was pending. These are component/interface tests, not actual-layout runs.

No `EMERGENCY_STOP` state transition or emergency-hold B-spline appeared in the stale-input case. The stale full-curve gate emitted keyed safety faults and suppressed later curves. This does not prove a physical hold. Source inspection also shows `checkCollisionCallback` runs `certifyLocalCurve` before it tests `getOdomDepthTimeout`; `queryReadiness` rejects the same timeout flag. The stale-depth emergency branch therefore remained unobserved in this single-threaded fixture. Keep emergency-stop/hold as an explicit open item.

## Verification and artifacts

- `bash tools/project.sh test` — pass: 251 unit tests plus navigation-adapter integration. Sphere query and full-curve tests included bounded-work cases.
- Current EGO component probe: active-map, completed-hold and stale-map scenarios all returned pass in ROS domain 102; `docker run --rm` cleanup confirmed.
- [Runner output](../../artifacts/runs/n06-20261023-safety-112/runner.log)
- Per-scenario result and planner logs: `artifacts/runs/n06-20261023-safety-112/{active-obstacle,completed-hold,stale-map}/`
- Machine report: [#113 JSON](n06-freshness-identity-resource-refusal-20261023-113.json), with SHA-256 values for each result and log.

## Limits and continuation

This closes the component/interface identity, stale-map, query-class and resource-bound refusal subitem. It does not close emergency hold behavior or convert synthetic component evidence into a layout result. N06 remains `in_progress`; next isolate the current emergency-stop/hold planner path without loosening the map, freshness or collision gates.
