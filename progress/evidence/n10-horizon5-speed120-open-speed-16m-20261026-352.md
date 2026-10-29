# N10.3 #352 horizon-5 speed-1.2 calibration result

**Outcome: failed calibration sample; not qualification.** The frozen profile loaded EGO `max_vel=1.2 m/s/axis`, `max_acc=0.25 m/s²/axis`, horizon `5.0 m`. Preflight and takeoff admission passed. The +16 m goal was accepted, then EGO aborted after `0.072` simulated seconds with `planner_full_curve_planning_failed`. No target arrival, dwell, 600 s ACTIVE hold, or braking measurement occurred.

## What blocked the curve

The read-only EGO diagnostics logged a maximum candidate control-point velocity bound of `1.300 m/s/axis` and acceleration bound of `1.200 m/s²/axis`; maximum normalized ratio was `2.200`. These are conservative control-point derivative bounds, not achieved flight speeds. The project-added 0044 loop repeatedly refined and rechecked candidate curves, then rejected them after three refinements. The PX4 speed observer recorded only `0.04761 m/s` from 3 samples during the short run; this does not measure the rejected curve.

Independent truth measured minimum target error `15.999 m`, with zero continuous dwell. No matching READY trajectory command was available for tracking evaluation. Contact assessment found 0 prohibited contacts. Six seconds of independent PX4/bridge readback confirmed disarmed, landed and zero control samples; the project container was stopped.

## Next step

Remove 0044's extra multi-pass final dynamics hard rejection and restore upstream's single feasibility check with one time-reallocation attempt. Keep the 1.2 m/s/axis, 0.25 m/s²/axis and 5 m-horizon profile fixed for the next run so the code-path change is the only experimental variable. The upstream routine still reports failure when its time-reallocation algorithm fails.

Raw measurements: [`n10-calibration-evaluation.json`](../../artifacts/runs/n10-20261026-352-horizon5-speed120-open-speed-16m/n10-calibration-evaluation.json). Full input hashes and candidate diagnostics: [result JSON](n10-horizon5-speed120-open-speed-16m-20261026-352.json). Frozen pre-run settings: [protocol](n10-horizon5-speed120-open-speed-16m-protocol-20261026-352.md).
