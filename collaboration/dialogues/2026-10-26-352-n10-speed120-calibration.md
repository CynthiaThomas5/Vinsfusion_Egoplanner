# #352 N10.3 speed-parameter calibration

- Goal: continue the user-authorized N10 completion scope.
- #351 loaded EGO max velocity 0.8 m/s/axis and max acceleration 0.25 m/s²/axis. It still rejected all full curves; 178 logged feasibility summaries reached maxima 1.04976 m/s/axis and 0.78 m/s²/axis. The candidate curves were not executed.
- Change only EGO planner max velocity to 1.2 m/s/axis; keep acceleration, horizon, geometry, task and runtime gates unchanged.
- Additional runtime/cancel-stop speed guards remain removed; EGO/PX4 speed telemetry is observation-only.
- Protocol and 658-file input contract frozen before SITL.
- Pending: run and evaluate actual curve speed, full task outcome, independent VIO/map/contact and PX4 terminal state.
