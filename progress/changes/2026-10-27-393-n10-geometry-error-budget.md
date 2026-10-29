# #393 N10 净空与跟踪误差离线预算

- 对话摘要：[`collaboration/dialogues/2026-10-27-393-n10-error-budget.md`](../../collaboration/dialogues/2026-10-27-393-n10-error-budget.md)
- 轻量证据：[`n10-geometry-error-budget-20261027-393.md`](../evidence/n10-geometry-error-budget-20261027-393.md)
- 原始输入：`artifacts/runs/n10-20261027-381-vins-velocity-full-route/`、`artifacts/runs/n10-20261027-385-arrival-dwell4-retry/`、`artifacts/runs/n10-20261027-391-integrated-calibration-retry/`

## 改动

- `tools/debug_truth/evaluate_n10_tracking_clearance.py` 输出 schema v2，新增逐点平移净空下界 `min(command body clearance to any active obstacle) - ||truth position - command position||`、负下界数量/比例、最差样本与 evaluator 自身 SHA-256。
- `tools/test_n10_clearance.py` 增加平移下界正值、负值语义和非法输入测试。
- 基于当前固定对齐复算 #381/#385/#391，结果另存于 `artifacts/runs/n10-20261027-389-archive-reuse/tracking-error-budget-{381,385,391}.json`；没有覆盖原始记录。
- 更新 N10.3 证据，将运行身份差异、全机包络、观测净空、保守误差预算及综合采集字段一并记录。

## 验证

- `python3 -m unittest tools.test_n10_clearance`：7 tests passed。
- `python3 tools/debug_truth/evaluate_n10_tracking_clearance.py <run> --output <new archive-reuse output>`：#381、#385、#391 均完成并保留逐样本报告；负下界样本比例为 18.37%、17.99%、21.09%。
- `PYTHONPYCACHEPREFIX=/tmp/codex-pycache-n10 python3 -m py_compile tools/debug_truth/evaluate_n10_tracking_clearance.py tools/test_n10_clearance.py`：通过。
- 未启动 SITL；未修改运行控制路径、验收门限或原始归档。

## 限制与下一步

逐点平移下界使用相同时间点、相同实际姿态扩展包络和 SDF 几何，不能替代姿态误差、运动区间、动态障碍时变、地图模型误差或完整任务的验证。三个运行都不能支持把 0.60 m 跟踪 P95 候选定为通过值；N10.3 保持未完成。下一子项审计并更新 N10.4 acceptance 草案，记录此不足态与下一次完整只读采集合同。
