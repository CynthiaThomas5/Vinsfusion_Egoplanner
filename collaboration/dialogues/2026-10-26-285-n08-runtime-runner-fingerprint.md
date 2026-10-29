# N08 runtime runner fingerprint correction (#285)

## Project task summary

Continue the user-authorized N08 Goal-completion work in the single-D435i simulation. Preserve all acceptance thresholds. Ordinary single-goal navigation ends after its own stop/hold; return remains a separate command.

## #284 outcome

The translation-only N05 support scan completed 6/6 stages. Its motion trace had zero invalid-localization samples and peak accelerometer-bias norm 0.11483 m/s². Same-identity post-release and an additional independent fresh online/offline N05 check passed; the fixture was absent and PX4/bridge were landed/disarmed/disabled.

The N08 mission then passed its 40.002 s read-only preflight and fresh current-area N05 admission but was refused before control enable. #276's historical source list included the Python trial runner hash from before #282, so the runner-only correction was mistaken for a compiled EGO source change. Installed #276 binaries still matched. No corridor pre-enable record or planner command was created. A new independent N05 readback confirmed safe landed/disarmed state, after which the simulator was stopped. The later odometry evaluator error belongs to the incomplete no-flight record.

## Correction and verification

The cold-run runtime manifest now fingerprints non-test Python/shell tools. Compiled sources and binaries remain checked against #276, while the trial runner must match the current run's runtime manifest. Regression coverage verifies the runner-only case and preserves fail-closed behavior for missing runner hashes and compiled-source drift. The full project suite passed 341 unit tests plus navigation-adapter integration; Python compilation, shell syntax and diff checks passed. No compiled source changed and no rebuild was needed.

## Next action

Start a fresh cold run with the revised runtime manifest, complete same-run N05 scan/admission, then retry the bounded 0.04–0.06 m/s single-goal caller-cancel stop/hold trial. Details are in [the #285 change record](../../progress/changes/2026-10-26-285-n08-runtime-runner-fingerprint.md).
