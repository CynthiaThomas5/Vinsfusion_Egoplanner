# #335 N10.2 证据覆盖与风险处置

## 工作范围与结果

完成 N01–N09 历史证据对 GOAL A/F 与 N11–N16 后续需要的覆盖分析。N10=`in_progress`；N10.2 审查完成，下一子项 N10.3。未运行算法实验、SITL 或飞行；既有通过项不复测。

## 决定

- 保留 N01–N09 原身份和范围；明确 N05/N06 旧 raw-known-free 证据的规则边界，N06 曲线仍是 planner-only。
- N02/#332 健康原因保持未知，所有质量/时序门不动；按已有安全落地路径界定失败处理，不把它改写成误报。
- N08 只支持已测低速：0.1 m/s 逐轴、0.25 m/s²、实际向量速度上限 0.12 m/s；短程停车结果不推广到默认0.5 m/s配置。
- GOAL F 固定为位置≤0.30 m、yaw≤15°、连续≥3仿真秒；当前1秒 dwell 和 wall-time arrival window 必须在 N10.4统一。
- 记录目标超时 simulation/wall 时域错配、长程/10分钟支持、官方策略重规划期限、N04一格地图阈值、unused occupancy field、manifest覆盖及 portable image archive等 N10 后续动作。

## 验证／过程

- 汇总 N01/N02/N03/N04/N08/N09 的机读证据；N09 arrival报告确认1秒 native dwell与墙钟连续窗约1.03–1.10秒。
- `progress/evidence/n10-evidence-coverage-20261026-335.json` 记录证据、限制、风险状态、决定和冻结前条件。
- 校正 #334 的75秒 timeout解释：75秒只约束 takeoff-to-ACTIVE；goal timeout180仿真秒，client wall wait184秒，低 RTF时可能提前过期。

关联对话摘要：`collaboration/dialogues/2026-10-26-335-n10-evidence-coverage.md`。
