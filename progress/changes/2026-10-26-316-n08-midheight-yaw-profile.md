# #316 N08 mid-height rear-turn diagnostic profile

## Change

Added a support-scan variant that retains the #315 stages and yaw/pitch order, climbs from z=0 to the existing intermediate level z=0.5 m, performs the rear yaw and stationary pitch observation there, returns yaw at neutral pitch, and descends at neutral yaw/pitch. Registered the profile with the fixture runner and host wrapper, and added a profile-contract test. No thresholds changed.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tools.test_preflight_scan`: 47 passed.
- `python3 tools/project_status.py`: Structure/design PASS.
- JSON parsing, joint-limit validation, shell syntax, and `git diff --check`: passed.
- SITL `n08-cancel-highspeed-prescan-20261026-316` aborted before stage 0 on an unattributed localization-gate failure. It did not test the altitude variable; see [startup-refusal evidence](../evidence/n08-midheight-profile-startup-refusal-20261026-316.md).

## Next

Instrument the unchanged health refusal with the failed predicate values and rerun the same cold-start profile. Only a full scan and same-identity post-release N05/preflight/forward-geometry pass can unlock a one-way forward motion-cancel mission.

Related dialogue: [#316 profile](../../collaboration/dialogues/2026-10-26-316-n08-midheight-yaw-profile.md).
