# 2026-10-26 #353 N10 upstream spline and follow-up

## User constraints and decisions

- User authorized removing the extra check that rejects a complete EGO curve, then continuing N10.
- Active EGO patch 0044 was removed; upstream single feasibility check and one time-reallocation/refinement attempt remain.
- Speed protection added by the project remains removed as previously authorized; EGO/PX4 speed telemetry is observation-only.
- The project localization health gate remains unchanged. Its configured normalized-cost limit is provisional, and no evidence currently supports widening it.
- Work is limited to single-D435i Gazebo/PX4 SITL; no real hardware or unrelated containers.

## #353 result

EGO emitted 26 B-splines and the PX4 bridge executed 1,071 READY position commands. Observed PX4 speed peaked at 0.859 m/s. The task aborted after 9.4 simulated seconds because the project localization adapter latched normalized_cost_exceeded at 1.007707962 versus configured 1.0. No target arrival, dwell, long hold, or controlled braking measurement was obtained. Independent PX4/bridge readback confirmed landed/disarmed, control disabled and zero control samples before stopping the project container.

The VINS solver provides cost/residual telemetry; the project's uav_localization adapter computes and enforces the threshold. VINS diagnostics do not abort EGO by themselves.

## Next step

Freeze #354 with one variable: EGO planner max velocity 1.2 to 0.8 m/s/axis. Keep acceleration 0.25 m/s²/axis, horizon 5 m, route, task, health policy and all other gates unchanged. Measure actual speed, command tracking, residual cost, goal progress and, only if arrival is achieved, dwell/hold/braking. Preserve the health lockout.
