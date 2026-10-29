# N09 official-policy cold-start qualification (#332)

Goal mode continues N09 after the user authorized official FAST Lab takeoff and collision semantics in #331. Current state and execution scope are in [CURRENT](../CURRENT.md); decision history is in the [dialogue summary](../../collaboration/dialogues/2026-10-26-332-n09-official-policy-repeat.md).

## Work and results

- Frozen runtime SHA256 `6b95d5fe48ea17f41649947547ccab4bf0798e9907a565dbb2dfd65cf0579f30` and N09 goal profile SHA256 `04d2287d22481257ab59cd983fa439b68e130f210d111f938a2f2fa89bd92012` were held constant.
- `n09-official-331-repeat01`, `repeat02`, and `repeat04` each completed the single 3D/yaw PX4 mission. Each independent evaluator passed all 11 N09 checks, including independent truth arrival, map/localization freshness, unique bridge-owned controls, contact evidence, and post-landing out-of-map refusal. Independent 6-second terminal readback confirmed landed/disarmed/control-disabled and zero Offboard/trajectory-setpoint messages.
- `repeat03` reached PX4 `ACTIVE` but failed safely after one VINS frame exceeded the unchanged normalized-cost guard. One visual cost outlier was observed; root cause remains unresolved. It is retained and not counted as a successful flight. PX4 and bridge independently read LANDED/disarmed with no control setpoints during the terminal readback.
- No runtime source, policy, health threshold, goal profile, or collision geometry was changed in this qualification subtask. The only added helper is a read-only terminal-state observer under the artifact directory; it is outside the runtime fingerprint.

## Verification

- Existing #331 verification: `bash tools/project.sh build ros` — 17 packages succeeded; `bash tools/project.sh test` — 397 tests and both legacy/current ROS action integrations succeeded; full pinned patch replay succeeded.
- `python3 tools/runtime_manifest.py ...` per cold start — all four runtime hashes match the frozen SHA above.
- Per-run N09 and vehicle-contact evaluation — repeat01/repeat02/repeat04 passed; repeat03 correctly did not pass.
- Per-run 6-second independent terminal readback — all four confirmed LANDED/disarmed/control-disabled and zero Offboard/trajectory setpoints.
- Evidence report: [N09 official-policy qualification](../evidence/n09-official-policy-qualification-20261026-332.md) and its machine-readable summary.

## Completion and handoff

N09's limited exit is complete: repeat01, repeat02, and repeat04 provide 3/3 successful independent cold starts. Repeat03's VINS lockout remains a separately recorded failed attempt and is not counted. No health threshold was relaxed. N09 is marked `passed` in milestones and `next_goal` advances to N10. The user-authorized scope ended at N09; N10 is not started in this change.
