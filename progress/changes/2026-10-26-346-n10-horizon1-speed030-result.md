# #346 N10.3 speed feasibility reduction result

## Change and verification

- Added `config/components/mapping/n10_horizon1_speed030_calibration.json`, changing only operational planner `max_velocity_m_s` from #345’s 0.32 to 0.30m/s/axis. Horizon remained 1.0m; no source or installed binary change.
- Protocol: `progress/evidence/n10-horizon1-speed030-protocol-20261026-346.md`; result: `progress/evidence/n10-horizon1-speed030-20261026-346.md` and `.json`. Reused #344's 405-test/integration evidence. JSON/hash/field checks and `git diff --check` passed.
- One fresh SITL run: preflight, takeoff admission and EGO graph passed.

## Outcome

- EGO final spline passed after two refinements, x derivative-control point max 0.314555m/s under its 0.315m/s per-axis feasibility gate.
- The unchanged 0.12m/s reference guard tripped at 0.120738m/s after 0.896 sim-s; EGO reference peak 0.124502m/s and PX4 measured peak 0.062623m/s. Native goal failed, minimum independent true goal error 15.99589m, no dwell/600s hold or braking distance.
- Short VIO, contact, refusal and independent landed/disarmed/bridge-control-off evidence passed. The project container stopped exit 0.

## Next action

The expected inverse time-reallocation relation did not hold for the measured reference. Stop small `max_velocity_m_s` scans. N10.3 next inspects the command-to-bridge interface and accepted N08 stop envelope to define one new evidence-driven action without removing or raising the 0.12m/s guard.
