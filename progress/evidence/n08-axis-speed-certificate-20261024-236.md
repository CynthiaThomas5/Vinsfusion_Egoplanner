# N08.2z #236：曲线证书补上 EGO 逐轴速度限制

## 结论

已修正 N08 live-curve certificate，使 `speed_pass` 同时要求：

- 每个方向 derivative-control-hull 绝对值上界 ≤ EGO 逐轴速度界 `max_vel × (1 + 0.05) + 0.0001`。本 profile 为 `0.075 × 1.05 + 0.0001 = 0.07885 m/s`。
- 三维导数控制点范数上界 ≤ 既有 `0.15 m/s` 向量门。

上游 `UniformBspline::checkFeasibility` 的实现按单轴分量检查，并应用 5% feasibility tolerance 和 1e−4 m/s 数值余量；相应源码路径和 SHA-256 在 JSON 证据中。#231 的 Y 分量上界 0.08157 m/s 因此明确不通过逐轴门，即使只看向量门会通过。#231 原始证据未改写；其几何门本来也因起点 hold unknown 未通过。

## 改动与验证

- `tools/evaluate_n08_curve_certificate.py` 增加纯函数 `certify_speed_bounds`，输出 per-axis、vector 独立结果和合并 `speed_pass`，证书 schema 更新为 v2。原有 identity、freshness、raw-map 几何门保持不变，`n08_execute_authorized` 仍固定 false。
- `config/components/mapping/n08_low_speed_vector_cap.json` 的 qualification 描述现在同时列出逐轴和向量门；规划数值和容差未变。
- 新增 `tools/test_n08_curve_certificate.py`，覆盖逐轴失败而向量通过、两门通过、向量门单独失败及非法 shape fail-closed。
- `python3 -m unittest tools.test_n08_curve_certificate tools.test_n08_compute_only`：7 tests passed。AST 语法、`python3 tools/project_status.py`、`git diff --check` 和 JSON parse passed。`py_compile` 因不能写入已有受保护的 `tools/__pycache__` 失败；测试 import 和 AST parse 均通过。

本项仅修复诊断证书，不改变 planner/controller/health/N05/N06 阈值，不运行 SITL、compute-only、XY 或制动测量。N08 仍 `in_progress`。变更记录：[change](../changes/2026-10-24-236-n08-axis-speed-certificate.md)；机器证据：[JSON](n08-axis-speed-certificate-20261024-236.json)。
