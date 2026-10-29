# #200：N07 重置后的首次合格 hover

## 范围与基础

Goal 完成模式，用户指定 N07。#199 使 streak 从 1/3 归零。本项使用固定 image/runtime/spawn、wall layout、N06 支架路线、30 秒 no-goal hover、同一只读 observer set 和全部原门限；不改项目源码、配置、N07 标准或阈值。

## 结果与记录

N05 支架路线 12/12 阶段完成，summary 14/14，扫描后／post-release／current-area online/offline gates 接受，独立释放安全读回 10/10。fixture helper 报 `fresh DISARMED status is required for every fixture command`，outcome failed 且 remove service ack false；独立 Gazebo scene absence、detach、final landed 均确认，异常保持可见。

No-goal runner PASS，30.0 仿真秒、33.671 墙钟秒，无目标／hover position command，最终 bridge landed/disarmed。PX4 ULog 12/12、独立 evaluator 11/11、graph 3/3 unique bridge/no-truth 和最终安全 readback 13/13。`project.sh stop` exit 0，容器 `exited 0`。

证据：[N07 #200 报告](../evidence/n07-no-goal-hover-20261024-200.md)、[JSON](../evidence/n07-no-goal-hover-20261024-200.json)，运行目录 `artifacts/runs/n07-20261024-200-01/`。run-local graph observer copies 与 #195 哈希一致；阈值未变。

## 验证

- `N07_KEEP_SIM=1 bash /tmp/n07-192-n05-runner.sh n07-20261024-200-01 wall_box_column n06_full_airframe_retreat_240_oblique_separated_return`：N05 summary 14/14；fixture helper 自身失败，已记录。
- `check_n05_entry_live.py` 与 `evaluate_n05_entry.py` current-area online/offline：PASS。
- `run_vio_no_goal_hover.py`：PASS，30.0 simulated seconds。
- `PYTHONPATH=/tmp/n07-pyulog-packages python3 tools/debug_truth/analyze_n07_ulog.py <run-ULog> --output artifacts/runs/n07-20261024-200-01/px4-ulog-analysis.json`：12/12 PASS。
- `python3 tools/diagnostics/reconcile_n07_ros_graph.py artifacts/runs/n07-20261024-200-01/ros-graph-audit.json --output artifacts/runs/n07-20261024-200-01/ros-graph-audit-reconciled.json`：3 snapshots PASS。
- `python3 tools/debug_truth/evaluate_n07_hover.py artifacts/runs/n07-20261024-200-01`：11/11 PASS。
- `bash tools/project.sh stop n07-20261024-200-01`：exit 0；容器 `exited 0`，无活动项目容器。
- `python3 tools/project_status.py`：PASS；`git diff --check`：PASS。

## 状态与下一步

#200 为重置后 streak 第 1/3 次通过；N07 继续 `in_progress`。下一项 N07.47 #201：再做一次全新独立 cold start，保持固定条件、observer 和原门限。
