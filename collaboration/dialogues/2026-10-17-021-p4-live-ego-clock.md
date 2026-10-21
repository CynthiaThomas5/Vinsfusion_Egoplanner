# P4 动态 EGO 目标规划与时钟对齐

日期：2026-10-17。

## 任务摘要

继续单 D435i 仿真导航 P4：在真实 D435i/VINS/在线地图链路下提交 `NavigateToPose`，检查 EGO 规划、yaw 传递与取消，再把可复查结果写入项目证据。

## 用户约束

- 仅推进 P0–P6 单 D435i 仿真导航；旧部署工程与 ROS_SEARCH 实验区只读。
- 所有 PX4 设定点及 `OffboardControlMode` 仍由 `uav_px4_bridge` 独占；本次不启动控制器或 PX4。
- 实测结果、失败路径与限制分开记录；不以在线规划或结构检查宣称完整验收。

## 决定与证据

- EGO 默认 `rclcpp::Clock().now()` 与 Gazebo `/clock` 不在同一时间域。添加 EGO patch 0018，让 manager、FSM、可视化和 traj_server 使用各自 node ROS clock，并在 `uav_navigation` 中以 BEST_EFFORT、互斥 callback group 接收 `/clock`。
- patch 0018 在固定 EGO revision 的 post-0017 文件上重放，五个变更 vendor 文件逐字节匹配；新目录 Jazzy 构建7包通过。
- run `p4-navigation-live-ego-20261017-06` 在 TRACKING、深度健康且地图非空时接受目标；EGO 生成10个 yaw sample、终值0.7 rad 的 B-spline；样条和首条 READY 命令相差7 ms。显式取消后 action 返回 `caller_cancel`，traj_server 发匹配 ABORT，之后没有 READY。
- 同一短运行的配对深度／位姿间隔 P95为0.396 s、最大0.495 s；监督节点 teardown 日志出现两条 Destroyable 异步异常，均保留为未解决限制。
- 原始 probe JSON 顶层 `latest_clock_ns` 为空，嵌套 `trajectory_clock_check.latest_clock_ns` 为3,969,000,000 ns；保留原始文件不做覆盖，以嵌套检查作为证据。

## 待办

- 调查地图配对输入时序长尾和导航节点 teardown 异常。
- 实现并测试 PX4 bridge 与 SITL 轨迹跟随；完成前，不把 EGO trajectory READY 解释为车辆已跟踪或到达。
- 完成 P0–P6 其余要求及正式验收。
