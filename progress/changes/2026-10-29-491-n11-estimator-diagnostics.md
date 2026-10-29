# #491 N11 formal06 and VINS estimator diagnostics

## Changes

- Archived and evaluated formal run `n11-20261029-491-formal06` on the unchanged N11 revision9 runtime and profile.
- Added run-local read-only VINS estimator telemetry capture and offline analysis scripts under `artifacts/n11-prepared/n11-20261029-491-formal06/`. They do not publish control or truth and are outside the frozen runtime.
- Added [formal failure evidence](../evidence/n11-formal-491-failure-20261029.md), [estimator/RPE review](../evidence/n11-estimator-diagnostics-20261029-491.md), and [dialogue summary](../../collaboration/dialogues/2026-10-29-491-n11-formal06-analysis.md).

## Verification

- `python3 artifacts/runs/n11-20261029-483-native-work-freeze/archive_and_evaluate.py n11-20261029-491-formal06` — run archived; frozen evaluator returned **FAIL**, not count eligible.
- `python3 artifacts/n11-prepared/n11-20261029-491-formal06/analyze_motion_origin.py` — completed; goal-motion translation RPE P95 0.106189 m.
- `python3 artifacts/n11-prepared/n11-20261029-491-formal06/analyze_truth_clock_sensitivity.py` — completed; best ±200 ms shift still 0.078328 m.
- `python3 artifacts/n11-prepared/n11-20261029-491-formal06/analyze_pose_velocity_consistency.py` — completed; descriptive only and not discriminative against prior passing runs.
- `python3 artifacts/n11-prepared/n11-20261029-491-formal06/analyze_estimator_telemetry.py` — completed; 808 goal samples, solver usable on all frames, no pending feature work.
- The separate telemetry collector was terminated with SIGINT after normal terminal readback and wrote all 2,246 rows plus a summary; its process log contains an `ExternalShutdownException` traceback on shutdown. This is an instrumentation limitation, not flight-process failure.

## Result and limitations

- The flight reached the goal and landed/disarmed; independent readback permitted normal container stop.
- RPE is a hard FAIL. Other applicable flight metrics and static-map metrics passed; sensor payload/receipt identity is INSUFFICIENT (31 unmatched IMU payloads), and the archived run lacks the hash-bound GUI window listing.
- Feature counts, solver status, and queue observations do not establish correct visual correspondences. Per-residual-family cost components were absent. Root cause remains unproven.
- The RPE high-error time window shifts among the failed runs. No threshold, configuration, runtime code, or control gate was modified.

## Next

Run one unchanged revision9 formal cold start without the supplemental telemetry observer. Persist the live Gazebo/RViz window listing before goal dispatch. This is a targeted control for observer overhead and evidence integrity, not a repeat accepted as passed in advance. N11 remains in progress at 2/3.
