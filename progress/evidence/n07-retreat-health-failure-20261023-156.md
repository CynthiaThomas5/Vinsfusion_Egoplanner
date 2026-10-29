# #156 N07 远后退重复性诊断

## 结果

- 新冷启动 `n07-20261023-156-01`，`spawn=-6.5m`，复用 #155 的 2.4m 纯平移后退/返回。初始 fresh N05 online/offline 一致拒绝 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope`。
- 向后段到达目标；返回末段触发 `accel_bias_norm_exceeded`。#156 仅完成 3/6 阶段，未产生 attached-check readiness marker，也没有解锁。fixture 安全返回支承位置并确认 detach、删除；PX4 `arming_state=1`，bridge DISABLED、landed=true。
- `health.json` 原门限为 0.15 m/s²；记录到的加速度 bias 首次在 sim 229.848s 超过门限（0.150071），峰值 0.159841 m/s²。#155 同一 2.4m 路线的峰值是 0.141274 m/s²，低于门限。该路线不能按 2.4m 跨冷启动重复性认定健康。
- 支架脱离后的 N05 检查在 150s 内未取得 optimized odometry；VINS 锁存 `accel_bias_norm_exceeded`，MapStatus `input_ready=false/map_reset_acknowledged`，所以没有释放后准入。没有起飞，N07 合格悬停仍 0/3。

## 下一项

停止盲目重复 2.4m 路线。#154 在 0.8m 后视仍留未知，#155 的 2.4m attached gate 清除 unknown 但边际健康不足，#156 在 return 锁存。下一假设将后视距离取中间值 1.5m：相机仍能从目标包络后方获得约 0.85m 观察距离，同时减少运动基线；yaw/pitch、duration、判据和 runtime spawn 不变。必须先验证静态走廊，再做单次 DISARMED 诊断。

机器报告：[n07-retreat-health-failure-20261023-156.json](n07-retreat-health-failure-20261023-156.json)。原始轨迹、bias telemetry、N05 错误和 PX4 日志在 [`artifacts/runs/n07-20261023-156-01/`](../../artifacts/runs/n07-20261023-156-01/)。
