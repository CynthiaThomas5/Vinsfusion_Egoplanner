# P5 observed_offset 与 estimated_offset 对照

对话摘要：[2026-10-17-050](../../collaboration/dialogues/2026-10-17-050-p5-px4-observed-estimated-offset.md)。

## 改动与结果

- 只读探针增加 `TimesyncStatus.observed_offset` 字段，同时保留 `estimated_offset`、PX4 telemetry 原始戳和 `/clock` 收包时刻；没有修改 PX4 bridge、时龄阈值或控制行为。
- #111 用独立 PX4 build 副本、ROS domain 227 和新 Gazebo partition 运行45秒。VIO→PX4 送达277条，EV position/yaw融合被观察到，GNSS/truth均未使用；控制样本为零并保持disarmed。
- 35/345条 telemetry stale detail 出现在估计offset变化窗口13.755–19.228秒及最后更新后68ms；此后25.72秒无stale。attitude/local-position在窗口中174/1812、90/907条超20ms未来界限；estimated_offset最后变化后两者P95分别4.746ms、8.874ms。
- 缺失的解释维度出现在 `observed_offset`：它在整次运行中以约−0.5804秒/墙秒变化，而仿真钟速率约0.4196仿真秒/墙秒；两者绝对值之和约1。estimated_offset从19.228秒起停在同一值，但observed_offset在之后又变化约−13.98秒。故此前“offset收敛/稳定”只能表述为“estimated_offset进入平台”，不能推断 timesync 真正收敛。
- PX4 v1.17 的Timesync源码包含高偏差拒绝及连续高偏差后重置路径；该模式与时龄失效窗口相关，但内部计数器未暴露，暂不判定根因。[报告](../evidence/p5-px4-observed-offset-diagnostic-20261017-111.json)

## 验证与下一步

- `python3 -m py_compile tools/probe_px4_bridge_live.py`、Jazzy `observed_offset` 字段/节点构造smoke通过；本轮SITL融合、truth隔离、零控制及disarmed检查通过。readiness仍因DISABLED下 `px4_preflight_failed` 为0，不代表通过。
- #112延长到75秒观察到两次估计值重估；两次都先发布 `estimated_offset=0`，紧接着按 `observed_offset` 建立新估计。estimated字段平台不等于timesync收敛。保持现有门限并fail closed，P5/P4/P6和GOAL A–H未完成。
