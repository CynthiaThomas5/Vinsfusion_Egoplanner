# 2026-10-28 N10.3/#404 综合校准准备与结果

- 用户指示继续按 N10 剩余执行顺序完成测试与任务；N10 保持 `in_progress`。N15 十二次正式故障测试与 N16 正式十分钟验收仍在 N10 冻结后。
- 延续约束：复用 #378–#380 制动、#385 到达校准及未受变更影响的 N07/N08 通过证据；校准不倒算正式次数。离线 evaluator、CPU/记录错误或统计阈值不能进入起飞/取消/降落分支；不恢复自加健康/年龄/速度/raw-known-free 门限。
- #403 已复用 #398 每 4 ms 真值记录得到正的空气中全机净空界；结果仍不含定位、地图和跟踪误差。
- #404 准备基于 #398 场景与 #402 的 source-stamp snapshot observer，增加 #403 interval evaluator 并记录 run-local X500 SDF SHA。
- 故障源码核对：传感器 bridge 使用一个 parameter_bridge 进程处理多路相机及 IMU。终止该进程会制造多路输入故障，因此本次综合校准不把它作为深度断流。待设计并验证深度单流中断后再测到自然 PX4 终态。一次性紧急 disarm 授权已在 #391 用完。
- #404 已完成一次当前 runtime 综合校准。16 m action 成功，独立位置/yaw 达标 4.352 仿真秒；15 秒保持仅为诊断。安全读回 landed/disarmed/control-disabled/zero-control 后停止本项目容器；未使用紧急 disarm。
- live snapshot 已有同 identity/source-covered 证据，但箱体内部有 18 个完整在实体内的 known-free voxel，分类候选 FAIL；仅两面有 occupied 支持，点查询服务不可用（0/26）。
- 物理步记录覆盖 26,005 个 4 ms 状态；模型界在 25,187 个空气中无接触区间均为正，最小 0.162761 m，817 个允许滑橇接触区间分开处理。该界不包括定位/地图/跟踪误差。
- 跟踪误差 P95 0.333776 m；逐点平移预算在 434/9,381 个样本为负。VIO 位置/yaw/RPE/速度复算已输出；资源观测为 189 秒但没有 VINS 内部队列容量或平台容量依据。总 acceptance `INSUFFICIENT`。
- 共享 parameter_bridge 因多路相机与 IMU 不具备深度单流故障隔离，本轮未注入故障；下一步先实现/验证该路径，再采集触发到自然 PX4 终态。N15/N16 仍在冻结后。
- 离线 VIO evaluator 修正当前 goal profile schema 兼容，并将 15 秒分段标名修正为 diagnostic；3 项单测与完整复算通过。无运行期控制或阈值变化。
- 完整结果：[证据报告](../../progress/evidence/n10-integrated-calibration-result-20261028-404.md)，运行归档为 `artifacts/runs/n10-20261028-404-speed040-integrated-calibration`。
