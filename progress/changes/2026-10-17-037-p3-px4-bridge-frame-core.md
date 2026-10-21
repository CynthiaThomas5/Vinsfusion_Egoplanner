# P3 PX4 bridge ENU/NED 转换核心

- 任务 ID／日期：037／2026-10-17
- 对话摘要：[P3 PX4 bridge 坐标转换核心](../../collaboration/dialogues/2026-10-17-037-p3-px4-bridge-frame-core.md)
- 修改文件：新增 `src/own/uav_px4_bridge` 包、`config/components/px4_bridge/frames.json`、`tools/test_px4_bridge_frames.py` 与 P3 部分证据；更新 `README.md`、`progress/CURRENT.md`、`progress/milestones.json`、`progress/evidence/README.md`。
- 行为变化及原因：新增纯 ENU→NED 转换和 profile gate。只有 `debug_truth`、对应 epoch frame、匹配 epoch 和有限 READY 轨迹会返回转换结果；非 READY 返回空值，最终 VIO profile 被拒绝。P3 从 not_started 调为 in_progress。
- 验证类型：静态已知轴单测、安装包导入和真实 Jazzy 新目录 colcon 构建；未运行 PX4、Gazebo 或控制。
- 验证命令与结果：`python3 tools/test_px4_bridge_frames.py` 8/8；固定镜像 `colcon ... --packages-up-to uav_px4_bridge` 2/2（`uav_interfaces`、`uav_px4_bridge`）；安装 overlay 导入、ENU/NED smoke 和生成的 ROS `PositionCommand` 转换通过；source SHA 清单通过；`python3 tools/project_status.py`、JSON 检查及 staged/unstaged `git diff --check` 通过。最终运行目录为 `artifacts/runs/p3-px4-bridge-frame-core-20261017-04`。
- 排除尝试：run `p3-px4-bridge-frame-core-20261017-01` 在 `source /opt/ros/jazzy/setup.bash` 前启用了 bash nounset，setup 因未初始化 `AMENT_TRACE_SETUP_FILES` 退出；colcon 未启动，不能计入构建。修正命令后先在 `...-02`、`...-03` 构建，最终 `...-04` 在当前完整源码和配置上以全新 build/install 完成并复验。
- 局限与下一步：该包当前没有 PX4 ROS publisher、Offboard 状态机、外部里程计、起飞／降落策略或 launch；ENU 假设只适用于 P3 debug truth，不处理 VINS 原点与安装外参。下一步先实现显式授权、状态新鲜度门控和 fail-closed 的 bridge 状态机，再做隔离 SITL 验证。
