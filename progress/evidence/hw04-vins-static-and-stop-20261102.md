# HW04 VINS / localization static and shutdown evidence

Status: **partial; HW04 remains in progress.** The static hardware localization and VINS-stop invalidation exits passed. The required 2–3 minute hand-held translation/lift/yaw/return route was not performed, so direction/scale, route displacement, return error, and dynamic backlog exits are not passed.

## Scope and identity

- Reused the serial-specific HW03 rig `c8c42778007c28a05acbeeca7533fb56ce67af175c3da337441f1d69ee2a9865` and hardware settings `d87f449536ab18b702f3e6acb13eaef53b26c6a2fa73a7be4e9d35da87239d26`.
- Nano workspace: `/home/jetson/D435i-VINS-EGO-ROS2-hardware`; runtime used Foxy, `use_sim_time=false`, system ROS time for source age, and monotonic receipt age.
- Final static session epoch: `ba46bb737bf24c449f37db0c9088bd16`; manifest SHA256 `35e06e3d6722ed2c10d92a47f26e270a1f48361920e09c131d2366e07d8a379f`.
- The immediately preceding stopped session used epoch `2665008815814d2a83d5825fb68d9097`; the new run used a distinct epoch and a newly generated session.

## Static run

The camera remained stationary. No extra ROS observer or high-rate probe was attached. VINS used UDPv4 with a 4 MiB receive-buffer request and the Nano's `net.core.rmem_max` temporarily set to 8 MiB; the localization adapter retained the normal SHM+UDP profile. The temporary kernel value was restored to 212,992 after shutdown.

Epoch `ba46bb737bf24c449f37db0c9088bd16` remained `TRACKING/valid` for 309.538 seconds across 302 one-second internal observations. Measured steady output rates over the run were approximately:

| Stream | Rate | Maximum source age | Configured source-age budget |
| --- | ---: | ---: | ---: |
| Left IR | 15.00 Hz | 0.177 s | 0.185 s |
| Right IR | 15.00 Hz | 0.179 s | 0.187 s |
| IMU | 166.71 Hz | 0.068 s | 0.168 s |
| Optimized odometry + telemetry | 6.82 Hz | 0.479 s | 0.868 s |
| Propagated odometry | 166.39 Hz | 0.074 s | 0.202 s |

The maximum displacement of the 302 logged optimized poses from the first valid pose was 0.990 mm; final displacement was 0.933 mm. This is a static stability observation, not a scale or route-accuracy result. The optimized and telemetry source streams remained paired. The cumulative maximum receipt interval for IMU was 0.193 s, above its 0.138 s budget; this maximum occurred at initial admission and did not increase during the subsequent five-minute tracking interval. Other cumulative maximum receipt intervals were left 0.227 s / budget 0.233 s, right 0.227 s / 0.233 s, optimized 0.355 s / 0.616 s, telemetry 0.355 s / 0.616 s, and propagated 0.064 s / 0.136 s.

Host UDP `RcvbufErrors` increased by zero between the pre-run snapshot and the snapshot taken after stopping VINS. The earlier buffer trial tuned only the adapter receiver while VINS remained at its default receive size; that run accumulated 3,578 UDP receive-buffer errors, saw only 2 optimized and 8 telemetry samples, and locked `telemetry_receipt_stale`. Moving the receive-buffer profile to the VINS participant eliminated the observed kernel receive-buffer errors and produced the stable static run.

## Stop and process cleanup

- `tools/hardware-localization.sh stop` stopped VINS first and observed a same-epoch `valid=false` adapter record afterward (`invalid_status_observed=adapter_log_after_vins_stop`). The final stop reason was `propagated_receipt_stale`, as expected after removing VINS output.
- The owned D435i session was then stopped. A fresh `ros2 node list --no-daemon` returned no nodes; process inspection found no VINS, localization, camera, or depth-conversion process.
- `net.core.rmem_max` was restored to its original 212,992 value. No localization or sensor ownership state remains on the Nano.

## Runtime limitations and unfinished exits

- The static run does not demonstrate direction or metric scale under motion, route displacement/return error, or behavior under translation/lift/yaw.
- The installed VINS binary SHA256 was `98933f87e7f068f985112a8b5077f5ebd57c607caaa9bf6939abb7474d3eeeda` (timestamped Oct 18). Its accepted odometry/telemetry path ran, but its telemetry did not contain the later native queue high-water fields. Flow-level ages and output frequency showed no growing latency during this static run; native estimator queue high-water was not independently measured.
- No camera movement was observed during the offered route window, so the physical route remains pending. The Nano is shut down cleanly and must be restarted with a fresh session when the route can be performed.

## Artifacts

- Raw final VINS log: `artifacts/runs/hw04-udp-vins-rxbuf02/vins.log`, SHA256 `a9c4c66c50d90c0a923d7371fec6e823cacdf7711eb401f8af37bc406db0aa71`.
- Raw final localization log: `artifacts/runs/hw04-udp-vins-rxbuf02/localization.log`, SHA256 `337a6a40203751103e04aa9650717bf782471039fdbea55bf637e156663a38be`.
- Session files: `artifacts/runs/hw04-udp-vins-rxbuf02/session/`.
- Per-run profile used in the successful runtime: `artifacts/runs/hw04-udp-vins-rxbuf02/fastdds_udp_rxbuf4m.xml`.
- Canonical VINS profile: `config/hardware/vins_fastdds_udp_rxbuf4m.xml`, SHA256 `f036afb14878744347e3da2702d05a07437686ca4f3290253be393016c609581`.
- UDP snapshots and the failed receiver-placement control: `artifacts/runs/hw04-udp-vins-rxbuf02/udp-{before,during2,after}-snmp.txt` and `artifacts/runs/hw04-udp-rxbuf01/`.
