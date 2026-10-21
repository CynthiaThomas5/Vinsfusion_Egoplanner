# 任务对话摘要

- 日期与任务 ID：2026-10-19，#070。
- 用户目标与明确约束：继续推进单 D435i、无 GNSS 的 P5 VIO/EGO/PX4 SITL；truth 只供独立只读评估；PX4 控制由 bridge 独占；不放宽 health、freshness 或 Offboard 门限。
- 已确认的决定：#189 的 PX4 preflight false 与当前 AUTO_LOITER 状态相伴，Offboard 起飞路径要先 disarmed prestream，再在 Offboard 状态通过 preflight 后解锁；不能把 pre_flight_checks_pass=true 当作 prestream 的前置条件。#189 的一次性 PRESTREAM 被 zero estimated_offset 源戳 freshness 锁定中止；#190 的 run-local preflight 守卫因此未请求 enable。#191 仅将 run-local 连续 freshness 等待从2秒延长到5秒，未更改 canonical bridge 或阈值。
- Agent 建议及待确认项：保持 normalized_cost=1.0；继续检查视觉残差与 feature-track 时间线，并单独查明降落阶段 Offboard signal loss/failsafe 转换。当前没有证据证明代价根因，也不声明 failsafe-free。
- 实施范围：#188–#190 的 ULog/PX4 源码离线复核；#191 低动态短目标 SITL；新增运行证据、离线 ULog 摘要、对齐评估及进度记录。canonical 运行时代码和 PX4 参数未修改。
- 对应改动记录：progress/changes/2026-10-19-070-p5-startup-freshness-and-low-dynamics.md。
