# P5 悬停与小目标视觉闭环诊断（#184–#187）

## 改动与行为

本条主要保存 SITL 诊断证据；#184–#187 使用 run-local 探针，不修改 canonical 控制逻辑或健康阈值。#186 完成一次20.007秒 no-goal hover；#187 发送小 3D 位置与 yaw action 后，被现有 `normalized_cost_exceeded` 门控中止，没有到达目标。

## 验证

- 每次 SITL 均检查无真值位置输入；debug_truth 只由 `raw_vins_readonly_probe` 只读订阅。
- #186 报告696条单调 PX4 轨迹设定点，并确认 landed/disarmed。
- #187 完成90秒真值／IMU采集；离线用一次固定尺度 SE(3) 对齐评估294组 flight-window 位姿，位置 RMSE/P95 为2.94/5.64 cm。
- #187 PX4 ULog 观察到 EV position/yaw 融合和零 GNSS position aiding；降落阶段记录短暂 failsafe 状态，因此该轮不属于 failsafe-free 证据。
- `tools/evaluate_vio_quality_alignment.py` 对 #187 计算首个质量锁点、代价变化和对齐误差；视觉代价占89.1%，不据此推断因果。

## 证据与限制

完整报告、run 目录与原始文件哈希见 [证据报告](../evidence/p5-vio-hover-goal-diagnostic-20261019-184-187.json)。#184/#185 是 freshness／preflight 诊断；#186 只证明一次 no-goal hover；#187 的 action 未成功。P5、P6 均未通过。

## 下一步

查清 independent cold start 下 VINS telemetry freshness 和 PX4 preflight 的间歇差异，再重试有限目标；健康门限保持不变。
