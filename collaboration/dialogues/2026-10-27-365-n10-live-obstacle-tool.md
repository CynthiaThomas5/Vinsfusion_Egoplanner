# N10.3 #365 动态障碍注入／观察工具

## 任务

- 用户要求以 Goal 完成模式继续 N10.1–N10.7，并要求遇到保护门时先查运行源码；本轮聚焦 #365，为 #364 冻结协议制作 run-local 工具并执行一次 PX4 SITL 诊断。
- 当前工作区已有用户未提交修改，全部保留；不触碰旧 PX4-ROS2-SLAM-Control-Deploy／ROS_SEARCH 来源，不用真值触发、控制或注入。
- 不恢复已删除的定位质量／定位回执龄门，不新增 raw-free 整曲线拒绝；单 D435i、`official_ego`、PX4 控制仅由 `uav_px4_bridge` 发布。

## 依据与约束

- 复核 `CURRENT.md`、milestones、`docs/remaining-small-goals.md`、N10 完成计划及 #364 协议。#361/#362 runtime contract 基线 SHA-256 为 `fdf104f5bd7b733128656fc4736af001f9ecdcbe1d93de123b41c7974a511a2f`。
- #364 固定 `vio_initialization` 世界 box `(0,0,1.4)m`、尺寸 `(0.8,0.8,2.8)m`，触发点为 `/navigation/ego_goal` 接收时间后 12.0 仿真秒且初始同 goal/epoch 样条已出现；1.0 仿真秒无替代轨迹时走现有 ROS action caller-cancel 以安全结束诊断。此时间只用于诊断收尾，不是生产阈值。
- 源码核对：`health.json` 中质量／定位回执龄值仅观察；`run_vio_ego_flight.py` 不再按 normalized-cost 作准入；当前 `official_ego` 分支不做 raw-free 整曲线拒绝。保留消息／epoch／时钟完整性、地图身份与新鲜度、PX4 bridge 状态机及控制约束。
- 额外只读观察器监听 `/clock`、goal、B 样条、position command、map status、优化里程计、单 D435i 图像及 EGO occupancy cloud；不创建 ROS publisher、不读真值。只允许一条 Gazebo create 请求和诊断需要时的一条 action cancel 请求。

## 交付与状态

- 工具及冻结文件位于 `artifacts/n10-prepared/n10-20261027-365-live-obstacle-replan-current/`。
- SITL 预期 run id：`n10-20261027-365-live-obstacle-replan-current`。
- 本摘要不作为验收证据。飞行、服务 ACK、轨迹变化、PX4 末态和净空结论以后续 `progress/evidence` 报告及 run artifacts 为准。
- N10.3 与 N10 父目标保持未完成，直到所有剩余校准、重建、回归和冻结出口均有证据。


## SITL结果补充

#365已按#364协议运行：Gazebo创建方箱ACK成功，camera/EGO occupancy显示箱体表面；同goal/epoch出现traj_id 45–72，后续轨迹几何绕行，但 native optimizer 后续再次`planning_failed`，项目0039立即中止goal，未到达目标。违规接触0，动态箱体离线采样净空扣除最大相邻样本运动后0.949m，PX4/bridge landed/disarmed/control-disabled/zero-control读回并安全停止。详细结果见`progress/evidence/n10-live-obstacle-replan-20261027-365.md`。
