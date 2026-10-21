# P2 活动轨迹深度 stale 处理

- 继续完成 `GOAL.md` 全部 A–H 与 P0–P6；没有缩小范围或启动 PX4 控制。
- #05 的重复手动目标覆盖了 stale 窗口，但 EGO 在 reset 前因 callback 内嵌套 `spin_some` 报 executor 异常而退出，不能计为安全行为。#06 单目标观察到 stale map 清理／重建，但没有活动任务响应结论。
- 记录上游 EGO #0008 补丁：手动目标由 callback 暂存，FSM wall timer 消费最新目标；EMERGENCY_STOP 时清掉待处理目标。补丁基于 #0007 后的固定上游 revision，定向 Jazzy 构建通过。
- #07 在新 epoch 中发布37个手动目标，目标窗口与深度注入窗口重叠。EGO 成功规划进入 `EXEC_TRAJ`，然后出现 `Depth Lost! EMERGENCY_STOP`；plan_env reset 得到新 map_id，点云清零并在深度恢复后重建。后续时间线复核发现 EGO 急停比 mapping adapter `depth_stale` 记录早约4.16墙钟秒，且此前已有 map timeout 日志，因此不能把它归因于 scheduled drop。脚本正常退出且清理后无活动测试进程。
- 证据范围限定为一次 live simulation；未启动 trajectory server、controller、PX4 或 control publisher。FSM 安全状态不证明实际车辆停止；run #07 也不证明 scheduled drop 导致急停。EGO 在深度恢复后仍保持 emergency state，重启／恢复与重复冷启动待验。
- 下一步：重复活动 stale 场景并验证安全恢复，再推进自维护 goal API、任务取消／替换／超时及 PX4 bridge 的唯一控制权。
