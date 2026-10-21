# P5 PX4 原始时间戳与 timesync offset 诊断

- 用户要求继续推进完整 `GOAL.md`，保留整个 P0–P6 / A–H 范围；本轮聚焦 P5 遥测 freshness。
- 遵守仓库边界：旧来源只读；此次使用独立的 PX4 SITL build 副本和临时 Jazzy 容器；没有真值订阅、控制发布、Offboard prestream、enable、解锁或飞行。
- 新只读探针记录 PX4 telemetry 原始 Agent 时间戳、最新 timesync estimated offset、恢复时间和收包时 `/clock`/monotonic。45秒 run #109 中定位 TRACKING、283条 VIO 到 PX4、EV position/yaw fused，GNSS flags全零，控制样本零且 disarmed。
- 34/345 次 `px4_telemetry_stale` detail 位于15.185–20.685 wall秒；estimated offset 从15.121秒开始更新，在20.638秒出现最后一次变化；最后 stale 出现在最后变化后47ms，此后24.33秒没有新 stale。高频 attitude/local-position 超20ms未来界限的176/1851、100/926条全部出现在调整窗口；收敛后 P95 分别4.758ms、8.847ms。该结果只来自单次运行，不能定义冻结策略。
- PX4 v1.17源码核对：EstimatorStatusFlags 在字段更新时发布；VehicleLandDetected 至少每1仿真秒发布，也因状态改变发布；VehicleStatus 每500ms或状态变化发布。此前对 land-detected 仅事件发布的表述不完整，已更正。
- 最终 readiness 仍为0，bridge DISABLED且 `px4_preflight_failed`；不算 P5 通过。#109 轻量证据：[progress/evidence/p5-px4-raw-timestamp-correlation-20261017-109.json](../../progress/evidence/p5-px4-raw-timestamp-correlation-20261017-109.json)。
- 待办：独立重复 offset 收敛观察，复核 PX4 HRT、timesync 与 Gazebo `/clock` 启动关联；保持现有阈值并 fail closed。随后继续 P5视觉导航、P4缺项及 P6/A–H。
