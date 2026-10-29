# #461 N10.3 校准复算与 N10.4 草案收口

对话摘要：[2026-10-28-461](../../collaboration/dialogues/2026-10-28-461-n10-calibration-and-evaluator.md)

## 改动

- 新增 [#461 证据报告](../evidence/n10-normal-navigation-calibration-closeout-20261028-461.md) 及机器可读摘要，记录 #460 当前候选版正常导航、物理步区间净空、跟踪、地图、重规划、资源和身份结果。
- `config/acceptance.json` 从 revision 7 升为 8，仅补 supporting-evidence 引用并将全机净空证据状态更新为已取得 #460 identity-bound solver-step/interval 校准；`status` 仍为 `draft`，数值阈值与 runtime effect 不变。
- 更新 N10 计划、CURRENT 和 milestones，将当前子项交接到 N10.5；父 N10 继续 `in_progress`。用户 #434 的故障校准排除继续生效。

## 验证

- `python3 tools/debug_truth/evaluate_n10_acceptance.py ...` 对 #460 隔离评估副本和外部重分析报告复放：13/13 当前范围内必需指标 `PASS`；fault exit 指标 `INSUFFICIENT` 且 `required=false`；配置为 draft，overall 仍 `INSUFFICIENT`。
- `PYTHONPYCACHEPREFIX=/tmp/n10-pycache python3 -m py_compile ...` 通过。
- `PYTHONPYCACHEPREFIX=/tmp/n10-pycache python3 -m unittest tools.test_n10_acceptance tools.test_n10_interval_clearance_bound tools.test_n10_tracking_clearance tools.test_n10_replan_reference -v`：51 tests passed。
- #460 原始 run archive 未改；重分析 JSON 输出于 `artifacts/reanalysis/n10-20261028-460-component-geometry/`。

## 限制与下一步

单次 #460 是当前候选版综合校准，不是重复资格或正式场景次数；未观测地图面、VINS 队列容量未知、CPU/RAM 主机容量估计方式及诊断型 hold 长度均已在报告中说明。N15 故障重复和 N16 连续 600 仿真秒运行均在 N10 冻结后。下一项 N10.5：从当前源码导出干净候选、按固定 source lock fetch/重放补丁，在新 ROS/PX4 build/install/log 目录真实构建。
