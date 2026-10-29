# #315 N08 neutral-pitch yaw diagnostic profile

## Change

Added an unarmed physical-support scan profile that keeps pitch neutral during both low-height yaw turns, adjusts pitch only at the stationary rear-facing pose, holds that view, then restores neutral pitch before returning yaw. The first 13 stages and all acceptance thresholds remain unchanged. Registered the profile with the runner and added a contract test.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tools.test_preflight_scan`: 46 passed.
- `python3 tools/project_status.py`: Structure/design PASS.
- JSON parsing, profile joint-limit validation, shell syntax, and `git diff --check`: passed.
- Cold-start SITL run `n08-cancel-highspeed-prescan-20261026-315` stopped at stage 14/20 with normalized-cost lockout; the runtime report records the safe readback. No post-release admission or mission followed.

## Limits and next step

This profile tested whether yaw movement at z≈0 can remain healthy with pitch 0; it did not. It provides no N05 release admission, planner geometry, trajectory execution, or braking evidence. #316 will repeat the same yaw sequence at z=0.5 m, then proceed through all same-identity post-release gates only if the scan succeeds.

Related dialogue: [#315 profile](../../collaboration/dialogues/2026-10-26-315-n08-neutral-pitch-yaw-profile.md).
