# N10.3 #364：PX4 在线动态障碍／EGO 重规划诊断协议

状态：**运行前协议已冻结；本文件不表示已飞行或通过。** 单 D435i、Gazebo/PX4 SITL、当前 gate-free runtime。该诊断不是 N12 正式三连，也不设立新的 VINS 质量阈值。

## 假设与唯一变量

在当前长程单目标飞行已产生 EGO 曲线后，于目标发出后的 **12.0 仿真秒**，在实际 `vio_initialization` 世界插入一个新静态方箱。假设单目深度／地图会观察到它，官方 EGO 会为同一 goal/epoch 发布不同 `traj_id` 的替代 B 样条，PX4/bridge 随后实际执行该曲线并到达目标。

相对 #361 的唯一任务场景变量是一个新障碍及其固定注入时刻。目标、spawn、EGO 参数、PX4 参数、映射／桥、碰撞策略和只读观察器不变。定位 cost、特征、source age 只记录；不恢复项目自加的质量或定位／里程计回执龄门限，也不加 raw-free 整曲线拒绝。

## 冻结注入条件

- 基线 runtime contract：`fdf104f5bd7b733128656fc4736af001f9ecdcbe1d93de123b41c7974a511a2f`；运行前重新计算并记录实际哈希，不匹配则本轮不得称为同候选结果。
- 使用 `config/components/simulation/n10_long_range_spawn_minus8.json`、`config/components/mapping/n10_horizon5_speed080_calibration.json` 和 `config/components/navigation/n10_long_range_vio_calibration_goal.json`，single D435i、`official_ego`、PX4 唯一控制者 `uav_px4_bridge`。
- 等待只读 planner observer 记录本 goal 的第一条 B 样条；以 `/navigation/ego_goal` 的 `target.header.stamp`（任务 goal 被接受时的仿真时钟）为零点，在 `t0+12.0s` 创建唯一模型 `n10_live_replan_box`。第一条 B 样条必须先出现。不读取 Gazebo truth 来触发注入。
- 注入为 `static=true`、box collision 与高对比 visual，世界位姿 `(0, 0, 1.4) m`、尺寸 `(0.8, 0.8, 2.8) m`、yaw `0`。当前静态 EGO 场景中该位置没有既有碰撞几何；最近的既有高柱中心约 `(0, 1.128, 0.5) m`、半径 `0.3 m`，方箱边与该柱约隔 `0.428 m`。插入后两者的 inflated 区域可能连接，允许 EGO 绕外侧规划。
- #361 历史轨迹在 goal+11.7s 位于约 `(-4.0,-1.27,2.64)m`，goal+13.6s 位于约 `(-3.0,-1.21,2.77)m`；新障碍在前方约4m，处于当前5m planning horizon 内。此历史真值只用于预估固定注入窗口，不参与运行触发或控制。

## 必须记录的事件和量

记录模型创建请求／Gazebo ACK、goal 与 epoch/map 身份、注入前后地图原始观测（可复算的深度或 raw occupancy 证据）、注入前后完整 EGO `traj_id` 与源时间、EGO position command、PX4 实际位置/速度、contact、debug truth 和桥状态。独立离线评估整段最小机体净空；真值不得进入导航、注入触发或控制。

一次有效的诊断成功样本需满足：

1. 当前 runtime 身份一致，goal 和初始轨迹已出现，方箱创建得到 ACK；
2. 观察到新增方箱对应的传感器／raw map 观测；
3. 同一 goal_id/epoch 出现不同 traj_id 的后续 EGO B 样条；
4. PX4/bridge 观测到曲线后的实际运动，任务完成原目标的 position/yaw dwell；
5. 禁止接触为0，contact/truth/planner/bridge 观察器覆盖终态；独立最终状态 landed、disarmed、control disabled、zero control，随后才停止容器。

任一事件缺失都保留为失败或不可判样本，不修改参数重写结果。若注入后 **1.0 仿真秒**仍无替代轨迹，runner 通过既有 caller-cancel 路径取消目标并交由 bridge 落地；这只是本次诊断的停止／保全流程，不是生产验收时限或新运行质量门。完整保留注入至取消的速度、位移、接触和末态数据。任何接触、状态不完整或终态读回失败时不得执行普通容器停止流程。

本协议固定运行事件与记录方式，不冻结 N10.3 的最终重规划 deadline、最小净空、VIO 误差或时效标准。一次诊断成功仅证明该次场景的闭环响应，不能替代 N12/N13 的正式重复。

## 执行前置与命令

执行前实现一个 run-local injector/observer，预先冻结其哈希；验证只监听 ROS 与发出一次 Gazebo create 请求，不发布控制、目标、轨迹、地图或真值。冷启动前确认没有本项目遗留容器；遵循现有 N10 runner 启动、五类观察器、独立末态读回和 `safe-to-stop.json` 流程。若工具不能确认身份或事件顺序，则不得开始任务飞行。

预期 SITL run：`n10-20261027-365-live-obstacle-replan-current`。不修改第三方 EGO 源码，不改变 official collision policy，不接入第二传感器。

机器协议：[JSON](n10-live-obstacle-replan-protocol-20261027-364.json)。
