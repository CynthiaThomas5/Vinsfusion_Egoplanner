# N08 #318 pitch-down scan result

- User authorized Goal completion mode for N08; continue until its exits pass or a concrete blocker is established. N07 passed evidence remains accepted and is not rerun.
- #318 ran only the disarmed support fixture. It completed 14/19 stages and entered the pitch-only movement to −0.35 rad at z=1 m. Before descent, same-epoch fresh localization became LOST with `normalized_cost_exceeded` (1.022938; receipt age 0.000048 s; source age 0.140 s).
- Initial N05 online/offline check matched and refused `ground_plane_insufficient_raw_occupied_voxels`. No post-release gate, mission preflight, geometry, goal, enable, flight, cancellation, or braking measurement was reached.
- Fixture removal and landing were verified. Independent 6 s readback showed DISABLED, disarmed/landed, zero control samples; #318 container exited 0.
- Keep all limits. #319 retains the successful #312 high-altitude rear scan and neutral view, then splits vertical descent into 0.1 m increments with two-second dwell per increment while preserving movement durations per segment. This tests whether small movement/settling steps avoid the prior cost crossing.
- If #319 reaches all stages, require same-identity release N05, current-area N05, read-only preflight and live forward-body geometry before the one-way goal/cancel task. Goal completion has no implicit return. N08 still needs controlled mode comparison, measured cancellation stop/hold and at least three same-version independent cold-start target runs, plus N05/N06 budget evidence.

Evidence: [#318 report](../../progress/evidence/n08-pitch-down-pre-descent-lockout-20261026-318.md). Profile preparation: [#318 change](../../progress/changes/2026-10-26-318-n08-pitch-down-descent-profile.md).
