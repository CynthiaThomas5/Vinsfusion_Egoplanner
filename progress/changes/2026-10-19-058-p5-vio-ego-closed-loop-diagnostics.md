# P5 VIO→PX4→EGO 飞行诊断与时间门修正

## 修改

- `src/own/uav_localization/uav_localization/health.py`：新鲜度比较使用整数纳秒，避免 `0.3` 秒边界经浮点换算变成 `0.30000000000000004` 后锁定。
- `tools/test_localization_health.py`：加入恰好 300,000,000 ns 与超出 1 ns 的边界回归。
- `src/own/uav_px4_bridge/uav_px4_bridge/px4_bridge_node.py`：每条 PX4 遥测保留回调时捕获的 Timesync offset；源龄和状态详情使用该样本自己的 offset，不因后续 timesync reset 追溯改变缓存样本的时间映射。
- `tools/test_px4_bridge_time_mapping.py`：覆盖 reset 前样本使用其 receipt-time offset 的情况。
- `config/components/px4_bridge/vio_closed_loop.json`：仅将 VIO profile 的 `px4_source_timestamp_max_future_sim_s` 设为 0.05 s。依据 #157 观察到的最大 41.048 ms PX4 遥测未来戳；stale、receipt、共享/debug_truth 和定位质量门均未放宽。
- `tools/test_px4_bridge_vio_profile.py`：确认 50 ms 仅出现在 VIO profile，共享 debug_truth 仍为 20 ms。
- 新增 P5 轻量报告与对话摘要，链接 #153–#159 原始 artifacts 和 SHA-256。

## 行为与结果

#154 的单次 future-propagated 样本阻止了控制服务调用；#156 暴露了恰好 300 ms 的浮点边界问题。整数纳秒修复后，#157 通过稳定性门并起飞，但此前 20 ms PX4 future limit 因遥测领先最多 41.048 ms 触发安全降落。50 ms VIO-only profile 使 #158/#159 均到达 ACTIVE 并发送导航目标；两轮随后分别以归一化代价 1.1278 与 1.0670 触发 fail-closed，并都安全落地、解除武装。

#159 的 run-only probe 记录到 raw depth 与 READY depth-health 继续运行，而 health lock 后 optimized odometry 和 mapping adapter 转发到 EGO 的深度/位姿停止。EGO 与 PX4 在同一事件窗口取消轨迹并降落。该轮没有真值或 debug_truth 输入，PX4 控制输入只有 `uav_px4_bridge` 发布者。EGO abort、map reset 与 health failure 的精确跨进程因果排序尚未证明。

对历史 raw-VINS telemetry 的探索性重算：21 个健康建图诊断轮共 5,294 次有效求解，归一化代价 P95 0.363、最大 0.398；两轮视觉退化回放共 772 次有效求解，P50 1.218、最大 1.218。#158/#159 的 1.067/1.128 落在两个场景之间，但这些历史数据没有覆盖飞行动作的真实 VIO 误差，不能证明可以接受该结果。`max_normalized_cost=1.0` 保持不变。

## 验证

- `python3 tools/test_localization_health.py`：11 tests，PASS。
- `python3 tools/test_fault_relay.py`：2 tests，PASS。
- `python3 tools/test_px4_bridge_time_mapping.py`：14 tests，PASS。
- `python3 tools/test_px4_bridge_control.py`：11 tests，PASS。
- `python3 tools/test_px4_bridge_frames.py`：19 tests，PASS。
- `python3 tools/test_px4_bridge_vio_profile.py`：7 tests，PASS。
- `python3 -m py_compile src/own/uav_localization/uav_localization/health.py src/own/uav_px4_bridge/uav_px4_bridge/px4_bridge_node.py`：PASS。
- `python3 tools/project_status.py`：PASS（只检查结构/设计一致性）。
- `git diff --check`：PASS。
- #158/#159：到达 ACTIVE、发送目标后因定位质量门中止；两轮均报告 landed/disarmed。两轮不是成功导航验收。

## 限制与下一步

VIO profile 的 50 ms future 容差仍是依据一次最大观测的 PROVISIONAL 设置。无完整 cost/features 时序、无 flight truth 误差对照；不调整归一化代价门限。下一步采集起飞前后 `LocalizationStatus` 质量时间序列并关联相机输入和运动，再以可追溯误差证据校准 F；之后重试无真值 goal，并做多场景/长时地图与安全落地验收。P5、P4 和 GOAL A–H 均未完成。

## 对话摘要

[2026-10-19 P5 VIO–PX4–EGO 飞行诊断](../../collaboration/dialogues/2026-10-19-058-p5-vio-ego-closed-loop-diagnostics.md)
