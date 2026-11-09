# HW04 hardware VINS and localization runtime

State: **partial; HW04 stays `in_progress` pending the physical motion route.**

Dialogue summary: [HW04 execution](../../collaboration/dialogues/2026-11-02-hw04-execution.md)

Runtime evidence: [static and stop report](../evidence/hw04-vins-static-and-stop-20261102.md)

## Changes

- Added hardware freshness admission and diagnostics in `src/own/uav_localization/uav_localization/health.py` and `node.py`: system ROS source age, monotonic receipt age, six-stream admission, usable-solver gating, body-frame velocity conversion, matched-axis IMU angular velocity, and a one-second internal pose/stream observation. Hardware sessions reject simulated ROS time.
- Added `config/components/localization/health_hardware.json`, bound by hash in generated hardware sessions.
- Added the owned Nano entrypoint `tools/hardware-localization.sh`, which starts the epoch-scoped VINS process before the adapter, waits for an actual VINS odometry publisher, passes `use_sim_time=false`, and verifies post-VINS-stop invalidation from the adapter's internal status log.
- Added the tested VINS UDP receive profile `config/hardware/vins_fastdds_udp_rxbuf4m.xml`. The launcher defaults VINS to this profile and rejects startup when the Nano receive-buffer kernel limit is below the tested 8 MiB requirement. The kernel limit is configured transiently by the operator and restored after the run.
- Reduced `tools/probe_localization_freshness.py` to low-rate optimized/status subscriptions. The formal static run used the adapter's internal logging and did not attach the probe.

## Verification

- `python3 tools/test_localization_health.py`: 11 tests passed.
- `python3 tools/test_hardware_rig.py`: 4 tests passed.
- `python3 -m py_compile src/own/uav_localization/uav_localization/health.py src/own/uav_localization/uav_localization/node.py tools/generate_vins_config.py tools/probe_localization_freshness.py tools/test_localization_health.py tools/test_hardware_rig.py`: passed.
- `bash -n tools/hardware-localization.sh`: passed.
- `python3 -m json.tool config/components/localization/health_hardware.json`: passed.
- Fast DDS XML parsing and targeted Nano start preflight passed. With the restored 212,992-byte kernel limit, startup exited 2 before creating session/process ownership state and reported the required 8 MiB setting.
- Nano build previously performed for the changed adapter: `colcon build --executor sequential --packages-select uav_localization --cmake-args -DBUILD_TESTING=OFF`: passed.
- Successful real static run and VINS-stop invalidation are detailed in the linked report. No mapping, planner, PX4, Gazebo, SITL, control, or flight process was started.
- `python3 tools/project_status.py`: structural consistency pass; it explicitly does not substitute for runtime or SITL evidence.
- `git diff --check`: passed after progress records were written.

## Limitations and next step

The physical 2–3 minute slow translation/lift/yaw/return route was not performed. Therefore route direction/scale, displacement, return error, and dynamic continuity remain unverified. Static stability cannot close those exits. The installed VINS binary did not expose native queue high-water fields, so queue growth is supported only indirectly by stable source ages and output gaps in the static run.

Next: when the operator is available, restart the owned D435i session, temporarily set `net.core.rmem_max=8388608`, generate a fresh VINS session, run the prescribed hand-held route for about 180 seconds, then stop VINS and capture the same-epoch invalid state plus the next distinct epoch. Restore the original kernel setting and stop all owned sensor/localization processes afterward.
