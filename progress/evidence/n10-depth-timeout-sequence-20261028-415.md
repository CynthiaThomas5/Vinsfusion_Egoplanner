# N10.3 #415 depth-timeout sequence audit

This is a read-only correlation of the archived #415 `vio.log`, flight result, and depth-fusion trace. It identifies the proximate event sequence, not the root cause of the invalid quaternion.

1. At sim time 121.088 s, `localization_adapter` locked the epoch with reason `propagated_invalid_quaternion`. Its integrity snapshot references the last optimized pair at 120.980 s.
2. EGO's last recorded depth-pose synchronization remained count 3,408, last pair stamp 120.980 s, and last sync callback time 121.032 s. Its last occupancy update was 121.080 s.
3. At sim time 121.516 s, EGO reported `odom or depth lost`; the 0.436 s age since the last occupancy update exceeded its configured native 0.400 s timeout. EGO aborted the active goal with `depth_odom_timeout`; the trajectory server reported `planner_full_curve_depth_odom_timeout`.
4. The run's final action result is `aborted`, at estimated position `[10.14999, -6.16198, 2.01568]` ENU, far from the target.

This supports the proximal chain `propagated_invalid_quaternion` integrity lockout → no new valid EGO depth/pose fusion → native EGO depth/odometry timeout → task abort. The cause of the invalid quaternion itself is not identified. This audit does not show that trace serialization caused or fixed the fault, and it does not change any runtime threshold.

The flight fault did not safely terminate the PX4/bridge stack: independent postflight and later same-domain reads show bridge `LANDING` with armed PX4 failsafe `DESCEND`. The existing safe-closeout hold remains mandatory.

The selected source lines are preserved in `artifacts/runs/n10-20261028-415-speed040-yawcap010-compacttrace-calibration/n10-depth-timeout-sequence-source-extract.txt`; their source offsets, extract hash, and the stable `flight.json`/fusion-trace hashes are in [the machine-readable sequence](n10-depth-timeout-sequence-20261028-415.json). The live `vio.log` was not hashed as a fixed input because the control stack still appends to it.
