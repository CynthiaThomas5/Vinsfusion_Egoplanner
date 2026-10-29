# #319 N08 runtime refusal during yaw return

## Result

The unarmed support scan completed 12/35 stages and then locked during yaw return from −π toward −π/2. The same-epoch localization sample was fresh and failed the unchanged `normalized_cost_exceeded` gate at 1.007907 (source age 44 ms). The segmented descent was never reached, so the intended dwell hypothesis has no runtime result. Initial N05 online/offline checks agreed on `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`; no mission or flight was attempted.

Fixture removal and landed state were confirmed. Independent 6 s PX4/bridge readback showed DISABLED, disarmed/landed and zero control samples; the fixture was absent from Gazebo. Only #319 was stopped; container exit 0.

## Next

Compare the source-matched #312 and #319 yaw-return records before another scan. Do not repeat the same profile or change any health or map threshold. Continue only if raw-data comparison yields a specific discriminating action.

Evidence: [#319 runtime refusal](../evidence/n08-segmented-neutral-descent-yaw-lockout-20261026-319.md). Static profile contract: [#319 profile](../evidence/n08-segmented-neutral-descent-profile-20261026-319.md).
