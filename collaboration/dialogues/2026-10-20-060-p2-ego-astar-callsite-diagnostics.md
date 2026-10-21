# GOAL C A* 调整循环与局部池越界追踪（#311）

- 用户目标仍是完成 `GOAL.md` 的 P0–P6 与 A–H；本轮继续单 D435i 仿真导航。
- #308 用 #306 同 profile 快照投影 #307 的一组 start/end，未复现池越界。为抓取实际 A* 调用，创建 run-local patch 0024，只增加坐标、格心分类、调整次数和越界点日志；与 0020/0022/0023 一起应用于 #297 重建源码的临时副本。
- #311 release overlay 五包构建通过。全栈传感器与定位进入 ready/valid 后发布手动目标；无 PX4、控制器、trajectory server、在线真值订阅或 snapshot service 调用。运动驱动器只发 Gazebo 力并接收时钟/IMU，不订阅模型真值位姿。探针收到了3条 B-spline，但没有执行轨迹。
- 直接观测到44,870次 `astar_search_reject`，全部对应起点或终点调整循环越出100³ A* pool；无原始输入点首次转换越界。逐条匹配 blocked-cell 与 exit 日志后，43,149次来自 `unknown=1,getOccupancy=0,inflate=1`，另1,721次来自已知但inflated单元。代表样例的中点格心 `(0.052704,-0.046601,0.035205)` 未知；patch 0020将unknown视作阻塞，算法将start沿远离end方向以0.1 m重复移动61次，直到尝试点 `(-5.171001,2.013147,-2.572760)` 越出局部池。
- 决定：0024以及未知阻塞策略继续保持实验态；不改 canonical `src/vendor/ego_planner`、`dependencies/sources.json`、默认参数或里程碑，不将 B-spline 计为轨迹/避障通过。将 #308 首次快照尝试中的描述性字符串修成明确布尔字段。
- 限制：#311 使用 0.5 m run-local inflation；106.7 MB 的诊断日志可能影响运行时序；没有同刻地图快照或第二布局重复，因而只确认该实验候选的失败机制。GOAL C/D/F 与 A–H 继续 pending。
- 证据：[A* callsite evidence](../../progress/evidence/p2-ego-astar-callsite-diagnostics-20261020-311.json)。后续先精简为只记录池退出，再为已知自由起点、unknown起点和inflated起点设计离线 fail-closed 测试。
