# N08 #318 downward-view descent profile

## Purpose

#312 completed the 180° rear turn and return at z=1 m, then locked during the first descent with neutral pitch. #317's turn at z=0.5 m also locked during the second yaw segment. #318 retains the demonstrated high-altitude turn and changes the camera pitch during the subsequent descent to −0.35 rad, a view angle used by previous rear-view scans.

## Profile contract

- Stages 0–13 are identical to the #312 `slow_return_slow_descent` profile, including the z=1 m rear turn and yaw return.
- At yaw 0 and z=1 m, pitch alone moves to −0.35 rad over 8 s.
- Keep yaw 0 and pitch −0.35 rad while descending 1→0.5 m over 12 s and 0.5→0 m over 7 s.
- At z=0, pitch alone resets to 0 over 8 s, then hold 5 s.
- Total: 19 stages, 478 simulated seconds, final target `[0, 0, 0, 0]`.
- All health, map, geometry, and admission thresholds remain unchanged.

## Static verification

- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tools.test_preflight_scan`: 49 passed.
- `python3 tools/project_status.py`: Structure/design PASS.
- Python compile using `/tmp/n08-pycache-318`, JSON parsing, profile joint-limit validation, shell syntax, and `git diff --check`: passed.

## Runtime result

Cold-start run `n08-cancel-highspeed-prescan-20261026-318` completed 14/19 stages. It failed at stage index 14, the pitch-only move from 0 to −0.35 rad at z=1 m, before either descent stage. The fresh same-epoch localization sample became `LOST` with `normalized_cost_exceeded` at cost 1.022938; its receipt age was 0.000048 s and source age 0.140 s. The final valid trace was z=1 m, yaw 0.0158 rad, pitch −0.1217 rad, cost 0.977689. This run does not determine whether pitch alone or accumulated scan history caused the crossing.

The initial N05 online/offline check agreed on `ground_plane_insufficient_raw_occupied_voxels`. No fixture-release admission, mission preflight, live geometry, goal, control enable, or braking test followed. The helper detached and removed the fixture and confirmed landed. A separate six-second PX4/bridge readback showed bridge DISABLED, control disabled, disarmed/landed, zero control-topic samples, and `vehicle_remained_disarmed=true`. Only this run's container was stopped; it exited 0. Full result and hashes: [#318 runtime refusal](n08-pitch-down-pre-descent-lockout-20261026-318.md) and [machine report](n08-pitch-down-pre-descent-lockout-20261026-318.json).

The next diagnostic keeps the #312 rear-view and yaw stages, returns to neutral pitch, and divides the same 1→0 m descent into 0.1 m movements with a two-second stationary dwell after each. Per-segment movement durations preserve the #312 rates. It tests whether pauses allow the localization cost to recover without changing any health or map threshold.
