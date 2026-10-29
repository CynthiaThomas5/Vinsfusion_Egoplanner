# N08 #319 profile decision

- #318 failed during pitch-only movement before descent. #312's rear scan and yaw return completed, but continuous neutral-pitch descent later crossed the existing localization-cost gate.
- #319 keeps #312's first 14 stages and neutral view. It divides the descent into ten 0.1 m movements, preserves the previous per-segment movement time, and inserts a two-second stationary dwell after each step. This tests whether pauses settle the localization estimate.
- All thresholds and flight geometry remain unchanged. Static validation passed: 50 profile tests, structural check, shell syntax and diff check.
- Next: run one cold unarmed scan. A failed stage or any N05/preflight/forward-geometry refusal means no goal or control enable. If all gates pass, the separate mission uses a one-way target with caller-cancel braking; no automatic return.

Evidence: [#319 profile](../../progress/evidence/n08-segmented-neutral-descent-profile-20261026-319.md); [#318 result](../../progress/evidence/n08-pitch-down-pre-descent-lockout-20261026-318.md).
