# #343 N10.3 spawn geometry diagnostic

- User asked to complete N10 under the existing Goal completion scope N10.1–N10.7; continue until all N10 exits have evidence.
- #342's 16 m run failed before a READY curve: EGO reported the local terminal target was in an obstacle. A world-geometry inference links the first 2 m target to the inflated region of the cylinder near x=−4 m; the rejected coordinate was not logged.
- Decision: one fresh SITL run changes only the run-specific spawn x from −6.5 m to −8.0 m. Keep goal, planner candidate, official collision policy, 0.12 m/s guard and all other limits fixed. Record the effective pose and profile hash.
- The first launch was blocked before PX4 spawn by a relative resolver path after changing into the PX4 build directory. This was fixed and covered by a regression assertion; no armed or flight state occurred. The earlier run directory reuse refusal also happened before container creation.
- The repaired code passed 405 unit tests, navigation-adapter integration and official-policy ROS probe. The actual mission will use the fresh run ID ending in `-r01`; there is exactly one PX4 flight attempt under this protocol.
- No second camera, hardware flight, unrelated container operation, gate relaxation or repeated same-profile experiment is authorized or needed for this diagnostic.
- N10.3 remains open until long-range VIO/map support, clearance, tracking/braking speed, replanning latency and source-age metrics have quantitative evidence. N10.4–N10.7 remain required afterward.
