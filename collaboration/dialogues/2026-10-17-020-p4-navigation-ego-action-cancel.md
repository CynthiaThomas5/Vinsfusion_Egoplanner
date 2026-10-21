# P4 导航 action 与 EGO 取消接口

- 用户要求继续执行 GOAL，并遵循本仓库阶段边界、源码迁移和证据记录约定。
- 本轮决定：将现有任务状态核心接到 `NavigateToPose` ROS action；将 `goal_id + epoch` 路由到 EGO 和 `traj_server`；对 EGO vendor 代码保留可重放补丁；只用合成输入测试接口，不把结果写成在线规划或飞行验收。
- 已实现并验证：7 个 Jazzy 包在新目录构建；合成 action 验证 goal 路由、显式取消、旧 epoch 拒绝和 ROS clock 回退；真实 C++ `traj_server` 验证目标 yaw、epoch frame、忽略过期取消及匹配 ABORT。
- 测试使用 Fast DDS UDPv4 隔离已记录的容器共享内存传输问题，没有修改项目默认传输配置。没有启动 Gazebo、VINS、PX4 控制或实机。
- 待办：用动态 D435i/VINS/地图运行验证真实 EGO 目标规划与轨迹跟踪；实现并验证 `uav_px4_bridge`、EKF2 外部视觉里程计融合、无真值闭环和 GOAL A–H 其余标准。
