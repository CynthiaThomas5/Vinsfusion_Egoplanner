# N08.2al #249：negative-only 获取当前地图，随后定位时间门拒绝

## 假设与范围

复用既有 `n08_overhead_negative_side_view`，在 fresh epoch 获取负 Y hold 区域的当前地图，避免把正、负两侧观察叠加。profile、定位健康门、地图门、planner 和阈值都未改。

## 结果

- N05 支架记录了 16/16 个阶段。fixture helper 最后报告 `fresh DISARMED status is required for every fixture command`；后续独立检查确认支架已脱离、模型不存在，PX4 DISARMED／landed。
- 同 epoch、同 map 的 after-scan 与 post-release N05 在线／离线门均通过：`all_entry_phases_known_and_clear`。初始 prescan 因没有 raw ground plane 而拒绝，符合扫描前状态。
- 40.01 秒只读 preflight 通过；最大 optimized odometry receipt gap 为 86.5 ms，超守卫样本为 0。
- 随后的 current-area 在线 N05 前置检查 fail-closed：`N05 online prerequisites did not become ready: localization_not_tracking`。没有启动 EGO goal、没有发布控制，也没有进入 compute-only 的曲线证书或 XY。
- Localization 在 sim clock 536.356s 锁存 `propagated_from_future`。当时 propagated source 为 536.304s，adapter 收到时记录的 ROS clock 为 536.152s，超前 152.0 ms；门限是 20 ms。归一化代价为 0.836（门限 1.0），stale observation 为空。这是 VINS propagated／adapter ROS-clock 观测时序拒绝；不是 PX4 HRT/ROS 时间差导致的 mission 拒绝。
- current-area failure 后做了 5 秒独立 PX4／bridge 末态读回：DISARMED、landed、bridge DISABLED、控制样本为零。`tools/project.sh stop` 返回 0，容器 Exited(0)。

#249 未完成同 run unknown-volume 审计、compute-only 曲线证书、XY 或制动距离测量；N08 仍 `in_progress`，N07 的既有通过不复测。

## 下一步

#250 使用已存在的只读 `record_n08_localization_sources.py`，从扫描前连续记录 `/clock`、raw VINS propagated/optimized、adapter output 与 telemetry 时间戳。判定未来时间戳是 raw VINS 已超前，还是 adapter 当时读到的 `/clock` 落后；保留 20 ms future guard 与所有原准入阈值。无证据前不改容差、不重放 compute-only。

## 产物

完整运行数据在 `artifacts/runs/n08-20261024-249-negative-only-current-map/`；摘要、末态和原始日志哈希见本报告旁的 JSON。
