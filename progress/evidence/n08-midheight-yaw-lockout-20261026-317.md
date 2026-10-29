# N08 #317 mid-height rear-yaw lockout

## Result

This cold-start run actually exercised the z=0.5 m profile. It completed 15 of 23 stages and locked during stage 15, the second yaw turn from −π/2 toward −π with pitch held at 0. The last fixture trace was at simulation time 458.300 s, z=0.49998 m, yaw −1.9558 rad, pitch≈0, normalized cost 0.896711; maximum recorded cost in the stage was 0.924565. The localization monitor captured the failure itself: state `LOST`, `valid=false`, reason `normalized_cost_exceeded`, cost 1.018659. Its source sample was 28 ms old and its ROS receipt age was 0.000039 s, so it was fresh and from the expected epoch. The health crossing pose was not present in the joint trace.

Moving the rear turn from z=0 to z=0.5 m did not prevent the lockout. The #312 comparison shows a full 180° turn at z=1 m completed with maximum yaw-segment trace cost 0.8125, but the subsequent neutral-pitch descent locked near z=0.813 m. This makes the remaining contrast the descent/view transition after a high rear scan; #318 tests a downward camera pitch held during the descent. It does not assume that pitch is the cause.

Initial same-run N05 online/offline refused `ground_plane_insufficient_raw_occupied_voxels`. Because the support scan stopped during yaw, no fixture-release N05, read-only preflight, live geometry, goal, or flight was run.

## Safe end state

The support-scan helper verified fixture detachment, fixture-model removal, and landed state. An independent six-second readback reported bridge `DISABLED`, PX4 arming state 1 (disarmed), landed, and zero offboard-control-mode, trajectory-setpoint, and vehicle-command samples. `vehicle_remained_disarmed=true`. `tools/project.sh stop` stopped only #317; container exit 0. No goal or enable command was issued.

## Evidence

- Run: `artifacts/runs/n08-cancel-highspeed-prescan-20261026-317/`
- Summary and diagnostics: `fixture-result.json`, `fixture-stages.json`, `fixture-trace.jsonl`
- Initial N05: `n05-before/n05-live-entry-check.json`
- Independent safe state: `post-scan-independent-live-readback.json`
- Profile definition: [#316 mid-height profile](n08-midheight-yaw-profile-20261026-316.md)

## Next discriminating action

Return the rear-yaw sequence to the demonstrated viable z=1 m level. At neutral yaw, adjust pitch alone to −0.35 rad; hold that view through the existing 1→0.5→0 m descent; reset pitch alone at ground. This tests whether a downward view through the descent can prevent the #312 descent lockout, without changing the yaw sequence or thresholds.
