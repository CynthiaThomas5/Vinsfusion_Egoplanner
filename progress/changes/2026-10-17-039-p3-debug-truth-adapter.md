# P3 debug_truth 真值适配器

- 日期／记录：2026-10-17／039
- 对话摘要：[P3 debug_truth 真值适配器](../../collaboration/dialogues/2026-10-17-039-p3-debug-truth-adapter.md)
- 修改：新增 epoch 隔离的 `uav_sim.debug_truth_adapter`，仅接受配置的 Gazebo `world`→`d435i_link` Odometry 与 guarded `debug_truth` profile；输出 `/debug_truth/optimized_imu_odom` 和 transient-local `/debug_truth/localization_status`，遇到 frame／数值错误、时钟回退、仿真时钟停滞或真值过期即锁定。新增 attach-to-existing-SITL 的 `debug_truth.launch.py`，不启动 PX4/Gazebo、不发布控制。相机／IMU／真值桥配置为 lazy，避免调试路径转发未订阅的高带宽相机数据。更新 uav_sim/PX4 bridge 文档、接口契约、README、CURRENT 与 P3 证据索引。
- 行为变化：Gazebo 真值的 `d435i_link` 位姿被标记为 `d435i_imu_<epoch>`；SDF 中 IMU 与相机 link 同位。真值和状态保持 `/debug_truth/*`，不伪装成 `/localization/*`。每次节点重启使用不同 epoch。相机桥在 subscriber 到达后激活；`/clock` 不惰性化。
- 验证：
  - 固定 Jazzy 镜像 run #18 新 build/install：`colcon build --base-paths src/own --packages-up-to uav_sim`，`uav_interfaces` 与 `uav_sim` 2/2通过。
  - run #18 隔离 live PX4 v1.17 x500+D435i SITL：10条真值 Odometry stamp 严格递增，状态 TRACKING，frame 为 `odom_<epoch>`／`d435i_imu_<epoch>`；`/fmu/in/offboard_control_mode`、`trajectory_setpoint`、`vehicle_command`、`vehicle_visual_odometry` 均观测到0个 ROS publisher。未启动 Micro XRCE-DDS Agent。
  - run #19 在新 Gazebo partition 下执行 `tools/check_sensors.py --seconds 15`，31/31检查通过；图像、CameraInfo、IMU、深度、clock 和 TF 在 lazy bridge 配置下均实际收到。
  - `python3 tools/test_px4_bridge_frames.py` 13/13、`python3 tools/test_px4_bridge_time_mapping.py` 6/6；`python3 tools/project_status.py` PASS（结构检查）；`py_compile`、JSON parse、`git diff --check` 与 cached diff check PASS。
- 局限：P3 控制节点与 PX4 DDS input 仍不存在；无在线 PX4 TimesyncStatus、EKF2 EV fusion/GNSS aiding 状态、local origin/yaw pairing、Offboard、arm、takeoff、goal/landing 验证。camera-link pose 不是 x500 base_link。run #18 退出时 bridge 先于 adapter 停止，stale watchdog 锁定后进程以0退出；仍需单独验证无告警 teardown。run #10 容器启动脚本用了不兼容 ROS setup 的 `set -u`；#11 首版 adapter 重复声明 `use_sim_time`；#12 eager camera bridge 造成 clock-stall lock；#14 首次导入未公开的 rclpy 异常类型失败；这些结果都保留并未作为通过证据。run #13–#17 的核心样本检查通过，但未取代最终 run #18。
- 运行目录：
  - SITL/构建：`artifacts/runs/p3-debug-truth-adapter-20261017-18/`
  - lazy sensor calibration：`artifacts/runs/p3-debug-truth-adapter-20261017-19/`
- 证据：[P3 adapter evidence](../evidence/p3-debug-truth-adapter.json)。没有暂存、提交或推送。
