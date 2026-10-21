# P5 VINS-only PX4 bridge profile 基础

- 任务：继续完成 GOAL.md；为 P5 的 VINS 外部视觉飞控路径移除 bridge 对 `debug_truth` 的运行时硬限制。
- 用户约束：唯一控制发布者仍为 `uav_px4_bridge`；最终 profile 不订阅 truth 位姿或完整世界地图；PX4 参数、运行数据需可追溯；不得把构建／节点加载误报成 EKF2 融合或飞行通过。
- 决定：保留 P3 `debug_truth` profile 与显式 validator；新增 `vio_closed_loop` profile，配置只保存 canonical VINS 输入、VIO 方差及共享控制设置引用，避免复制 PX4 bridge 参数。VIO 输入为 `/localization/status`、`/localization/optimized_imu_odom` 和 `/clock`，使用同一 ENU→NED/FRD 转换和 EKF/GNSS readiness gate。VIO 方差与新鲜度值继续 PROVISIONAL，`runtime_ready=false`。
- 结果：固定 Jazzy 镜像新目录构建 `uav_px4_bridge` 1/1；两个 profile 的节点 smoke 都通过；VIO 无 truth 输入订阅，两个 profile 初始控制阶段均为 `DISABLED`。桥接、坐标、时间、参数和定位健康相关共52项测试通过。
- 限制／待办：未启动 PX4 SITL，未发布视觉里程计样本，未用 PX4 参数证明 GPS 关闭、EV aid 实际融合、起飞、任务、降落或 ULog 状态。P5 仅实现中，P4 也仍在进行。
- 证据：`progress/evidence/p5-vio-bridge-profile-smoke.json`；运行目录 `artifacts/runs/p5-vio-bridge-profile-20261017-86/`。
