# N10.3 #378 caller-cancel result

## Task and frozen conditions

One fresh PX4 SITL cancellation measurement at the evidence-selected actual horizontal speed window [0.60,0.66] m/s. Same runtime source/install SHA `b4707af345d1cd082dfb1cae3a24f24103134eedfce306205785b44342582ea7`, horizon5 / max_vel0.8 / max_acc0.25 official_ego planner, spawn [-8,0,0.3], +16m/+0.10m/+0.20rad goal, same stop-band and read-only observers.

## Result

Valid sample at PX4 horizontal 0.600867 m/s; EGO reference 0.628064 m/s. Caller cancellation was acknowledged in 0.000938 wall seconds; new trajectory id 96 appeared 0.092 simulated seconds later. PX4 entered the defined stop band 4.844 simulated seconds after cancel and confirmed 1.02 simulated seconds of dwell with 52 samples and a 0.028 second maximum gap. Truth horizontal path length to band entry was 1.376716 m; horizontal endpoint displacement 1.152746 m; truth max sample gap 0.020 seconds. Contact evaluation passed with zero prohibited contacts. Independent final readback confirmed LANDED, disarmed, control disabled, zero-control, and container stopped safely.

The same flight provided raw VINS diagnostics over 65.984 simulated seconds and 18.793 m truth path: position RMSE/P95/max 0.0415/0.0658/0.0733 m; yaw RMSE/P95/max 0.2399/0.4621/0.4926 degrees. One fixed scale-1 SE(3) transform was applied once before takeoff. These are not yet acceptance limits.

## Limits and next work

This is one complete sample, not a distribution or general stopping guarantee. N10.3 still needs same-runtime repeatability and evidence synthesis for localization/map errors, clearance, replanning, fault exit behavior and the supported scope. Then continue N10.4–N10.7. N10 remains `in_progress`.
