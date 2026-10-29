# N10.3 horizon experiment retry protocol

#338 was not sampled: immediate ROS topic introspection returned Unknown topic before graph discovery and exited before runner startup. The wrapper now performs a bounded 10-second readiness retry and verifies the intended publisher/subscriber pair. #339 uses the same horizon=2 contrast and original 16 m + 600 sim-second hold conditions; only the preflight discovery race fix differs from #338.
