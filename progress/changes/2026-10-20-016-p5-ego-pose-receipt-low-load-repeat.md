# P5 EGO pose receipt 低负载复测 #225–#226

对话摘要：[2026-10-20-016](../../collaboration/dialogues/2026-10-20-016-p5-ego-pose-receipt-low-load-repeat.md)。证据：[run #225](../evidence/p5-vins-anisotropy-filter-pose-receipt-patch0015-20261020-225.json)、[低负载 run #226](../evidence/p5-vins-anisotropy-filter-pose-receipt-low-load-repeat-20261020-226.json)。

- **范围**：#225 在独立 EGO 源副本按 0012→0013→0015 顺序应用已记录补丁并构建五个 EGO 包；#226 复用该二进制与 bridge 安装。没有改 canonical VINS、健康阈值、PX4 参数、控制状态机或地图配置。两轮均无 truth 输入，PX4 控制设定点仍由 `uav_px4_bridge` 独占。
- **#225**：定位/PX4 前置条件可用，但稳定门以 `imu_stale` 关闭，未发送 action goal，PX4 保持 disarmed。EGO patch-0015 计数显示 pose receipt 停在 source stamp 10.036 s，独立 harness 看到转发 pose 到 15.052 s；depth receipt 28→49，pose/depth message-lost 回调均为零。该 harness 自身仍订阅 raw depth、forwarded depth 和 occupancy cloud，因此不是低负载结论。
- **#226**：run-local harness 移除了 raw depth、forwarded depth 与 occupancy cloud 订阅，以 `/mapping/status` 的 occupied count 与 `input_ready` 保留原地图门。四次可恢复的 pose receipt 停顿共 98 条 timeout warning；末组 EGO 计数停在 source stamp 42.704 s，对端转发流到 44.156 s，depth receipt 继续且 lost 回调仍为零。前置门通过并派发 0.30 m/+30° 目标，action 以 `goal_timeout` 结束。之后定位在 source 44.300 s 以 `normalized_cost_exceeded` 失效；PX4 进入 AUTO_LAND、触地并解除武装。ULog dropout 为零、GNSS aiding 标志为零。goal timeout 与后续质量门锁存分开记录，不推断因果。
- **验证类型**：run-local 补丁 pre/post 哈希检查与 EGO 五包 colcon build（#225）；launcher `bash -n`、harness `py_compile`、容器内 ROS `MapStatus` 导入与依赖前缀检查（#226）；两轮真实 SITL 结果见轻量证据。结构状态检查不代替构建、回放、SITL 或实机验收。
- **结果与边界**：#225/#226 的 evidence report 所列 22/24 个文件 SHA-256 全部匹配。低负载复测降低了“外部图像/点云观察器造成停顿”的可能性，但不能区分 DDS reader 未取样、executor 延迟或回调处理问题；RMW 的 message-lost 回调为零不代表无消息丢失。P5 导航未通过，所有阈值保持原值。
- **下一步**：检查 EGO executor 与 ROS 2 message_filters 的实际 take/回调路径，设计不订阅额外图像负载的低开销分阶段 trace；确认诊断点后再复测，不放宽 freshness、bias、cost 或 PX4 门限。
