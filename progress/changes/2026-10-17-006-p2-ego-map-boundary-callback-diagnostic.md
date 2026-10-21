# P2 EGO 地图下界与 callback 诊断

日期：2026-10-17。对话摘要：[2026-10-17-006-p2-ego-map-boundary-callback-diagnostic.md](../../collaboration/dialogues/2026-10-17-006-p2-ego-map-boundary-callback-diagnostic.md)。

- 修改：EGO patch 0010 在 timeout 日志中记录按 map reset 清零的深度／位姿同步 callback 次数、最近源 stamp、callback 时 ROS clock、地图内判定和相机位姿。patch 0011 将 `ground_height` 暴露为 launch 参数；`config/components/mapping/ego_planner.json` 暂设 `-0.15 m`。`tools/probe_mapping_runtime.py` 改为连续 executor、独立可并行输入／clock callback group，点云坐标解码移到采样结束后；每条相机 pose 附接收墙钟和最近 `/clock` stamp。
- 根因证据：run #20 在 Ready／Tracking 状态下出现355条 timeout 日志，单组 callback 计数315→476持续增长，但每条最近 pose 均被 `isInMap` 拒绝，Z为 -0.0133 至 -0.0278 m；旧地图实际拒绝阈值约 -0.0099 m，occupancy 最后更新时间停在27.985 s。说明该组不是同步 callback 停滞。
- 边界复测：run #21 将 lower bound 设为 -0.15 m，timeout 时 callback pose 保持地图内，40秒 probe 区间内没有 EGO timeout；其 probe 使用早期单回调 observer，因此只作 supporting evidence。
- 时序复测：排除 run #22 的 probe backlog 后，run #23 使用修正 probe 完成40.024秒 no-fault 采样。观测332组配对输入，源间隔 p50/p95/max 为0.066/0.165/0.297 s，接收时源年龄 p50/p95/max 为0.074/0.110/0.183 s，最大占据点1775、地图点数变化180次，深度 READY、定位 TRACKING。采样窗口内没有 EGO timeout。8条 timeout 日志首条在 probe 窗口结束后11.145秒，位于运行脚本的后续检查／清理阶段，不纳入样本。目标、controller、PX4 与 actuator 均未启动。
- 构建：Jazzy 独立 overlay 中 patch 0010 相关五包 `plan_env`、`traj_utils`、`bspline_opt`、`path_searching`、`ego_planner` 构建通过；patch 0011 后 `ego_planner` 单包构建通过并复用前一 overlay 依赖。`ros2 launch ego_planner advanced_param.launch.py --show-args` 列出 `ground_height`。构建明细及日志哈希见 [P0 诊断构建报告](../evidence/p0-ego-map-timeout-diagnostic-build.json)。
- 验证：`python3 -m py_compile tools/probe_mapping_runtime.py`、run #20–23 shell 的 `bash -n`、证据 JSON 解析、patch replay、目标构建和启动参数检查通过。运行后进程审计未发现活跃 Gazebo、VINS、EGO、adapter 或 probe；旧 defunct 进程项保留在容器进程表中。
- 限制：`ground_height=-0.15 m` 和 `odom_depth_timeout=0.4 s` 都是 PROVISIONAL。只有一段 timing-quality no-fault run；floor 几何、长时垂向漂移、重复故障响应、active-goal 安全行为、轨迹跟踪及 PX4 均未验证。
- 下一步：重复修正 probe 的 no-fault 观测并在相同地图参数下重复活动深度 stale；之后完成 own 层三维位置／yaw 目标 API、epoch/time rewind 处理、地图快照回读与多场景几何检查。
