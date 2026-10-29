# N08 #310：支架准入通过，单程几何门仍拒绝

状态：没有发送 N08 目标。N05 支架扫描完成并移除 fixture；after、post-release、mission-current-area 的同身份 online/offline N05 均通过；40 秒只读 preflight 通过。实时 N08 前向包络检查在启用控制前因 rear rotor 区域 unknown 拒绝。

## N05 和 preflight

- 冷启动使用 `n08_overhead_free_sector_negative_y_side_view` 与 `n08_low_speed_trial.json`。15/15 阶段完成，#309 曾触发健康锁存的返程段未复现；trace 最高 normalized cost 为 0.9531。helper 仍保留泛化 localization warning，但最后读数有效、fixture 已确认移除，且 fresh post-release/current-area 检查接受。
- after、post-release、mission-current-area 的 `epoch` / `map_id` 相同；N05 online/offline 为 `all_entry_phases_known_and_clear`。current-area 快照有 60,310 free、5,019 occupied 和 9,534,671 unknown voxels；全部五个入口阶段 unknown 数为 0。
- 40.002 秒 read-only preflight 通过；optimized-odom 最大回执间隔 0.08570 秒，超 guard 计数 0。

## 实时几何拒绝

- 0.6 m single-goal 和 0.5 m caller-cancel 候选均在目标和 enable 之前被拒绝；occupied 为 0。
- current pose 为 ENU `[-0.23737, -0.05754, 1.03640] m`、yaw `0.04547 rad`，目标方向为 +X。起点保持有 16 个 unknown；前向距离 0 和 0.025 m 的查询分别有 27 和 21 个 unknown；从 0.05 m 开始的查询和 terminal hold 均无 unknown。
- 逐体素复算定位到同一个 27-cell 薄层：中心 x=`−1.05 m`、y=`−0.25…0.45 m`、z=`0.85…1.15 m`，均属于后方 `rotor_1_collision` 查询。它与名义 rotor 碰撞体的最近距离约 0.37479 m；现有空间余量 0.24868 m 与最大跟踪误差 0.15 m 线性合计 0.39868 m，因此现有 raw-map 门必须拒绝。所有原空间、跟踪、unknown 和 occupied 判据保持不变。
- 离线复算与实时地图一致：0.6 m 目标和 0.5 m cancel 路径都只在起点／最初 2.5 cm 的扩张包络触及该薄层；没有证据支持把它误称为目标前方障碍。

## 安全末态和未完成项

`action_goal_sent=false`、`return_action_sent=false`，没有 goal、控制 enable、起飞或制动测量。独立 PX4 读回 `DISARMED/landed/at_rest`；bridge `DISABLED/control_enabled=false/armed=false/landed=true`。只停止本 run 的项目容器，stop 与容器退出码均为 0。

完整机器摘要：[#310 N08 拒绝 JSON](n08-forward-geometry-refusal-20261026-310.json)。raw-cell 清单：[rear unknown slab](n08-forward-unknown-slab-20261026-310.json)。全部 25/21 个站点的可复算地图回放：[#310 几何 replay](n08-forward-reachable-geometry-replay-20261026-310.json)。原始运行在 `artifacts/runs/n08-cancel-highspeed-prescan-20261026-310/`。

## 下一步

保持 N08 flight 单程向前语义。以 N05 支架上的 rear-facing observation 单独验证这 27 个 unknown 是否是相机后向遮挡；这只改变未解锁的观测姿态，不加入返航 goal，也不降低任何阈值。复用 #307 已到达 rear-facing 视角的路线，唯一试验变量是 yaw 回中后的下降时间从 8 s 增至 12 s，以缓解其在 z≈0.899 m 时 cost=1.00986 的边缘健康拒绝。只有同身份 post-release N05、mission-current-area、preflight 和实时 N08 几何全部通过，才继续单程 motion-cancel 试验。
