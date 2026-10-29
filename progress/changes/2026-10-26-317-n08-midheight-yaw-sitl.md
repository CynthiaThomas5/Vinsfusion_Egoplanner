# #317 N08 mid-height yaw SITL result

## Result

The profile ran through the initial route and reached z=0.5 m. The first neutral-pitch yaw segment to −π/2 completed; the second segment toward −π failed at stage 15/23. The new diagnostic showed a fresh same-epoch localization sample in `LOST` state from `normalized_cost_exceeded` at 1.018659. Receipt age was 0.000039 s against the unchanged 0.5 s limit; source age was 28 ms. The joint trace ended at yaw −1.9558 rad with cost 0.896711, so the crossing pose was not sampled by that trace.

The altitude change to z=0.5 m did not prevent the low-height rear-turn lockout. #312's z=1 m rear turn reached −π and returned with maximum trace cost 0.8125, followed by a lockout during neutral-pitch descent near z=0.813 m. #318 will hold pitch −0.35 rad through that descent after the high turn, testing a view-conditioning hypothesis without threshold changes.

## Gates and safety

Initial same-run N05 online/offline refused `ground_plane_insufficient_raw_occupied_voxels`. No post-release N05, 40 s preflight, live geometry, mission, or flight followed. Fixture detach/removal/landed state passed; independent six-second readback confirmed bridge disabled, PX4 disarmed/landed, and zero control-topic samples. Only #317 was stopped; container exit 0.

See [#317 report](../evidence/n08-midheight-yaw-lockout-20261026-317.md) and run artifacts at `artifacts/runs/n08-cancel-highspeed-prescan-20261026-317/`.

## Next

Run #318 using the proven z=1 m turn, then a pitch-only adjustment at neutral yaw to −0.35 rad held through descent to z=0; reset pitch on the ground. Keep N05, localization, map, and geometry thresholds unchanged.

Related dialogue: [#317 mid-height result](../../collaboration/dialogues/2026-10-26-317-n08-midheight-yaw-lockout.md).
