# N08 #316 mid-height profile startup refusal

## Result and scope

Cold-start run `n08-cancel-highspeed-prescan-20261026-316` launched with the planned z=0.5 m rear-turn profile, but completed **0 of 23 stages**. The support-scan helper aborted before the first stage command with the generic error `localization changed or became invalid during physical scan`. Its final captured localization record was TRACKING/valid with normalized cost 0.084701, so the failing-time condition is not recorded. The exact stale/state/epoch predicate is unknown. This is a pre-stage helper health refusal and supplies no evidence for or against the z=0.5 m yaw hypothesis.

The initial N05 online/offline result was identical and refused `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`. No support movement stage, fixture-release N05, read-only preflight, live geometry, mission, or flight occurred.

## Safe end state

The helper verified fixture detachment, model removal, and landed state. A separate six-second readback reported bridge `DISABLED`, control disabled, PX4 arming state 1 (disarmed), landed, and zero offboard-control-mode, trajectory-setpoint, and vehicle-command samples. The run container was stopped via `tools/project.sh stop` and exited 0. No goal or enable command was issued.

## Evidence

- Run: `artifacts/runs/n08-cancel-highspeed-prescan-20261026-316/`
- Summary and empty stage list: `fixture-result.json`, `fixture-stages.json`
- Initial same-run N05: `n05-before/n05-live-entry-check.json`
- Independent safety readback: `post-scan-independent-live-readback.json`
- The final localization record is preserved in `fixture-result.json`; the rejected sample's predicate fields were not captured.

## Next action

Add diagnostic fields to the existing fail-closed localization check (state, valid flag, epoch match, receipt age, and freshness limit) without changing its predicate or threshold. Add focused tests for the diagnostic classification, then repeat the same z=0.5 m profile in a new cold start. Only that result can test turn altitude.
