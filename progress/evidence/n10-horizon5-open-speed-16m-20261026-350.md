# N10.3 #350 horizon-5 calibration result

**Outcome: failed calibration sample; not qualification.** The frozen 5 m horizon was loaded by the actual launch (`max_vel=0.25`, `max_acc=0.25`, `planning_horizon=5.0`). The full EGO/PX4 path reached bridge ACTIVE and the 16 m goal was sent. EGO formed rebound candidates that route around the central cylinder, but its final-spline feasibility stage rejected them after three refinements. No READY position-command curve was emitted; none of the candidate speeds below were flown.

## What the test established

The first rejected candidate reported max absolute axis velocity `(0.354, 0.748, 0.066) m/s` and max absolute axis acceleration `(0.044, 0.120, 0.013) m/s²`, against EGO planner settings `0.25 m/s/axis` and `0.25 m/s²/axis`. The next two refinements reduced but did not bring velocity below the configured per-axis value; their velocity ratios were 2.111 and 2.398. Acceleration stayed below 0.25 m/s²/axis. The planner then logged `Full-curve safety rejected: planning_failed`. This identifies the active parameter relationship: the configured EGO velocity is used by the planner to establish whether its proposed curve is dynamically feasible. It is not an external PX4/runtime speed cancellation guard. The additional runtime and cancel-stop numerical speed guards remain disabled as requested.

The 0.748 m/s value is an optimizer candidate from a curve that EGO rejected. It is **not** an achieved or measured flight speed. PX4 measured peak speed in the two goal-window samples was only 0.05790 m/s; no EGO READY command samples existed. The run had 0 m forward progress after goal dispatch, minimum truth target error 15.999 m, no arrival dwell, no 600 s ACTIVE hold and no braking-distance measurement.

## Other evidence and cleanup

- Preflight passed for 40.002 s; RTF 0.9119; max optimized-odometry receipt gap 0.09891 s, with zero samples over the existing 0.3 s guard. Official EGO takeoff admission passed at static odometry speed 0.000143 m/s.
- Raw VIO PRESTREAM-to-LANDED evaluation covered 28.584 simulated seconds and 1.821 m paired path (including takeoff/landing): position RMSE 0.01916 m, p95 0.03933 m, max 0.04457 m; absolute yaw RMSE 0.1336°, p95 0.2852°, max 0.3131°. This is not a long-range drift qualification.
- Tracking error is unmeasurable: zero matching READY position commands. Goal-window map source/occupancy ages peaked at 0.160/0.116 simulated seconds in the short record.
- Contact evaluation passed with zero prohibited contacts. Independent 6 s postflight readback confirmed `LANDED`, disarmed, bridge control disabled and zero control samples. `project.sh stop` returned 0 and the container exited 0; unrelated containers were preserved.
- Full measurement report: [`n10-calibration-evaluation.json`](../../artifacts/runs/n10-20261026-350-horizon5-open-speed-16m/n10-calibration-evaluation.json), runtime contract SHA-256 `57a94ad15861ad36ad95f9cbab31143e9b6449d37624bb10cf79f5b7be26364c` (656 files). Effective launch parameters are recorded in [`launch-manifest.json`](../../artifacts/runs/n10-20261026-350-horizon5-open-speed-16m-stack/launch-manifest.json).

## Next calibration step

#351 is frozen to change only EGO's `max_velocity_m_s` planner parameter from 0.25 to 0.8 m/s per axis, rounding the observed rejected candidate peak of 0.747555 m/s upward. Keep horizon 5.0 m, acceleration 0.25 m/s²/axis, spawn, target, collision policy and every runtime check fixed. Runtime EGO/PX4 speed remains observation-only. This is an evidence-based planner setting test, not a new runtime speed guard or a changed acceptance threshold.

Structured values and hashes are in [the #350 result JSON](n10-horizon5-open-speed-16m-20261026-350.json); raw logs remain under [`artifacts/runs/n10-20261026-350-horizon5-open-speed-16m`](../../artifacts/runs/n10-20261026-350-horizon5-open-speed-16m/).
