# N10.3 #351 horizon-5 speed-0.8 calibration result

**Outcome: failed calibration sample; not qualification.** The frozen profile was loaded as intended: EGO max velocity 0.8 m/s/axis, max acceleration 0.25 m/s²/axis, horizon 5.0 m. PX4 reached ACTIVE and received the 16 m goal. EGO produced 178 logged final-spline feasibility summaries, but none passed; it aborted with `planner_full_curve_planning_failed` after 1.576 simulated seconds of goal wait. No goal arrival, dwell, 600 s ACTIVE hold or braking measurement occurred.

## Measured relationship between EGO parameters and candidate curves

Across the logged optimizer candidate summaries, the largest per-axis proposed velocity was 1.04976 m/s and largest per-axis proposed acceleration was 0.78 m/s². Both exceeded the loaded EGO dynamics parameters (0.8 m/s and 0.25 m/s² per axis). Those proposed curves were rejected and were not executed. This clarifies that EGO's `max_vel` and `max_acc` parameters affect final curve feasibility; they are separate from the extra project runtime/cancel-stop speed guards, which remained disabled.

The run contained 167 matching READY position-command samples, with fixed-SE(3) truth tracking median 0.03779 m, p95 0.07294 m, max 0.07778 m. These samples only cover the brief takeoff/initial response (command reference x span 0.044 m, z span 0.069 m); they do not measure the rejected obstacle-avoidance curve. The EGO/PX4 speed observation peaks were 0.08962/0.05028 m/s, not the candidate maxima. Independent truth minimum target error was 15.9994 m and forward world-X goal progress 0 m.

Raw VIO PRESTREAM-to-LANDED evaluation covered 30.076 simulated seconds and 1.958 m paired truth path including takeoff/landing: position RMSE 0.01538 m, p95 0.02830 m, max 0.03008 m; absolute yaw RMSE 0.1298°, p95 0.2519°, max 0.2727°. This is not a long-range drift qualification. Map source/occupancy ages peaked at 0.160/0.108 simulated seconds in the short window. Contact evaluation passed with zero prohibited contacts.

## Safe end state and next step

Independent 6 s PX4/bridge readback confirmed `LANDED`, disarmed, bridge control disabled and zero control samples. `project.sh stop` returned 0 and the container exited 0; unrelated containers were preserved.

#352 changes only the EGO max-velocity planner parameter from 0.8 to 1.2 m/s/axis, rounded above the measured rejected candidate peak of 1.04976 m/s. Keep the 0.25 m/s²/axis acceleration setting and 5 m horizon unchanged. This tests the velocity parameter alone; if acceleration remains the active feasibility limit, preserve that result and handle it as a separate evidence-based planner-parameter experiment. No runtime speed guard is added and no acceptance criterion changes.

Full measurements: [`n10-calibration-evaluation.json`](../../artifacts/runs/n10-20261026-351-horizon5-speed080-open-speed-16m/n10-calibration-evaluation.json). Runtime contract SHA-256 `f39082d77188f3d7682275adaf5a6e6328eb5437d7594b239fc9decc66013ea0` (657 files). Effective parameters and raw file hashes are listed in [the #351 result JSON](n10-horizon5-speed080-open-speed-16m-20261026-351.json).
