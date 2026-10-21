# P5 悬停基线独立复测中止 #182

## 改动与行为

- 以 #181 的 run-local VINS timing/cost overlay、同一 `vio_closed_loop` 参数和 20 秒无目标悬停探针开启新 PX4 SITL 副本；ROS domain 改为229、Gazebo partition 和 PX4 build 副本独立。
- 探针通过 localization、PX4 telemetry 稳定门并进入 ACTIVE；未发送导航目标。悬停不到1秒后，PX4 报告 Offboard 信号丢失并进入 failsafe/landing。桥接器跟随安全路径，车辆落地并解除武装。
- 运行图仍确认 PX4 控制输入仅由 `uav_px4_bridge` 发布，debug truth 仅供 `raw_vins_readonly_probe`；#182 保留为失败路径证据，不计为悬停基线。

## 结果

PX4 ULog 在36.184秒记录 `pre_flight_checks_pass=false` 与 `offboard_control_signal_lost=true`，36.196秒记录 failsafe。`battery_warning`、`battery_low_remaining_time`、`battery_unhealthy` 与 BatteryStatus warning 均保持0；日志中的通用快速告警音不能单独证明电池原因。OffboardControlMode 有102条日志样本、时间范围26.180–36.184秒，最大相邻间隔0.132秒；该记录没有显示触发前的大间隔，但信号为何被判失效仍未定位。

定位与 PX4 稳定前置门通过；probe 因 `px4_preflight_failed` 结束，20秒悬停未完成。failsafe 后 PX4 自动落地、disarmed。该轮不用于悬停精度或代价统计，也不解释 #181/#180 的 VINS 行为。

## 验证

- PX4 ULog `ulog_info`：v1.17.0、`No Dropouts`；事件时间和 Offboard/Battery 标志由 `pyulog` 解码复核。
- #182 只读真值 capture 90.014秒：929条 telemetry、3,048条 truth、12,308条 IMU；解析错误0、输出全有限。
- #182 运行图：truth topic 单一 observer；bridge 无 truth subscription，四个 PX4 控制输入由 bridge 独占。
- 该运行的 ULog、PX4/VIO 日志、报告、图信息和参数快照的 SHA-256 见 [失败路径证据](../evidence/p5-vio-hover-repeat-offboard-abort-20261019-182.json)。
- 容器及 SITL 进程已退出；#182 probe exit 1（保护中止），truth capture exit 0。未更改 canonical 源码、健康门或 PX4 参数。

## 局限与下一步

- ULog 记录了 Offboard signal-loss 标志，但在触发前最后一段有持续 OffboardControlMode 更新，因此更细根因尚不清楚。需要对齐 bridge 发布、PX4 接收和 timesync 源戳，再决定是否复跑悬停。
- #181 的20.011秒 no-goal dwell仍是唯一有效悬停基线；#182 不可算第二次冷启动通过。P5继续进行中，不改变质量门或阈值。

## 对话摘要

[P5 悬停基线独立复测中止](../../collaboration/dialogues/2026-10-19-066-p5-hover-repeat-abort.md)
