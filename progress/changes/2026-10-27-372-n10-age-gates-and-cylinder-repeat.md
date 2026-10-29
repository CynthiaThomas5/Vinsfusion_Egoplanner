# N10.3/#372 — remove project-added age gates and correct cylinder observation

## Scope

Continue the user-authorized N10 Goal completion. Keep the existing mission, world, EGO profile, dynamic box, trigger, and acceptance thresholds fixed. Audit the active path for project-added freshness/health gates; remove those numeric gates when they are not part of upstream PX4/EGO behavior. Preserve evidence and failures from #371.

## Changes

- Removed the remaining project-local receipt/source-age and 5-second stability gates from N10 preflight and the EGO flight runner. Raw telemetry ages remain in diagnostics. Current PX4 state, external-vision fusion, no-GNSS state, VINS epoch, map identity, and PX4's own preflight remain checked.
- Added EGO patch `0054-remove-project-map-age-refusals.patch` to remove the project-added occupancy-update and depth-source age cutoffs from map-query readiness. Query responses retain their timestamps; EGO's upstream depth/odometry watchdog and inflated-occupied collision handling remain active. Registered the patch and resulting source hash in `dependencies/sources.json` and the EGO patch README.
- Removed the stale-source expectation from the ROS adapter regression: an old reported source/fusion timestamp with valid identity and classification is now expected to forward to EGO; unknown, occupied, identity mismatch, timeout, and cancellation behavior remain covered.
- Prepared #372 with read-only instrumentation aimed at `unit_cylinder_0`, the actual #371 contact. Its occupancy query center is derived from the approaching EGO command and lies on the cylinder-facing surface. The prior one-sim-second diagnostic auto-cancel on missing replacement spline is now log-only; native EGO/PX4 behavior and the outer goal timeout decide the result.
- Kept the 0.1 m/s static takeoff condition: the official ZJU-FAST-Lab Fast-Drone-250 `PX4CtrlFSM.cpp` explicitly rejects AUTO_TAKEOFF above this speed. This is an upstream rule, not a project-added health gate.

## Verification

- `PYTHONPYCACHEPREFIX=/tmp/n10-pycache-372 python3 -m py_compile tools/check_navigation_ready.py tools/run_vio_ego_flight.py artifacts/n10-prepared/n10-20261027-372-gatefree-cylinder0-observation/n10_live_obstacle_injector.py` — passed.
- `bash -n tools/run_n10_cancel_calibration.sh artifacts/n10-prepared/n10-20261027-372-gatefree-cylinder0-observation/n10-runtime-driver.sh` — passed.
- Patch 0054 dry-run/apply against the previous `grid_map.cpp` content — passed; reconstructed source SHA matches `dependencies/sources.json`.
- `bash tools/project.sh build ros` — 17 packages passed. `plan_env` emitted existing ROS `ConstPtr` deprecation warnings.
- `bash tools/project.sh test` — 413 unit tests passed, navigation-adapter ROS integration passed, and the official_ego ROS policy probe passed.
- The #372 runtime contract is frozen at `ff7ccf032737fd31b77ccbc2015590ef846b159a5b320ef87b720a51ed86075c` (665 files). This is a prelaunch identity, not flight evidence.

## #371 disposition and next step

#371 is a failed diagnostic: the box was inserted and a replacement spline was observed, but rotor 2 contacted `unit_cylinder_0`; the added cylinder observer instead watched `unit_cylinder_4`, leaving no encounter-level camera, occupied-cloud, or map-query evidence. The action ended after `external_odometry_stale`. The independent stop readback confirmed landed, disarmed, control disabled, and zero control samples. See [#371 result](../evidence/n10-live-obstacle-cylinder-observation-result-20261027-371.md).

At preparation time, #372 was frozen with no goal sent and was awaiting runtime/service/contact-sensor preflight. Its subsequent launch attempt stopped on the planner-configuration mismatch documented below. N10.3 and parent N10 remain `in_progress`.

Dialogue summary: [2026-10-27 N10 age-gate removal and cylinder repeat](../../collaboration/dialogues/2026-10-27-372-n10-age-gate-removal-and-cylinder-repeat.md).


## #372 runtime attempt

- The frozen driver stopped before goal submission because the container was started without `D435I_PLANNER_CONFIG`; the loaded default planner was 0.5 m/s and 0.8 m/s², while the protocol requires the N10 calibration profile at 0.8 m/s and 0.25 m/s².
- No goal, obstacle injection, or mission observation began. The independent PX4/bridge readback confirmed DISABLED, landed, disarmed, control disabled, and zero control samples; the container was then stopped.
- Result: [#372 launch mismatch report](../evidence/n10-preflight-launch-config-mismatch-20261027-372.md). The failure is retained and does not count as a flight result.
- Correction: start #373 with the protocol's explicit `D435I_PLANNER_CONFIG` environment override. Mission geometry, planner values, thresholds, and age-gate-removal patch are unchanged.
