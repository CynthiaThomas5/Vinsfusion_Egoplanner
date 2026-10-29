# #285 N08 runtime runner fingerprint correction

Related dialogue: [2026-10-26-285 N08 runner fingerprint](../../collaboration/dialogues/2026-10-26-285-n08-runtime-runner-fingerprint.md)

## Scope and #284 result

Continue the user-authorized N08 Goal-completion scope in simulation. N08 remains `in_progress`; no N07 test was repeated and no N08 threshold or exit criterion changed.

#284 completed the N05 support profile, post-release admission, fixture removal, and fresh final readback. The N08 mission passed its 40.002 s read-only preflight and fresh N05 current-area admission, then refused before enabling control because the #276 build record listed the Python `tools/run_n08_braking_trial.py` hash from before the #282 runner-only correction. The EGO/interface compiled sources and installed binaries still matched #276. Planner observer output contained zero messages; no pre-enable corridor record, goal, enable, or flight occurred. A fresh post-refusal N05 readback confirmed the same accepted map, `DISABLED`, disarmed/landed, and valid localization; the project container was stopped. See [#284 N05 scan](../evidence/n08-translation-prescan-admission-20261026-284.md) and [#284 refusal](../evidence/n08-runtime-source-fingerprint-refusal-20261026-284.md).

## Changes

- `tools/runtime_manifest.py` now records non-test `.py` and `.sh` files under `tools/`, so cold-run manifests include N08 mission entrypoints and evaluators.
- `tools/run_n08_braking_trial.py` keeps compiled-source and binary checks strict. The Python runner is checked against its current cold-run manifest hash instead of its stale entry in the historical compiled-build source list.
- Added regression tests for runtime-tool manifest coverage, accepting a runner-only change only when authenticated by the current runtime manifest, rejecting missing/mismatched runner fingerprints, and continuing to reject compiled-source drift.

## Verification

- `bash tools/project.sh test`: 341 unit tests passed; navigation-adapter integration passed.
- `PYTHONPYCACHEPREFIX=/tmp/n08-pycache-285-final python3 -m py_compile tools/runtime_manifest.py tools/test_runtime_manifest.py tools/run_n08_braking_trial.py tools/test_run_n08_braking_trial.py`: passed.
- `bash -n tools/mission_runtime.sh tools/project.sh tools/sim_runtime.sh`: passed.
- `git diff --check`: passed.
- `python3 tools/runtime_manifest.py /tmp/n08-runtime-manifest-check-285.json`: current snapshot included `tools/run_n08_braking_trial.py` with the exact current SHA256. #276 installed runtime binary hashes still match; no compiled source changed, so no build was required.

## Next step

Start a new cold simulation, repeat fresh N05 support scan/admission, then retry the bounded `single_goal motion_cancel` at 0.04–0.06 m/s only if every gate passes. Require a valid replacement stop spline, no old trajectory resumption, measured response/distance, stop/hold and landed/disarmed. Continue N08 controlled comparisons and measured N05/N06 budget feedback; keep N08 open until all formal exits pass.
