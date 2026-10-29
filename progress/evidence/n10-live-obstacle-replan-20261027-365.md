# N10.3 #365：动态障碍单次 SITL 诊断结果

状态：**运行已结束；任务诊断失败，安全落地与停止通过；不计 N10/N12 通过次数。**

## 运行事实

- runtime contract `fdf104f5bd7b733128656fc4736af001f9ecdcbe1d93de123b41c7974a511a2f`（665 项），单 D435i、`official_ego`、PX4 唯一控制者 `uav_px4_bridge`。
- goal 起始仿真时刻 `83.164s`；首条 B 样条 `83.180s`；goal 后 **12.016s** 创建静态方箱，Gazebo ACK=`true`。
- 注入时真值最近样本 `[-3.274664763280432, 1.4403439291221283, 0.9094299799022623]` m，箱体中心 `[0.0, 0.0, 1.4]` m，中心间距 **3.611m**；在 5m EGO planning horizon 内。#364 使用的历史位置只用于预估，不是实际运行位置。
- D435i/EGO occupancy ROI 观察到箱体表面点：最大 497 点，最近表面点距箱体中心 0.456m。箱体中心内部的 raw sphere query 仍为 unknown；它不适合单独判定表面是否被看到。

## 重规划与任务结果

同一 goal/epoch 产生 traj_id 45–72。traj_id 45 的整条规划中心线仍穿过箱体；之后滚动样条中心线逐步绕开。约在注入后 **5.472 仿真秒**，原生 EGO 优化日志报告 `refined trajectory hits obstacles`、`refine_success=0`，同时当前曲线又被判定碰撞。项目补丁0039将暂时规划失败立即转换为 `planner_full_curve_planning_failed`，goal 在真值最小位置误差 **9.822m** 时中止；不是导航到达。

独立真值评估得到箱体相对机体包络采样最小间距 **0.967m**，扣除最大观测相邻样本包络运动 **0.0173m** 后为 **0.949m**。这是正的离线采样结果，不是连续动力学证明。禁止接触为0；raw VIO覆盖45.404仿真秒／10.497m，位置误差p95 0.0525m、yaw p95 0.1322°；这些是该失败轨迹的观察值，不是支持长程任务的最终阈值。

PX4实际 landed/disarmed，bridge=`LANDED`、control disabled、零控制样本；contact/truth/planner/bridge terminal observers均覆盖，独立读回 `safe-to-stop=true`，容器已停止。

## 结论与后续

#365 证实障碍创建、相机/地图表面观测和后续几何绕行轨迹；但 EGO 在一次后续优化仍不可行时由项目新增的立即中止逻辑结束任务。#366 已移除项目自加的整曲线准入调用并恢复上游重试状态；**当前运行代码还未用该新版本复测**。#367 以相同目标、箱体、注入时间和参数，单独验证 EGO 重试是否能完成任务。

原始数据：[`artifacts/runs/n10-20261027-365-live-obstacle-replan-current`](../../artifacts/runs/n10-20261027-365-live-obstacle-replan-current)。机器报告：[JSON](n10-live-obstacle-replan-20261027-365.json)。运行输入哈希在机器报告中。
