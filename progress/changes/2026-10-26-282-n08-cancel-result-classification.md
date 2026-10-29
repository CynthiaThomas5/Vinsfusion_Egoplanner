# #282 N08 caller-cancel result classification correction

Related dialogue: [2026-10-26-282 N08 cancel classification](../../collaboration/dialogues/2026-10-26-282-n08-cancel-result-classification.md)

## Scope

Continue the user-authorized N08 Goal-completion work in simulation. Keep the documented acceptance criteria and thresholds. Normal single-goal completion remains separate from an explicit return command. N07 stays passed and is not retested.

## #281 outcome

The fresh #281 run captured the corrected #280 runtime manifest, passed the complete N05 support scan and post-release admission, and passed the read-only mission preflight. It sent one forward EGO goal and canceled at an observed PX4 horizontal speed of 0.04323 m/s and EGO reference speed 0.06092 m/s, within the configured 0.04–0.06 m/s trigger window. The planner observer recorded `MODE_STOP_HOLD` (1), reason `caller_cancel`.

The N08 runner then raised `navigation_action_did_not_report_caller_canceled`. The action contract serializes the enum as `outcome="canceled"` and carries `caller_cancel` in `reason`; the runner incorrectly compared `outcome` with the reason string. It failed before checking for a replacement stop spline and safely disabled Offboard, landing and disarming the vehicle. Only the original trajectory id was recorded; the run has no qualified stop distance, response or hold result. It is not an N08 pass. See [#281 evidence](../evidence/n08-caller-cancel-classification-20261026-281.md).

## Changes

- `tools/run_n08_braking_trial.py`: validate `STATUS_CANCELED`, `outcome="canceled"`, and `reason="caller_cancel"` as distinct fields. Persist the trigger sample and action result before any later stop-spline assertion so a failed attempt remains diagnosable.
- `tools/test_run_n08_braking_trial.py`: add coverage for valid cancellation and incorrect status/outcome/reason combinations.
- `progress/CURRENT.md`, this change record, dialogue summary, and #281/#282 evidence reports.

## Verification

- `bash tools/project.sh test`: 336 unit tests passed; navigation-adapter integration passed.
- `python3 -m py_compile` for the changed runner and related manifest/test files passed.
- `bash -n tools/mission_runtime.sh tools/project.sh tools/sim_runtime.sh` passed.
- `git diff --check` passed.
- The change touches Python runner/evidence code only. #276 remains the applicable compiled EGO/interface build; this test pass does not establish #0046 stop-spline behavior.

## Next step

Start a fresh cold run with the #280 runtime manifest and #282 runner fix. Complete same-run N05 scan/admission and repeat the 0.04–0.06 m/s motion-cancel trial. Require source-clocked cancellation, correct action result, a new certified EGO stop spline, no old-trajectory resumption, active stop/hold, measured response/distance, and safe landing/disarm. Keep N08 `in_progress` until every remaining controlled comparison, budget feedback, and frozen-version three-run ordinary single-goal exit passes.
