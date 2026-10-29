# #349 N10.3 open-speed calibration result

Archived the #349 PX4 SITL outcome and independent measurements. The run reached ACTIVE with both additional speed protections disabled, then failed because EGO could not produce a full curve around the tall cylinder on the straight target route. Independent truth shows only 2.159 m forward progress and 13.910 m minimum target error. No arrival, dwell, long ACTIVE hold or braking measurement was obtained.

The report preserves speed, short-window VIO, tracking, map-age, contact and PX4 terminal-state evidence. The provisional 0.15 m tracking candidate was exceeded; it remains descriptive pending N10.4. The run ended landed/disarmed, bridge control disabled and control samples zero before the project container was stopped.

The next experiment (#350) changes only EGO planning horizon from 1 m to the repository default 5 m. The 0.25 m/s/axis and 0.25 m/s²/axis planner settings, task and user-authorized speed observation-only policy stay fixed. See [#349 result](../evidence/n10-open-speed-16m-20261026-349.md), [#350 frozen protocol](../evidence/n10-horizon5-open-speed-16m-protocol-20261026-350.md), and [dialogue summary](../../collaboration/dialogues/2026-10-26-349-n10-open-speed-calibration.md).
