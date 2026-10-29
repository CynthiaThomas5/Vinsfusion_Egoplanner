# N07.42 #196：第三次连续 no-goal hover cold start 未进入飞行

## 模式、基础与缺口

Goal 完成模式，用户指定范围 N07。开始时 #194、#195 连续通过，streak 为 2/3；本子项按 N07 出口执行第三个独立 cold start。固定镜像/runtime/spawn/layout/support profile、健康与控制阈值、N05 准入门和飞行验收标准不变。

## 本轮假设与唯一判据

本轮是冻结条件下的正式重复性验收，不做参数探索。判据是 N05 完成全路径和 fresh online/offline gate 后才允许飞行；任一健康门失败则 fail-closed、无飞行并按 N07 契约重置连续计数。

## 执行与结果

运行 `n07-20261024-196-01` 使用 `wall_box_column`、`n06_full_airframe_retreat_240_oblique_separated_return`。初始 online/offline N05 检查一致因 `TAKEOFF_CONTACT:raw_unknown_in_expanded_vehicle_envelope` 拒绝。支架扫描第 7/12 阶段出现 `normalized_cost_exceeded`，cost 为 `1.0601070975543245`；helper 退出码 1，未到 N05 在线窗口。没有启动飞行，因此 streak 从 2/3 重置为 0/3。

支架移除、无 fixture 残留、PX4 disarmed/landed、bridge DISABLED 且无控制、无运行任务进程均经读回确认。bridge 首次读回因 DDS 尚未发现 publisher 而失败；等待发现后重读通过。项目容器安全停止，exit 0。未改项目源码、配置、健康门限或 evaluator。

完整数据与哈希见[N07 #196 失败证据](../evidence/n07-preflight-health-failure-20261024-196.md)。

## 下一步

#197 按完全相同固定条件执行全新 cold start。只有 N05 支架路径、释放后/current-area online/offline gate 和 14 项摘要全通过后才进入 no-goal flight；任何失败仍保留未通过并归零连续计数。
