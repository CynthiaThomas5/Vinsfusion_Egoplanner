# N10.3 source audit — project-local health gates

## Result

The N10 runtime path had remaining boolean health-state gates after numeric VINS, age, alignment, and curve gates were removed. The `LocalizationStatus.valid/TRACKING` checks in project navigation, flight runner, bridge, and preflight were project-authored, so they are now observational in N10. Invalid status no longer rejects an epoch-matched goal or triggers the bridge trajectory fault.

The project `DepthHealth` monitor and the 16-sampled-pixel minimum were also project-authored runtime gates. Standard VIO/EGO and debug-truth launch no longer start or subscribe to that monitor. The mapping adapter still checks epoch/body-frame identity, image encoding/dimensions/storage layout, increasing timestamps, finite odometry, and map reset identity. Correctly shaped depth images pass even when sampled pixels are all zero; the existing EGO invalid-depth behavior keeps such pixels unknown.

#373 exposed a report-only stale-key `KeyError`; that report field is now removed while measured receipt gaps remain.

## Retained behavior

Epoch/map/frame identity, message structure, timestamp monotonicity, ROS clock rollback handling, map reset acknowledgement, PX4 native preflight and EV fusion, unique PX4 bridge control ownership, EGO upstream collision semantics and its native depth/odometry watchdog remain active. The 0.1 m/s static takeoff check matches the official FAST Lab PX4CtrlFSM rule.

## Verification

`bash tools/project.sh build ros` passed all 17 packages. `bash tools/project.sh test` passed 415 unit tests, the navigation-adapter ROS integration (including a degraded/invalid status), and the official_ego ROS probe. Python compilation and `git diff --check` passed. This audit contains no SITL or flight evidence.

See the [JSON audit](n10-project-health-gate-audit-20261027-374.json).
