# N10.3/#407 — #404 遮挡箱体内 raw-free 体素归因审查

日期：2026-10-28。范围仅为 #404 归档离线分析；未启动 ROS、Gazebo、PX4 或飞行，也未改变运行门限。

## 结果

离线重放复现了 18 个八角完整位于实体箱体内、但 raw occupancy 为 known-free 的体素。体素索引为 x=276–278、y=197–203、z=34，集中在一个 3×7×1 层。最近箱体面的全体素内部余量为 0.000351 m（y 正面边界的两格）；靠 x 负面边界的七格距该面约 0.001623–0.001686 m。该结果确认空间聚集和边界关系，不单独说明这些 free 值如何产生。

完整传感器 MCAP 包含双目红外图像及 IMU，但没有 `/sensors/d435i/depth`。观察器另外保留的稀疏深度图只有 6 帧，其中注入前 2 帧；投影到这些体素的最早相关帧无有效深度返回，且记录没有逐体素更新历史。因此无法判定它们来自旧 free 投票、射线终点处理、深度配准或其他更新顺序。当前 mapper 源码使用 hit/miss log-odds，不记录逐体素最后更新时间，也未发现未观测体素的时间衰减；旧 free 投票可持续存在是可能性，不是本次数据支持的根因结论。

本子项结论：归档数据不足以对 18 格做因果归因，状态为 `INSUFFICIENT`。raw 分类候选仍为 `FAIL`；不调低/删除离线指标，不添加在线拒飞或任务取消门限。下一次综合校准若本身执行，应同步记录短时深度 ROI 与目标栅格更新前后状态，并绑定 epoch/map/frame、源时间和位姿；只有这些数据仍不足时才加逐格更新来源追踪。无需为此单独重飞。

## 复现

- `python3 tools/debug_truth/analyze_n10_occluded_free_cells.py artifacts/runs/n10-20261028-404-speed040-integrated-calibration --output artifacts/runs/n10-20261028-407-map-cell-attribution/voxel-source-audit.json`：通过，18 格。
- `PYTHONPATH=tools/debug_truth python3 -m unittest tools/test_n10_occluded_free_cell_attribution.py`：2 项通过。
- Python 编译检查：通过。

离线明细、输入清单与 SHA-256：[`voxel-source-audit.json`](../../artifacts/runs/n10-20261028-407-map-cell-attribution/voxel-source-audit.json)。审查结论不替代 N10 分类出口；该项仍未通过。
