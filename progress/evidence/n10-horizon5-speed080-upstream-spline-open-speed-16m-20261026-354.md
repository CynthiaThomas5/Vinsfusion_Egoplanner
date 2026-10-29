# N10.3 #354 upstream spline, speed-0.8 result

**Outcome: failed calibration sample; not qualification.** The planner profile was loaded at max velocity 0.8 m/s per axis, max acceleration 0.25 m/s² per axis, and 5 m horizon. Runtime contract matched #353 exactly: 658 files, SHA-256 304c2f8551172d95813fbdeb62f2c7aa68f57cfbf467c90bce71dee18db58591.

## Flight and measurements

The PX4 vehicle reached a minimum true 3D goal error of 0.06099 m and progressed 15.972 m forward. The longest continuous true-position dwell was 2.085 s, short of the required 3 s. The navigation action aborted on localization normalized cost 1.08530 above the unchanged provisional 1.0 setting. No 600 s ACTIVE hold or controlled braking measurement occurred.

Observed vector-speed peaks were 0.678 m/s for EGO position-command references and 0.610 m/s for PX4 local-position telemetry. The fixed preflight-alignment command-to-truth-IMU error was median 0.568 m, p95 0.627 m, maximum 0.709 m.

Compared with #353 on the same source/runtime contract and route, #354's lower planner parameter coincided with lower measured EGO/PX4 vector speed, reduced p95 tracking error (0.942 to 0.627 m), and progress closer to the target (5.191 to 15.972 m). This single pair supports a relationship between the planner setting and measured motion but does not establish a final speed or acceptance limit.

Raw VIO over the recorded pre-enable interval had RMSE 0.02125 m, p95 0.04090 m, and maximum 0.04571 m. Contact evaluation found zero prohibited contacts. Independent 6 s PX4/bridge readback confirmed LANDED, disarmed, control disabled, and zero control samples; the project container then stopped with exit code 0.

## Next step

The user requested disabling all health gate limits and continuing. Preserve this #354 failure and its original 1.0 threshold. The next diagnostic run will use an explicit localization-health bypass, keep logging actual cost/freshness/quality observations, and continue to preserve malformed-data, epoch/time-integrity, collision, and PX4 control-state protections. It remains diagnostic evidence only and cannot be counted as formal health qualification.

Detailed data: [calibration evaluation](../../artifacts/runs/n10-20261026-354-upstream-spline-speed080-open-speed-16m/n10-calibration-evaluation.json), [arrival evaluation](../../artifacts/runs/n10-20261026-354-upstream-spline-speed080-open-speed-16m/arrival-evaluation.json), [PX4/bridge readback](../../artifacts/runs/n10-20261026-354-upstream-spline-speed080-open-speed-16m/postflight-px4-bridge-readback.json). Machine-readable summary: [result JSON](n10-horizon5-speed080-upstream-spline-open-speed-16m-20261026-354.json).
