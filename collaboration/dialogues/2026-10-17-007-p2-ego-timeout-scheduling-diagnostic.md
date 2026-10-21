# P2 EGO 窗口内 timeout 复现与调度诊断

日期：2026-10-17

- 用户约束：继续推进 GOAL.md P0–P6；保护已有 staged／unstaged 改动；不推送；不启动 PX4 控制或实机飞行。
- 新证据：run #24 是 ground_height=-0.15 m、timeout=0.4 s 的 no-fault 场景；深度 READY、定位 TRACKING，40.026 s 窗口收到415组 EGO depth/pose 配对输出。EGO 在前三组告警内记录73条 timeout，所有最近 camera pose 都在地图内。独立 observer 在相同源时间区间持续收到配对输出，告警附近源间隔最大0.231 s；另6条日志位于 probe 结束后的运行尾段。
- 解释：run #23 仍是一段真实的无 timeout 窗口，但 run #24 证明这一行为不可重复，不能据此校准0.4 s。EGO 源码使用单线程 `rclcpp::spin(node)`；同步输入与50 ms occupancy timer 位于默认 callback group，timer 中做深度投影和 raycast。这是可能的 EGO 侧调度积压机制，尚未有 callback／timer 时长数据证实。
- 决定：先给 GridMap 增加 steady-clock 的输入 callback 年龄、timer 间隔与最近 occupancy 处理耗时诊断；保持第三方改动只在 `dependencies/patches/ego`，先不将多线程执行器作为未经线程安全审查的修复。
- 待决：构建并运行诊断补丁；确认告警是否对应 EGO 输入队列积压、昂贵 occupancy 回调或其他 timer 延迟；之后再完成 no-fault 重复与活动 stale／map reset 验收。
