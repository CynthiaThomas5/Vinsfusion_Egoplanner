# #283 N08 prerequisite scan health refusal

Related dialogue: [2026-10-26-283 N08 scan health refusal](../../collaboration/dialogues/2026-10-26-283-n08-n05-scan-health-refusal.md)

## Scope

Continue the user-authorized N08 Goal-completion work in simulation. Do not change N08 gates or the N05 localization-health threshold. Normal target and explicit return remain separate commands. N07 is reused without retest.

## Result

The new cold run captured the corrected runtime manifest, but the `n08_far_small_pitch_view` N05 support scan stopped at stage 9/15. During translation from x≈−2.4 m toward −1.2 m, the accelerometer-bias norm first crossed the unchanged 0.15 m/s² health gate at sim time 314.196 s (0.1500687) and later peaked at 0.1792709. The solver was still usable; the failure was specifically `accel_bias_norm_exceeded`, not the normalized-cost gate. The initial static N05 map had correctly refused due insufficient raw ground support. There was no `n05-prescan-ready`, post-release admission, mission, control goal, or flight.

PX4 remained DISARMED, fresh LandDetector status was true, the fixture was detached and removed, and the container was stopped. See [#283 evidence](../evidence/n08-n05-scan-health-refusal-20261026-283.md).

The same `n08_far_small_pitch_view` recipe completed in #279 and #281 with maximum recorded accel-bias norms 0.05738 and 0.07990, and N05 post-release admission passed in both. The #283 result therefore records a variable health-gate refusal; it does not justify changing the threshold or blindly repeating the same scan.

## Next bounded experiment

Use the existing supported `n06_full_airframe_retreat_240_translation_only` scan profile on the same `n08_overhead_calibration` geometry. Hypothesis: the same 2.4 m out-and-back support coverage with no pitch perturbations and one continuous return may avoid the angular-excitation / estimator-bias interaction observed in #283. The only selected variable is the preflight scan profile. Acceptance remains unchanged: full configured profile, same epoch/map identity, all N05 phases online/offline accepted after release, transfer pose within budget, and confirmed detached/removed plus landed/disarmed. If the gate refuses, preserve it and reassess; do not raise the bias or unknown threshold.

## Verification and files

- Read-only analysis of `fixture-vins.jsonl`, `fixture-trace.jsonl`, `fixture-stages.json`, and `fixture-result.json`; threshold-crossing source sample was 314.196 s.
- Safety cleanup verified detached support, absent Gazebo fixture, DISARMED state, and landed state; `bash tools/project.sh stop` exited and no project processes remained.
- No source/config changes in #283. Artifacts are listed in [#283 evidence](../evidence/n08-n05-scan-health-refusal-20261026-283.json).

N08 remains `in_progress`; #283 is a scan-prerequisite failure and does not count as an N08 flight attempt or repeat.
