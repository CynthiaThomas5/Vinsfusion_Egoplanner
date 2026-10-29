# #199：N07 no-goal hover 准入前定位停滞

## 范围与基础

Goal 完成模式，用户指定 N07。#198 为 streak 1/3；本项执行 #199 第二个独立 cold start。继续复用固定 image/runtime/spawn、wall layout、N06 支架路线、全部原门限和只读 observer；不改项目源码、配置、N07 标准或阈值。

## 结果与记录

N05 支架路线执行 12/12 阶段，fixture 已脱离并移除，after、post-release、current-area online/offline gate 接受且 summary 为 14/14。fixture helper 在最终健康轮询记录失败 `localization changed or became invalid during physical scan`，该异常被保留；trace 13,247 行、单 epoch、0 条 invalid localization。独立释放安全读回 9/9 通过。

no-goal runner 因 `localization_not_tracking` / `clock_stalled` 在准入前失败，没有 goal、位置命令或控制服务调用，也没有起飞。优化里程计接收停止在 sim time 576.748s，而 raw VINS odometry 与 PX4 local state继续更新；根因未确定。Graph waiter未观察到 ACTIVE+armed，本次无 graph snapshot。安全读回 9/9；容器 `Exited(0)`。

证据报告：[N07 #199](../evidence/n07-preflight-localization-stall-20261024-199.md)，结构化运行分析：[JSON](../evidence/n07-preflight-localization-stall-20261024-199.json)，原始运行目录：`artifacts/runs/n07-20261024-199-01/`。run-local graph observer copies 与 #195 哈希一致；flight/evaluator/门限未改。

## 验证

- `N07_KEEP_SIM=1 bash /tmp/n07-192-n05-runner.sh n07-20261024-199-01 wall_box_column n06_full_airframe_retreat_240_oblique_separated_return`：runner完成；N05 summary 14/14。fixture helper 自身 outcome failed，已单独记录。
- `python3 /workspace/tools/check_n05_entry_live.py --output-dir /workspace/artifacts/runs/n07-20261024-199-01/n05-current-area --wait-s 120` 与 `python3 /workspace/tools/evaluate_n05_entry.py --live-report /workspace/artifacts/runs/n07-20261024-199-01/n05-current-area/n05-live-entry-check.json`：online/offline 均通过。
- `run_vio_no_goal_hover.py`：FAIL，`vio_bridge_map_preconditions_not_ready`；未起飞。
- `bash tools/project.sh stop n07-20261024-199-01`：exit 0；容器 `exited 0`，无活动项目容器或观察器。
- `python3 tools/project_status.py`：PASS；`git diff --check`：PASS。

## 状态与下一步

#199 不合格，连续计数从 1/3 归零到 0/3；N07 保持 `in_progress`。下一子项 N07.46 #200：新的独立 cold start，保持所有固定条件与原门限，观察定位适配状态能否持续到 ACTIVE/armed 与完整 30 秒悬停出口。
