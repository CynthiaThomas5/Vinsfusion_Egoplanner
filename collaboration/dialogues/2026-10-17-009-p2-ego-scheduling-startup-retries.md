# P2 EGO 调度诊断重试与定位启动失败

日期：2026-10-17

- 用户约束：继续推进 GOAL.md；保护已有 staged／unstaged 改动；不推送；不启动 PX4 控制或实机飞行。
- 运行：run #26 使用 patch 0012 隔离 overlay、全新 epoch/domain。深度 READY；VINS 日志含 `Initialization finish!` 和连续 solver 输出，但 localization adapter 进入 `initialization_timeout`，状态 WAITING→DEGRADED→LOCKED。没有被 adapter 接纳的优化里程计，没有 EGO depth/pose 对，未触发 EGO timeout 诊断。
- 决定：run #26 与 #25 均作为定位启动失败保留并排除；不再仅靠重复 EGO 运行来碰运气。先比较 run #23 与 #25/#26 的 VINS telemetry、raw odometry、publisher identity、输入年龄和 adapter 接纳门控，再恢复有效 TRACKING。
- 待决：定位输入接纳差异；随后采集 patch 0012 steady-clock 指标，解释 run #24 in-window timeout。
