# N08 #315 neutral-pitch yaw profile

## Purpose

This unarmed support-scan profile follows #314, where the pitch-only move at z≈0 passed but the subsequent yaw turn with pitch held at −0.35 rad exceeded the existing localization-health limit. #315 tests whether the low-height yaw turn is viable with neutral camera pitch while retaining a stationary rear-facing downward view.

## Profile contract

- Stages 0–12 are identical to the existing low-rear-view profile.
- At z=0, yaw turns 0→−π/2→−π at pitch 0 (12 s + 18 s).
- At stationary rear yaw, pitch changes alone to −0.35 rad over 8 s and is held for 4 s; pitch then resets alone to 0 over 8 s.
- Yaw returns −π→−π/2→0 at pitch 0 (12 s + 12 s).
- Total: 20 stages, 490 simulated seconds, final target `[0, 0, 0, 0]`.
- Health, map, geometry, and admission thresholds are unchanged.

## Static verification

- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tools.test_preflight_scan`: 46 passed.
- `python3 tools/project_status.py`: Structure/design PASS; this check does not qualify builds or SITL.
- Configuration and milestone JSON parsing, profile model-joint limits, shell syntax, and `git diff --check`: passed.

## Runtime result

The cold-start run `n08-cancel-highspeed-prescan-20261026-315` stopped at stage 14/20 with a localization health lockout; see [#315 runtime report](n08-neutral-pitch-yaw-lockout-20261026-315.md). The static profile result does not pass N08. The next task tests the same yaw sequence at z=0.5 m. Any eventual completed scan still requires same-identity online/offline N05 admission, read-only preflight, and live forward geometry before considering a one-way EGO cancellation run.
