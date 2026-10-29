# #350 N10.3 horizon-5 calibration protocol freeze

Created the N10-only profile `n10_horizon5_speed025_calibration.json`, changing the EGO local planning horizon from 1.0 m to the repository default 5.0 m. Max velocity and acceleration per axis, inflation, spawn, goal, speed-observation-only behavior and remaining runtime rules are fixed to #349.

Captured a 656-file prelaunch runtime contract (`57a94ad15861ad36ad95f9cbab31143e9b6449d37624bb10cf79f5b7be26364c`) and froze the single-variable hypothesis and full 16 m/3D/yaw/600 simulation-second task before starting SITL. This is a diagnostic calibration run, not qualification and not a relaxed acceptance criterion. See [protocol](../evidence/n10-horizon5-open-speed-16m-protocol-20261026-350.md) and [prelaunch input manifest](../evidence/n10-horizon5-open-speed-16m-runtime-contract-prelaunch-20261026-350.json).
