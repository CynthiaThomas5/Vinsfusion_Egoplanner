#264：N08 支架扫描在 telemetry 源龄门处安全中止

## 结果

#264 使用全新 SITL，并核对 launch manifest 确认加载 `config/components/mapping/n08_low_speed_trial.json`；source hash 为 `f8216372bdeda44f02b891381adbdb806c8866f252698dda87c29d14a6e29cce`，EGO 参数为 `max_vel=0.10 m/s`、`max_acc=0.25 m/s²`。因此 #263 的 planner profile 配置错误已排除。

扫描前的只读 N05 检查因 `ground_plane_insufficient_raw_occupied_voxels` 拒绝，raw ground-plane 候选数为 0。未武装支架扫描随后开始，在 15 个阶段中完成 6 个后被定位健康门终止。该门在仿真时钟 231.920 s 锁存 `telemetry_stale`：VINS telemetry 源戳为 231.596 s，源龄 324 ms，高于既有 300 ms 限值；接收龄 264 ms，低于 500 ms 限值。此时 normalized cost 为 0.46155，solver usable/current 为真，145 个 stereo features、113 条 long tracks、求解耗时 19.7 ms。证据指向遥测源龄超限，不支持把它归为重投影代价超限；延迟发生在何处仍未查明。

原始 VINS 数据在锁存后继续前进，但本 epoch 的定位适配器按既有 fail-closed 规则保持 LOST 并清空地图。扫描器执行清理并验证支架已脱离、模型已移除、PX4 DISARMED 且 landed。没有 `n05-prescan-ready`、post-release N05 正向门、mission 当前区门、`flight.json`、任务目标、控制发布或起飞；项目容器已安全停止。

## 单变量后续

本次额外启动了 `record_n08_localization_sources.py` 时间线订阅器。它可能增加观察负载，但 #264 不能证明它造成了 24 ms 的源龄越限；之前也出现过类似健康锁存。因此 #265 只关闭 `N05_N08_SOURCE_TIMELINE`，其他布局、支架 profile、低速 planner、定位健康阈值和执行门保持一致。假设是：额外观察器可能影响源龄；判据是全机支架扫描期间原有定位门能否保持有效并完成 15/15 阶段。若再次锁存，保留日志并停止重复扫描，转向已记录的输入源与处理时序证据分析。

返航约束继续采用用户指定的顺序：前向制动后先原地 yaw 约 180°，确认转向后地图新鲜，再由 EGO 按机头前向规则规划返航。#264 未进入飞行阶段，因此没有产生转向或返航结果。

## 证据

- 在线入口拒绝：`artifacts/runs/n08-20261025-264-yaw-first-return/n05-before/n05-live-entry-check.json`，SHA256 `84ffba65c132210475054bb1921253d0b33aa89bf99776733bc757212886bda2`。
- 支架结果：`artifacts/runs/n08-20261025-264-yaw-first-return/fixture-result.json`，SHA256 `2cb592ce21aac694993a5abc96caa7bc4a0845665e8840cb968abd5b7f618290`。
- 时序记录：`artifacts/runs/n08-20261025-264-yaw-first-return/n08-prescan-localization-source-timeline.json`，SHA256 `1894a6279b7221cb93ce4361c0ff6439fee8c9b9103345acfab99229d017ba33`。
- VINS／定位日志：`artifacts/runs/n08-20261025-264-yaw-first-return/vio.log`，SHA256 `cba8c0a72c8402a5f0b38f5dd074294b88d0facb5cd70c6bea0faed14957caeb`。
- Run inputs：`artifacts/runs/n08-20261025-264-yaw-first-return/n05-run-inputs.json`，SHA256 `6be94157907a283f4e8509c25eecf44b290b57519027827dcc6281614e6962c7`。
- launch manifest：`artifacts/runs/n08-20261025-264-yaw-first-return-stack/launch-manifest.json`，SHA256 `5e78e60e0daaf1a429ca751179ad0cb1e34499f8e1276018d39ba2bc0d818c48`。

N08 保持 `in_progress`；该次只作为健康门拒绝与安全清理证据，不算扫描通过、飞行通过或返航通过。
