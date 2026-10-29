# N10.3 #414 integrated-calibration result

## Outcome

Run `n10-20261028-414-speed040-yawcap010-map-trace-calibration` directly **FAILed**. The independent 3D/yaw arrival dwell failed; minimum true 3D position error was 8.2459 m against the unchanged 0.30 m position tolerance, with 3.0 simulated seconds required for joint dwell. The vehicle-contact evaluator recorded 39 prohibited contact events. The inter-solver-step clearance report is consequently `INSUFFICIENT_PROHIBITED_CONTACT`; its model-bound minimum reached zero at a cylinder.

The acceptance evaluator was bound to the runtime identity and added no runtime gate, but its overall result is `FAIL`. Raw map surface geometry, raw classification, and the v1 voxel trace passed for their captured scope. The covered trace interval matched 181 fusion events and 8,832 ROI updates without trace linkage mismatches. These passes do not offset the arrival/contact failures.

## Evidence limits and terminal state

Raw VIO absolute error, 10-second RPE, velocity error, map-source age, tracking-to-clearance budget, dynamic replanning, fault-exit calibration, and resource/queue acceptance were `INSUFFICIENT`. The snapshot was source-covered and identity-matched, but no map point-query archive was captured. This run does not establish the full N10 acceptance standard.

The run did reach a natural safe terminal: bridge `LANDED`, PX4 disarmed and land-detected, bridge control disabled, and zero control messages in the independent postflight readback. The project container was safe to stop. No emergency disarm was used.

## Machine-readable source records

The source run reports are retained under `artifacts/runs/n10-20261028-414-speed040-yawcap010-map-trace-calibration/`. Their hashes and the summarized metrics are recorded in [the machine-readable result](n10-integrated-calibration-result-20261028-414.json). This report is a recovery of the missing progress summary from already-archived outputs; it is not new flight evidence.
