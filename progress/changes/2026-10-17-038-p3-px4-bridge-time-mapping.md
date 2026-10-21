# P3 PX4 bridge 坐标与时间域核心

- 日期／记录：2026-10-17／038
- 对话摘要：[P3 PX4 bridge 坐标与时间域核心](../../collaboration/dialogues/2026-10-17-038-p3-px4-bridge-time-mapping.md)
- 修改：扩展 `trajectory.py` 的 NED 原点偏移、角差与 ENU/FLU→NED/FRD 姿态转换；增加 `vision_odometry.py` debug-only 字段映射；增加 `time_mapping.py` 将 ROS 仿真时间以实测时钟速率、PX4 DDS offset 映射到 PX4 域，并在输入不足或异常时拒绝；把真值 odometry/status 输入显式放到 `/debug_truth/*` 配置域，配置唯一时间阈值，扩展测试、包说明、CURRENT、P3 evidence index 与 milestones 证据引用。
- 行为变化：外部里程计不再从 ROS stamp 隐式计算 `timestamp_sample`，调用方必须显式给出 PX4 时间域映射值；质量值由配置传入并校验；时钟回退锁定 mapper。当前节点不存在，因此尚无控制行为变化。
- 验证：`python3 tools/test_px4_bridge_frames.py` 13/13；`python3 tools/test_px4_bridge_time_mapping.py` 6/6；固定 Jazzy 镜像全新 build/install/log 目录 colcon 构建2/2包；安装 overlay 对生成的 `PositionCommand`、`nav_msgs/Odometry` 转换和时间映射做 smoke；`python3 tools/project_status.py` PASS；`python3 -m py_compile ...`、JSON parse、`git diff --check` 和 `git diff --cached --check` PASS。运行目录：`artifacts/runs/p3-px4-bridge-final-core-20261017-07`，轻量报告：`progress/evidence/p3-px4-bridge-time-mapping.json`。
- 局限：无 PX4/Gazebo运行、PX4在线 timestamp 对时、EKF2融合、Offboard状态机、飞行、目标到达或降落证据。定位输出 child 为 `d435i_imu_<epoch>`，debug 外部 odometry 要求 `base_link`；相机安装外参和 truth odometry source 未实现。两次 smoke harness 失败（生成常量实例赋值、Python 代码拼写错误）均保留；修正后 smoke 通过。阈值 PROVISIONAL，P3仍在进行。
- 下一步：先实现单 D435i 飞行模型和隔离的 truth odometry/epoch adapter，完成 base_link/frame 与原点航向配对验证，再实现显式启用控制链。
