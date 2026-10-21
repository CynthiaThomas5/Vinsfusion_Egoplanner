# 非 ROS 外部依赖

PX4-Autopilot 官方 v1.17.0 tag 已按固定 commit 检出至 `external/PX4-Autopilot`，39 个递归 submodule 均检出到父仓库 gitlink 指定 SHA；清单和 clone 日志见 `artifacts/runs/p0-px4-source-20261016-01/`。PX4 SITL 固件及 Gazebo Harmonic 插件已编译，证据见 `progress/evidence/p0-px4-firmware-build.json`。该目录保持外部只读来源；构建输出保存在 artifacts。PX4 进程、Gazebo 场景及 DDS Agent 互通尚未运行验证。
