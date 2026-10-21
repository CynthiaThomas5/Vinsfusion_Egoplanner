# P2 实际 ROS clock 回退故障注入

日期：2026-10-17

- 用户目标：继续完整推进 [GOAL.md](../../GOAL.md) 的 P0–P6 与 A–H，不降低范围。
- 用户约束：保护既有 staged／unstaged 修改；旧工程和 vendor 只读；仅单 D435i 仿真导航；不发布 PX4 控制、不解锁或实机飞行。
- 本轮实施：增加只在 TRACKING 且在线 map 非空后注入一次 1 秒 ROS `/clock` 回退的 relay，以及只读状态／map／输出观察器。Gazebo clock 先重映射到私有 source topic，relay 重新发布；传感器源时间仍递增。未修改生产代码或项目配置。
- 两次独立通过：run #05 与 #06 使用 ROS domain 193／194、Gazebo partition `p2_clock_regression_05`／`_06`，并生成不同 VINS epoch。注入前 VINS 均 TRACKING、EGO 地图分别观测到741／908点；各注入恰好1秒回退。定位状态转为 LOCKED、`clock_regression`，mapping adapter 请求新 map_id，EGO map 变空。每次回退时已有10／10及15／15组 EGO 深度／位姿输出；定位 optimized／propagated 里程计也有非零计数，全部在 settle 后保持不变。
- 决定：只认 #05/#06 为通过。#01–#04 的 harness／观测时序问题及原始数据均保留并列为 excluded attempts。来源与运行时 self-maintained localization/mapping Python 文件哈希一致。独立 domain188–194 CLI daemon 已停止；domain186／187 未触碰。
- 局限：无任务／轨迹节点，无 PX4，因此不能证明目标和轨迹取消、Offboard 丢失降落、10分钟满负载或实机结果。地图只验证清空行为，不验证几何与避障；GOAL E 整体仍未通过。
- 证据：[p2-clock-rollback.json](../../progress/evidence/p2-clock-rollback.json)，两次运行日志、状态与端点信息位于 `artifacts/runs/p2-ego-clock-regression-20261017-05/` 和 `-06/`。
- 对应改动记录：[progress/changes/2026-10-17-017-p2-clock-regression-replay.md](../../progress/changes/2026-10-17-017-p2-clock-regression-replay.md)。
