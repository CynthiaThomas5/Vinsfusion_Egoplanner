# 对话摘要：N08 #216 的定位 stale 锁存

- 用户担心 N07 改为累计通过、无需连续且已通过项不复测，会不会使后续任务卡住。
- 判定：验收方式合理。#198/#200/#204 的 N07 3/3 不被后续失败清零；#206/#207 PX4 HRT 时间参考修复与地面读回无需重测。实时 freshness 门仍保留。
- #216 支撑扫描和 N05 release/current-area gate 通过；compute-only 因 localization `telemetry_stale` 锁存而在 bridge DISABLED 状态拒绝，未解锁、无 goal、无飞行。故障后 raw VINS stream 已恢复新鲜，adapter status 的 source stamp 仍冻结，表明这不是 PX4 时间参考回归。
- #212 hold 通过、#213 N05 gates 通过，N08 并未被 PX4 问题整体卡住；但依赖 fresh localization 的单次 N08 任务会因锁存状态 fail-closed。
- 下一步 #217：从支撑扫描前持续采集到 N05 与 compute-only readiness 结束，抓首次 stale 及其 source/receipt/clock 对齐；若 bridge 进入 PRESTREAM，则先结束 observer。N08 保持 `in_progress`。
