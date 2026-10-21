# P5 VIO→EKF2 世界系统与融合诊断

对话摘要：[2026-10-17-045](../../collaboration/dialogues/2026-10-17-045-p5-vio-ekf2-world-systems.md)。

## 改动

- 更新 `tools/prepare_px4_vio_bootstrap_world.py`：以 PX4 默认世界为基础，增加项目校准墙，显式写入 PX4 `server.config` 中的 13 个世界系统；报告 PX4 世界、系统配置、项目墙体和输出哈希。生成墙体副本时消除 link 内 collision/visual 重名。
- 新增只读诊断工具 tools/probe_vio_stream_freshness.py，按会话 manifest 订阅原始图像、IMU、VINS telemetry/odom、仿真时钟与定位状态，统计源龄和接收间隔；不发布消息或控制。
- 更新 `tools/test_px4_vio_bootstrap_world.py`：验证地面、物理／地磁／气压元数据、PX4 系统插件、墙体及无真值输入。CLI 可同时写出世界生成报告。
- 更新 README、CURRENT 与 P5 milestone evidence 链接；P5 保持 `in_progress`，P4/P6 和 GOAL A–H 均不调整通过状态。
- run #94 因 PX4_GZ_MODELS 指向错误目录而无法生成 x500_d435i，单独排除。run #95 发现过一次 telemetry_stale 锁存；run #96 使用只读原始流探针复跑，未复现该锁存并保持定位 TRACKING。

## 验证

- 静态：世界生成（1）、传感器桥隔离（2）、PX4 参数（2）、VIO profile（6）、bridge control（11）、frame（19）、时间映射（6）、定位健康（9）共56项测试通过；工具 `py_compile` 通过。生成世界由 Gazebo Harmonic 的 `gz sdf -k` 报告 `Valid.`。
- `python3 tools/project_status.py`：`Structure/design check: PASS`。该项只检查结构与设计，不代替运行验证。
- `git diff --check` 与 `git diff --cached --check`：通过。未运行 colcon，因为本轮没有改 ROS package 源码、接口或构建配置。
- SITL：run #95 使用 PX4 v1.17.0、Gazebo Harmonic、Jazzy、VIO autostart 5011。参数为 `EKF2_EV_CTRL=15`、`EKF2_GPS_CTRL=0`、`SIM_GZ_EN_ODOM=0`；ROS 图没有 `debug_truth` 输入，桥接控制保持 DISABLED，机体未解锁。
- ULog：记录90条 `vehicle_visual_odometry`；77条 `estimator_status_flags` 中 `cs_ev_pos` 置位21次、`cs_ev_yaw` 置位15次；EV position/yaw aid 数据的 fused 字段分别为78/90、62/90。GNSS position/velocity/yaw、GPS height 与 auxiliary global position aiding flags 均为零。ULog SHA-256 为 `d695ecdba25476b3a09dbdd7f39adee3e7b52cf89e2aad2663d7e64b97cfd6e1`。
- 结果分类为部分通过：runtime qualification 的最终快照为 FAIL，但这只是采样末端状态；重读完整 ULog 和 probe 状态计数确认 EV 融合曾实际发生。复核见 `progress/evidence/p5-vio-ekf2-fusion-observed-20261017-95.json` 与 run 目录中的 `ulog-analysis.json`。

## 未验证与限制

- #96 的75秒 SITL 中，定位末端为 TRACKING、good_pairs=524；45秒原始流探针测得 VINS telemetry 最大接收间隔0.491秒、最大相对 /clock 源龄0.20秒。PX4 ULog 记录345条 VehicleOdometry，EKF2 状态位 cs_ev_pos/cs_ev_yaw 分别置位65/127和45/127次，GNSS aiding flags全零。
- #96 末端 PX4 bridge 的 EV fusion flags仍为真，但 readiness=false、reason=px4_timesync_stale；控制保持 DISABLED、机体未解锁。需先查明 PX4 timesync readiness，仍不能推进飞行。证据见 progress/evidence/p5-vio-ekf2-stream-stability-20261017-96.json。

- 定位适配器在154组有效配对后于观察窗口内锁存 `telemetry_stale`；最终没有持续有效定位，profile 仍为 `runtime_ready=false`。该 freshness 门槛继续保持，不据此认定稳定融合。
- 未运行 EGO、Offboard、解锁、飞行、导航或降落；run #95 仅证明曾发生 EV 融合且无 GNSS aiding。P5 未通过，P4 与 P6 仍未完成。
- #94 的环境启动错误及全部原始日志保留在 `artifacts/runs/p5-vio-ekf2-world-systems-20261017-94/`，不计入传感器、融合或验收证据。

## 下一步

调查 #96 末端 px4_timesync_stale readiness 阻塞并重复无 GNSS/真值融合；保持控制禁用，不放宽健康阈值。只有 readiness 稳定后才推进视觉控制闭环。P5 保持 in_progress。

