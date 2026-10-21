# P2 EGO pose reader RMW trace 诊断

日期：2026-10-17

- 用户目标：继续完成 GOAL.md 的 P0–P6 与 A–H 验收，不降低范围。
- 用户约束：保护用户已有 staged／unstaged 工作；只读第三方源码；仅推进单 D435i 仿真链路；不启动 PX4 控制或实机飞行。
- 观察：patch 0016 将 EGO pose reader history 设为100后，健康 #43/#44 仍有31/90条窗口内 timeout。两次 trace 中 adapter 的 pose/depth 发布最终均对应到 EGO `rmw_take`，但 pose publish→take 延迟远高于 depth；#44 的两组间断中有15/23条 pose 在约2秒后被批量取。callback/executor trace 未显示长 callback 或大于约90 ms 的 wait。
- 解释边界：症状位于 EGO pose 消费路径，延迟涉及 DDS reader availability/notification、executor ready-entity选择或其他RMW原因仍不能区分。外部 probe callback wall interval 不作为 publisher 运行时证据。时序trace可能增加系统负载。
- 决定：history=100只保留为诊断补丁，不宣称修复；0.4秒 timeout 与 `ground_height=-0.15 m` 继续标记 PROVISIONAL；禁止在共享 GridMap 输入、timer、reset状态未加锁前改为多线程。
- 环境限制：容器报告 kernel tracer unavailable；宿主 `perf` 读 `sched_switch` 被 `/sys/kernel/tracing` 权限拒绝，当前无法采集内核调度状态。
- 下一步：检查 Jazzy RMW/Fast DDS reader通知与端点配置；保持项目无PX4控制。相关证据见[progress/evidence/p2-ego-reader-delivery-trace.json](../../progress/evidence/p2-ego-reader-delivery-trace.json)。
- 对应改动记录：[progress/changes/2026-10-17-014-p2-ego-reader-delivery-trace.md](../../progress/changes/2026-10-17-014-p2-ego-reader-delivery-trace.md)。
