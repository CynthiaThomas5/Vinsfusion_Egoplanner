# N10.3/#398 综合校准结果

## 用户目标与约束

继续 N10.1–N10.7 Goal 完成模式，先完成校准依据，不提前运行 N15/N16 正式矩阵。复用 #378–#380 制动、#385 到达和未受影响的历史证据。离线指标不能改变飞行控制或新增拒飞/暂停/取消/Land 规则。紧急 disarm 的一次性授权已在 #391 使用；后续要求正常结束并独立确认终态。

## 本次结果

修复了 propagated stream 首条消息 GID 绑定竞态后，以新 runtime identity 按 0.4 m/s planner profile 完成 16 m EGO 任务、3.344 仿真秒联合位置/yaw 达标、15 仿真秒诊断保持，并正常落地上锁。收集连续 4 ms Gazebo solver states、VIO、tracking、sensor receipts、map/obstacle、资源队列和安全终态。任务运行成功，不能等同 N10 通过。

tracking 与机体净空仍没有已证明的接受阈值；快照只观测到两面。source stamp 晚于首条被记录 box cloud 604 ms、早于快照前第二条被记录 cloud 16 ms，且 occupancy cloud 每十帧采样，不能关联精确融合帧。#399 随后用 voxel 八角 containment 复核，分出 13 个完整落在实体箱内的 known-free cells 和21个跨表面单元。此结果保留为草案 classification FAIL 候选；不连接运行控制。

## 结果与继续项

综合校准指标总评 `INSUFFICIENT`。#398 不含故障注入，不能回答真实断流/规划器退出后能否正常 landed/disarmed。后续先准备 source-stamp 覆盖完整的 observer-only snapshot 和故障末态只读 readback，再按复用矩阵校准一类当前版本故障。无 emergency-disarm 复用。
