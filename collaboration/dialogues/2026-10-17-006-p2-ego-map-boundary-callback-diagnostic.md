# P2 EGO 地图边界与 callback 诊断

日期：2026-10-17

- 用户约束：继续完成 GOAL.md 的 P0–P6，不提前降级目标；保留原有 staged／unstaged 文件；不向远端推送；不启动 PX4 控制或实机飞行。
- 发现：run #20 的 EGO 同步 callback 在 timeout 期间继续执行，但 pose 始终低于旧地图有效 z 下界，occupancy 更新停止；run #23 的修正 probe 在40.024秒 no-fault窗口内记录332组配对输入，源最大间隔0.297秒、接收源年龄最大0.183秒，窗口内无 EGO timeout。
- 决定：保留 `odom_depth_timeout_sim_s=0.4` 为 PROVISIONAL；通过 patch 0011 从 mapping config 传入 `ground_height=-0.15 m`，只作为基于现有 pose envelope 的诊断余量，尚未冻结地图范围。patch 0010 的回调计数只作观测，不改变建图门控行为。
- 排除：run #19 因附件缺失和随后复用目录已有一次性输出而没有启动，不计运行；run #22 probe 在互斥 callback group 中滞后，排除 timing calibration；run #23 在 probe 窗口结束11秒后出现的 timeout 日志属于停机尾段。
- 待决：重复 run #23 timing-quality no-fault观测；在新 lower bound 下重跑活动深度 stale；评估地面几何和长时 VIO 垂向漂移；随后接入 own 3D+yaw task API 和 map snapshot readback。
