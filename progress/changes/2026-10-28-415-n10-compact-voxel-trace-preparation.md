# N10.3 #415 compact voxel trace preparation

Linked dialogue summary: `collaboration/dialogues/2026-10-28-415-n10-compact-voxel-trace.md`.

## Changes

- Added EGO patch 0059 and compact v2 decoder coverage for read-only per-voxel update traces.
- Prepared a run-specific #415 profile, protocol, prelaunch identity script, and runtime driver. ROI, route, speed040 values, 0.10 rad/s yaw cap, goal, spawn, obstacle, sensors, and acceptance configuration remain identical to #414.
- Added offline reporting changes that preserve direct FAIL/INSUFFICIENT results and do not synthesize completion windows or endpoints.

## Verification

`bash tools/project.sh build ros` passed 17/17 packages; focused tests passed 24/24; AST/shell/JSON syntax, `python3 tools/project_status.py`, and `git diff --check` passed. See `progress/evidence/n10-integrated-calibration-build-20261028-415.json`.

## Limits and next step

This is not the N10.5 clean ROS/PX4 rebuild and it is not a flight result. The next subtask is to start #415, verify its runtime identity and grounded terminal state before goal submission, then compare trace volume and full mission evidence against #414.
