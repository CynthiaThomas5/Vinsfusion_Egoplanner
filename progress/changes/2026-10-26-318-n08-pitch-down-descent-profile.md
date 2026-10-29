# #318 N08 pitch-down descent diagnostic profile

## Change

Added a profile based on #312's high-altitude rear turn and return. After reaching neutral yaw at z=1 m, it pitches down alone to −0.35 rad, keeps that view through the existing 1→0.5→0 m descent, then resets pitch on the ground. The profile is registered with the fixture runner and host wrapper and has a contract test. No acceptance threshold changed.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tools.test_preflight_scan`: 49 passed.
- `python3 tools/project_status.py`: Structure/design PASS.
- Python compile, JSON parsing, joint limits, shell syntax, and `git diff --check`: passed.
- SITL run `n08-cancel-highspeed-prescan-20261026-318` completed 14/19 stages, then a fresh same-epoch `normalized_cost_exceeded` lockout occurred during the pitch-only stage before descent. Fixture removal, landed state and an independent disarmed/zero-control readback were confirmed; the container exited 0. See [runtime refusal evidence](../evidence/n08-pitch-down-pre-descent-lockout-20261026-318.md).

## Next

The next scan is #319, which retains the #312 neutral-pitch rear-view route and segments the final descent into 0.1 m steps with two-second settling holds. If it completes, require same-run fixture release, N05, read-only preflight and forward geometry before the one-way EGO cancellation task. A refused gate must not issue a goal or enable control.

Related dialogue: [#318 profile](../../collaboration/dialogues/2026-10-26-318-n08-pitch-down-descent-profile.md).
