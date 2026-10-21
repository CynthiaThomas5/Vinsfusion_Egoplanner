# 任务对话摘要

- 日期与任务 ID：2026-10-17，027。
- 用户目标与约束：继续完成 `GOAL.md` 全部 A–H／P0–P6；遵守项目边界，保护已有工作区修改，不推送。此次仅执行正常时钟无目标诊断，不启动 PX4 控制或真机。
- 已确认：#57 使用 run-private 外部 faulthandler 信号，将 #56 的4次栈采样提高到80次。全部信号成功；executor generator 主线程 CPU中位数0.668 s/s。最常见瞬时栈在 `WaitSet.wait`（26/80）、waitable readiness（9/80）、waitable entity count（8/80）。这些计数不是CPU时间分布，不证明根因。
- 状态：850个定位状态样本中832有效；18个启动期 `waiting_for_propagated` 随后恢复为有效 tracking。EGO有47条 odom/depth timeout。导航存活到观察结束，wrapper清理完成。未发送 action goal、未启控制器／PX4；没有生产源码或参数变化。
- 未决事项：executor generator的高CPU来源、正常时钟 action 稳定性、EGO输入超时、重复 clean teardown、轨迹跟踪／到达、PX4 EKF2融合与飞行、以及 A–H 全部交付。
- 下一步：正常时钟下重测 caller-cancel 和活动目标 SIGINT，确认 status、地图／轨迹及停机表现；保持原 freshness 与 EGO timeout，不用相关性放宽标准。
- 对应改动记录：`progress/changes/2026-10-17-027-p4-navigation-stack-sampling.md`。

只保存必要脱敏摘要，不保存完整聊天。
