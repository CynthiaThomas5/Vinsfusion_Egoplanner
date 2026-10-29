# N10.3/#373 — correct planner-profile launch invocation

## Scope

Repeat the #372 diagnostic with its frozen planner profile explicitly loaded. Do not change the mission, world, goal, planner values, thresholds, age-gate-removal patch, or observation design.

## Changes

- Preserved #372's failed no-flight preflight report and independent safe-stop readback.
- Created a new run package and protocol for #373.
- Bound #373 to `config/components/mapping/n10_horizon5_speed080_calibration.json` through `D435I_PLANNER_CONFIG`; updated the prepared driver/injector and tool hashes for the new run ID.

## Verification

- #372 launch manifest showed the wrong default profile (`max_vel=0.5`, `max_acc=0.8`); the frozen profile requires `0.8`, `0.25`, horizon `5.0`, and `official_ego`.
- #372 driver exited before goal submission; no `flight.json` or observer output exists.
- Independent readback: landed, disarmed, control disabled, zero control samples; container stopped.
- #373 is prepared, not yet run. Protocol and prelaunch identities are recorded in `progress/evidence/n10-live-obstacle-age-gates-removed-cylinder0-protocol-20261027-373.json` and `...prelaunch-20261027-373.json`.

## Next

Start #373 with the required planner-config environment override; preserve the entire run and evaluate the result before deciding the next N10.3 subtask.
