# #351 N10.3 speed-parameter calibration

- Goal: continue the user-authorized N10 completion scope, currently N10.3.
- #350 confirmed horizon 5 m but EGO rejected obstacle-around candidates because max axis velocity was 0.748 m/s against the planner's configured 0.25 m/s/axis. The candidate was not flown; actual PX4 goal-window peak was 0.0579 m/s before abort.
- Change only the EGO planner velocity-model parameter to 0.8 m/s/axis, rounded above the measured rejected candidate. Keep acceleration 0.25, horizon 5 m, geometry, target and runtime checks fixed.
- User constraint: no extra runtime or cancel-stop speed protections; speed telemetry is observation-only. The EGO max-velocity setting remains a planner trajectory parameter and is not used as a PX4 speed cancellation.
- Protocol and 657-file input contract frozen before SITL.
- Pending: execute one calibration task and measure the realized curve/actual speed, arrival, VIO, mapping, contact and PX4 terminal state.
