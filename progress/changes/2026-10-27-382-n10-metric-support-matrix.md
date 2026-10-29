# #382 N10.3 指标支持矩阵

- **对话摘要**：[2026-10-27-382](../../collaboration/dialogues/2026-10-27-382-n10-metric-support-matrix.md)
- **工作**：把 N04、#361、#376、#378–#381 和 GOAL F/E 的现有量测统一成指标/时间域/参考点/统计/候选数值/适用范围矩阵；源码核对地图更新 watchdog 与 PX4 offboard loss 参数。
- **新增产物**：[矩阵报告](../evidence/n10-metric-support-matrix-provisional-20261027-382.md)、[机器可读矩阵](../evidence/n10-metric-support-matrix-provisional-20261027-382.json)。
- **关键发现**：现有到达评估器 `tools/debug_truth/evaluate_arrival.py` 累计 `wall_s`。#381 的联合窗口为3.055墙钟秒但仅2.34仿真秒；GOAL F/本项目N10.2决策要求3.0仿真秒。因此当前全链诊断不能按此前 wall-time PASS 标记为 GOAL F 到达通过，#361/#376/#381须用仿真时间重新分类。N10.4修复判断器并调整任务实际保持后重测。
- **候选值**：到达保留合同0.30 m/15°/3.0 sim s；地图表面中心误差暂按0.10 m单体素；source/update age仅作离线0.20 sim s观察候选；在0.60–0.66 m/s caller-cancel协议下，三次最大真值制动路径1.376716 m、最大停止带进入5.116 sim s，故提出1.50 m/6.0 sim s的profile专用离线候选。其他VIO、速度、跟踪和重规划候选以及未支持的净空/故障/完整负载边界均在矩阵中标注置信度和缺口。
- **边界**：不改飞行代码、planner、速度上限或项目运行时健康策略；保留 upstream EGO occupancy-update timeout，PX4 native preflight/EV 与 PX4 loss action；不恢复 raw-free 全曲线拒绝。
- **验证**：只读字段核对 `grid_map.cpp::updateOccupancyCallback`、PX4 `COM_OF_LOSS_T` 参数定义/有效配置、现有归档 JSON；机器可读矩阵 JSON 解析通过。结构检查和差异检查待本轮收尾。
- **限制与下一步**：矩阵是草案，不满足最终冻结。#383修正sim-time到达评估并重算归档样本，之后完成唯一验收配置/判断器；补齐可证明的全机净空、N15端到端故障边界与N16完整负载资源证据。父N10保持`in_progress`。
