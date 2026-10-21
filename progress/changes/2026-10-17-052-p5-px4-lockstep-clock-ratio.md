# P5 PX4 lockstep 与 Agent wall-clock 对照

对话摘要：[2026-10-17-052](../../collaboration/dialogues/2026-10-17-052-p5-px4-lockstep-clock-ratio.md)。

## 结果

- #113 使用 ROS domain 229、新 Gazebo partition 和独立 PX4 build 副本运行45秒被动 SITL。保留 PX4 lockstep、Gazebo D435i 机体模型、XRCE Agent、vio_closed_loop 参数配置与 DISABLED bridge；未启动 VINS/localization，不发布控制。
- 记录11,238个 `/clock` 样本、45条 DDS `TimesyncStatus`。仿真时钟端到端速率为1.000005仿真秒/墙秒，`observed_offset` 对墙钟线性斜率为−0.000003秒/秒；无 estimated_offset 零值 reset、无 PX4 debug reset 消息。Agent 会话建立一次，车辆保持 disarmed，控制话题零样本；profile 的 `EKF2_GPS_CTRL=0`，GNSS aiding flags 全零，未发现 truth topic/subscription。
- 与全 VIO #112 对照：其仿真速率0.417598、observed_offset斜率−0.582393，两个速率绝对值之和0.999991并出现两次滤波器 reset。#113 两者速率和为1.000008且未 reset。两组结果强烈支持 offset 漂移近似 `RTF - 1`，并指向慢速 lockstep 仿真相对 Agent wall-clock 的时基差。
- #113 移除了 VINS 与 localization 计算，不能单独证明 VINS 是唯一负载来源，也不证明全视觉链可维持 RTF=1。VIO送达数为0，bridge 因 `localization_not_tracking` 保持 DISABLED，未观察 EV fusion 或 readiness；不作为 P5 通过证据。

完整 SITL 输出、PX4 ULog、配置、探针与哈希见[轻量证据](../evidence/p5-px4-lockstep-clock-ratio-20261017-113.json)及 [run artifacts](../../artifacts/runs/p5-px4-lockstep-clock-ratio-20261017-113/)。

## 验证与下一步

- `bash -n` 运行脚本、`python3 -m py_compile` 分析器通过；45秒被动SITL完成，离线统计与原始 `/clock`、TimesyncStatus 样本一致。
- `python3 tools/project_status.py` 与 `git diff --check` 在完成记录后运行。
- 下一步对完整 VINS/建图/规划负载作 CPU 与 Gazebo RTF profiling；优先在不改变相机规格、定位健康门和PX4来源参数的条件下恢复实时。如果无法维持实时，再设计有明确 profile 边界的仿真时基处理，并通过有效 VIO 重复验证。P4/P5/P6 与 GOAL A–H 仍未完成。
