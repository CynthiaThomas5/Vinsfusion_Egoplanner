# N08 #315 neutral-pitch low-height yaw scan refusal

## Scope and result

Cold-start unarmed physical-support scan with the #315 profile. It completed 14 of 20 stages and stopped during the second low-height yaw segment, from −π/2 toward −π with pitch held at 0. The last trace before the health lockout was at simulation time 447.0 s, yaw −2.0613 rad, pitch approximately 0, with normalized cost 0.896595. The highest traced cost within that stage was 0.931764; the localization health monitor then reported `normalized_cost_exceeded` at 1.065024. Because the lockout sample itself was not captured in the joint trace, its exact yaw is unknown.

The first neutral-pitch yaw segment (0→−π/2) completed with maximum trace cost 0.906320. Compared with #314, a downward camera pitch is not necessary for this low-height rear-turn lockout. Both runs stopped in the second yaw segment near the rear-facing direction, which makes low-height accumulated yaw/visual coverage a stronger candidate than pitch alone. This remains an inference: the trials do not identify a single visual residual or prove the causal mechanism.

The initial same-run N05 online/offline result agreed and refused `ground_plane_insufficient_raw_occupied_voxels`. The scan stopped before fixture release, post-release N05, read-only preflight, N08 forward geometry, mission, or flight. No goal or control enable was issued.

## Safe end state

The fixture helper verified detach, model removal, and landed state. Independent six-second live readback reported bridge `DISABLED`, `armed=false`, `control_enabled=false`, `landed=true`; PX4 arming state `1` (disarmed); and zero control-mode, trajectory-setpoint, and vehicle-command samples. `vehicle_remained_disarmed=true`. `tools/project.sh stop` stopped only this run container, which exited 0.

## Evidence

- Run: `artifacts/runs/n08-cancel-highspeed-prescan-20261026-315/`
- Summary and stage data: `fixture-result.json`, `fixture-stages.json`, `fixture-trace.jsonl`
- Same-run initial N05 snapshot: `n05-before/n05-live-entry-check.json`
- Independent safe-state check: `post-scan-independent-live-readback.json`
- Post-scan world inventory: `post-scan-gz-model-list.txt`
- Static profile contract: [#315 profile](n08-neutral-pitch-yaw-profile-20261026-315.md)

## Next discriminating action

Run the same low-height rear yaw/pitch sequence at z=0.5 m. This altitude is the existing scan's intermediate level, already traversed at neutral yaw; only the altitude at which the rear-turn sequence occurs changes. If yaw survives at 0.5 m, continue through pitch observation, neutral-pitch yaw return, and final descent. Preserve all thresholds and do not issue a goal unless all support-scan and post-release admission gates pass.
