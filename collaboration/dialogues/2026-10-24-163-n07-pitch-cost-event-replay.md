# N07.9 #163：pitch health 事件复现

## 目标与约束

Goal 完成模式继续推进 N07。保持 #162 的 fixture 路线和参数，捕捉逐事件 `/localization/status`，补齐最终 `normalized_cost_exceeded` 与 telemetry 之间的时间对应。用户关于地面边界的要求保持：完全在 raw-ground plane 以下的 whole-cell 从接触阶段排除；平面及以上仍按现有 unknown 规则判定。

## 假设

#162 的健康锁存触发样本未保存在 fixture trace 中。只读 status 历史可区分瞬时 cost 尖峰与持续质量退化，同时让完整路线有机会产生 post-scan N05 证据。

## 执行决定

运行固定冷启动 `n07-20261024-163-01`，只增加一个 `/localization/status` 只读事件记录器，复用 `n07_spawn_minus65_retreat_180_pitch045_return_view`。N05、VINS 健康门、飞控模式和控制输出都不变。只有 scan 完成且 released N05 online/offline 五阶段全通过，才在原 epoch 继续 N07 无目标悬停；任何拒绝都保持 DISABLED/DISARMED 并安全停止。

## 结果

run `n07-20261024-163-01` 的9/9支架路线完成，前一轮pitch转入的cost故障未重现。status历史捕获到 sim=335.152s 的 `telemetry_stale` 锁存（normalized cost=0.472924；全历史峰值0.718690），而raw VINS telemetry继续至340.432s。attached N05 checker因没有新鲜optimized odometry，在120s期限后失败，没有快照；因此没有released gate或hover。最终LandDetected fresh=true、PX4 DISARMED、fixture移除、bridge DISABLED，容器Exited(0)。

地下范围审计保持原边界：ground plane以下whole-cell排除；#163初始接触阶段436个未知体素中心没有一个低于平面，HOLD的566个未知中心全部位于地面以上。坐标见`progress/evidence/n07-n05-unknown-volume-audit-20261024-163.json`。

下一轮#164将保持同一路线和判据，由marker-watcher自动触发attached/released检查，以缩短post-scan快照延迟。released N05 online/offline五阶段全通过以前不解锁。
