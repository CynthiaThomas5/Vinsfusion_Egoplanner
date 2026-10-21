# P5 PX4 timesync、遥测与源时间对齐诊断

对话摘要：[2026-10-17-046](../../collaboration/dialogues/2026-10-17-046-p5-px4-time-domains-and-readiness.md)。

## 改动

- `RosClockMapper` 将 ROS `/clock` 源 stamp 逆映射进 XRCE Agent 时钟域，让 PX4 解码后恢复 VINS 源采样时间；`timestamp` 使用 Agent 时钟。新增 PX4 HRT 恢复年龄和 ROS/PX4 源戳间距计算。
- PX4 timesync 与低频状态消息按 `/clock` 和恢复后的 PX4 HRT 比较仿真时钟年龄，同时保留墙钟接收上限。低频状态消息的墙钟上限为3秒，PX4 源戳上限为1.5仿真秒，位置/姿态仍保留0.5秒墙钟上限。
- PX4 rig-frame 对齐现在比较 ROS 源戳与 PX4 local-position 源戳（转换到共同仿真时钟），阈值0.12仿真秒，不再用不同发布节奏的墙钟收包时刻做配对。
- bridge detail 和只读 live probe 增加各类 PX4 telemetry 的源戳仿真年龄、墙钟收包年龄与对齐戳差，便于后续定位间歇 freshness 闭锁。
- `progress/evidence/p5-px4-timesync-remap-20261017-104.json` 记录本轮有效的 run-scope 结果；P5 里程碑保持 `in_progress`。

## 验证

- `tools/test_px4_bridge_time_mapping.py`：10项通过；`tools/test_px4_bridge_vio_profile.py`：6项通过；`tools/test_px4_bridge_control.py`：11项通过。
- `py_compile`、桥接配置 JSON 校验通过；Jazzy 隔离 overlay build #105 中 `uav_px4_bridge` 1/1 构建通过。
- 新增 detail 订阅的只读 probe 在 Jazzy ROS 环境以 `--seconds 0` 初始化并写出预期 JSON 字段。
- SITL #104：75秒、ROS domain 225、VIO profile、GNSS aiding 关闭、ROS 图无 truth 输入。只读 probe 记录73次 timesync，`/clock` 与恢复 HRT 年龄最大4ms，bridge reason 中 `px4_timesync_stale` 为0。PX4 ULog 有506条外部视觉里程计，采样到接收延迟中位64ms、P95 138.2ms，样本戳未被解码为接收时刻；EKF2 EV position/yaw flags各37次，所有 GNSS aiding flags为0。源戳对齐门下 `px4_frame_unaligned` 为0。
- #104 全程没有 `OffboardControlMode`、TrajectorySetpoint 或 VehicleCommand 发布样本，机体保持 disarmed，bridge phase 为 DISABLED；ROS 图无真值 topic/订阅。详细 ULog 与 probe 哈希见[轻量证据](../evidence/p5-px4-timesync-remap-20261017-104.json)。
- `python3 tools/project_status.py`、`git diff --check` 与 `git diff --cached --check` 在完成记录后执行；结构检查不代表 P5 通过。

## 限制与下一步

- #104 readiness 最后10秒覆盖率为0；PX4 在 DISABLED 的当前模式中 `pre_flight_checks_pass=false`，事件记录了无手动输入、GCS、mission、global position 与 Offboard signal。桥接 supervisor 设计为先做 disarmed prestream、再要求 PX4 preflight 批准后解锁；本轮没有调用 enable service，也没有验证该路径。
- #104 有66/570条桥状态报告 `px4_telemetry_stale`，虽不是最后一项状态原因。逐源年龄 detail 在 #104 之后才加入，当前通过构建和静态测试，尚无 live capture；不调整健康门以掩盖该现象。
- #102 因墙钟 telemetry stale、#103 因墙钟对齐配对被单列为诊断尝试，不作为 readiness 证据。它们及 #101 探针启动缺陷记录在各自 run 目录。
- P5 仍未完成；本轮不证明稳定 readiness、Offboard、arming、飞行、目标到达、避障或 P4/P6/GOAL A–H。继续保持控制禁用；后续先用新的 detail 捕获定位间歇 freshness 失败，再评估 disarmed prestream 是否满足项目授权和验收约束。
