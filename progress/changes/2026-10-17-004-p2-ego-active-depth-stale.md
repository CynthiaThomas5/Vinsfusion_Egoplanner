# P2 EGO 活动轨迹深度 stale 响应

日期：2026-10-17。对应对话摘要：[2026-10-17-004-p2-ego-active-depth-stale.md](../../collaboration/dialogues/2026-10-17-004-p2-ego-active-depth-stale.md)。

- 修改：新增第三方补丁 `0009-recoverable-depth-timeout.patch`。EGO 只有在收到新鲜、位于地图内的占据更新后才清除先前 timeout 锁存；advanced launch 增加 `odom_depth_timeout` 参数。诊断配置暂设 0.4 仿真秒，标记 PROVISIONAL。
- 构建：独立 Jazzy build/install overlay 编译 `plan_env`、`traj_utils`、`bspline_opt`、`path_searching`、`ego_planner` 共5包，退出码0；launch `--show-args` 显示新参数。来源与 binary 哈希见 [P0 构建证据](../evidence/p0-ego-map-timeout-build.json)。
- 运行：#12 与 #15 单目标 live Gazebo 注入均记录 EGO `EXEC_TRAJ -> EMERGENCY_STOP`，发生在健康门 stale 和 map reset 前；#15 的 B-spline active interval 覆盖急停、stale 与 reset 时刻。源记录及哈希见 [P2 活动 stale 证据](../evidence/p2-ego-active-depth-stale.json) 与 `artifacts/runs/p2-ego-depth-stale-20261017-12/`、`...-15/`。
- 排除：#13 定位因 IMU stale 失效；#14 在注入前已出现 EGO occupancy gap；均不计因果响应。早期 #07/#11 也因急停早于注入而排除。
- 限制：阈值未基于正常地图更新间隔校准；#15 仅证实 EGO 规划状态，不含 trajectory server、controller、PX4 或执行器；深度恢复后仍处于急停。没有完成安全恢复、飞控停止或正式阈值验收。
- 下一步：在正常动态运行中量测地图更新间隔和相机位置是否越界，再校准阈值；设计新会话安全恢复并重复故障测试。
