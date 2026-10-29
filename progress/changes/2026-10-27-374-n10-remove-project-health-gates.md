# N10.3/#374 source audit — remove remaining project health gates

## Scope

Follow the user instruction to search runtime source for project-added protections and remove those gates from the N10 execution path. Keep official PX4/EGO behavior and epoch/frame/time integrity.

## Changes

- Removed localization `valid/TRACKING` rejection and active abort from N10 navigation admission, task state, readiness, flight execution, and the bridge's `trajectory_fault` path. Keep the status as telemetry and preserve epoch identity.
- Disabled the custom `DepthHealth` gate in standard VIO/EGO and debug-truth launch and removed its adapter subscription/receipt prerequisite.
- Removed the project minimum-16-valid-pixel depth gate. Correctly laid-out frames are forwarded; invalid pixels remain unknown through EGO's existing invalid-depth patch. Frame, encoding, dimensions, buffer layout, finite odometry, epoch, and increasing timestamp checks remain.
- Fixed #373's stale age-threshold report reference, preserving receipt-gap observations.
- #374's prepared runtime was superseded before SITL; no container, run directory, goal, or flight was started for #374. The new candidate is #375.

## Verification

- `bash tools/project.sh build ros`: 17 ROS packages passed.
- `bash tools/project.sh test`: 415 unit tests, navigation-adapter ROS integration (with invalid/degraded same-epoch status), and official_ego ROS probe passed.
- Relevant Python compilation and `git diff --check` passed.
- No SITL/flight evidence is claimed for this source audit. See [source audit report](../evidence/n10-project-health-gate-audit-20261027-374.md).

## Next

Use #375's explicit planner-config environment and fresh runtime/tool hashes to rerun the frozen cylinder-observation diagnostic.
