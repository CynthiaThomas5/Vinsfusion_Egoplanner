# #280 N08 runtime fingerprint refusal and correction

Related dialogue: [2026-10-26-280 N08 runtime manifest](../../collaboration/dialogues/2026-10-26-280-n08-runtime-manifest-refusal.md)

## Scope and starting state

Continue the user-authorized N08 Goal-completion scope in simulation only. N07 evidence is reused without retest. A normal N08 target ends at its stop/hold; return remains a separate command. Preserve every existing speed, map, tracking, timing, health, and geometry gate.

## Runs and findings

- **#278**: the 40-second read-only navigation preflight passed, then fresh N05 admission refused `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`. The raw map contained 14,751 free voxels and 110 raw ground-plane occupied voxels; all flight-volume phases contained unknown cells, with zero occupied collision cells. Online and offline N05 agreed. PX4 remained disarmed and landed, bridge disabled, and no control or goal was published. This is a preflight refusal, not a flight attempt. See [#278 evidence](../evidence/n08-n05-preflight-refusal-20261026-278.md).
- **#279 N05 preparation**: the documented `n08_overhead_calibration` / `n08_far_small_pitch_view` support scan completed all 15 stages. Same-epoch/map identity, post-release online/offline admission, and the pose transfer gate passed. The scan runner could not confirm a fresh status during cleanup, so the safety wrapper retained the simulator. A subsequent independent fresh N05 check confirmed `DISABLED`, disarmed, landed, accepted entry, and unchanged identity; an independent Gazebo model list confirmed the support fixture absent. The project was stopped only after these checks.
- **#279 N08 runner**: the 40-second mission preflight and current N05 admission passed, but the runner refused before ROS action/enable setup because the startup runtime manifest omitted `install/uav_navigation/lib/uav_navigation/navigation_supervisor`. The installed launcher SHA256 matched the pinned #276 build evidence (`c9ddb17931ef244d150caffe9f04164c3fd2ba76160cd02b03c7455267c11923`); the manifest omission caused the mismatch. No trial pre-enable admission was produced and no goal/cancel/flight action ran. The downstream odometry evaluator's non-monotonic timestamp error belongs to this incomplete failure record and provides no motion data. See [#279 evidence](../evidence/n08-runner-fingerprint-refusal-20261026-279.md).
- **#280 correction**: `tools/runtime_manifest.py` now records the installed `navigation_supervisor` launcher. Added `tools/test_runtime_manifest.py` to cover it. The targeted unittest passed (1/1), the current workspace manifest included the launcher with the #276 build SHA, shell syntax checks passed, and `git diff --check` passed. See [#280 verification](../evidence/n08-runtime-manifest-20261026-280.md).

## Files changed

- `tools/runtime_manifest.py`
- `tools/test_runtime_manifest.py`
- `progress/CURRENT.md`
- `progress/evidence/n08-n05-preflight-refusal-20261026-278.{json,md}`
- `progress/evidence/n08-runner-fingerprint-refusal-20261026-279.{json,md}`
- `progress/evidence/n08-runtime-manifest-20261026-280.{json,md}`
- This change record and its dialogue summary.

## Remaining work

N08 remains `in_progress`. #278 and #279 do not count as motion trials. Next: start a fresh cold simulation with the runtime manifest fix, complete same-run N05 support scan and admission, then rerun the bounded 0.04–0.06 m/s caller-cancel test against the #276 compiled N08 build. Validate replacement-stop spline, old-trajectory non-resumption, stop/hold, landing/disarm and independently measured response/distance. Then finish required hold/compute-only/execute comparisons, feed measured budgets to N05/N06, freeze the qualifying version, and obtain three independent cold-start ordinary single-goal passes. No threshold has changed.
