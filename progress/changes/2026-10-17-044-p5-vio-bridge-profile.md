# P5 VINS-only PX4 bridge profile 基础

对话摘要：[2026-10-17-044](../../collaboration/dialogues/2026-10-17-044-p5-vio-bridge-profile.md)。

## 改动

- `trajectory.py` 增加 profile-aware 校验：保留 `debug_truth` 的 P3 限定检查，同时允许只使用 VINS 的 `vio_closed_loop` source contract。ENU 轨迹与里程计转换对两个通过校验的 profile 共用；不匹配的 truth/GNSS flags 仍拒绝。
- `control_state.py` 和 `vision_odometry.py` 接受上述已校验 profile。`px4_bridge_node.py` 按 profile 选输入；VIO 只订阅 `/clock`、`/localization/status`、`/localization/optimized_imu_odom`，拒绝含 `debug_truth` 键的 VIO bridge 配置。Offboard 仍由唯一 bridge 发布且默认禁用。
- 新增 `vio_closed_loop` bridge 配置、独立 frame contract 与 attach launch；profile 配置只保存 canonical VINS 输入和位置／姿态／速度方差0.01／0.01／0.04，并引用唯一共享控制配置，避免重复 PX4 bridge 参数。VIO 方差均为 PROVISIONAL；profile 标为 `in_progress`、`runtime_ready=false`。
- 新增独立 profile 回归脚本，并更新 control-state 测试和只读结构检查器。P5 阶段改为 `in_progress`，不代表阶段出口通过。

## 验证

- `tools/test_px4_bridge_control.py`：11项；`test_px4_bridge_frames.py`：19项；`test_px4_bridge_time_mapping.py`：6项；`test_px4_debug_params.py`：1项；VIO profile：6项；定位健康：9项，共52项通过。完整命令输出见 `artifacts/runs/p5-vio-bridge-profile-20261017-86/bridge-regression-tests.log`。
- 固定 Jazzy `d435i-vins:dev` 镜像，新 build/install 目录构建 `uav_px4_bridge` 1/1通过。装入文件与当前 Python 源码、launch SHA 一致。
- `tools/probe_px4_bridge_profile_load.py` 分别实例化 debug_truth 和 VIO profile，不 spin／enable；VIO 仅选择 canonical VINS topics 且无 truth source subscription，两个 profile 状态都为 `DISABLED`。输出见 `build-and-smoke.log` 与 `profile-load-smoke-final.log`。
- `python3 tools/project_status.py`：P4/P5 仍进行中的结构检查；仅结构设计检查，不覆盖 ROS build 或 SITL。
- `git diff --check`：通过。

## 局限与下一步

没有 PX4 SITL 或 `/fmu/in/vehicle_visual_odometry` 样本，没有确认 PX4 参数、GNSS aiding flags、EKF2 EV fusion、ULog 或任何飞行行为。接下来完成 profile 对应的 PX4 启动参数与整合 launch，在全 VINS 链路下检查 EV 真实融合和无 GNSS aiding，再运行受控 SITL。P4 的地图／轨迹跟踪、故障响应、多场景和长时验收仍需继续。

主要证据：`progress/evidence/p5-vio-bridge-profile-smoke.json`。
