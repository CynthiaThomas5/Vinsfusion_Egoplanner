# P5 悬停基线独立复测中止 #182

## 任务摘要

- 按 #181 的下一步，在同一单 D435i `vio_closed_loop` 参数和 run-local VINS 诊断 overlay 下重新启动独立 PX4 SITL，检查 no-goal 悬停基线能否复现。
- 继续保持唯一控制发布者、debug truth 只读隔离和原有 fail-closed 质量门。

## 结果

- PX4 参数快照和固件 SHA 与 #181 一致；定位、PX4 telemetry 前置门通过并进入 ACTIVE。导航 action 没有收到目标。
- Offboard dwell 不到1秒时 PX4 进入 failsafe/landing；bridge 最终 `LANDED`、解除武装。probe 以 `px4_preflight_failed` 安全中止。
- ULog 同时记录 `offboard_control_signal_lost` 和 `pre_flight_checks_pass=false`；电池相关 failsafe flags 与 BatteryStatus warning 为0。最近一段 OffboardControlMode 日志约10Hz、最大记录间隔0.132秒，具体的失联判定来源仍待查。
- 90秒只读真值 capture 成功；PX4 bridge 未订阅 truth，控制输入仍只有 bridge 发布。#182 排除出悬停基线精度统计。

## 决定与待办

- 不把泛化的“battery warning”提示音当作电池根因证据，也不降低阈值或重试起飞。
- 先核查 bridge 的 OffboardControlMode/TrajectorySetpoint 发布、PX4 接收与 timestamp mapping 的同一时间线；确认安全条件后再重跑悬停。
- P4/P5与 GOAL A–H 仍未完成。
