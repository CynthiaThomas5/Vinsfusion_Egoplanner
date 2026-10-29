# #345 N10.3 shorter local planning horizon protocol

## Actual change

- Added `config/components/mapping/n10_horizon1_speed032_calibration.json`. The only operational field changed from the #344 candidate is `planning_horizon_m`, from `2.0` to `1.0 m`; planner velocity remains `0.32 m/s/axis`, and every goal, safety limit, spawn, sensor and collision setting stays fixed.
- Added the pre-run frozen protocol in `progress/evidence/n10-horizon1-speed032-protocol-20261026-345.md` and `.json`.
- JSON parsing, a field-by-field one-variable comparison (excluding rationale/qualification prose), and `git diff --check` passed. No source or installed binary changed, so the #344 405-test/integration result is reused; no ROS/C++ rebuild was required.

## Basis and next step

#344 produced B-splines but tripped the unchanged 0.12 m/s reference guard at 0.120142 m/s. PX4 actual speed peaked at 0.085965 m/s; after cancellation, the planner refused an N08-calibrated stop curve and the bridge landed. The #345 hypothesis is that a 1 m local horizon lowers initial reference speed while repeated replanning still advances toward the full 16 m target.

The single frozen PX4/Gazebo run is `n10-20261026-345-horizon1-speed032`. Preserve any guard trip, planner refusal, map/freshness failure, or incomplete coverage. Do not alter limits or repeat an unchanged profile.
