# N10.3/#372 preflight result — planner configuration mismatch

## Result

#372 stopped before sending a navigation goal. `tools/project.sh sim` was started without `D435I_PLANNER_CONFIG`, so the stack loaded the default `config/components/mapping/ego_planner.json` (`max_vel=0.5`, `max_acc=0.8`). The frozen scenario requires `config/components/mapping/n10_horizon5_speed080_calibration.json` (`max_vel=0.8`, `max_acc=0.25`, horizon 5.0, `official_ego`). The frozen driver rejected this mismatch before any mission action.

No goal was sent, no obstacle was injected, no flight record was created, and the mission observers were not started. This is a launch-configuration failure, not an EGO/PX4 flight result and not an N10 pass.

## Safe stop

Independent readback showed bridge `DISABLED`, landed, disarmed, and control disabled; the vehicle remained disarmed and the control sample count was zero. The container was stopped after that readback.

## Correction

Start the replacement run with `D435I_PLANNER_CONFIG=config/components/mapping/n10_horizon5_speed080_calibration.json`. Preserve the #372 world, spawn, goal, EGO settings, dynamic-box trigger, observation targets, and thresholds. The next run is #373.

Machine-readable details and hashes: [JSON report](n10-preflight-launch-config-mismatch-20261027-372.json).
