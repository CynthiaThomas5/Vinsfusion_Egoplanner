# N10 Goal completion — age gates and #372 diagnostic

## User intent and constraints

- Continue N10 through its planned exits, not stop after a single internal subtask.
- For protective checks such as health/freshness thresholds, inspect source ownership first and remove project-added gates under the user's authorization.
- Preserve prior passing evidence and all failures. Do not change N10 acceptance thresholds or claim N10 passed before all exits have evidence.
- Keep the single-D435i Gazebo/PX4 SITL scope and one PX4 control owner.

## Confirmed decisions

- The active N10 path still contained project-local map-query source/update-age cutoffs and PX4 telemetry age plus continuous-stability gates. These have been removed; the corresponding measurements remain observable.
- Retained epoch/map identity, ROS clock rollback, PX4 native preflight and external-vision fusion state, EGO's upstream depth/odometry watchdog, inflated-occupied collision behavior, and the single PX4 bridge control owner.
- Retained the 0.1 m/s takeoff-static condition because it appears in the official [Fast-Drone-250 PX4CtrlFSM.cpp](https://github.com/ZJU-FAST-Lab/Fast-Drone-250/blob/master/src/realflight_modules/px4ctrl/src/PX4CtrlFSM.cpp#L1622-L1660).
- #371 contacted `unit_cylinder_0` while its added observer watched `unit_cylinder_4`; that run cannot determine whether the actual cylinder was observed or entered the occupied map. Keep it failed and incomplete.
- #372 preserves the mission and targets `unit_cylinder_0` with read-only image, occupied-cloud, and map-query observation. The one-second custom auto-cancel on absent replanning is removed; that condition is logged only.

## Current state

- 17-package ROS build passed; 413 unit tests, navigation-adapter ROS integration, and official_ego ROS policy probe passed.
- #372 runtime/tool identity and protocol are frozen. Runtime and service preflight are still required before sending the goal.
- N10.3/#372 is active; N10 remains `in_progress`. No flight result or N10 pass is claimed.
