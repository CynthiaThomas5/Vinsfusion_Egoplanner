# P3 PX4 bridge 坐标转换核心

- 用户目标：继续完成 `GOAL.md`，按实际阶段推进并保留验证证据。
- 项目约束：单 D435i 仿真；在线真值仅在 `debug_truth`；PX4 控制 publisher 只能由 `uav_px4_bridge` 独占；最终组合不得使用真值；不触碰旧来源、不覆盖已有用户修改、不暂存或提交。
- 发现：P3 需要的 `uav_px4_bridge` 之前只有 README 占位；EGO `PositionCommand` 使用 epoch 专属局部坐标，PX4 `TrajectorySetpoint` 使用 NED。若不检查 profile、epoch 和坐标，直接转发会有方向与高度符号风险。
- 实施决定：新增可构建的 `uav_px4_bridge` ament_python 包、统一 ENU/NED 参数文件和纯轨迹转换模块。当前入口仅接受 debug_truth 配置、`odom_<epoch>` frame、匹配 epoch 与有限 READY 轨迹；VIO profile、无效 frame 和非法数值拒绝。终态轨迹不产生 setpoint。
- 验证：8 项已知轴、航向、完整轨迹字段、非 READY、profile、epoch frame、非有限值和不支持坐标配置测试通过；固定 Jazzy 镜像新 build/install 中 `uav_interfaces` 与 `uav_px4_bridge` 2/2 构建通过，并用生成的 ROS `PositionCommand` 消息实际调用转换函数成功。
- 阶段决定：P3 改为 `in_progress`，不标记通过。没有 PX4 publisher、Offboard 状态机、外部里程计、Gazebo 飞行场景或控制运行；本次没有启动 PX4/Gazebo，也没有发布控制。初次构建命令因 `set -u` 在 ROS setup 前失败，未运行 colcon，已明确排除。
- 下一步：实现显式启用和状态门控的 PX4 ROS 控制节点；在连接它之前，完成 `debug_truth` 位姿适配与相机/飞行模型装配的接口审计。
- 证据：[P3 PX4 bridge 转换核心](../../progress/evidence/p3-px4-bridge-frame-core.json)；有效构建日志与 source manifest 在忽略目录 `artifacts/runs/p3-px4-bridge-frame-core-20261017-04`。
