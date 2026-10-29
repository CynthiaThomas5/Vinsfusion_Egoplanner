# #345 N10.3 local-horizon diagnostic result

## Actual change and verification

- Added `config/components/mapping/n10_horizon1_speed032_calibration.json`, changing only operational `planning_horizon_m` from #344's 2.0 to 1.0m. Protocol: `progress/evidence/n10-horizon1-speed032-protocol-20261026-345.md`.
- JSON and one-variable comparison passed. `python3 tools/project_status.py` reported Structure/design check PASS (80 optional historical artifact links absent, pre-existing report); `git diff --check` passed. Source and installed binary were unchanged; reused #344's 405 unit tests, navigation-adapter integration and official-policy ROS probe.
- One fresh SITL mission after the stack-ready marker: preflight and official takeoff admission passed. An earlier call exited 10 before any goal/control because the marker had not yet appeared; it is recorded as startup synchronization, not a second mission run.

## Outcome

- EGO emitted a feasible first B-spline; x derivative-control-point maximum `0.328734m/s`, under the `.32×1.05=.336m/s` per-axis feasibility gate.
- Reference speed crossed the unchanged 0.12m/s guard at `0.120101m/s` after `0.792 sim-s`; maximum reference `0.123444m/s`, maximum PX4 measured speed `0.047868m/s`. The action canceled, leaving minimum independently measured true target error `15.99938m`, no dwell or 600s hold. A stationary-looking B-spline followed cancellation, but no braking evaluator produced a stopping-distance result.
- Short VIO, contact, live refusal, independent PX4/bridge landed/disarmed readback, and safe container shutdown are recorded in `progress/evidence/n10-horizon1-speed032-20261026-345.md` and `.json`.

## Next evidence action

The horizon change did not lower reference velocity below the existing guard. #346 changes only planner `max_velocity_m_s` from 0.32 to 0.30m/s/axis with horizon fixed at 1.0m. The new 0.315m/s feasibility gate is 0.013734m/s below the #345 x derivative-control-point maximum; estimated time stretch is 4.36%, a hypothesis only. Keep global goal, spawn, 0.12m/s guard and all acceptance/safety thresholds fixed.
