# N10.6 final-runtime regression — #470

## Result

PASS under the final frozen runtime contract. The one-leg 3D/yaw navigation action succeeded and the independent truth-only offline arrival evaluator found a continuous joint tolerance window of 3.72 simulated seconds. The maximum 3D position error was 0.299543 m against 0.30 m; maximum yaw error was 0.105601 rad against 15 degrees. This is one representative final-version task, not an N11 formal repeat.

The contact evaluator passed with zero prohibited contacts and observed landing ground contact. The official-policy out-of-map refusal probe passed without enabling control. Direct terminal readback reported bridge `LANDED`, control disabled, PX4 disarmed (`arming_state=1`), landed, `failsafe=false`; the project container stopped with exit 0. Runtime contract SHA-256 (internal fingerprint) was `7366605b679d13033919ed93651452dbcf7557bb13159876a9cc040c557f0b6b` over 711 files; the JSON file SHA-256 is `1b3564c899db879915a9622edd7cbd6bc3aaf346b1c24e852695da66cdf0257d`.

The orchestration waited a fixed 10 wall-clock seconds between simulator startup return and mission launch so the raw PRESTREAM pose anchor was recorded. This delay is not a runtime health gate. No project-local CPU, recorder, tracking, or queue threshold was added to flight admission or control.

## Artifact hashes

- `flight.json`: `88a371a3b61ea488d55ba7ebab5147b0be7a289be8c1bd76b724000f00043a5b`
- `arrival-evaluation.json`: `90b99232a520b81524b76bbd6ee60601bc66d26a446a94f2e071d612db4f8933`
- `vehicle-contact-evaluation.json`: `db43022de96aee11bffb533ff3e9f0e85ae18dc991058c61ba16c5a0306e79ec`
- `debug-truth-kinematics-observation.json`: `753e618801da398df0e035504f184ab6046fa8b5e547ae7df7d02c65f65af726`
- `n09-live-refusal.json`: `8efe28e88b534f43c5d83f1a260396fb8b73602029d796403452c8233f429391`
- `final-live-readback.txt`: `c11271619cfceaaf6b48260baeeb730f60dbfb75e0377ff4def23ad4d5a894c8`

All run files are under [`artifacts/runs/n10-20261028-470-frozen-runtime-regression`](../../artifacts/runs/n10-20261028-470-frozen-runtime-regression/). The successful #470 task does not replace a 600-second N16 run or any formal scenario repetition.
