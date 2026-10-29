# N10.3 #415 preparation

The run tests only per-voxel trace serialization volume. It keeps #414's route, speed040 profile, 0.10 rad/s yaw-rate cap, exact trace ROI, spawn, goal, obstacle geometry/timing, sensor streams, contact model, collision behavior, and acceptance thresholds. The v2 trace preserves voxel indices, hit/miss votes, pre/post log odds, and pre/post class codes.

Preparation and 17-package incremental ROS build passed. No SITL session or flight goal has started. Before any goal, the run-local script will compare the live runtime contract, launch manifest, planner arguments, spawn, obstacle ROI, native PX4/bridge readback, and unique control graph.

The build and focused check details are in [build evidence](n10-integrated-calibration-build-20261028-415.md); the frozen candidate protocol is [here](n10-integrated-calibration-protocol-20261028-415.md).
