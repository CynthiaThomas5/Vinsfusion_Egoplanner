# #386 N10 到达评估器兼容修复

对话摘要：[2026-10-27-386](../../collaboration/dialogues/2026-10-27-386-n10-arrival-evaluator-compatibility.md)。

## 变更

- `tools/debug_truth/evaluate_arrival.py` 的只读报告增加固定 ground SE(3) 旋转／平移、yaw 偏移和最小真值位置误差，供校准后处理器使用。
- 将 #385 使用的评估器原字节保存到 `artifacts/n10-prepared/n10-20261027-385-arrival-dwell4-retry/evaluate_arrival-frozen-v1.py`；SHA-256 为 `f15e952ca8d5b4f606b142317317d4cddb5d41249b259d86e5ceaf6538ad8d19`。
- 新建 `artifacts/runs/n10-20261027-385-arrival-dwell4-retry/n10_calibration_postrun_v2.py`，读取新的 sim-time report 并写入独立的 `n10-calibration-evaluation-simtime-v2.json`。原报告和失败日志不覆盖。
- 归档 #384 无飞行准备失败、#385 到达驻留诊断和本兼容修复报告；CURRENT 与里程碑仍将 N10 标为 `in_progress`。

## 验证

- `python3 -B - <<'PY' ... compile(...) ... PY`：到达评估器和 post-run analyzer 内存语法编译通过。
- `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest tools.test_arrival_evaluator -v`：6/6 通过。
- `python3 -B tools/debug_truth/evaluate_arrival.py artifacts/runs/n10-20261027-385-arrival-dwell4-retry --output arrival-evaluation-simtime-v2.json`：独立到达 PASS，联合窗口 3.320 sim s，合同要求 3.000 sim s。
- `python3 -B artifacts/runs/n10-20261027-385-arrival-dwell4-retry/n10_calibration_postrun_v2.py artifacts/runs/n10-20261027-385-arrival-dwell4-retry`：分析完成，输出 `n10-calibration-evaluation-simtime-v2.json`。

## 局限与下一步

#385 原始 driver 的退出码仍记录为 1，因为当时冻结的离线 analyzer 读取不存在的 `ground_rotation`；#386 的 post-run 复算不改写历史退出码。#385 仍只是单次诊断；动态障碍轨迹与箱体的坐标假设／零净距结果未能证明绕行，全机采样净空也不是连续动力学证明。下一子项 #387 只读核对该 run 的真实坐标变换与障碍轨迹几何，再继续 N10.3 的净空、N15 故障与 N16 负载支持缺口。
