# GOAL C 同 epoch 多时刻地图快照 #294

日期：2026-10-20

## 任务摘要

延续 #293 对单时刻地图表面一致性的探索，在单 D435i 力驱动运动序列中捕获三个同 epoch 占据快照，比较 known/free/raw occupied 增长、occupied集合重合度及对同场景SDF的距离。

## 约束与决定

- 仅运行 D435i/VINS/定位与深度健康适配器、mapping adapter、隔离 EGO `plan_env`；不启动 PX4、controller、traj_server 或导航目标。
- 重用 #292 已构建的隔离候选二进制；不改 `src/vendor`，不把 patch 0021 加入 `dependencies/sources.json`。
- 运行时 ROS graph 不订阅真值或控制topic。fixture truth 独立记录，仅作离线单一固定尺度 SE(3) 轨迹对齐。
- 多时刻同场景结果仍是一次探索运行；不冻结覆盖、重影、clearance或规划验收阈值，GOAL C保持 pending。

## 结果与后续

三份快照使用同一 epoch/map_id/frame和0.1 m栅格；known voxel数从13,688增长到19,878、20,283。两段 raw occupied Jaccard 为0.702与0.885，occupied中心到已知场景SDF表面距离均小于0.10 m。EGO无目标、保持`WAIT_TARGET`，并在两个时间段记录共36条odom/depth lost告警，所以本轮不作为规划器就绪证据。

下一步换用第二种障碍布局重复数据采集，确定有界ROI和可审查的覆盖/时序指标，再审查候选patch的canonical重建流程。权威证据与限制在对应 progress/evidence 和运行报告；本摘要不作为测试通过凭证。
