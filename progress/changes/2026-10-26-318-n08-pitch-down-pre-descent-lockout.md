# #318 N08 pitch-down scan runtime result

## Change

Recorded the failed cold-start result for the previously documented pitch-down profile. The scan stopped during a pitch-only stage before descent after a fresh same-epoch `normalized_cost_exceeded` lockout. Fixture cleanup and independent PX4/bridge safety readback were confirmed. No health, geometry, or admission threshold changed.

Added a new bounded #319 scan profile. It retains #312's completed rear-view/yaw stages and neutral pitch, then divides the descent into 0.1 m steps with a two-second stationary dwell after each. Each movement keeps the corresponding #312 segment rate. The profile is intended to distinguish continuous-descent effects from a view-angle change.

## Verification

- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tools.test_preflight_scan`: 50 passed.
- `bash -n tools/run_n05_preflight_layout.sh`: passed.
- `git diff --check`: passed before documentation updates.
- #318 runtime: 14/19 stages; no descent or N08 mission; fixture removed; independent 6 s readback stayed disarmed with zero control samples; container exit 0.

## Next

Run #319 as an unarmed support scan. Continue to mission preflight and one-way N08 cancellation only if every support stage, fixture-release N05 admission, mission N05 admission, read-only preflight, and live forward geometry pass on the same run and identity.

Related evidence: [#318 result](../evidence/n08-pitch-down-pre-descent-lockout-20261026-318.md). Related profile contract: [#318 profile](../evidence/n08-pitch-down-descent-profile-20261026-318.md).
