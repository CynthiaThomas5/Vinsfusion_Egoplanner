# #283 N05 scan stopped by accelerometer-bias health gate

The correct startup runtime manifest was captured, but no N08 mission ran. The initial raw-map N05 check refused because it did not yet contain enough ground support. The DISARMED support scan reached 9/15 stages, then localization became invalid with `accel_bias_norm_exceeded` during the return translation from about x=-2.4 m toward -1.2 m.

The first recorded accelerometer-bias norm above the unchanged 0.15 m/s² gate was 0.15006874 at sim time 314.196s; the recorded peak was 0.17927088 at 319.740s. VINS solver status remained usable and the last valid localization cost was about 0.513. The failure is specifically the accel-bias health gate, not the normalized-cost gate.

No post-release N05 admission, goal, enable, or flight was attempted. PX4 stayed disarmed, the support fixture was detached and absent, fresh landed status was recorded, and the project container was stopped. The N05 health threshold was not changed.
