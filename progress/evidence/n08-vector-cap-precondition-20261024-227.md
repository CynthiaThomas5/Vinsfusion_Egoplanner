# N08.2q #227：低速向量速度门与运行前置诊断

**结果：#227 未完成，速度假设没有得到曲线验证；无 XY。** 两份新 run 都在生成可用 B-spline 前被前置条件挡住，N08 execute 继续锁定。

第一份 run `n08-20261024-227-vector-cap-01` 未按 #225 流程先做支持扫描。fresh N05 current-area online/offline 一致拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`；TAKEOFF_CONTACT 有 436 个 unknown，HOLD 最大 566 个 unknown。没有启动 N08 runner。

第二份 run `n08-20261024-227-vector-cap-02` 使用与 #225 相同的 `n08_overhead_calibration`／`n08_overhead_free_sector_view` 支持扫描，完成 15/15 stages。post-release 和 mission current-area N05 online/offline 均通过，epoch/map_id 一致；初始静止图因 ground-plane raw occupied voxel 不足而拒绝。fixture helper 仍报 `fresh DISARMED status is required for every fixture command`，该错误保留；fixture report 显示已 detach/remove，Gazebo 实时模型列表没有 fixture，N05 新鲜回读显示 bridge DISABLED、未武装、landed。

mission 前检通过，但 compute-only runner 在发 goal 前以 `vio_bridge_map_preconditions_not_ready` fail-closed，最终 landed/disarmed。LocalizationStatus 最初仍为 fresh，随后锁存 `telemetry_stale`：source stamp 停在 sim 513.380 s，status header 继续到 567.800 s，`accepted_optimized` 保持 7638；该间隔约 54.42 s。`vio.log` 在 sim 513.284 s 出现 mapping gate closed，并在 513.384 s 将 map_id 从 `...3e2048befa8049c3b54911d0f27cd1e4` reset 为 `...4e1f9ca5158c4ed2838d879af8bc6fbb`。VINS logger 随后仍有 solver 输出直到 sim 641.092 s，但没有 ROS topic 到达记录，不能据此断言 raw odometry/telemetry 仍在发布。

目标、READY 样条均未出现；same-run spline/map capture 记录为 `matching_goal_epoch_bspline_not_observed`。修复过的证书评估器将本 run 记录为 `compute_only_runner_not_passed`，而不是曲线通过。PX4 boot readback 为 `MPC_ACC_HOR=3`、`MPC_ACC_HOR_MAX=5`、`MPC_JERK_AUTO=4`、`MPC_XY_VEL_MAX=12`；它们是最大限制，不提供最小减速度或响应延迟上界。

作为评估器数学实现校验，纯 NumPy de Boor 重算 #225 archived B-spline 得到时长 5.267489712 s、导数控制点速度范数上界 0.201796891 m/s、稠密峰值 0.193695042 m/s，逐项与 #226 审计一致；这只是既有曲线的离线方法校验，不是 #227 新 profile 的运行结果。

## 运行证据

- `artifacts/runs/n08-20261024-227-vector-cap-01/`：N05 fresh gate、raw map、preflight 和在线／离线拒绝记录。
- `artifacts/runs/n08-20261024-227-vector-cap-02/`：N05 15 阶段支持扫描、post-release/current-area maps、mission preflight、`flight.json`、PX4 参数、VIO 日志、失败的曲线捕获与 no-go 证书。
- #02 容器停止命令 `bash tools/project.sh stop n08-20261024-227-vector-cap-02` 返回 0；运行记录显示 bridge disabled、disarmed、landed，fixture 不在模型列表。

下一步 #228 增加只读 ROS source/receipt timeline，同时记录 raw VINS telemetry、raw/adapter odometry、LocalizationStatus、MapStatus 和 `/clock`，区分上游发布与 adapter 接收／配对中断。未定位前不发送导航目标或 XY。
