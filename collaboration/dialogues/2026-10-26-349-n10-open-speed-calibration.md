# #349 N10.3 open-speed calibration

- Goal: continue the user-authorized N10 completion sequence, currently N10.3.
- User constraint: remove the project's extra speed protections; speed telemetry is observation-only. Keep the official EGO planner's own dynamics model and the other agreed navigation/identity/freshness/collision/bridge contracts.
- Prior state: #347 stopped at the old 0.12 m/s reference-speed guard. #348 removed the extra speed guards, rebuilt and passed the existing regression checks, without starting SITL.
- Decision: freeze a new first post-#348 calibration run at the existing 0.25 m/s/axis, 0.25 m/s²/axis, 1 m horizon candidate. Keep the 16 m ENU / +0.10 m / +0.20 rad target, 3 s dwell and 600 simulation-second ACTIVE hold. Record speed only.
- Pending: execute and independently evaluate one calibration flight, including truth/VIO, tracking, map/source age, contact and PX4 landed/disarmed/control-disabled evidence.


## #349 result and #350 next step

- #349 reached bridge ACTIVE with speed observation-only; it did not reach the 16 m goal. EGO aborted after full-curve planning failure around the cylinder at world X≈-4 m. Independent minimum target error was 13.910 m and forward progress 2.159 m.
- Recorded EGO/PX4 vector-speed maxima were 0.2411/0.2551 m/s; these did not trigger cancellation. The short VIO window and tracking result are retained as calibration observations, not as long-range qualification.
- Independent 6 s PX4/bridge readback confirmed LANDED/disarmed, control disabled and zero control samples; project stop and container exit were 0.
- #350 is frozen before SITL with only `planning_horizon_m` changed 1.0→5.0 m. The 16 m task, planner axis dynamics, and all other runtime rules remain fixed.
- User constraint persists: the extra numerical speed protections stay removed; speeds are observations only.
