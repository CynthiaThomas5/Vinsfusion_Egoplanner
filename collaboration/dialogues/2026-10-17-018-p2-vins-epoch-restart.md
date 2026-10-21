# P2 VINS 实际进程重启与新 epoch 隔离

- 用户要求继续推进项目目标；本轮承接 clock 回退双次仿真之后的 VINS 进程重启验证。
- 保持项目约束：旧来源与设备只读；只运行单 D435i 仿真；不启动 PX4 控制；真值不进入在线估计或探针；不把结构检查当运行证据。
- 决定在独立 ROS domain 与 Gazebo partition 中运行两次真实 VINS 停止／新 session 启动。旧适配器先观察锁定与 plan_env 清图，再停止旧适配器并创建新 manifest/epoch；探针同时核对切换后 pose/odometry frame。
- 两次均观察到旧 epoch `LOCKED / optimized_publisher_missing_or_ambiguous`、EGO 空图及输出计数稳定；新 epoch 空图屏障后恢复 TRACKING、非空地图，且切换后的 frame 只使用新 epoch。完整数值与原始日志哈希见 [P2 VINS epoch restart 证据](../../progress/evidence/p2-vins-epoch-restart.json)。
- 待办：目标与轨迹状态机取消、PX4 故障动作、10 分钟负载、规划闭环与真实设备验收仍缺失；GOAL E、P2、P4 继续进行中。
