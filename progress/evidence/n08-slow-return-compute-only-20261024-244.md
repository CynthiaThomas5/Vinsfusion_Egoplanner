# N08 #244：慢垂直回程、N05 准入与 compute-only

## 结果

- 新增 16-stage `n08_overhead_free_sector_view_decoupled_slow_vertical_return` profile；相对 #243 只把末端 z=0.5 m→0 m 支架回程由 7 s 延长到 20 s。定向 profile 测试 33 项通过。
- N05 支架动作完成 16/16。helper 的 `fresh DISARMED status is required for every fixture command` 错误保留；夹具实际 detached/removed，独立 fresh 读回确认 DISARMED、landed、at-rest，bridge 控制关闭，fixture model 不在 Gazebo。post-release 与 mission current-area N05 online/offline gate 均接受 `all_entry_phases_known_and_clear`，same epoch/map，`diagnostic_pass=true`。
- compute-only mission 的 readiness preflight 与专用 12 项 evaluator 通过：EGO READY、cancel accepted/action canceled、桥保持、落地并解锁。EGO goal/curve 通过 remap 与 PX4 隔离，没有 XY 控制或制动测量。
- 同 run stop-corridor certificate **未通过**：启动 manifest 使用 `n08_low_speed_calibration.json`（max_vel=0.15 m/s），但 evaluator 要求 `n08_low_speed_vector_cap.json`（max_vel=0.075 m/s），因此返回 `lowered_speed_profile_not_used`，并未继续认证速度或几何。下一 run 应从 launch 起使用正确 vector-cap 配置并重新获取同 run fresh map。

最终 readback：DISARMED、landed/at-rest、bridge `LANDED` 且 control disabled、fixture absent；容器 stop exit 0。无 HRT/ROS observer、XY 或制动结论。

机器证据及 SHA-256：[JSON](n08-slow-return-compute-only-20261024-244.json)；原始产物：`artifacts/runs/n08-20261024-244-overhead-free-slow-vertical-return/`。
