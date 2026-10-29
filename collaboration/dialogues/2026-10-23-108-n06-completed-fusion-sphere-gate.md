# N06.10 r33 completed-fusion sphere gate

## Scope

- User resumed the existing Goal-completion task with `codex resume --last`.
- Authorized scope remains N06; do not advance to N07 until every N06 exit has evidence.
- Single D435i simulation and planner-only EGO diagnostics. No PX4, bridge, control, flight, truth feedback, or changes to N05 thresholds.

## Decision

r32 showed a ready, fresh map status while the read-only sphere service rejected `no_fresh_fused_depth`. Source inspection found that the sphere service required no pending map update while the existing full-curve certifier explicitly reads the last completed fusion. Patch only that readiness argument. Keep all identity, freshness, pose, frame, and raw occupancy checks. Extend the recorded-input window to 160 wall seconds because r32's third snapshot source stamp exceeded its recorded pose window by 4.191 seconds; leave the r32 motion and candidate target unchanged.

## Result

r33 matched all three fused-depth source stamps to one camera pose each. Snapshot and live body/sweep/hold checks were raw free. EGO logged a 22-query `reason=free` full-curve certificate and generated one planner-only B-spline. No planner fault or control publisher was observed. The exact request-time pending flag was not recorded, so r32's pending-gate explanation remains an inference.

## Next

Continue N06.2 with the other actual layout using the same strict snapshot and live certificate gates. N06/S4 remain in progress; preserve the original two-layout, hold, handoff, freshness/identity, resource, and refusal exits.
