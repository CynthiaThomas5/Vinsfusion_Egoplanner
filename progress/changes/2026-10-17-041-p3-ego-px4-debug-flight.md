# P3 debug_truth EGO→PX4 目标飞行闭环

对话摘要：[2026-10-17-041](../../collaboration/dialogues/2026-10-17-041-p3-ego-px4-debug-flight.md)。

## 改动

- 新增 `uav_px4_bridge/launch/debug_truth_ego_px4.launch.py`，把深度健康门、时间配对建图适配器、EGO、导航 action、traj_server 与 PX4 bridge 组合起来。定位状态／里程计均 remap 到 epoch 隔离的 `/debug_truth/*`；相机 intrinsics 从 D435i SDF 推导，规划与轨迹参数在 config 中。
- 新增 `config/components/navigation/debug_truth_smoke_goal.json` 与 `tools/run_px4_debug_ego_flight.py`：先验证地图和非 preflight 控制门，再通过唯一 enable 服务起飞、提交 action 目标、校验匹配 EGO READY 轨迹及目标结果，最后通过 disable 服务降落。
- `ego_planner.json` 显式设置低速 MANUAL_TARGET smoke 参数。#33 的 PRESET_TARGET 空闲航点引起空转，#34 改为 MANUAL_TARGET 后保持 WAIT_TARGET 等待 action。
- `DepthHealthMonitor` 在 ROS context 已关闭时忽略 rclpy wait-set `RCLError`；如果 context 仍有效则重抛。
- 更新 P3 exit audit、CURRENT、里程碑和组件说明；P3 标为 passed，限制写明未验收避障净空／最终视觉运行。

## 验证

- #34 fresh build/install：`colcon build --base-paths src/own --packages-select uav_interfaces uav_sim uav_mapping uav_navigation uav_px4_bridge`，5包通过。
- live SITL：`bash artifacts/runs/p3-px4-bridge-node-20261017-34/run-debug-ego-flight-sitl.sh`，PASS。plan_env 观测192份占据云、峰值2,047点；同 epoch action 目标到达误差0.06131 m，938份 READY `PositionCommand` 匹配同一 goal ID；PX4 由唯一 bridge 控制并 landed/disarmed。
- #34 ULog：34.3 s，808条外部视觉里程计；EV pos/vel/yaw aid source融合1165/1167、1164/1165、1166/1167；EKF2 GPS control=0，GNSS flags全零，14.960 s armed、34.004 s disarmed，无failsafe样本。
- 测试：bridge control 11、frames 19、time mapping 6、PX4 debug params 1、sim geometry 3、mapping input 4、navigation task state 10项通过；navigation adapter 和 trajectory server ROS 集成测试通过；`python3 tools/project_status.py`、JSON/XML parse、py_compile、`git diff --check` 通过。

## 限制与下一步

P3 route 使用 Gazebo debug_truth，SITL raw GPS 传感器仍存在，且未专门设置障碍；结果只满足 debug_truth 在线建图／EGO／PX4闭环阶段，不证明 obstacle clearance 或最终视觉导航。继续 P4 的 canonical `/clock` VINS→map→EGO活动目标复测，再做无GNSS/真值辅助的 EKF2/P5 与 A–H 最终验收。

完整运行与 SHA-256 见 `progress/evidence/p3-px4-ego-flight.json`；出口判定见 `progress/evidence/p3-stage-exit-audit.json`。
