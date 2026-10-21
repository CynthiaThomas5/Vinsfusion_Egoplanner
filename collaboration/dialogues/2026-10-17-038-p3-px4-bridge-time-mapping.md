# P3 PX4 bridge 坐标与时间域核心

- 用户目标：继续完成 `GOAL.md`，按 P0–P6 推进并保留可复核证据。
- 约束：只推进单 D435i 仿真导航；在线真值仅在 `debug_truth`；PX4 控制输出由 `uav_px4_bridge` 独占；不修改旧来源，不覆盖既有用户改动，不暂存、提交或推送。
- 本轮核实：现有 VINS 适配器发布 `odom_<epoch>` 下的 `d435i_imu_<epoch>` child frame，而 debug 外部里程计契约需要机体 `base_link`。不能把该 VINS 输出直接冒充机体真值。ROS `/clock` 的时间也不能直接作为 PX4 启动时间戳；PX4 DDS `TimesyncStatus.estimated_offset` 必须配合宿主时间域映射。
- 实施：扩展 ENU/NED 原点偏移和 ENU/FLU→NED/FRD 姿态转换；增加 debug-only 外部里程计字段转换，要求调用方显式给出 PX4 域 `timestamp_sample_us`。增加 `RosClockMapper`，以 `/clock` 样本和单调接收时钟拟合仿真时钟速率，再结合 PX4 DDS offset 映射时间；回退、过期、RTT、拟合误差和速率异常均拒绝。
- 验证：坐标/姿态/外部里程计回归13/13；时钟映射回归6/6；固定 Jazzy 镜像全新目录构建 `uav_interfaces` 与 `uav_px4_bridge` 2/2；安装 overlay 中生成的 `PositionCommand`、`nav_msgs/Odometry` 转换和时间映射 smoke 通过；`project_status.py`、py_compile、JSON parse 和 diff 检查通过。
- 边界：本轮未发布任何 PX4 控制，也未启动 PX4/Gazebo；无控制节点、Offboard 状态机、EKF2 融合和飞行证据。当前 `debug_truth.json` 中的时间年龄与速率阈值是 PROVISIONAL。#05 初次 smoke harness 试图给生成消息实例覆写常量而失败；#07 第一次安装 smoke 代码有语法错误；两份失败日志均保留，修正后的 #07 retry 完整验证通过。
- 下一步：实现并验证单 D435i 飞行模型、真值 odometry/epoch 适配和 `base_link` 来源；再通过姿态/位置配对验证 PX4 原点与航向对齐，之后连接显式启用和 fail-closed 控制状态机。
- 证据：[P3 bridge 坐标与时间域核心](../../progress/evidence/p3-px4-bridge-time-mapping.json)，原始运行目录 `artifacts/runs/p3-px4-bridge-final-core-20261017-07/`。
