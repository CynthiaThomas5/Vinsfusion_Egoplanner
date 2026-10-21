# P5 EGO rclcpp take/callback trace #227

对话摘要：[2026-10-20-017](../../collaboration/dialogues/2026-10-20-017-p5-ego-rclcpp-trace-repeat.md)。证据：[EGO trace 与 PX4 ULog](../evidence/p5-ego-rclcpp-take-callback-trace-20261020-227.json)。

## 范围与配置

#227 复用 #226 的低负载 harness 和 #225 构建的 EGO run-local overlay，补丁顺序为 0012→0013→0015。目标仍为 ENU +0.30 m 横移、+30° yaw，run-local anisotropy filter 为 0.01；未修改 canonical 阈值、QoS、PX4 参数或控制逻辑。harness 不订阅 raw depth、EGO depth 或 occupancy cloud，以低频 MapStatus 保留地图门；没有启动 truth 输入，PX4 设定点与控制模式仍由 uav_px4_bridge 独占发布。

在 VIO/EGO graph 初始化前启动 LTTng session，采集 ROS 2 核心 tracepoint。初始化后 untrack 所有 VPIDs，只 track EGO VPID 902。CTF trace 共 33 个文件、7,308,816 字节；逐文件 SHA-256 清单已落在 run 目录，33/33 校验通过。Babeltrace2 只安装在一次性分析容器中，运行镜像没有改变。

## 运行与 trace 结果

定位和 PX4 稳定门通过，0.30 m/+30° action 以 position_yaw_tolerance_held 成功，最终位置为 [0.323815, -0.055940, 0.858902] m。之后 bridge history 记录 operator_disable，再在 LANDING 阶段记录 normalized_cost_exceeded；action 成功、质量锁存与 landing 分开记载，不推断因果。

trace 选取后的首 32.5 秒窗口中，EGO 相机位姿 successful rmw_take 共 565 次，最大间隔 1.713745 秒；depth 567 次、最大间隔 0.255020 秒；optimized odometry 604 次、最大间隔 0.268764 秒。相机位姿最大间隔位于 trace selection 后约 3.923–5.637 秒。完整选取窗口内相机位姿 successful take 与 message_filters callback 各 658 次；pose callback 平均/P95/最大耗时为 0.591/1.573/2.970 ms，depth callback 最大 1.742 ms。全部已配对 callback 中最长为 map reset service 的 9.871 ms。没有映射到相机位姿 subscription 的 taken=0 记录；trace 没有显示可解释 1.7 秒间隔的长同步 callback。

独立 harness 的相机位姿 observer 收到 548 条消息，source stamp 从 13.368 s 到 32.572 s，最大 receipt gap 0.265 s、最大 source-stamp gap 0.100 s；该观测持续到 harness wall elapsed 31.204 s。它和 trace 只有同 run/window 对照，没有按 header stamp 逐消息匹配。EGO 日志共有 1,443 条 odom/depth timeout warning，receipt 计数停顿时 last pose stamp/count 分别为 11.584/74、13.564/127、31.684/643、32.572/668；warning 总数不等同于 RMW 丢包数。

PX4 ULog 覆盖 31.444 仿真秒，dropout 为 0；EKF2_EV_CTRL=15、EKF2_GPS_CTRL=0，EV position/yaw/velocity flag 各为 28/41，GNSS aiding flags 均为零。PX4 进入 AUTO_LAND，记录 touchdown 并解除武装；电池 warning/fault 均为零。最终 bridge 状态为 LANDED，reason 为 normalized_cost_exceeded。

## 结论边界与验证

证据把长停顿定位在 EGO 相机位姿 successful take 时间线上；深度、优化里程计与 EGO callback 执行时间没有出现同量级长间隔。这还不能证明是 DDS reader，也不能排除 publisher 侧没有写出、wait set 未就绪或 executor 调度延迟：本轮没有跟踪上游 pose publisher，没有记录消息身份配对，也没有测量样本在 DDS 和 executor wait set 中的停留时间。官方 [ROS 2 Jazzy tracing instrumentation design](https://github.com/ros2/ros2_tracing/blob/jazzy/doc/design_ros_2.md) 描述了 RMW take、rcl/rclcpp take 与 callback 生命周期等 tracepoint；本轮 trace 只覆盖 EGO 进程。

本次执行的验证包括：真实 SITL action 与 landing/disarm；ULog pyulog 汇总；Babeltrace2 CTF 解析；trace 原始文件 33/33 SHA-256 校验。没有新增源码构建或单元测试。该轮为单次 run-local 诊断，不是 P5 或 GOAL A–H 验收。没有使用真值、canonical 门控未变。

下一步 #228 同时跟踪 camera-pose publisher 与 EGO，加入 publisher source-stamp 与 EGO callback source-stamp/receipt 对照，并保留 executor wait/ready tracepoint。继续使用低负载 harness，不增加图像/点云 observer，不调整 QoS 或任何阈值。
