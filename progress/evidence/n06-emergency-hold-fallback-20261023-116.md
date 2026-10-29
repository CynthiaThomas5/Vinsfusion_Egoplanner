# #116 N06.2.5 emergency hold and N06.2.6 current-version layout verification

**Scope:** Patched EGO/plan_env planner admission and hold certification, isolated fault-injection components, plus actual Gazebo + D435i + VINS + plan_env/EGO map and curve certificates in corridor and wall layouts. No PX4, bridge, controller, traj_server, navigation supervisor, control publisher, or trajectory execution.

## Result

Patch 0043 fixes the emergency-hold branch for map-blocked active curves. When active-curve certification reports raw occupied, unknown, outside-map, or terminal-hold map obstruction, EGO enters EMERGENCY_STOP and attempts a stationary spline. The existing emergency-hold path must still pass current freshness, epoch/map/frame identity, raw body and terminal-hold certificates before publishing. Other failures, including stale input, identity mismatch, invalid query, and query/resource failure, remain fail-closed through stopForSafety.

The component probes exercised both outcomes. With an active-path obstacle at x=3.4 m and a raw-free hold at x=2.0 m, EGO entered EMERGENCY_STOP, published hold trajectory ID 3 after a two-query free hold certificate, and emitted no later curve. With the obstacle at x=1.5 m, the hold volume was unknown: EGO entered EMERGENCY_STOP, rejected the hold with full_curve_unknown, emitted no hold spline, and produced no late curve. After an already completed curve, a new terminal-hold obstacle also triggered EMERGENCY_STOP and a certified constant-position spline. A stale-map run remained fail-closed with full_curve_occupancy_update_stale and full_curve_depth_pose_gate_closed; it did not claim an emergency hold.

Current-patch actual-layout verification passed in both required layouts:

| Run | Layout and goal | Map certificate | EGO result | Scope |
| --- | --- | --- | --- | --- |
| #123 | corridor_box_column, +0.25 m y | Three source-matched snapshots; live body sphere, 10/10 continuous-sweep queries, and terminal hold raw-free | One curve; 22 full-curve queries, 0.219 ms, reason=free | Planner-only; no control graph |
| #122 | wall_box_column, +0.6 m then +0.9 m y | Three source-matched snapshots pass for both goals; live body/sweep/hold pass | Curves use 45 queries/0.544 ms and 61 queries/0.624 ms; FSM records EXEC_TRAJ to REPLAN_TRAJ to EXEC_TRAJ | Planner-only; no control graph |

Both runs used the same current source and patch hashes. Each reported stable epoch/map/frame identity, ready MapStatus, and source/fusion/odometry ages below the unchanged 0.4 s limit. Snapshot body, full-body continuous sweep, and terminal-hold checks had zero unknown and occupied cells. The planner curves were emitted only for diagnosis and were not executed.

The separate #121 corridor attempt at +0.6 m y was correctly rejected: the body sphere was free, but continuous sweep hit four raw occupied cells at 0.175 s and the terminal-hold query also contained occupied/unknown cells. No goal curve was published. This is a useful actual-layout refusal, not a positive certificate.

## Planner entry conditions recorded for later calibration

A planner goal is eligible only when MapStatus is ready and reset-acknowledged; goal, VINS pose, map, frame and epoch agree; source, fusion and optimized odometry ages are each at most 0.4 s; the configured full-body sphere is raw-free; the entire configured-speed swept body volume and terminal hold are raw-free; and all bounded occupancy queries complete within their resource limits. Emergency hold publication repeats the current-map freshness, identity, body and terminal-hold checks. Failure suppresses the curve/hold publication.

These are planner admission conditions for later controlled calibration. They do not certify takeoff, physical stopping distance, dynamic braking, PX4 behavior, or flight. N08 owns braking measurement; N05's takeoff/landing no-go boundary remains in force.

## Verification and artifacts

- Clean EGO package build: colcon build --base-paths src/vendor/ego_planner/planner --packages-select ego_planner --cmake-clean-cache --cmake-args -DCMAKE_BUILD_TYPE=Release — pass.
- Locked-source patch replay: python3 tools/fetch_dependencies.py --source ego_planner --target /tmp/ego-planner-n06-0043-replay — pass; all ordered patches applied and final source hashes verified.
- Project regression: bash tools/project.sh test — pass, 251 tests plus navigation-adapter integration, including bounded query/sweep, wrong identity, stale, timeout, late reply, cancellation and busy cases.
- #116 active obstacle/free hold, #118 blocked hold, #119 stale map, and #120 completed-curve terminal hold all ran in isolated EGO/plan_env components. Their structured result and planner-log hashes are in the machine summary.
- #121, #122 and #123 used bash tools/run_n04_map_layout.sh with motion_n06 profiles; every run exited 0 and its project container was cleaned up. The two passing runs had no forbidden graph nodes or control topics. Only unrelated containers remained afterward.
- python3 tools/project_status.py — pass (structure/design only; this is not a ROS build or SITL result).
- bash -n tools/run_n04_map_layout.sh tools/run_n04_map_layout_container.sh, JSON parsing, Python AST parsing, and git diff --check — pass.
- Docker cleanup check — the run containers exited; only the unrelated volant-height-route-probe and natfrp-service containers remained.

## Parent result and limits

N06's original planner-level exits are covered: two actual layouts with matching raw occupancy snapshots and full-body sweeps; active-obstacle, terminal-hold, stale/identity/query/resource refusal; zero late curves after faults; replan handoff; and measured query/time costs. N06 is passed at the planner integration scope. P6/S4 and the A–H final acceptance remain in progress. No trajectory was executed, so dynamic stopping remains unproven and is deferred to N08. N05's no-go diagnosis still does not authorize takeoff or flight.
