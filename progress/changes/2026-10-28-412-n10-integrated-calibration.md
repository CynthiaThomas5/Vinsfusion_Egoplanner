# #412 N10 integrated calibration closeout

Updated the N10 evidence record with the #412 result. The run completed the 16 m goal, independent 3.056 sim-second joint arrival dwell, 20 sim-second diagnostic hold, obstacle insertion, receipt-to-MCAP check and normal PX4/bridge landed/disarmed closeout. It measured the combined VIO, tracking, 4 ms clearance, raw/inflated map, replan and resource/queue signals.

The acceptance outcome remains `INSUFFICIENT`: goal-motion 10 s translation RPE and maximum velocity error exceed their unchanged provisional candidates; raw-map classification has 39 fully-contained known-free cells; no ROI cloud watermark was observed; tracking/clearance and resource thresholds lack a justified basis. The first interval result reported insufficient identity because it ran under `/workspace` without usable Git metadata. Replaying the same raw data and evaluator against the locked host checkout passed all PX4/Gazebo/model/plugin identity checks and yielded a positive 0.41054 m lower bound across every airborne interval; the original report is preserved. The 39 cells are nearest the positive-Y (35) and negative-X (4) obstacle faces, with nearest-face interior margin 0.000562–0.001391 m. Prohibited contact count is zero.

Files added:

- `progress/evidence/n10-integrated-calibration-result-20261028-412.md`
- `progress/evidence/n10-integrated-calibration-result-20261028-412.json`
- `collaboration/dialogues/2026-10-28-412-n10-integrated-calibration.md`

No runtime code, parameter or threshold changed in this closeout. The additional interval analysis is an offline replay written to `n10-interval-clearance-bound-host-replay.json`. No flight was started or stopped by this documentation update. Validation: JSON parse, `git diff --check`, and repository structure check.
