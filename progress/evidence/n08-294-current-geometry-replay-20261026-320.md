# N08 #320：复用已通过的单程扫描路线并复算当前机体几何

## 证据

用当前 `n08_trial_gate.py` 和当前含桨机体碰撞几何，对 #294 归档的同 run raw map、同起点和同航向做离线复算。单程 +0.6 m 目标的 25 个查询、起点 hold、终点 hold 均无 unknown／occupied；motion-cancel 0.5 m 停车走廊的 21 个查询及两端 hold 也全部通过。可达中心上界 0.250778 m，空间余量允许 0.262500 m。

#294 使用 `n06_full_airframe_retreat_240_translation_only` 支架扫描；释放后 N05 与 mission-current-area N05 在线／离线准入通过。它的 native mission 为 `single_goal motion_cancel`，`return_action_sent=false`，飞行记录为 PASS，符合“目标结束即本段结束”的语义。其执行版本早于当前完整机体几何门，因此只作可复用路线证据，不直接计入当前冻结版本的 3 次重复。

机器报告：[当前几何离线复算](n08-294-current-geometry-replay-20261026-320.json)。原始地图和任务记录：[ #294 run](../../artifacts/runs/n08-cancel-translation-prescan-20261026-294/)。

## 下一步

#321 使用同一已通过的 translation-only 支架扫描路线，在新冷启动内重新检查完整阶段、fixture release、同 identity N05 online/offline、只读 preflight 和当前 live forward-body geometry。只有这些门全部通过，才运行 `single_goal motion_cancel 0.04 0.06`。拒绝即不发 goal／enable。该次若完整通过可作为当前版本重复候选；N08 仍需累计 3 次同版本独立目标运行。
