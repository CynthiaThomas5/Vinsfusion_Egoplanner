# P5 PX4 lockstep 当前时间戳与 VINS 分组代价诊断（#199–#202）

对话摘要：[2026-10-20-002](../../collaboration/dialogues/2026-10-20-002-p5-lockstep-current-time-cost-diagnostic.md)。机器可读证据：[轻量报告](../evidence/p5-px4-lockstep-current-time-cost-diagnostic-20261020-199-202.json)。

## 变更

- `RosClockMapper.current_lockstep_px4_time_us()` 为 Gazebo lockstep 下当前控制时间戳提供最新 `/clock` 样本直读；只有 `UXRCE_DDS_SYNCT=0` 时，bridge 当前 Offboard/control 时间戳使用该路径。
- 仍要求足量样本、mapper 未锁定、接收时间不回退和样本新鲜；VIO 历史 source-stamp 映射及 rate/freshness 限值不变。没有更改任何验收或健康阈值。
- `tools/test_px4_bridge_time_mapping.py` 增加直接时间戳路径、rate-fit 边界、样本过期与时间回退覆盖。
- #202 run-local collector 保留 VINS `cost_components`；记录 `landing-failsafe-timeline.json`。

## 运行与验证

- #199 首次捕获 `clock_mapping_rate_out_of_bounds`，发生在 TAKEOFF、goal 前；该轮没有确认具体拟合率数值。
- #200/#202 使用有效 ROS domain 和各自 run-local build/install，均无 bridge timestamp error，达到 ACTIVE 并发送目标；现有质量门中止后 landed/disarmed。
- #201 使用 ROS domain 233，PX4 XRCE-DDS participant 因 Fast DDS 端口超限未建立，作为无效轮次排除。
- #202 grouped-cost sample 与完整求解 cost 误差约 `9.1e-13`，分组 residual dimensions 总和与完整求解一致；report 同时保存 paired-image/tracker timing、PX4 ULog 与 raw artifact hashes。
- 对应 57 个 bridge/time/frame/profile 单测通过，Python 编译检查通过；#200/#202 各 6/6 run-local 包构建通过。命令及哈希见轻量报告。

## 局限与下一步

#202 中视觉 cost 占 82.589%，但没有逐特征残差、图像区域标签，也没有在线真值订阅来确认实际机体位移；不能将视觉 cost 占比解释为已确认根因。PX4 touchdown 后短暂进入 DESCEND/failsafe，需按冻结的故障边界继续评估。下一步保留 1.0 quality gate，收集可关联至特征/图像区域的只读残差诊断，并继续完成 P4/P5/P6 与 GOAL A–H。
