# N08 负侧视后中立恢复保持触发定位健康门（#303）

状态：未通过。负 Y 侧视和 yaw 回中完成，但新增中立保持期间 VINS 定位健康门锁存；未生成支架释放后地图或 N08 任务准入。

## 结果

- `n08_overhead_free_sector_with_negative_side_recovery` 完成 15/19 阶段。stage 12–13 到达 yaw −π/2 负 Y 侧视，stage 14 回中 yaw 0；第 16 阶段新增的 yaw 0、z=1 m 中立保持期间，`normalized_cost=1.0007072056` 超过既有 1.0 门限，扫描以 `normalized_cost_exceeded` 停止。
- 初始 N05 因 `ground_plane_insufficient_raw_occupied_voxels` 拒绝；健康门锁存后未执行 post-release N05 检查。无目标、无 enable、无飞行或制动数据。
- fixture 已 detach，Gazebo scene model 不存在，fresh land detector 显示 landed。独立 4 秒读回确认 bridge `DISABLED`、PX4 未解锁且 landed、控制消息为 0，容器停止并以 Exit(0) 退出。

## 判读与下一步

额外 15 秒中立等待没有把定位恢复到原健康门内，反而在该保持阶段触发了锁存；因此不再延长静止等待。下一子项 #304 只缩短 yaw −π/2 到位后的额外静止观察段 18 秒为 8 秒，保持转向时长、路线、回中、回收、地图／健康门和控制门限不变，检查能否更早完成回收并获得 fresh post-release N05。只有 same-identity post-release/current-area N05 及 N08 corridor/start/terminal-hold 全部通过后才允许执行运动任务。

机器可读摘要与原始文件哈希见此 JSON；原始运行在 `artifacts/runs/n08-cancel-highspeed-prescan-20261026-303/`。
