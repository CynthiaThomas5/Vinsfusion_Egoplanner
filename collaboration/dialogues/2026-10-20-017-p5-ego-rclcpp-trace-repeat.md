# 任务对话摘要

- 日期与任务 ID：2026-10-20，017。
- 用户目标与约束：继续 P5 单 D435i、无真值 VINS→EGO→PX4 SITL 诊断；保留 canonical 定位质量、安全与 PX4 freshness 门，不改变唯一控制发布者边界。
- 已确认的决定：在 #226 低负载 harness 和 #225 run-local EGO overlay 上启动 #227；加入 ROS 2 core LTTng trace，图初始化后只跟踪 EGO PID 902；继续使用同一 0.30 m 横移、+30° yaw 目标和 0.01 run-local feature filter。
- 结果：目标 action 成功；PX4 ULog 记录 EV position/yaw/velocity fusion、GNSS aiding 全零、无 dropout，并最终 touchdown/disarmed。EGO trace 的首 32.5 秒窗口内，相机位姿 successful RMW take 最大间隔 1.713745 秒，depth / optimized odometry 分别为 0.255020 / 0.268764 秒；相机位姿 callback 最大 2.970 ms。独立 pose observer 最大 receipt gap 0.264985 秒。trace 未采上游 publisher，也未按消息 header stamp 一一配对，无法判定 DDS reader 与 executor 哪层造成停顿。normalized_cost_exceeded 出现在 LANDING 阶段，与 action 成功及降落分开记录。
- 待决问题：EGO reader 长间隔来自 publisher/DDS 交付、wait set readiness 还是 executor 调度；还需要同窗 publisher write 与 EGO header-stamp receipt 对照。
- 实施范围：新增 run-local trace 与 ULog 汇总、轻量证据、当前状态/索引和记录；没有修改 canonical 算法、参数、QoS、安全门或 PX4 控制逻辑。#227 不算 P5 通过。
- 下一步：#228 同时采上游 camera-pose publisher 与 EGO，记录 source header stamp 的 publish/receipt 以及 executor wait/ready 时间；维持低负载 harness、唯一控制发布者和无真值约束。
- 对应改动记录：progress/changes/2026-10-20-017-p5-ego-rclcpp-trace-repeat.md
