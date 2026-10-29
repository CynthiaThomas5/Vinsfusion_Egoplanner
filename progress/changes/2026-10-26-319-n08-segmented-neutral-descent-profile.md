# #319 N08 segmented neutral-pitch descent diagnostic

## Change

Added a 35-stage support-scan profile that retains #312's completed rear-view and yaw-return prefix. It divides the 1→0 m neutral-pitch descent into ten 0.1 m moves and adds a two-second dwell after each. Each movement duration preserves the corresponding #312 segment rate. No localization, geometry, map, speed, tracking or admission threshold changed.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tools.test_preflight_scan`: 50 passed.
- `python3 tools/project_status.py`: Structure/design PASS.
- `bash -n tools/run_n05_preflight_layout.sh` and `git diff --check`: passed.
- #319 SITL ended after 12/35 stages during the second half of rear-yaw return. Fresh same-epoch localization crossed the unchanged normalized-cost limit (1.007907; source age 44 ms). The proposed segmented descent was not reached, so this run gives no result on that hypothesis. Initial N05 online/offline agreed on `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`; no mission or flight occurred. Fixture was detached/removed and landed; independent 6 s readback confirmed DISABLED, disarmed/landed and zero control samples. Container exit 0. See [runtime evidence](../evidence/n08-segmented-neutral-descent-yaw-lockout-20261026-319.md).

## Next

The next action is a read-only comparison of #312 and #319 around their identical yaw-return prefix, using source-matched VINS features, solver costs, bias, timestamps and normalized health. Choose a new scan only if this comparison supplies a discriminating cause and safe path; do not repeat the same profile or change thresholds.

Related result: [#318 pitch lockout](../evidence/n08-pitch-down-pre-descent-lockout-20261026-318.md). Profile contract: [#319 static report](../evidence/n08-segmented-neutral-descent-profile-20261026-319.md).
