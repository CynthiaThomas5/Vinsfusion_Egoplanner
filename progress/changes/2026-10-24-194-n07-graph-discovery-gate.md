# N07.40 #194：有界等待 graph capture 自身 discovery

## 模式、基础与缺口

Goal 完成模式，用户指定范围 N07，父目标 in_progress，当前连续合格 cold start 为 0/3。#193 已完成 30 秒 no-goal hover、N05 14/14、ULog 12/12 和最终 landed/disarmed；N07 evaluator 唯一失败为 ROS graph。外层 waiter 观测到 bridge ACTIVE+armed 后启动未更改 capture，但 capture 首快照自身 `bridge_status=null`、四个 PX4 control topics 各 0 publisher；后续快照识别四个唯一 `uav_px4_bridge` publisher，无 truth。

## 唯一变量／假设

假设是 capture 进程启动后的首个固定 1 秒快照时，其 DDS participant 尚未发现 bridge/status 与 control endpoints。#194 只修改 run-local 只读 capture 脚本：首快照最多等 5 秒，同时要求本进程已收到 ACTIVE+armed status、四个 PX4 控制 topic 各恰有一个 `uav_px4_bridge` publisher；随后执行与原脚本相同的快照内容和 reconciliation。超时保留当时失败快照并退出，不跳过、修补或过滤快照。外层 ACTIVE waiter、flight、其余观察器均不变。

## 执行与出口

运行 ID `n07-20261024-194-01`；相同固定 image/runtime/spawn/layout/support profile、N05/health/control thresholds、no-probe observer set、30 秒 no-goal hover 及 ULog/evaluator。N05 14/14 和 current-area fresh gate 不通过时不启用。要求 N07 evaluator 11/11、PX4 ULog 12/12、graph airborne/landed 唯一 bridge publisher 且无 truth、最终 landed/disarmed；通过计 1/3，否则保持 0/3。

本轮只允许 run-local observer 副本、仿真档案和文档变化；不改源码、配置、flight 控制或评估阈值。


## 结果、验证与下一步

#194 **通过 N07 单次 cold-start 出口，计为 1/3**。N05 support profile 12/12、布局摘要14/14、current-area online/offline准入一致；no-goal hover 30.0仿真秒，flight runner exit 0，最终 landed/disarmed。PX4 ULog 12/12、原 evaluator 11/11、graph 三快照全部唯一 `uav_px4_bridge` publisher 且无 truth。实测误差见 [证据报告](../evidence/n07-no-goal-hover-20261024-194.md)。

容器停止前确认 PX4 DISARMED、land detector landed、支架已移除且无 flight/observer进程；`bash tools/project.sh stop n07-20261024-194-01` exit 0，容器 `Exited (0)`，活动项目容器为0。运行产物及哈希见 `artifacts/runs/n07-20261024-194-01/`。

复核快照顺序时发现 run-local capture 的 `airborne_active` 快照先于 `active_discovery_ready`；首张快照自身已满足 ACTIVE+armed、四个唯一 bridge publisher 和无 truth。N07 运行出口仍满足，evaluator与raw graph均通过；但不能据此说 discovery wait 导致通过。详情见运行目录 `graph-capture-discovery-review.json`。#195 将修正为在自身 DDS ready 或5秒 timeout前不采任何快照；timeout仍保留失败快照。飞行、N05、health/control门、observer集合及评估标准不变。

验证命令：
- `PYTHONPATH=/tmp/n07-pyulog-packages python3 tools/debug_truth/analyze_n07_ulog.py <run-ULog> --output artifacts/runs/n07-20261024-194-01/px4-ulog-analysis.json`：12/12 PASS。
- `python3 tools/diagnostics/reconcile_n07_ros_graph.py artifacts/runs/n07-20261024-194-01/ros-graph-audit.json --output artifacts/runs/n07-20261024-194-01/ros-graph-audit-reconciled.json`：3快照 PASS。
- `python3 tools/debug_truth/evaluate_n07_hover.py /tmp/n07-eval-194/n07-20261024-194-01`：11/11 PASS；评估器源码未改。
- Flight runner：30.0 simulated seconds，exit 0；安全停机命令 exit 0。
