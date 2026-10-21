# 任务对话摘要

- 日期与任务 ID：2026-10-20，继续项目 Goal；P5 run #208–#209。
- 用户目标与明确约束：继续推进 GOAL；保留定位 freshness、normalized-cost 与 PX4 控制安全门，不使用真值，不把单次 action 结果写成通过。
- 已确认的决定：复用 #207 的 run-local anisotropy-filter 二进制，使用既有 0.30 m 横移、30° yaw 目标重复尝试；#208/#209 未过前置门时不再派发目标。
- Agent 建议及待确认项：定位适配器记录 `telemetry_stale` 后保持 fail-closed；下一步用只读时间线核对 estimator telemetry、优化/传播里程计、`/clock` 与 LocalizationStatus 的源戳和收包年龄。
- 实施范围：隔离 SITL 两轮、PX4 ULog分析、run-local 来源清单和轻量报告；无飞行目标派发，无安全门改动。
- 对应改动记录：progress/changes/2026-10-20-008-p5-anisotropy-filter-preflight-repeat.md
