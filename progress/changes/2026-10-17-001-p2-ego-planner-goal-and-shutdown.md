# P2 EGO 目标规划与停机

- 关联对话：[任务摘要](../../collaboration/dialogues/2026-10-17-001-p2-ego-planner-goal-and-shutdown.md)。
- 文件与行为：新增 EGO patch 0007，按顺序应用于 upstream revision `23a8d5a191711dd65633df689bd00f55d4dea8f9` 的 patch 0006 之后。初始化等待 `EXEC_TRAJ` 时现在检查 `rclcpp::ok()`，且 shutdown 后跳过 `rclcpp::spin`。更新来源清单、补丁说明、接口说明、milestones、CURRENT 和本次证据。没有修改旧来源。
- 静态／构建验证：在 `d435i-vins-build` 的 ROS Jazzy 中只重建 `ego_planner` 包，构建通过；其依赖包从既有安装解析。详细命令、事件日志和 SHA256 见[验收报告](../evidence/p2-ego-planner-goal-and-shutdown.json)。
- 动态规划验证：run #09 使用全新 epoch 和 ROS domain 120，观测 385 条优化位姿、669 组建图配对和 953–1683 个地图点。EGO 手动收到目标 `(1,0,1)` m，首条 B-spline 优化成功一次并进入 `EXEC_TRAJ`。该 launch 没有 `traj_server`、PX4 或控制节点；FSM 后续回到 `WAIT_TARGET` 不代表车辆到达目标。
- 动态停机验证：run #11 使用默认原点预设目标，确认 EGO 在小于 0.2 m 的目标距离下连续重试；SIGINT 后 EGO launch 报告 clean finish，进程组无活动进程且 wait status 为 0，没有升级到 SIGTERM／SIGKILL。复查发现测试脚本误清空 sensor launch PID 列表，遗留的传感器组在后续运行排障时被发现并停止；这不影响 EGO 进程退出结果。随后的 5 秒静止地图探针观测到有效定位、深度、45 条优化里程计与 81 组配对，但没有占据点，因此探针本身返回非零；不计入地图通过。
- 局限：各自仅一次动态观察；地图输入停止时仍会出现 stale；planner 重复性、轨迹跟踪、目标到达、3D+yaw API、碰撞间距、受控故障、PX4 SITL／实机闭环未验证。默认 preset 目标配置和上游手动目标忽略 Z/yaw 的问题仍需 own 导航层处理。
- 下一步：实现 own 层 goal/status API 与 EGO 的显式映射；冻结位置、yaw、容差和超时阈值，再独立重复目标规划及停机，并继续完成受控 stale、epoch reset、时钟回退和地图快照验证。
