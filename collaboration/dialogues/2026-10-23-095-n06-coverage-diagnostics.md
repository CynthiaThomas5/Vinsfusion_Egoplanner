# N06 coverage diagnostics

- 用户通过 `codex resume --last` 恢复此前明确的 Goal 完成模式，范围 N06；不创建新 Goal。
- 约束：N06/S4 未通过前保持 `in_progress`；unknown fail-closed、N05 几何／预算和原验收阈值不变；不运行 PX4、bridge、controller、setpoint、实机或 flight。
- #095 对 wall-r10／corridor-r10 的 source-03 raw body／hold 查询与采集相机 pose 做了独立几何投影。所有 unknown cell center 均未在采集视场中；射线清除／分类正确性未被证明。wall query 的 `no_fresh_fused_depth` 可能是 pending-pair 保守拒绝，但请求时状态未记录。corridor 末段缺少 fresh odometry 与定位 `normalized_cost_exceeded` 一致。
- 保留后续唯一变量：r21 将 yaw 峰值角速度降四倍，其他观测条件和静止位置保持。若定位 health lock，等待 motion/input 落盘后 runner 在 snapshot wait 前清理；若通过，继续 fresh snapshots 与无控制 live EGO。
- 待完成：`bash -n`、结构状态检查、执行 r21 并记录结果；N06.2 实际两布局正向集成仍未通过。
