# HW04 startup admission fix and dynamic route

State: **passed for the bounded ground-handheld route; HW03 calibration remains PROVISIONAL.**

Evidence: [HW04 dynamic route and freshness report](../evidence/hw04-vins-dynamic-route-20261103.md)
Dialogue summary: [HW04 route session](../../collaboration/dialogues/2026-11-03-001-hw04-route.md)

## Change

- `src/own/uav_localization/uav_localization/health.py`: in hardware `gate` mode, `paired()` now keeps the adapter in `INITIALIZING` while any configured stream's current source age or monotonic receipt age exceeds its existing measured budget. A future source stamp still locks. Once admitted to `TRACKING`, the existing lock-on-stale path is unchanged.
- `tools/test_localization_health.py`: added regression coverage for stale startup samples, admission after fresh samples arrive, stale data after tracking, and future stamps.
- No thresholds, configurations, frame contracts, PX4 interfaces, or control behavior changed.

## Verification

- `python3 tools/test_localization_health.py`: 12 passed.
- `python3 -m py_compile src/own/uav_localization/uav_localization/health.py tools/test_localization_health.py`: passed.
- Deployed only `health.py` to the Nano and ran `colcon build --executor sequential --packages-select uav_localization --cmake-args -DBUILD_TESTING=OFF`: passed.
- Measured ground route stayed valid for 420.6 s, with about 200 s of motion; route direction, approximate scale, return error, and stream ages are tabulated in the linked report.
- VINS stop invalidation, new-epoch start, Nano sysctl restoration to `212992`, owned sensor shutdown, empty ROS node list, and no project processes were verified.
- `git diff --check`: passed.

## Limitations

The operator accepted approximate translation/yaw results, but exact ruler readings were not separately reported. The side/return estimate overshot through the origin; keep it visible as the least reliable axis result. The installed VINS binary lacks native queue high-water telemetry, so queue continuity is supported indirectly by measured stream ages and output gaps. A separate post-route startup attempt locked after one stereo pair; a later fresh epoch passed a 51.3 s static check. The one-pair failure's cause remains unknown and no freshness budget was widened.
