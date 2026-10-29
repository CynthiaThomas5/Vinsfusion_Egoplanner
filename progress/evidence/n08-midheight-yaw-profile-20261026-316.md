# N08 #316 mid-height rear-turn profile

## Purpose

#312 completed a 180° rear turn at z=1 m but later locked during descent. #313–#315 completed the initial descent before turning, then locked during the second low-height yaw segment. #316 moves the same neutral-pitch yaw and stationary rear pitch-observation sequence to the existing intermediate height z=0.5 m. It tests altitude dependence while retaining the #315 yaw/pitch ordering.

## Profile contract

- Stages 0–12 are identical to #315 and complete the route back to z=0 at neutral yaw/pitch.
- Ascend to z=0.5 m at neutral yaw/pitch over 12 s.
- Turn yaw 0→−π/2→−π at pitch 0 (12 s + 18 s).
- At stationary rear yaw, pitch alone to −0.35 rad over 8 s and hold 4 s; restore pitch 0 over 8 s.
- Return yaw −π→−π/2→0 at z=0.5 m and pitch 0 (12 s + 12 s).
- Descend to z=0 over 12 s and hold 5 s.
- Total: 23 stages, 519 simulated seconds, final target `[0, 0, 0, 0]`.
- Acceptance thresholds are unchanged.

## Static verification

- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tools.test_preflight_scan`: 47 passed.
- `python3 tools/project_status.py`: Structure/design PASS (no build or SITL qualification implied).
- JSON parsing, profile model-joint limits, shell syntax, and `git diff --check`: passed.

## Runtime status

Cold-start run `n08-cancel-highspeed-prescan-20261026-316` aborted before stage 0 on an unattributed localization gate; it does not test turn altitude. See [startup refusal](n08-midheight-profile-startup-refusal-20261026-316.md). Any N08 forward goal remains gated on full scan completion, fixture removal, same-identity post-release N05 online/offline admission, read-only preflight, and live forward geometry.
