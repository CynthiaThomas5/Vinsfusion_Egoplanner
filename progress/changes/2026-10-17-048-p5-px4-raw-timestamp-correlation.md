# P5 PX4 原始时间戳与 estimated_offset 平台诊断

对话摘要：[2026-10-17-048](../../collaboration/dialogues/2026-10-17-048-p5-px4-raw-timestamp-correlation.md)。

## 改动

- `tools/probe_px4_bridge_live.py` 逐条记录 PX4 Agent 时间戳、回调时最近的 `estimated_offset`、恢复后的 PX4 时间、最近 `/clock` 值及 monotonic 收包时刻。该探针只订阅，不发布控制。
- 运行 #109 基于隔离的新 PX4 SITL build 副本，45 秒被动运行；bridge 安装复用 #108，安装包中的 `px4_bridge_node.py` 与当前自维护源码 SHA-256 相同。未修改 freshness 阈值或桥接控制行为。
- 新证据记录原始样本和 PX4 build、profile、bridge/frame/sensor 配置与运行产物哈希：[P5 原始时间戳相关性](../evidence/p5-px4-raw-timestamp-correlation-20261017-109.json)。

## 结果

- localization 进入 TRACKING，PX4 收到 283 条 VIO；桥接状态和 PX4 `EstimatorStatusFlags` 观察到 EV position/yaw 融合，GNSS aiding flags 全零。无 ROS truth topic、无 truth subscription、无控制话题样本，车辆保持 disarmed。
- 对 source callback 单调时刻用相邻 `/clock` 样本分段线性插值后，34/345 个 `px4_telemetry_stale` detail 样本集中在 15.185–20.685 wall 秒。timesync offset 在 15.121–20.638 秒经历26次数值更新；最后一次 offset 变化之后47 ms还有一条 stale，之后余下24.33秒没有 stale。高频 attitude/local-position 收包样本超过20 ms“未来”界限的176/1851与100/926条全部落在 offset 调整窗口；稳定段分别 P95 4.758 ms 与8.847 ms。
- PX4 源码复核：`EstimatorStatusFlags` 在状态字段更新时发布；`VehicleLandDetected` 至少每1个仿真秒发布一次，也会因状态变化提前发布；`VehicleStatus` 每500 ms或状态变化时发布。因此先前记录中把 land-detected 简写成仅事件发布并不准确，本记录更正该语义。此次 stale 簇与 timesync offset 调整同窗；单次运行尚不能确立跨运行根因或冻结收敛策略。
- 末端 readiness 覆盖率为0，bridge 仍 `DISABLED`，PX4 原因是当前模式 `px4_preflight_failed`。本轮没有 Offboard prestream、enable、arm 或飞行，故既不报告 readiness 通过，也不报告 P5 通过。

## 验证

- `python3 -m py_compile tools/probe_px4_bridge_live.py`：通过。
- Jazzy 容器中 source PX4/Jazzy overlay 后构造只读 probe 节点：通过。
- `python3 tools/test_px4_bridge_time_mapping.py`：12项通过；`python3 tools/test_px4_bridge_control.py`：11项通过。
- `docker run --rm --init ... bash artifacts/runs/p5-px4-raw-timestamp-correlation-20261017-109/run-px4-raw-timestamp-correlation.sh`：融合、GNSS/truth隔离及无控制/disarmed检查通过；readiness 条件失败并按诊断运行保留。
- `python3 tools/project_status.py` 与 `git diff --check` 在完成记录后运行。

## 下一步

#112已在75秒run观察到两次滤波重置状态：`estimated_offset`短暂归零后由下一观测重建；Agent日志无DDS重连，PX4高偏差重置为最有力解释，但内部计数器未直接记录。下一步量化PX4 lockstep HRT、Gazebo `/clock` 与 Agent wall-clock的时基关系，并验证仿真时间处理。保持健康门限并fail closed；DISABLED下preflight readiness尚不具代表性。P4/P5/P6与GOAL A–H均未完成。
