# #315 N08 neutral-pitch low-height yaw SITL result

## Result

The new neutral-pitch profile improved the interpretation over #314 but still did not complete. The first low-height yaw stage (0→−π/2 at pitch 0) completed. The second stage, continuing yaw toward −π at pitch 0, ended with a localization health lockout at normalized cost 1.065024. The last trace before lockout was yaw −2.0613 rad/cost 0.896595; maximum recorded trace cost in the stage was 0.931764. The lockout pose itself was not recorded, so the precise crossing angle cannot be claimed.

The evidence makes downward pitch alone an unlikely explanation. #314 and #315 both stopped in the second low-height yaw segment, near rear-facing orientation, despite different pitch timing. Low-height yaw/visual coverage is now the leading diagnostic hypothesis, but the specific residual mechanism remains unproven.

## Safety and acceptance scope

Initial same-run N05 online/offline agreed but refused `ground_plane_insufficient_raw_occupied_voxels`. The scan did not reach fixture-release admission, read-only preflight, live geometry, or a goal. Fixture detachment/removal and landed state passed; independent six-second PX4/bridge readback confirmed disabled, disarmed, landed, and zero control-topic samples. Only run #315 was stopped and exited 0.

See [#315 report](../evidence/n08-neutral-pitch-yaw-lockout-20261026-315.md) and `artifacts/runs/n08-cancel-highspeed-prescan-20261026-315/`.

## Next

Run #316 with the same rear turn at the existing intermediate height z=0.5 m. This changes only turn altitude, uses the same yaw/pitch stages and thresholds, and tests whether the lockout is specific to the z=0 turn. If it passes, continue observation/return and the same-run admission gates; no goal is allowed before all gates pass.

Related dialogue: [#315 SITL result](../../collaboration/dialogues/2026-10-26-315-n08-neutral-pitch-yaw-sitl.md).
