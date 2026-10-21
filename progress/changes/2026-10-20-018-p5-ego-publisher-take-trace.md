# P5 camera-pose publisher 与 EGO take 双进程 trace #228

对话摘要：[2026-10-20-018](../../collaboration/dialogues/2026-10-20-018-p5-ego-publisher-take-trace.md)。证据：[publisher/take trace 与 PX4 ULog](../evidence/p5-ego-publisher-take-trace-20261020-228.json)。

## 范围与配置

#228 复用 #227 的低负载 harness 和 #225 构建的 EGO run-local overlay，仍按 0012→0013→0015 应用补丁，run-local anisotropy filter 为 0.01。目标与 #226/#227 一致：ENU +0.30 m 横移、+30° yaw。没有改 canonical 算法阈值、QoS、PX4 参数或控制状态机；未订阅 raw depth、EGO depth 或 occupancy cloud；没有 truth 输入，控制发布仍由 uav_px4_bridge 独占。

LTTng session 在 graph 启动前开始，以保留 publisher/subscription handle 元数据；graph 初始化后只 track EGO PID 909 和 mapping_input_adapter PID 908。两个进程之外没有 post-selection trace event。采集 ROS 2 publisher init/write、RMW take、callback 与 executor tracepoint。原始 CTF 共 33 个文件、9,623,992 字节；逐文件 SHA-256 清单 33/33 校验通过。Babeltrace2 仅安装在一次性分析容器，运行镜像没有变化。

## 发布与接收结果

首 32.5 秒 trace 窗口中，mapping_input_adapter 对 /drone_0_camera_pose 记录 575 次 rcl_publish 与 575 次 rmw_publish；EGO 记录 548 次 successful rmw_take。EGO 最大成功 take 间隔为 2.521827 秒，发生在 trace selection 后约 8.540–11.062 秒。就在这段空档内，publisher 仍产生 50 次 rmw_publish，最大写端间隔为 0.122401 秒；同一 CTF 时钟对齐显示写端持续活动。

该空档期间没有映射到 camera-pose reader 的 rmw_take 调用，也没有该 reader 的 taken=0 记录。一个 message_filters pose callback_start 位于空档起点后的 0.9 微秒，之后直到下一次 successful take 没有新的 pose callback_start。EGO pose callback 平均/P95/最大耗时为 0.586/1.543/6.134 ms，未观察到与 2.52 秒空档同量级的同步回调。独立 harness observer 的 pose receipt 最大间隔 0.267 秒、source-stamp 最大间隔 0.068 秒。

publisher 的 rmw_publish trace 证明调用到达 RMW 写端，不能证明样本进入 EGO Fast DDS DataReader。EGO 的 rclcpp_executor_get_next_ready、wait_for_work 和 execute tracepoint 在空档内分别记录 2,235、1,099、889 次，但这些 Jazzy tracepoint 没有 selected-entity 字段，不能指出 pose subscription 是否 ready 或被 executor 选中。因而此次结果把边界缩小到 publisher 写端之后、EGO successful take 之前，尚不能在 DataReader delivery/readiness 与 executor wait-set 选择之间归因。

## 飞行结果与验证

前置门通过并发出了目标，但 action 以 localization_accel_bias_norm_exceeded 中止。PX4 ULog 覆盖 29.748 仿真秒，dropout 为零；EKF2_EV_CTRL=15、EKF2_GPS_CTRL=0，EV position/yaw/velocity flags 各为 24/40，GNSS aiding flags 全零。PX4 进入 AUTO_LAND，随后短暂 DESCEND/failsafe，记录 touchdown 并解除武装；电池 warning/fault 为零。该安全终态与发布/接收 gap 分开记录，不推断因果。此诊断不构成 P5 或 GOAL A–H 验收。

执行了 run-local launcher bash -n、publisher trace analyzer py_compile、真实 SITL、pyulog ULog 汇总、Babeltrace2 CTF 分析与 33/33 trace 文件哈希校验。没有源码修改，因此没有新增 ROS package build 或单元测试。

## 下一步

在另一轮飞行前，先检查固定 Jazzy/Fast DDS 环境可用的 per-reader data-available/readiness 观测点，并做隔离低开销 preflight。若可以直接观察 EGO DataReader 状态，再以同一个低负载组合将 reader 状态、RMW take 和 executor wait 事件放在同一时间线上；不调整 QoS/阈值，不增加图像/点云 observer。
