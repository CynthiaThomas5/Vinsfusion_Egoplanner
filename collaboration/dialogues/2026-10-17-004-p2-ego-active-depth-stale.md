# P2 EGO 活动轨迹深度 stale 响应

日期：2026-10-17

- 用户约束：按 GOAL.md 持续推进 P0–P6；保护现有修改；第三方变更保存为有基准与顺序的 patch；不启动真机或 PX4 控制。
- 发现：上游 `GridMap::updateOccupancyCallback` 在一次无占据更新超过阈值后设置 timeout 标志，却不会在后续新鲜占据更新时清除；旧标志会在很久以后第一次接收目标时错误触发 EGO 急停。
- 决定：加入 EGO patch 0009，在新的有效占据更新处恢复 timeout 标志，并暴露 launch 参数。诊断值先取 0.4 仿真秒，保持 PROVISIONAL，不当作最终飞行参数。
- 证据：新 Jazzy overlay 的5个依赖包构建通过。run #12 和 #15 单目标深度注入期间观察到 EGO `EXEC_TRAJ -> EMERGENCY_STOP`，并早于健康门 stale/map reset；#15 记录的 B-spline 有效区间覆盖急停、stale 与 reset。
- 排除：#13 因 VINS IMU stale 不具备有效定位；#14 在注入前地图更新已停止，急停不能归因于注入；#07/#11 也在注入前已急停。
- 待决：0.4 仿真秒阈值需要正常动态地图数据年龄测量和校准；EGO 急停后恢复策略尚未定义；没有启动轨迹服务器、控制器、PX4 或执行器，因此没有证明实际制动。
