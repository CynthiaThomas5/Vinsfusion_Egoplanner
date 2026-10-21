# P5 PX4 lockstep 时钟域复核 #194

## 任务摘要

承接 #193 的 no-motion 对照：查清 PX4 attitude/local-position 源时间戳领先 ROS `/clock` 的可能来源，并先验证时钟域修正，不放宽健康或质量门。

## 约束与决定

- PX4 控制仍由 `uav_px4_bridge` 独占；本轮 bridge 保持 DISABLED，不派发目标、不解锁、不发控制样本。
- 不启动 VINS、定位、建图、导航或在线真值输入；debug_truth 只读图不属于本轮运行图。
- 使用 Gazebo lockstep `/clock` 直接映射 PX4 时间戳，关闭 XRCE Agent 的时钟同步；PX4 `UXRCE_DDS_SYNCT=0`。所有既有 freshness、future-stamp 与 normalized-cost 门限保持不变。
- #194 被归类为被动时钟域验证，不能证明完整 VIO 负载下的 freshness，也不能作为 no-motion 或 P5 飞行验收。

## 结论与待办

固定 PX4 固件与镜像下，20 秒运行测得 PX4 原始时间戳与 Gazebo `/clock` 最大差 8 ms；155 条 bridge detail 均无未来源年龄。无控制样本，车辆保持 disarmed。时钟域混用是 #193 future-stamp 的较可能解释，但仍需在完整 VIO 图中确认。

下一步先以 direct lockstep 时钟域被动运行完整 VIO 图；若 freshness 持续有效，再重做零位移目标对照。

轻量证据：[P5 #194 被动 PX4 时钟域验证](../../progress/evidence/p5-px4-clock-direct-passive-20261019-194.json)。
