# #249 N08 negative-only map and localization timestamp lockout

## Constraints

- Continue N08 only. Reuse the established negative-only profile; keep thresholds and PX4 behavior unchanged.
- Do not issue XY unless same-run gates and the curve certificate pass. Do not retest N07’s already passed items.
- If health locks, preserve its snapshot, independently read back safety state, stop the container, and do not retry blindly.

## Result

The same-identity N05 post-release map gate passed, but the later current-area check failed closed because raw propagated VINS odometry was 152 ms ahead of the localization adapter’s last `/clock` receipt, exceeding its 20 ms guard. No goal/control/XY was sent. Independent readback showed DISARMED, landed, bridge DISABLED, zero control samples; container stopped with exit 0.

## Decision

Next #250 will capture the existing read-only localization source timeline through one evidence-directed diagnostic run. It will determine whether the future stamp is already present in raw VINS output or whether `/clock` delivery to the adapter is lagging. Do not increase future tolerance or loosen admission gates without that evidence.
