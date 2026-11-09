# HW04 dynamic VINS / localization route evidence

Status: **passed for the bounded ground-handheld route, with the approximate-motion limits below.** No mapping, planner, PX4, Gazebo, SITL, control, or flight process was started.

## Identity and implementation

- Nano workspace: `/home/jetson/D435i-VINS-EGO-ROS2-hardware`; Foxy, `use_sim_time=false`.
- Rig/calibration ID: `c8c42778007c28a05acbeeca7533fb56ce67af175c3da337441f1d69ee2a9865`.
- Hardware settings SHA256: `d87f449536ab18b702f3e6acb13eaef53b26c6a2fa73a7be4e9d35da87239d26`.
- Fixed a cold-start admission fault in `health.py`: during `INITIALIZING`, hardware gate now waits until every configured stream's current source and monotonic receipt ages fit the existing measured budgets. Future stamps still lock immediately; after `TRACKING`, stale data still locks. No freshness budget was changed.
- Added a targeted regression for stale startup samples, fresh admission, post-admission staleness, and future stamps.

## Runtime trials

| Run | Epoch | Result |
| --- | --- | --- |
| `hw04-physical-route-20261103-01` | `beed3921c355427980e1774f4390aa27` | Before the fix, initial left/right image samples were 0.206/0.208 s old against fixed 0.185/0.187 s budgets; the first solver pair locked `left_source_stale`. This was an initialization transient, not a sustained camera dropout. |
| `hw04-physical-route-20261103-02` | `25814b401171464e9fefb52e8ee91509` | Approximate first route stayed valid for 213.254 s. The operator later described this route as approximate, so it is retained as exploratory evidence only. Estimated max excursion 168 mm and end displacement 53.9 mm. |
| `hw04-measured-route-20261103-03` | `535e81e4b7a74ee8ac61466a15580683` | Main route stayed `TRACKING/valid` for 420.6 s. A roughly 200 s movement window included forward/return, right/return, lift/lower, yaw both ways and return. No freshness lock or sustained loss occurred. |
| `hw04-post-route-fresh-20261103-04` | `760681390abb42d6b635a7a99cf7340f` | Fresh start produced only one stereo pair before `left_source_stale`. Adapter logged 1 left/right frame; VINS stopped receiving further images although its process remained alive. The camera publisher later measured normally; exact cause of this one startup failure is unconfirmed. |
| `hw04-post-route-fresh-20261103-05` | `857587dc6aa140ffb415e3d99dc542ee` | Fresh retry after the transient failure stayed valid for 51.3 s. This epoch differed from all previous sessions. VINS stop produced same-epoch `valid=false`. |

The operator said yaw was performed by feel and that moderate angle error was acceptable; after reviewing the VINS estimates, the operator replied “没问题，继续下一项”. The instructed translation targets were 60 mm forward, 60 mm to the camera's right, and 40 mm upward. Exact ruler readings were not separately reported, so these comparisons remain approximate rather than a calibrated accuracy claim.

## Measured route response

Positions were transformed from VINS world coordinates into the initial camera-body axes using the starting pose orientation; the rig defines X as optical right, Y as optical down, and Z as optical forward.

- Forward segment: peak approximately **+44.7 mm on Z**, versus the instructed 60 mm target.
- Right/return segment: X reached about **+45 mm**, then swung to about **−75 mm** before settling near the start. This is the least reliable part of the hand-held route and is reported as observed excursion, not a clean 60 mm scale result.
- Lift segment: about **−48 mm on Y** (upward), versus the instructed 40 mm target.
- Yaw: approximately **−8.1° to +11.9°** around the start orientation; final yaw offset about **−0.3°**.
- Maximum position displacement from the first valid pose: **82.7 mm**. End displacement from that pose: **19.7 mm**.

These measurements show the expected forward/up directions, approximate metric scale under the instructed small motions, yaw response in both directions, and return to the starting neighborhood. They do not establish a calibrated per-axis error bound. The user accepted this bounded route result for HW04.

## Continuity, age, and output rate

Over the valid route epoch, the adapter accepted optimized odometry at approximately **6.69 Hz** and propagated odometry at **171.7 Hz**. Latest source rates were left/right **15.0 Hz**, IMU **172.0 Hz**, optimized/telemetry **6.69 Hz**, and propagated **171.2 Hz**.

| Stream | Maximum source age | Fixed source budget | Maximum current receipt age | Fixed receipt budget |
| --- | ---: | ---: | ---: | ---: |
| Left IR | 0.101 s | 0.185 s | 0.082 s | 0.233 s |
| Right IR | 0.101 s | 0.187 s | 0.080 s | 0.233 s |
| IMU | 0.078 s | 0.168 s | 0.037 s | 0.138 s |
| Optimized / telemetry | 0.729 s | 0.868 s | 0.289 s | 0.616 s |
| Propagated | 0.052 s | 0.202 s | 0.012 s | 0.136 s |

The largest optimized/telemetry receipt interval during tracking was 0.403 s, below its 0.616 s budget. The 0.180 s IMU and 0.180 s propagated maxima occurred at startup admission and did not grow during tracking; current ages remained within budget. No native VINS queue high-water field is present in the installed binary, so backlog is supported indirectly by output gaps and source/receipt age, not independently measured inside the estimator.

A short diagnostic `ros2 topic hz` observer was attached only after the failed run04, not during either route. It measured 14.9/15.0 Hz IR and 245.8 Hz IMU at that later time. The sensor log contained USB `control_transfer` EAGAIN warnings; they were not proven to cause run04's one-pair failure.

## Stop, epoch, and cleanup

- The owned helper stopped VINS first for epochs `25814…`, `535e…`, `760681…`, and `857587…`; where the epoch had reached valid tracking, the adapter logged same-epoch `valid=false` after VINS stopped.
- Post-route successful fresh epoch `857587dc6aa140ffb415e3d99dc542ee` was distinct from route epoch `535e81e4b7a74ee8ac61466a15580683` and remained valid for 51.3 s before the stop test.
- Nano `net.core.rmem_max` was restored from the temporary 8 MiB to its original `212992`. The owned sensor session was stopped. Final `ros2 node list --no-daemon` and process inspection were empty for this project.

## Targeted verification

- `python3 tools/test_localization_health.py`: **12 passed**.
- `python3 -m py_compile src/own/uav_localization/uav_localization/health.py tools/test_localization_health.py`: passed.
- Nano: `colcon build --executor sequential --packages-select uav_localization --cmake-args -DBUILD_TESTING=OFF`: passed.
- `git diff --check`: passed after progress updates.

## Raw artifacts

All paths below are relative to the repository root. Raw logs are in `artifacts/runs/` and are ignored by Git.

- Main route manifest: `artifacts/runs/hw04-measured-route-20261103-03/session/session.json`, SHA256 `fe8f119c61235a4fcf8f0b13d89d8f8b23a745d0816cf9167c7edfafb9ef2791e`.
- Main route localization log: `artifacts/runs/hw04-measured-route-20261103-03/localization-final.log`, SHA256 `a1493fdd1cd3bb7e295927fb915fd9dd5e020c2a5a8e4b83e1ace2390e283e1c`.
- Main route VINS log: `artifacts/runs/hw04-measured-route-20261103-03/vins-final.log`, SHA256 `b421aa192881f5d1bbfefc69c02c261faccefd774456b6a6884fab6334ef57db`.
- Post-route fresh-session manifest: `artifacts/runs/hw04-post-route-fresh-20261103-05/session/session.json`, SHA256 `3e0f35dd8dc78d775fcc29c68ef6e4f256ad751921976d927c50faec4396db5f`.
- Post-route fresh-session localization log: `artifacts/runs/hw04-post-route-fresh-20261103-05/localization-final.log`, SHA256 `2fc4b6a7aa75596ec230b3e7dd0122ea04c55d2ef51c51d0894bd34c95f36877`.
- The failed first admission and run04 one-pair startup attempt, plus exploratory run02, remain preserved in their respective run directories.
