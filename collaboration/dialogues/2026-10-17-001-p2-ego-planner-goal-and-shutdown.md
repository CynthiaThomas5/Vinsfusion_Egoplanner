# P2 EGO 目标规划与停机诊断

- 继续推进 `GOAL.md` 的完整 A–H、P0–P6 目标；本次不改变验收范围，也不启动 PX4 或任何控制发布者。
- run #03 使用 EGO 上游 preset 模式，默认只给一个 `(0,0,0)` 航点。该 run 首个优化位姿距原点约 0.00074 m；EGO 的 `reboundReplan` 对小于 0.2 m 的目标直接返回失败，因此该配置解释了最初的重复“Close to goal”失败。后续优化器失败仍需独立分析。
- run #09 明确使用手动模式并发送非零 `/move_base_simple/goal`，EGO 首次优化成功并进入 `EXEC_TRAJ`。这是一次 B-spline 规划观察；没有轨迹跟踪、到达确认或 PX4。上游手动 waypoint 回调目前忽略消息 Z 和 yaw，把 Z 固定为 1 m。
- EGO 初始化中的同步循环曾在退化 preset 目标下持续重试，SIGINT／SIGTERM 未让进程返回。新增 patch 0007 检查 ROS context 并在初始化时跳过 shutdown 后的 `spin()`。`ego_planner` Jazzy 单包重建通过；run #11 在 440 次近目标重试时 SIGINT，EGO 和 launch 干净退出，没有升级信号。
- run #11 后续静止场景地图探针没有占据点并返回非零，故该 run 的地图探针不计通过；只保留 EGO 停机观察。
- 下一步在 `src/own/uav_navigation` 实现满足 GOAL 的 goal/status API，并将 3D+yaw、容差、取消、超时与 EGO 上游接口差异显式处理；重复验证目标规划与停机，再执行地图故障注入。所有 P 阶段仍为进行中或未开始。

- 后续复查发现 run #11 的测试脚本在确认 EGO 退出后清空了整个 launch PID 列表，导致传感器 launch 组仍活动；该组在 run #12 排障时被发现并停止。EGO 节点本身的 SIGINT clean exit 与 ROS graph 消失观察不变。
