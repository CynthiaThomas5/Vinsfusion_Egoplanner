# N10.3/#399：#398 体素体积分类与验收器复算

## 用户约束

- N10 在 N15/N16 正式矩阵之前完成校准、验收标准依据、干净重建、回归和冻结。
- 当前故障终态、采样间净空、定位/跟踪误差是三个实质技术风险。
- 离线统计不新增拒飞、暂停、取消或降落分支；不恢复项目自加健康门。
- #378–#380 制动、#385 到达校准及未受变更影响的 N07/N08/N09 证据复用。
- 一次紧急 disarm 授权已在 #391 使用；后续运行必须依正常 PX4/bridge 路径落地并独立确认。

## 本项决定

复用 #398，修正 map snapshot 离线报告对 boundary voxel 的描述。增加八角 containment 几何；只有八角均位于实体真值箱体的 known-free voxel 才计入 truth-occluded raw-free 候选。总计 34 个 center-inside free 中有 13 个 fully contained、21 个跨边界。保留草案阈值 0，不通过删指标或泛化门限掩盖结果。快照 source stamp 晚于第一条被记录的 ROI cloud 604 ms、早于快照前第二条被记录 cloud 16 ms；point cloud 仅每十条采样一条，因此不能确定精确融合帧。

离线 acceptance 仍 `INSUFFICIENT`；raw map classification 候选指标为 `FAIL`，surface 支持不足。所有记录器、查询器和评估器均只读，不接入控制。

## 待办

1. 用 source-stamp 覆盖首个记录 box cloud 的 map snapshot 重复观测，判断完全位于实体内的 free cell 是否仍保留。
2. 继续当前版本真实断流或 planner-exit 的端到端 PX4 末态校准；不使用已消耗的一次性 emergency disarm 授权。
3. 继续收敛 tracking/clearance、资源/队列依据、N10.4 门限和 N10.5–N10.7。
