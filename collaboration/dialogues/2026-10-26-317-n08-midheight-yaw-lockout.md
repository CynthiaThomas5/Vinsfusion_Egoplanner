# N08 #317 mid-height yaw result

- The z=0.5 m profile ran and completed 15/23 stages, then exceeded the unchanged localization threshold during the second yaw turn toward −π.
- Diagnostic evidence shows a fresh same-epoch VINS sample (`receipt age 0.000039 s`, source age 28 ms) with state LOST and reason `normalized_cost_exceeded`, normalized cost 1.018659. It was not a stale-message or epoch error. The exact threshold-crossing pose was not captured; last trace was yaw −1.9558 rad, z≈0.5 m.
- Initial same-run N05 online/offline refused ground-plane raw occupied voxel sufficiency. No post-release admission or mission followed.
- Fixture detached/removed, landed and disarmed; independent readback showed bridge DISABLED and zero control samples. Only #317 stopped, exit 0.
- #316 before-stage refusal was transient/tooling attribution; #317 provides actual z=0.5 m evidence. The turn still locks there. Next #318 tests pitch −0.35 held through descent after the #312 z=1 m turn that completed.
- N08 remains in progress.
