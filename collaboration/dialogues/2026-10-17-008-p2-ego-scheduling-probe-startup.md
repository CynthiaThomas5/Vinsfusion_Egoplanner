# P2 EGO 调度诊断构建与首次运行

日期：2026-10-17

- 用户约束：继续 GOAL.md 的 P0–P6；保护已有 staged／unstaged 文件；不推送；不启动 PX4 控制或实机飞行。
- 修改：新增第三方 patch 0012，仅增加 steady-clock 回调年龄／耗时、occupancy timer 间隔和最近融合耗时日志。vendor 树保持不变；补丁在隔离源码副本中应用并构建。
- 构建：Jazzy `plan_env`、`traj_utils`、`bspline_opt`、`path_searching`、`ego_planner` 五包通过，colcon 退出码0、约134.93秒；补丁回放逐字节一致。
- 运行：run #25 采用新 overlay，但 localization 仅经历 WAITING→`initialization_timeout`，优化里程计和 EGO 同步输入均为0，故没有命中 EGO timeout 诊断。报告未计入建图或调度结果。
- 决定：保留 run #25 失败产物；用新的 session/domain 重跑，只有实际达到 TRACKING 且产生成对 EGO 输入后才分析 patch 0012 指标。
- 待决：稳定获得 tracking；随后从 timeout 日志比较 depth/pose callback wall age、callback copy 时长、timer 墙钟间隔及 occupancy 融合耗时，解释 run #24。
