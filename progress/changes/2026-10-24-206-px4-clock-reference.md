# #206：修复 PX4 遥测与 ROS 时钟接收滞后的比较

对话摘要：[2026-10-24 #206 PX4 时间参考](../../collaboration/dialogues/2026-10-24-206-px4-clock-reference.md)。证据：[机器报告](../evidence/n07-px4-clock-reference-20261024-206.json)、[验收说明](../evidence/n07-px4-clock-reference-20261024-206.md)。

## 改动

- 在 `px4_bridge_node.py` 中恢复 PX4 当前 HRT，并以 PX4 HRT 与映射后的 ROS `/clock` 的较新有效值作为当前时间。
- PX4 遥测源龄检查和 uXRCE DDS 时间同步关闭时的控制时间戳使用该参考。
- 增加 PX4 HRT、ROS clock gap 与 clock 收到／推进年龄的诊断字段。
- 保留现有 `/clock` 活性门及所有 PX4 telemetry age/future 门限。
- 按用户指令将 N07 三次独立冷启动改为累计次数，失败不清除通过记录；#198/#200/#204 已通过，明确禁止复测。

## 验证与限制

- `bash tools/project.sh build ros`：17 个包完成，成功。
- 对 #198/#200/#203/#204 历史 ACTIVE/TAKEOFF 桥接快照按 PX4 HRT 参考复算：共覆盖 1518 个样本，零个 PX4 源龄或 future 限值违规；#203 首次 `/clock` 滞后中止行的假未来龄消失。
- #206 做在线集成前的 N05 支架扫描在 stage 7/12 因 `normalized_cost_exceeded` 失败，未到 post-release gate，也未起飞。扫描安全收尾确认 landed、disarmed、fixture detached/removed，容器 exit 0。
- #203 独立 VIO odometry 停顿现象保留，不归入此修复。

## 后续结果

#207 在 ground SITL 中读取到 HRT、ROS clock gap、clock callback age 和 PX4 telemetry source age；bridge 保持 `DISABLED`，没有武装或起飞。结合 #203 特定延迟轨迹离线复算和 #198/#200/#204 累计 hover 3/3，N07 限定出口通过。N05 的 #206 扫描失败不清除既有通过。详见[#207 读回](../evidence/n07-px4-clock-live-ground-20261024-207.md)。
