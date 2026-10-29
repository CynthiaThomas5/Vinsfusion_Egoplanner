# N08.2f #216：支撑扫描健康，任务入口遇到锁存 stale

## 假设、变量与判据

- 假设：#215 的定位 stale 可能发生在支撑扫描结束后的 N05／bridge 就绪交接，单看支撑扫描内的 VINS source stamp 会漏掉触发窗口。
- 唯一诊断变量：新增一个只读、低负载 recorder，订阅 `/clock`、raw VINS telemetry／odometry、optimized odometry 和 LocalizationStatus；未修改源码、配置或阈值。记录器在支撑扫描结束后停下，另在 compute-only precondition 失败后作短时只读回读。
- 判据：source stamp、到达间隔与 `/clock` 年龄能否对齐到 LocalizationStatus stale；飞行仅可在 N05 与 bridge precondition 均通过后开始。

## 结果

Run：`n08-20261024-216-vio-timeline-01`。

- 未武装支撑扫描完成 12/12 阶段；helper 在清理／读取 DISARMED 状态时返回 `fresh DISARMED status is required for every fixture command`，该错误保留。fixture 已移除、最终 landed、所有记录车辆状态均 DISARMED；独立 `n05-run-summary.json` 的 14 项检查通过。
- post-release 与 current-area N05 online/offline gate 均 `all_entry_phases_known_and_clear`，同一 epoch/map。当前区域 gate `accepted=true`。
- 支撑扫描内记录到 5,157 条 VINS telemetry：最大 source stamp gap 0.068 s、最大 `/clock` 年龄 0.096 s，LocalizationStatus 没有从 TRACKING 转换。raw VINS odometry指标相同。optimized odometry 最大 source gap 0.068 s、最大 source/clock 年龄 0.104 s；其 observer 最大接收间隔 0.408 s。
- 随后的 40.01 s navigation preflight 报 `passed=true`，但记录到一次 `optimized_odometry_receipt_stale`，最大接收间隔 0.341 s。N05 current-area gate 随后通过；bridge readiness 仍记录 `DISABLED/external_odometry_stale` 和 `DISABLED/localization_not_tracking`。mapping log 记录 `mapping gate closed: telemetry_stale`。
- compute-only runner 以 `vio_bridge_map_preconditions_not_ready` 结束：`action_goal_sent=false`、`trajectory_ready_seen=false`、bridge 保持 DISABLED，PX4 未武装、已 landed/disarmed；没有飞行或 EGO 目标执行。
- 故障后的短时 observer 看到 LocalizationStatus 仍锁存 `telemetry_stale`：状态 header／clock 约 527.42 s，status `source_stamp` 停在 465.364 s，source-age 约 62.064 s；与此同时 raw VINS telemetry 和 odometry 已恢复，最新 telemetry source 527.344 s，相对 `/clock` 年龄 0.056 s，观察窗口内 source gap 最大 0.068 s。这证明 failure latch 持续存在于 fresh raw source 恢复之后；但未连续记录 stale 的首次转换，仍不能确认触发链路或精确起点。

## 判断与局限

#216 支持：这是 VINS/localization health fail-closed，不是 PX4 HRT 时间参考回归。N07 #198/#200/#204 的累计 3/3 保持有效、无需连续且不复测。N08 先前 #212 hold 与 #213 N05 gates 均有通过证据，因此 PX4 时间参考没有把 N08 主线整体卡死；但当前 run 因 adapter stale 锁存无法进入 compute-only，重复发生时会继续挡住依赖新鲜定位的任务。

记录器开始覆盖支撑扫描，但在 fixture helper 结束时停止；首次 stale 发生在这个窗口之后，尚未捕获触发前后连续的 source/receipt 时间。N08 父目标仍 `in_progress`；不能把本轮支撑扫描或 N05 gates 算作 N08 通过，也不能放宽 0.30 s localization source-age 门。

## 收尾与下一步

`flight.json` 与 bridge timeline 确认未解锁、未发送目标且最终 landed/disarmed。`tools/project.sh stop n08-20261024-216-vio-timeline-01` 返回 0；无活动项目容器。

N08.2g #217：新 cold start 下让同一低负载 recorder 从支撑扫描前持续到 N05 release/current-area、navigation preflight 和 compute-only readiness 终止，捕获首次 LocalizationStatus stale 转换及触发前 source/receipt/clock 值。若 bridge 开始 PRESTREAM，立即停止诊断 observer，避免把 observer 负载带入飞行窗口。所有 N07 已通过项不重测。

关键产物 SHA-256：

- `fixture-result.json`: `55bd69ae6e72e0ff5d7cd2712deebe225c2a277dd114000f3d928d0bbc964825`
- `n05-run-summary.json`: `ed123ce1a1b9e04cd456b6f33e0d0b8e69bc0b9bf72b60c0c016a976d675cea67a`
- `n05-current-area/n05-live-entry-check.json`: `6ca86f9a8eea6fd666f603d4a155a225875c04d8626f246497ee604be9369691`
- `preflight.json`: `c87687c50129d4b84e65b49b2fc97ed54d2a0143def7dbf1d4c545c143c5c63b`
- `flight.json`: `fb080d1b17342efabb796bd99f0337b98aabcfee541e1b3c0c582b72f17c993d`
- `bridge-alignment-timeline.jsonl`: `7be0750b2e9d27a478f26d1a400274fe2419aad0682961240a003e64de468c59`
- `vio-clock-timeline.jsonl`: `fbc77186a0d0c4144ae6ced95135926b35e8e217f861bb5373f538fe56f5119b`
- `vio-clock-followup.jsonl`: `457d9b657c965e8a7577350ef34fbadab134d372211eb602c6a3541e9ae4a99d`
- recorder source: `vio_clock_timeline_probe.py` `f4b3ece7d0467a1e2f43d1411eefba15279a6ee37e2aa5b5c7c8ae0825447430`

原始数据：[`artifacts/runs/n08-20261024-216-vio-timeline-01/`](../../artifacts/runs/n08-20261024-216-vio-timeline-01/)。
