# P3 PX4 bridge Offboard 与 EKF2 融合 SITL smoke

对话摘要：[2026-10-17-040](../../collaboration/dialogues/2026-10-17-040-p3-px4-offboard-flight-smoke.md)。

## 改动

- 为 `uav_px4_bridge` 完成新 build/install 后的隔离 SITL 运行留存 PX4 ULog、bridge 报告和参数 stage；新增 `progress/evidence/p3-px4-bridge-offboard-flight.json`。
- 更新根 README、bridge 使用说明与 `progress/CURRENT.md`，将已验证的控制／融合范围和尚未接入 EGO 的边界写清楚。
- 将 P3 证据路径加入 `progress/milestones.json`，阶段仍为 `in_progress`；结构检查器的 P3 下一步提示改为 EGO 轨迹和避障整合。

## 验证

- `colcon build --base-paths src/own --packages-up-to uav_px4_bridge`：#32 新 build/install，3 包完成。
- `bash artifacts/runs/p3-px4-bridge-node-20261017-32/run-debug-flight-sitl.sh`：PASS。唯一控制服务路径完成 prestream、preflight、起飞（ROS 报告爬升0.9115 m）、受控降落和解除武装；PX4 四个输入话题各有一个 ROS publisher。
- PX4 ULog（30.376 s）：661 条 `vehicle_visual_odometry`；EV pos/vel/yaw aid sources 分别融合978/980、977/978、979/980条；EV pos/hgt/yaw/vel flags 各24/39；GNSS aiding flags 为零。`EKF2_GPS_CTRL=0`，`SIM_GZ_EN_ODOM=0`。ULog armed 状态在14.604 s进入，30.072 s回到 disarmed；无 failsafe 样本。
- `python3 tools/test_px4_bridge_control.py` 11 项、`test_px4_bridge_frames.py` 19 项、`test_px4_bridge_time_mapping.py` 6 项、`test_sim_geometry.py` 3 项、`test_px4_debug_params.py` 1 项：通过。`python3 tools/project_status.py`、py_compile、JSON parse、`git diff --check`：通过。

## 局限与下一步

本次使用 Gazebo debug_truth，且 PX4 SITL 原始 GPS sensor 样本存在；只证明该参数组合下 EKF2 没有 GNSS aiding，不能证明最终无 GPS 传感器依赖。起降路径是 bridge hold test，没有发出 EGO `PositionCommand`，因此没有在线地图避障、指定目标/yaw、到达反馈或 P3 阶段闭环。继续连接 EGO READY 轨迹，验证运行时 frame/time contract 和状态机降级行为；P3 保持进行中。

运行与源码哈希、ULog 摘要详见 `progress/evidence/p3-px4-bridge-offboard-flight.json`。
