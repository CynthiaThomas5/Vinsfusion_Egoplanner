# #350 N10.3 horizon-5 calibration

- Goal: continue the user-authorized N10.1–N10.7 completion scope, currently N10.3.
- #349 result: speed protections were disabled and remained observation-only; EGO failed full-curve planning near the central cylinder after about 2.16 m forward progress. The vehicle landed/disarmed and the bridge was control-disabled before stop.
- Hypothesis: the 1 m EGO horizon put the local target within the inflated cylinder region. Change only `planning_horizon_m` to the repository default 5 m.
- Fixed: 0.25 m/s/axis and 0.25 m/s²/axis planner dynamics, inflation, spawn, +16 m/+0.10 m/+0.20 rad target, official_ego policy, PX4 bridge ownership, remaining freshness/contact/watchdog rules. Speed remains observation-only.
- Protocol was frozen against 656 runtime input hashes before SITL.
- Pending: run one calibration task, independently evaluate truth/VIO/tracking/map/contact/PX4 state and the 600 simulated-second ACTIVE hold.
