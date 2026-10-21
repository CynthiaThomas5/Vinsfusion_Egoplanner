# P5 VIO→EKF2 世界系统与融合诊断

- 日期与任务 ID：2026-10-17-045。
- 用户目标与明确约束：继续完成 GOAL.md 的 P5；只运行单 D435i SITL 诊断，禁用 GNSS 位置辅助与 Gazebo truth odometry，不启用 Offboard、不解锁；保持 PX4 bridge 为唯一控制出口；失败尝试保留并如实记录。
- 已确认的决定：诊断世界使用 PX4 默认物理环境、地面和坐标元数据，加项目校准墙与 PX4 server.config 中全部世界系统；生成副本记录 PX4 世界、系统配置及项目几何哈希。保留现有 PROVISIONAL 定位健康门，不为通过而放宽。
- 后续结果：#95 的 telemetry_stale 在 #96 未复现。#96 运行75秒且定位末端 TRACKING，PX4 ULog 证明 EV 位置/yaw 持续融合且 GNSS aiding flags 为零；45秒只读探针记录原始 VINS 流间隔。末端唯一 readiness 原因为 px4_timesync_stale，bridge 控制保持禁用，未解锁或飞行。
- Agent 建议及待确认项：先诊断 PX4 timesync freshness/readiness 后再重复验收；保持控制禁用与现有健康阈值。当前没有待用户确认项。
- 实施范围：更新 PX4 VIO 诊断世界生成工具和测试，新增只读时序探针；run #94 因模型搜索路径错误排除，#95 观测到融合但末端健康锁定，#96 重复验证持续 tracking 与 EV 融合；更新证据和当前进度，P5 仍不标为通过。
- 对应改动记录：progress/changes/2026-10-17-045-p5-vio-ekf2-world-systems.md。

