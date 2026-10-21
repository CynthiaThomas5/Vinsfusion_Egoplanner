# P5 PX4 timesync、遥测与源时间对齐

- 用户请求：继续推进 GOAL.md 当前阶段。
- 任务范围：诊断 P5 VINS→PX4 EKF2 时间映射与 readiness；保持 PX4 bridge control disabled，不解锁、不飞行，不把结构检查或单项融合观测标成阶段通过。
- 已确认决定：PX4 lockstep 下 freshness 按仿真源时钟判断，同时保留墙钟接收上限；rig-frame 配对改为比较共同仿真域的 ROS/PX4 源戳。
- 结果：#104 观测到原始 VIO sample stamp 经 XRCE 传到 PX4，EV position/yaw 融合，无 GNSS aiding/truth 输入，timesync age 最大4ms。bridge readiness 未通过：末端是当前 DISABLED 模式下的 PX4 preflight failure；期间有66/570条状态报告 telemetry stale。P5 保持 in_progress。
- 约束：未调用 `/uav_px4_bridge/enable_offboard`，没有预流、Offboard 控制、arming 或飞行；不放宽 P2 健康阈值。
- 待处理：用新加的 per-source telemetry age detail 做 live capture，判断间歇 stale 来源；在继续控制路径前确认 disarmed prestream 的授权和验收边界。
- 改动记录：[`2026-10-17-046-p5-px4-time-domains-and-readiness.md`](../../progress/changes/2026-10-17-046-p5-px4-time-domains-and-readiness.md)。
