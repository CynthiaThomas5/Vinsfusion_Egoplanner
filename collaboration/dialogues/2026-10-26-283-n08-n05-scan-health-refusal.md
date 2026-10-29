# N08 prerequisite scan health refusal (#283)

## Project task summary

Continue the user-authorized N08 Goal-completion work in single-D435i simulation. Keep N08 acceptance criteria and all safety thresholds unchanged. A normal target ends at its own stop/hold; return requires a separate command. Reuse passed N07 evidence without retesting.

## Finding

Cold run #283 captured the corrected runtime manifest, then the existing `n08_far_small_pitch_view` N05 support scan stopped at stage 9/15 during the return translation. Accelerometer-bias norm first crossed the unchanged 0.15 m/s² gate at sim time 314.196 s (0.1500687) and peaked at 0.1792709 m/s². The explicit failure was `accel_bias_norm_exceeded`; no post-release admission, mission, control goal, or flight occurred. PX4 remained disarmed and landed; the support fixture was detached and removed; the project container was safely stopped.

The same scan recipe completed in #279 and #281 with peaks of 0.05738 and 0.07990 m/s², respectively. This run is a health-gate refusal; it does not justify changing the threshold or repeating the same recipe without a new hypothesis.

## Next bounded experiment

Use the existing `n06_full_airframe_retreat_240_translation_only` scan profile with the same `n08_overhead_calibration` geometry and N08 low-speed planner. The hypothesis is that removing pitch perturbations and using a continuous translation-only return avoids the excitation interaction observed in #283. The scan recipe is the only selected variable. Require full profile completion, stable epoch/map identity, fresh online/offline N05 post-release admission, transfer budget, detached/removed fixture, and landed/disarmed status. Do not run the N08 mission if any gate fails. If the scan passes, resume the 0.04–0.06 m/s caller-cancel stop/hold trial.

Details: [#283 change record](../../progress/changes/2026-10-26-283-n08-n05-scan-health-refusal.md) and [#283 evidence](../../progress/evidence/n08-n05-scan-health-refusal-20261026-283.md).
