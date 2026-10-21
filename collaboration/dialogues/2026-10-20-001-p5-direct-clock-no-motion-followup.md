# P5 direct lockstep 完整 VIO 与零偏移目标复核

## 任务摘要

承接 #194，先用完整 VIO/EGO/navigation graph 被动确认 direct lockstep 时钟域，再按前置 freshness gate 重做 no-motion 目标，以区分时钟故障和定位质量门故障。

## 约束与决定

- PX4 控制继续由 `uav_px4_bridge` 独占。#195 的 ROS 包前缀误加载旧 overlay，记录后排除；#196 通过 run-local package-prefix 断言后才作为被动时钟证据。
- #196 不派发目标、不启用控制、不解锁、不订阅 debug_truth。#197/#198 的 action 测试只使用 VIO 定位、EGO、导航和 PX4 状态；没有启动在线真值输入。
- 不改 PX4 telemetry freshness、future-stamp、定位健康或 normalized-cost 门限。
- 为定位 #197 的 `px4_timestamp_unavailable` 增加只读 `px4_timestamp_error` 详情字段；不改变映射、故障门控或控制行为。

## 结论与待办

正确 overlay 的 #196 35 秒被动完整图观察到 PX4 direct time domain 始终有效、VIO 到达 PX4、EV position/yaw 融合且 GNSS aid 为零，没有控制或解锁。#197 通过前置门后在目标发送前进入 LANDING，原因是 `px4_timestamp_unavailable`。#198 未复现该错误，完整通过 Offboard 前置门并发送零偏移目标，但在 normalized_cost=1.0175 后 fail-closed 中止并安全降落；因此时钟域问题得到被动与一次主动复核支持，P5 仍未通过。

下一步检查 #198 质量越线附近的 VINS 视觉残差和特征时序；保持 normalized-cost 1.0 与其他所有门限不变。

轻量报告：[完整 VIO direct-clock 后续 #195–#196](../../progress/evidence/p5-px4-vio-direct-clock-followup-20261020-195-196.json)；[no-motion direct-clock 尝试 #197–#198](../../progress/evidence/p5-px4-vio-no-motion-direct-20261020-197-198.json)。
