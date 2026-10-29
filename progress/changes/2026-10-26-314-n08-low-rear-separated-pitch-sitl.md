# #314 N08 low-rear separated-pitch SITL result

## Change

Recorded the #314 cold-start support-scan outcome, independent PX4/bridge safety readback, and next discriminating N08 profile. A later profile audit corrected the original interpretation: stage 13 changed yaw and pitch together, and stage 14 continued yaw at fixed pitch. This did not isolate the axes. The next profile will place pitch adjustment at a stationary rear-facing pose and keep all yaw turns at neutral pitch.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tools.test_preflight_scan`: 45 passed for the #314 profile and existing scan profiles.
- `python3 tools/project_status.py`: Structure/design PASS.
- JSON parsing, shell syntax, joint-limit validation, and `git diff --check`: passed for the #314 profile.
- SITL `n08-cancel-highspeed-prescan-20261026-314`: refused at stage 14/19 when localization normalized cost reached 1.0025576068; no post-release N05, preflight, geometry, goal, or flight was run.
- Independent six-second live readback confirmed bridge disabled, disarmed and landed state, and zero offboard control, trajectory-setpoint, and vehicle-command samples. `bash tools/project.sh stop n08-cancel-highspeed-prescan-20261026-314` stopped only this container; it exited 0.

## Evidence and limit

See [#314 evidence](../evidence/n08-low-rear-separated-yaw-lockout-20261026-314.md) and raw artifacts under `artifacts/runs/n08-cancel-highspeed-prescan-20261026-314/`. The result shows that a first combined yaw/pitch stage completed, while the subsequent low-height yaw continuation at fixed pitch −0.35 rad did not. It does not establish that neutral-pitch yaw will pass, and it provides no N08 flight or braking evidence.

## Next

Continue N08 as #315: keep the same low-height route, yaw with pitch 0, pitch only while stationary at the rear-facing pose, restore pitch 0, and return yaw with pitch 0. Preserve all acceptance gates and require the same-run post-release N05 and live geometry checks before any one-way EGO cancellation test.

Related dialogue: [#314 SITL result](../../collaboration/dialogues/2026-10-26-314-n08-low-rear-separated-pitch-sitl.md).
