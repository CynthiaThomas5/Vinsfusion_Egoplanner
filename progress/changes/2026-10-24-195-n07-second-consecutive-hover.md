# N07.41 #195：第二次连续 no-goal hover cold start

## 模式、基础与缺口

Goal 完成模式，用户指定范围 N07，父目标 `in_progress`；#194已通过，当前连续合格 cold start 为1/3。#194 的实际 ROS graph 三快照和evaluator均通过，但首张`airborne_active`早于capture metadata标记的`active_discovery_ready`。本轮沿用已通过的固定运行条件，确保run-local graph capture在任何snapshot前完成自身DDS discovery gate。

## 唯一变量／假设

假设：capture首张快照前确认status与四个control endpoints在本进程DDS图中可见，能避免#193启动期快照缺endpoint。本轮只对run-local只读capture副本调整顺序：在 ACTIVE+armed 且四个PX4 control topic各只有一个`uav_px4_bridge` publisher前不采任何快照；最多等待5秒，超时保存明确失败快照。外部active waiter、flight/N05/health/control规则、observer集合、evaluator、阈值和固定runtime不变；不运行optional freshness probe。

## 执行与出口

运行 ID `n07-20261024-195-01`，使用同一固定image/runtime/spawn/layout/support profile。先完成N05 support scan 12/12、14项summary和current-area fresh online/offline gate，再执行30.0秒 no-goal hover。运行出口要求原evaluator11/11、ULog12/12、所有graph快照唯一bridge/no-truth、最终landed/disarmed和安全停机；通过后streak为2/3，否则归零。允许修改仅run-local observer与记录文档，不改项目源码、配置或验收标准。


## 结果、验证与下一步

#195通过N07第二次连续cold-start出口，streak **2/3**。N05 support path 12/12，summary14/14，post-release/current-area fresh online/offline gate均一致准入；flight runner PASS/exit0，no-goal hover 30.0仿真秒，tracking与PX4 telemetry stability通过。ULog12/12，原evaluator11/11，graph 3/3快照通过。支架helper错误 `localization changed or became invalid during physical scan` 保留；它发生在profile 12/12与fixture removal已记录后，trace单epoch、无invalid rows，post-release/current-area gate准入。

本轮run-local graph recorder先等待自身DDS满足ACTIVE+armed和四个唯一bridge control publisher，0.410秒后采首张`active_discovery_ready`快照；随后airborne与最终快照均通过。final landed/disarmed与Gazebo fixture absence读回通过；`bash tools/project.sh stop n07-20261024-195-01` exit0，容器Exited(0)，活动项目容器0。详情见[证据报告](../evidence/n07-no-goal-hover-20261024-195.md)与运行档案 `artifacts/runs/n07-20261024-195-01/`。

N05地面边界证据仍只说明未武装准入，HOLD无subground排除；没有地下飞行。本轮没有修改项目源码、配置、threshold或evaluator。

验证命令：
- `PYTHONPATH=/tmp/n07-pyulog-packages python3 tools/debug_truth/analyze_n07_ulog.py <run-ULog> --output artifacts/runs/n07-20261024-195-01/px4-ulog-analysis.json`：12/12 PASS。
- `python3 tools/diagnostics/reconcile_n07_ros_graph.py artifacts/runs/n07-20261024-195-01/ros-graph-audit.json --output artifacts/runs/n07-20261024-195-01/ros-graph-audit-reconciled.json`：3快照 PASS。
- `python3 tools/debug_truth/evaluate_n07_hover.py /tmp/n07-eval-195/n07-20261024-195-01`：11/11 PASS；评估器未改。
- Flight runner 30.0 simulated seconds, exit0；安全停机 exit0。

下一子任务#196执行同一recipe完成第三次独立cold start；否则连续计数归零。
