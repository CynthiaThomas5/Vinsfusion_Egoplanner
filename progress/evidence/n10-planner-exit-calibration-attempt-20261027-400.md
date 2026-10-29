# N10.3/#400 规划器进程退出校准尝试

## 结论

本次没有成功注入规划器退出，不能计为该故障类别的校准。注入器在等待活动动作状态期间拒绝了信号；记录的原因是桥已离开 `ACTIVE` 且 action status stale/missing，实际 `SIGTERM` 次数为 0，规划器进程没有被终止。

运行中另发生 PX4 本地位置有效性丢失。bridge 在仿真时间 119.316 s 转入 `LANDING`，原因 `px4_local_position_invalid`；随后观察到 EV position 不再融合。bridge 在 124.536 s 到达 `LANDED`，PX4 disarmed、land-detected，控制关闭。导航 action 却仍保持 executing，直到在独立确认 landed/disarmed 后，对唯一 goal `b893b44e86244a739fcedad6d3a7b74f` 发出一次精确 action cancel。没有执行紧急 disarm。

15 秒的终态后读回捕获到 1,099 条相同 goal/epoch 的 `READY` `PositionCommand`（trajectory id 157）；随后另一段 5 秒读回捕获 328 条。控制量在终态后为零，但 `no_old_epoch_goal_or_trajectory` 为 false，原生故障终态评估为 `INSUFFICIENT`。现有读回字段无法判断所有这些命令是否为残留运动轨迹或取消后的 stop-hold 轨迹，因此不将它们解释为碰撞或实际运动。

## 运行身份和证据

- run：`artifacts/runs/n10-20261027-400-planner-process-exit-calibration/`
- runtime contract：`4bd013db9195cb7b424a00259872d5dd678450b200fb577df4cf423213b0973b`
- goal id / epoch：`b893b44e86244a739fcedad6d3a7b74f` / `43b696c43df04fb795ac4dd4e136f5ce`
- 注入记录：[n10-planner-process-exit-injection.json](../../artifacts/runs/n10-20261027-400-planner-process-exit-calibration/n10-planner-process-exit-injection.json)
- bridge 转移：[bridge-alignment-timeline.jsonl](../../artifacts/runs/n10-20261027-400-planner-process-exit-calibration/bridge-alignment-timeline.jsonl)
- PX4/bridge 终态读回：[postflight-px4-bridge-readback.json](../../artifacts/runs/n10-20261027-400-planner-process-exit-calibration/postflight-px4-bridge-readback.json)
- 终态分类：[n10-native-terminal-evidence-summary.json](../../artifacts/runs/n10-20261027-400-planner-process-exit-calibration/n10-native-terminal-evidence-summary.json)
- 精确 action closeout：[n10-exact-action-cancel-normalized.json](../../artifacts/runs/n10-20261027-400-planner-process-exit-calibration/n10-exact-action-cancel-normalized.json)
- 物理安全停止读回：[n10-controlled-stop-assessment.json](../../artifacts/runs/n10-20261027-400-planner-process-exit-calibration/n10-controlled-stop-assessment.json)
- 采集评估：[n10-sensor-capture-evaluation.json](../../artifacts/runs/n10-20261027-400-planner-process-exit-calibration/n10-sensor-capture-evaluation.json)
- 结构化报告：[JSON](n10-planner-exit-calibration-attempt-20261027-400.json)，SHA-256 `0b6409cb643e6b5950921440bda3977bcf216ab7d8a5b00788af14e61239798d`

传感器 bag 可离线读取，但 capture 因外部 shutdown、未覆盖安全终态、run identity 缺 map_id 而为 `INSUFFICIENT`；资源观察、truth/contact 最终报告和本次净空评估缺失。没有为缺字段补造结果。

## 后续实现

当前 bridge 的安全降落转移没有通知 navigation 终止对应 action。下一子项 N10.3/#401 将补 goal_id+epoch 匹配的 bridge-fault-to-navigation abort，使导航清除 EGO 任务；这只结束已进入既有安全降落路径的任务，不新增 takeoff/health/observer gate。另将 action status observer 改为 transient-local QoS，以匹配实际 publisher；注入仍只在唯一活动 goal、epoch、桥 ACTIVE/armed 和唯一进程身份均匹配时发送一次信号。修正运行脚本的 observer 收尾，使物理安全停止条件与离线证据完整性分开记录。

本次结构检查不能替代故障校准。N10 保持 `in_progress`；N15/N16 正式次数仍留在 N10 冻结后。
