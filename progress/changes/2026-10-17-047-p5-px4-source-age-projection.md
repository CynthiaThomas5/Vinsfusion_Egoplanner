# P5 PX4源龄投影与逐消息复核

对话摘要：[2026-10-17-047](../../collaboration/dialogues/2026-10-17-047-p5-px4-source-age-projection.md)。

## 改动

- `RosClockMapper` 新增从 `/clock` 样本拟合值投影到 freshness 检查的 monotonic 时刻；PX4遥测源龄不再直接与异步收到的最后一条 `/clock` 作比较。没有修改任何健康阈值或控制行为。
- 只读 live probe 保存逐条 `/clock` 的仿真增量、墙钟间隔及导出的 rate，用于和PX4源龄对照。
- 新证据汇总 #106逐源capture、#107排除运行及#108投影后SITL；P5保持 `in_progress`。

## 验证

- `tools/test_px4_bridge_time_mapping.py`：12项通过；`tools/test_px4_bridge_control.py`：11项通过；`tools/test_px4_bridge_frames.py`：19项通过；`tools/test_px4_bridge_vio_profile.py`：6项通过。
- `py_compile` 与 Jazzy `--seconds 0`只读probe schema smoke通过；隔离 overlay 中 `uav_px4_bridge`构建1/1通过。
- #108 75秒被动SITL中，ROS收到478条视觉里程计；PX4 ULog记录506条外部视觉里程计，EV position/yaw分别融合40/38次，GNSS aiding flags全零。无truth topic/订阅、无控制topic样本，保持DISABLED/disarmed。
- 新投影后仍有70/577状态样本报告 `px4_telemetry_stale`；末端 readiness覆盖0，原因是DISABLED模式下 `px4_preflight_failed`。#107只有4条VIO输入且没有融合，作为诊断排除。详细源龄、source/config hashes与raw artifact hashes见[证据](../evidence/p5-px4-source-age-projection-20261017-108.json)。

## 限制与下一步

- 当前投影没有解除P5 readiness限制，也不能据跨run stale计数变化声称改善。固定PX4源码显示 `EstimatorStatusFlags` 与 `VehicleLandDetected` 采用事件更新语义；对这些topic直接按源时间年龄判断liveness不成立。PX4 `VehicleStatus` 周期发布，但部分样本也表现为源龄过大；需要按逐消息接收时刻、时间映射误差和topic语义分解。
- 不放宽20 ms未来时戳或1.5 s源龄阈值；在确定topic contract和健康门前不调用enable service、不解锁或飞行。P5/P4/P6与GOAL A–H均未完成。
